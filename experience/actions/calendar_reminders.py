"""Calendar (.ics) reminder file generator for scheme application deadlines."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import uuid
from icalendar import Alarm, Calendar, Event
from shared.config import OUTPUT_DIR
from shared.schemas import MatchResult


def create_scheme_reminder_ics(match: MatchResult, days_ahead: int = 14) -> Path:
    """Generates a RFC 5545 compliant .ics calendar file to remind citizen of scheme application deadlines."""
    cal = Calendar()
    cal.add('prodid', '-//YojanaAgent//Government Scheme Reminder//EN')
    cal.add('version', '2.0')

    event = Event()
    now_utc = datetime.now(timezone.utc)

    # UID and DTSTAMP
    event.add('uid', f"{uuid.uuid4()}@yojanaagent")
    event.add('dtstamp', now_utc)

    # Deadline handling
    has_deadline = False
    target_date = now_utc + timedelta(days=days_ahead)

    if match.deadline:
        try:
            if "T" in match.deadline:
                dl_dt = datetime.fromisoformat(match.deadline)
            else:
                dl_dt = datetime.strptime(match.deadline, "%Y-%m-%d")
            if dl_dt.tzinfo is None:
                dl_dt = dl_dt.replace(tzinfo=timezone.utc)
            target_date = dl_dt
            has_deadline = True
        except Exception:
            has_deadline = False

    if has_deadline:
        event.add('summary', f"Deadline: Apply for {match.scheme_name}")
        event.add('description', f"Official deadline: {match.deadline}\nApply via: {match.official_url}\nDocuments needed: {', '.join(match.documents_required)}")

        # Alarms 7 days and 1 day before deadline
        alarm_7d = Alarm()
        alarm_7d.add('action', 'DISPLAY')
        alarm_7d.add('description', f"Application deadline for {match.scheme_name} in 7 days")
        alarm_7d.add('trigger', -timedelta(days=7))
        event.add_component(alarm_7d)

        alarm_1d = Alarm()
        alarm_1d.add('action', 'DISPLAY')
        alarm_1d.add('description', f"Application deadline for {match.scheme_name} tomorrow")
        alarm_1d.add('trigger', -timedelta(days=1))
        event.add_component(alarm_1d)
    else:
        # No deadline exists - do NOT title it Deadline Reminder or pretend a deadline exists
        event.add('summary', f"Start your application: {match.scheme_name}")
        event.add('description', f"Apply via official portal: {match.official_url}\nDocuments needed: {', '.join(match.documents_required)}")

        alarm = Alarm()
        alarm.add('action', 'DISPLAY')
        alarm.add('description', f"Reminder: Start your application for {match.scheme_name}")
        alarm.add('trigger', -timedelta(days=1))
        event.add_component(alarm)

    event.add('dtstart', target_date)
    event.add('dtend', target_date + timedelta(hours=1))

    cal.add_component(event)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_ics = OUTPUT_DIR / f"Reminder_{match.scheme_id}.ics"
    with open(output_ics, 'wb') as f:
        f.write(cal.to_ical())

    return output_ics
