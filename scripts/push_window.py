"""Beijing-time publishing windows, with Friday night continuing into Saturday."""
import datetime
import sys

BEIJING = datetime.timezone(datetime.timedelta(hours=8))


def in_push_window(now):
    local = now.astimezone(BEIJING)
    weekday = local.weekday()
    clock = (local.hour, local.minute)
    return (
        weekday < 5 and ((8, 50) <= clock <= (15, 20) or clock >= (20, 50))
        or 1 <= weekday <= 5 and clock <= (2, 30)
    )


if __name__ == "__main__":
    sys.exit(0 if in_push_window(datetime.datetime.now(BEIJING)) else 1)
