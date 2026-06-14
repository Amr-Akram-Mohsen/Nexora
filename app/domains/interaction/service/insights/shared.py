# app/domains/interaction/service/insights/shared.py
from datetime import datetime, timedelta, timezone

def get_start_date(time_frame: str):
    now = datetime.now(timezone.utc)
    if time_frame == "today":
        return now - timedelta(days=1)
    elif time_frame == "7_days":
        return now - timedelta(days=7)
    elif time_frame == "30_days":
        return now - timedelta(days=30)
    else: # all_time
        return None
