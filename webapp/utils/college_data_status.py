"""Derive per-college seat-data availability from scraper health.

A college is stale when:

1. An admin has turned off ``data_available``, or
2. There is a scraper and no successful scrape in the last N hours
   (default 24), or
3. The latest completed scraper_log is error/partial with 0 courses.

Colleges with no scraper row are left ``ok`` so brand-new schools are not
flagged before their first run. Checkout and the public UI both use this
signal; notification sending is not affected.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Literal, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models.college import College
from models.scraper import Scraper
from models.scraper_log import ScraperLog

DataStatus = Literal["ok", "stale"]
FAILED_EMPTY_OUTCOMES = frozenset({"error", "partial"})
DEFAULT_STALE_AFTER_HOURS = 24.0


@dataclass(frozen=True)
class CollegeDataStatus:
    data_status: DataStatus
    last_updated_at: Optional[datetime]


@dataclass(frozen=True)
class _LatestLog:
    outcome: Optional[str]
    courses_created: int
    completed_at: Optional[datetime]
    started_at: Optional[datetime]


def _as_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def get_stale_after_hours() -> float:
    """Return the configured stale window, falling back to 24 hours."""
    try:
        from config import settings

        hours = getattr(settings, "COLLEGE_DATA_STALE_HOURS", None)
        if hours is None:
            return DEFAULT_STALE_AFTER_HOURS
        return float(hours)
    except Exception:
        return DEFAULT_STALE_AFTER_HOURS


def derive_college_data_status(
    *,
    data_available: bool = True,
    has_scraper: bool = False,
    last_success_at: Optional[datetime] = None,
    latest_outcome: Optional[str] = None,
    latest_courses_created: int = 0,
    now: Optional[datetime] = None,
    stale_after_hours: Optional[float] = None,
) -> CollegeDataStatus:
    """Pure derivation used by the API and tests.

    ``last_updated_at`` is the last successful scrape time (if any), even
    when the resulting status is stale.
    """
    now_utc = _as_utc(now) or datetime.now(timezone.utc)
    last_success = _as_utc(last_success_at)
    window_hours = (
        DEFAULT_STALE_AFTER_HOURS
        if stale_after_hours is None
        else float(stale_after_hours)
    )
    threshold = now_utc - timedelta(hours=window_hours)

    stale = False
    if not data_available:
        stale = True
    elif has_scraper:
        if last_success is None or last_success < threshold:
            stale = True
        elif (
            latest_outcome in FAILED_EMPTY_OUTCOMES
            and (latest_courses_created or 0) == 0
        ):
            stale = True

    return CollegeDataStatus(
        data_status="stale" if stale else "ok",
        last_updated_at=last_success,
    )


def _latest_completed_logs_by_college(
    db: Session, college_ids: list[int]
) -> dict[int, _LatestLog]:
    if not college_ids:
        return {}

    ranked = (
        select(
            Scraper.college_id.label("college_id"),
            ScraperLog.outcome,
            ScraperLog.courses_created,
            ScraperLog.completed_at,
            ScraperLog.started_at,
            func.row_number()
            .over(
                partition_by=Scraper.college_id,
                order_by=ScraperLog.started_at.desc(),
            )
            .label("rn"),
        )
        .select_from(ScraperLog)
        .join(Scraper, ScraperLog.scraper_id == Scraper.id)
        .where(
            Scraper.college_id.in_(college_ids),
            ScraperLog.outcome != "running",
        )
        .subquery()
    )

    rows = db.execute(
        select(
            ranked.c.college_id,
            ranked.c.outcome,
            ranked.c.courses_created,
            ranked.c.completed_at,
            ranked.c.started_at,
        ).where(ranked.c.rn == 1)
    ).all()

    latest: dict[int, _LatestLog] = {}
    for row in rows:
        latest[row.college_id] = _LatestLog(
            outcome=row.outcome,
            courses_created=row.courses_created or 0,
            completed_at=row.completed_at,
            started_at=row.started_at,
        )
    return latest


def get_colleges_data_status(
    db: Session,
    colleges: Iterable[College],
    *,
    now: Optional[datetime] = None,
    stale_after_hours: Optional[float] = None,
) -> dict[int, CollegeDataStatus]:
    """Batch-compute data status for the given colleges."""
    college_list = [c for c in colleges if c is not None and c.id is not None]
    if not college_list:
        return {}

    college_ids = [c.id for c in college_list]
    window_hours = (
        get_stale_after_hours() if stale_after_hours is None else stale_after_hours
    )
    now_utc = _as_utc(now) or datetime.now(timezone.utc)

    scrapers = {
        row.college_id: row
        for row in db.execute(
            select(Scraper).where(Scraper.college_id.in_(college_ids))
        ).scalars()
    }
    latest_logs = _latest_completed_logs_by_college(db, college_ids)

    result: dict[int, CollegeDataStatus] = {}
    for college in college_list:
        scraper = scrapers.get(college.id)
        latest = latest_logs.get(college.id)
        last_success = scraper.last_success_at if scraper is not None else None
        result[college.id] = derive_college_data_status(
            data_available=bool(getattr(college, "data_available", True)),
            has_scraper=scraper is not None,
            last_success_at=last_success,
            latest_outcome=latest.outcome if latest is not None else None,
            latest_courses_created=(
                latest.courses_created if latest is not None else 0
            ),
            now=now_utc,
            stale_after_hours=window_hours,
        )
    return result


def get_college_data_status(
    db: Session,
    college: College,
    *,
    now: Optional[datetime] = None,
    stale_after_hours: Optional[float] = None,
) -> CollegeDataStatus:
    """Compute data status for a single college."""
    return get_colleges_data_status(
        db, [college], now=now, stale_after_hours=stale_after_hours
    )[college.id]


def apply_data_status(college, status: CollegeDataStatus):
    """Return a CollegeResponse with computed status fields attached."""
    from schemas.college import CollegeResponse

    response = CollegeResponse.model_validate(college)
    return response.model_copy(
        update={
            "data_status": status.data_status,
            "last_updated_at": status.last_updated_at,
        }
    )


def apply_data_status_map(
    colleges: Iterable[College], status_map: dict[int, CollegeDataStatus]
):
    return [
        apply_data_status(
            college,
            status_map.get(
                college.id, CollegeDataStatus(data_status="ok", last_updated_at=None)
            ),
        )
        for college in colleges
    ]


def overlay_data_status_on_college_dicts(db: Session, payloads: list[dict]) -> None:
    """Refresh dataStatus/lastUpdatedAt on cached college JSON dicts in place."""
    college_ids = [
        item.get("id") for item in payloads if isinstance(item, dict) and item.get("id")
    ]
    if not college_ids:
        return

    colleges = (
        db.execute(select(College).where(College.id.in_(college_ids))).scalars().all()
    )
    status_map = get_colleges_data_status(db, colleges)
    for item in payloads:
        if not isinstance(item, dict):
            continue
        status = status_map.get(item.get("id"))
        if status is None:
            continue
        item["dataStatus"] = status.data_status
        item["lastUpdatedAt"] = (
            status.last_updated_at.isoformat() if status.last_updated_at else None
        )
