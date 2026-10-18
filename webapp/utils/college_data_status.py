"""Derive per-college seat-data availability from scraper health.

A college is **stale** (banner / hide live seat counts) when:

1. An admin has turned off ``data_available``, or
2. There is a scraper and no successful scrape in the last N hours
   (default 24), or
3. The last two consecutive completed scraper_logs (ordered by
   ``started_at``, excluding ``running`` and ``orphaned by restart``)
   are both error or 0-course partial.

Checkout and Plus/Pro plan CTAs use only rules 1 and 2
(``checkout_blocked``). Rule 3 must not block billing — a recent
success with two later errors still shows the banner but allows
checkout.

A single error or 0-course partial does not flag the school. Colleges
with no scraper row are left ``ok`` so brand-new schools are not
flagged before their first run. Inactive / dropped colleges
(``is_active=false``) stay ``ok`` with checkout allowed so leftover
profiles (e.g. Brown, UF) never see the banner or a pricing pause.
Notification sending is not affected.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Literal, Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models.college import College
from models.scraper import Scraper
from models.scraper_log import ScraperLog

DataStatus = Literal["ok", "stale"]
FAILED_EMPTY_OUTCOMES = frozenset({"error", "partial"})
DEFAULT_STALE_AFTER_HOURS = 24.0
CONSECUTIVE_FAILED_EMPTY_TO_STALE = 2
ORPHANED_BY_RESTART_MESSAGE = "orphaned by restart"


@dataclass(frozen=True)
class CollegeDataStatus:
    data_status: DataStatus
    last_updated_at: Optional[datetime]
    checkout_blocked: bool = False


@dataclass(frozen=True)
class _CompletedLog:
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


def is_failed_empty_run(outcome: Optional[str], courses_created: int = 0) -> bool:
    """True for error or 0-course partial runs."""
    return outcome in FAILED_EMPTY_OUTCOMES and (courses_created or 0) == 0


def _two_consecutive_failed_empty(
    recent_runs: Sequence[tuple[Optional[str], int]],
) -> bool:
    """Rule 3: last two completed runs (newest first) are both failed-empty."""
    if len(recent_runs) < CONSECUTIVE_FAILED_EMPTY_TO_STALE:
        return False
    first, second = recent_runs[0], recent_runs[1]
    return is_failed_empty_run(*first) and is_failed_empty_run(*second)


def derive_college_data_status(
    *,
    data_available: bool = True,
    has_scraper: bool = False,
    last_success_at: Optional[datetime] = None,
    recent_runs: Optional[Sequence[tuple[Optional[str], int]]] = None,
    now: Optional[datetime] = None,
    stale_after_hours: Optional[float] = None,
    is_active: bool = True,
) -> CollegeDataStatus:
    """Pure derivation used by the API and tests.

    ``recent_runs`` is newest-first by ``started_at``, each item
    ``(outcome, courses_created)``. ``last_updated_at`` is the last
    successful scrape time (if any), even when the resulting status is
    stale.

    ``checkout_blocked`` follows only the admin flag and the 24h
    no-success window. Two consecutive failed-empty runs set
    ``data_status`` to stale without blocking checkout.

    Inactive colleges always return ``ok`` / not checkout-blocked,
    regardless of scraper health or the admin availability flag.
    """
    now_utc = _as_utc(now) or datetime.now(timezone.utc)
    last_success = _as_utc(last_success_at)
    if not is_active:
        return CollegeDataStatus(
            data_status="ok",
            last_updated_at=last_success,
            checkout_blocked=False,
        )
    window_hours = (
        DEFAULT_STALE_AFTER_HOURS
        if stale_after_hours is None
        else float(stale_after_hours)
    )
    threshold = now_utc - timedelta(hours=window_hours)
    runs = list(recent_runs or [])

    stale = False
    checkout_blocked = False
    if not data_available:
        stale = True
        checkout_blocked = True
    elif has_scraper:
        if last_success is None or last_success < threshold:
            stale = True
            checkout_blocked = True
        elif _two_consecutive_failed_empty(runs):
            stale = True

    return CollegeDataStatus(
        data_status="stale" if stale else "ok",
        last_updated_at=last_success,
        checkout_blocked=checkout_blocked,
    )


def _recent_completed_logs_by_college(
    db: Session, college_ids: list[int]
) -> dict[int, list[_CompletedLog]]:
    """Return up to the last two completed logs per college.

    Logs are ordered by ``started_at`` descending. ``running`` rows and
    rows marked ``orphaned by restart`` are excluded.
    """
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
            ScraperLog.error_message.is_distinct_from(ORPHANED_BY_RESTART_MESSAGE),
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
        )
        .where(ranked.c.rn <= CONSECUTIVE_FAILED_EMPTY_TO_STALE)
        .order_by(ranked.c.college_id, ranked.c.rn)
    ).all()

    recent: dict[int, list[_CompletedLog]] = {}
    for row in rows:
        recent.setdefault(row.college_id, []).append(
            _CompletedLog(
                outcome=row.outcome,
                courses_created=row.courses_created or 0,
                completed_at=row.completed_at,
                started_at=row.started_at,
            )
        )
    return recent


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
    recent_logs = _recent_completed_logs_by_college(db, college_ids)

    result: dict[int, CollegeDataStatus] = {}
    for college in college_list:
        scraper = scrapers.get(college.id)
        logs = recent_logs.get(college.id, [])
        last_success = scraper.last_success_at if scraper is not None else None
        result[college.id] = derive_college_data_status(
            data_available=bool(getattr(college, "data_available", True)),
            has_scraper=scraper is not None,
            last_success_at=last_success,
            recent_runs=[(log.outcome, log.courses_created) for log in logs],
            now=now_utc,
            stale_after_hours=window_hours,
            is_active=bool(getattr(college, "is_active", True)),
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
            "checkout_blocked": status.checkout_blocked,
        }
    )


def apply_data_status_map(
    colleges: Iterable[College], status_map: dict[int, CollegeDataStatus]
):
    return [
        apply_data_status(
            college,
            status_map.get(
                college.id,
                CollegeDataStatus(
                    data_status="ok",
                    last_updated_at=None,
                    checkout_blocked=False,
                ),
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
        item["checkoutBlocked"] = status.checkout_blocked
