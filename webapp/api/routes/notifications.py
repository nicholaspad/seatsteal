"""Notification API routes"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta

from db.session import get_db
from models.user import Profile
from api.middleware.auth import require_auth

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("/trends")
async def get_notification_trends(
    db: Session = Depends(get_db),
    user: Profile = Depends(require_auth),
):
    """
    Get notification trends for the past 7 days for the current user.

    Returns notifications grouped by date with course names.
    Only includes notifications sent to the current user.
    Uses a rolling 7-day window (last 7 days from today).
    """
    try:
        # Get the last 7 days (rolling window)
        now = datetime.utcnow()
        # Start from 6 days ago at midnight to include today as the 7th day
        start_date = (now - timedelta(days=6)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end_date = now

        # Query notification logs for the current user in the past 7 days
        # Uses user_id directly for efficient lookup without JOIN
        trends_query = text(
            """
            SELECT
                DATE(nl.sent_at) as notification_date,
                nl.message,
                nl.notification_type
            FROM notification_logs nl
            WHERE nl.user_id = CAST(:user_id AS UUID)
              AND nl.sent_at >= :start_date
              AND nl.sent_at <= :end_date
              AND nl.status = 'sent'
            ORDER BY nl.sent_at
            """
        )

        result = db.execute(
            trends_query,
            {
                "user_id": str(user.id),
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        rows = result.fetchall()

        # Initialize trend data for each of the last 7 days
        trends = []
        date_to_index = {}

        for i in range(7):
            date = (start_date + timedelta(days=i)).date()
            date_to_index[date] = i
            trends.append(
                {
                    "date": date.isoformat(),  # ISO format: YYYY-MM-DD
                    "notifications": 0,
                    "courses": [],
                }
            )

        # Track unique courses per day to avoid duplicates (since we log both email and SMS)
        day_courses_set = [set() for _ in range(7)]

        for row in rows:
            notification_date = row.notification_date
            day_index = date_to_index.get(notification_date)

            if day_index is None:
                continue  # Skip if date is outside our range

            # Parse course name from message (format: "Course Title (COURSE_CODE) Section at College is OPEN!")
            message = row.message or ""
            # Extract just the course title/code part before " at "
            course_part = message.split(" at ")[0] if " at " in message else message
            # Remove " is OPEN!" if present
            course_part = course_part.replace(" is OPEN!", "").strip()

            if course_part and course_part not in day_courses_set[day_index]:
                day_courses_set[day_index].add(course_part)
                trends[day_index]["courses"].append(course_part)

            # Count all notifications (email + SMS separately)
            trends[day_index]["notifications"] += 1

        return {
            "success": True,
            "data": trends,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch notification trends: {str(e)}"
        )
