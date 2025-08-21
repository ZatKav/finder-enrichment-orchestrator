from datetime import datetime, timezone

def generate_datetime_string():
    return f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"