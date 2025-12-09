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
    Get notification trends for the past week for the current user.

    Returns notifications grouped by day of week (Mon-Sun) with course names.
    Only includes notifications sent to the current user.
    """
    try:
        # Get the start of the week (last Monday) and end (next Sunday)
        now = datetime.utcnow()
        # Calculate days since last Monday (Monday = 0)
        days_since_monday = now.weekday()
        week_start = (now - timedelta(days=days_since_monday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        week_end = week_start + timedelta(days=7)

        # Query notification logs for the current user in the past week
        # Uses user_id directly for efficient lookup without JOIN
        trends_query = text(
            """
            SELECT
                EXTRACT(DOW FROM nl.sent_at) as day_of_week,
                nl.message,
                nl.notification_type
            FROM notification_logs nl
            WHERE nl.user_id = CAST(:user_id AS UUID)
              AND nl.sent_at >= :week_start
              AND nl.sent_at < :week_end
              AND nl.status = 'sent'
            ORDER BY nl.sent_at
            """
        )

        result = db.execute(
            trends_query,
            {
                "user_id": str(user.id),
                "week_start": week_start,
                "week_end": week_end,
            },
        )
        rows = result.fetchall()

        # Initialize trend data for each day
        # DOW: 0 = Sunday, 1 = Monday, ... 6 = Saturday
        # Frontend expects: Mon, Tue, Wed, Thu, Fri, Sat, Sun
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        day_dow_map = {
            1: 0,  # Monday -> index 0
            2: 1,  # Tuesday -> index 1
            3: 2,  # Wednesday -> index 2
            4: 3,  # Thursday -> index 3
            5: 4,  # Friday -> index 4
            6: 5,  # Saturday -> index 5
            0: 6,  # Sunday -> index 6
        }

        trends = [
            {"day": day_name, "notifications": 0, "courses": []}
            for day_name in day_names
        ]

        # Track unique courses per day to avoid duplicates (since we log both email and SMS)
        day_courses_set = [set() for _ in range(7)]

        for row in rows:
            # Convert DOW from SQL to our index
            dow = int(row.day_of_week)
            day_index = day_dow_map.get(dow, 0)

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
