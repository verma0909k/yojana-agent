"""Calendar (.ics) reminder file generator for scheme application deadlines."""

from datetime import datetime, timedelta
from pathlib import Path
from icalendar import Calendar, Event
from yojanaagent.shared.config import OUTPUT_DIR
from yojanaagent.shared.schemas import MatchResult


def create_scheme_reminder_ics(match: MatchResult, days_ahead: int = 14) -> Path:
    """Generates an .ics calendar file to remind citizen of scheme application deadlines."""
    cal = Calendar()
    cal.add('prodid', '-//YojanaAgent//Government Scheme Reminder//EN')
    cal.add('version', '2.0')

    event = Event()
    event.add('summary', f"Deadline Reminder: Apply for {match.scheme_name}")
    event.add('description', f"Apply via official portal: {match.official_url}\nDocuments needed: {', '.join(match.documents_required)}")

    target_date = datetime.now() + timedelta(days=days_ahead)
    event.add('dtstart', target_date)
    event.add('dtend', target_date + timedelta(hours=1))

    cal.add_component(event)

    output_ics = OUTPUT_DIR / f"Reminder_{match.scheme_id}.ics"
    with open(output_ics, 'wb') as f:
        f.write(cal.to_ical())

    return output_ics
