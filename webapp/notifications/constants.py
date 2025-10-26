"""
Notification cadence constants

These constants define how often different user tiers receive notifications:
- FREE_TIER_MINUTES: Free tier users get notified every 30 minutes (at :00 and :30)
- PLUS_TIER_MINUTES: Plus tier users get notified every 5 minutes
- PRO_TIER_MINUTES: Pro tier users get notified every minute (always)
"""

# Notification cadence in minutes
NOTIFICATION_CADENCE = {
    "FREE_TIER_MINUTES": 30,
    "PLUS_TIER_MINUTES": 5,
    "PRO_TIER_MINUTES": 1,
}

# User tier names
USER_TIERS = {
    "FREE": "free",
    "PLUS": "plus",
    "PRO": "pro",
}
