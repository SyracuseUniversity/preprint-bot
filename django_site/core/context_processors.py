"""
Custom context processor that injects commonly needed values into every template.
"""

from datetime import date, timedelta


def date_helpers(request):
    """Inject today / week_ago / month_ago for quick-filter buttons."""
    today = date.today()
    return {
        "today": today.isoformat(),
        "week_ago": (today - timedelta(days=7)).isoformat(),
        "month_ago": (today - timedelta(days=30)).isoformat(),
    }
