"""Notification API routes"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from datetime import datetime, timedelta

from ...db.session import get_db
from ...models.notification_log import NotificationLog

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("/trends")
async def get_notification_trends(db: AsyncSession = Depends(get_db)):
    """Get notification trends for the last 30 days"""
    try:
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        # Daily notification counts
        trends_query = text(
            """
            SELECT
                DATE(sent_at) as date,
                COUNT(*) as count
            FROM notification_logs
            WHERE sent_at >= :thirty_days_ago
            GROUP BY DATE(sent_at)
            ORDER BY DATE(sent_at)
            """
        )

        result = await db.execute(trends_query, {"thirty_days_ago": thirty_days_ago})
        rows = result.fetchall()

        trends = [
            {
                "date": row.date.isoformat() if row.date else None,
                "count": row.count,
            }
            for row in rows
        ]

        return {
            "success": True,
            "data": trends,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch notification trends: {str(e)}"
        )
