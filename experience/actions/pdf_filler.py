"""Pre-filled Application PDF Generator using ReportLab."""

from pathlib import Path
import uuid
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from shared.config import CONFIDENCE_THRESHOLD, OUTPUT_DIR
from shared.schemas import CitizenProfile, Fact, MatchResult, Source


def format_fact_value(fact: Fact, formatter=None) -> str:
    """Formats a Fact tri-state value with confidence/provenance.

    Tri-state: Unknown shows 'Not provided', never 'No'.
    Shows '(from document, NN% confidence)' or '(self-reported)' based on Fact.source.
    Never prints 'Verified' unless source is DOCUMENT and confidence >= CONFIDENCE_THRESHOLD.
    """
    if not fact.known or fact.value is None:
        return "Not provided"

    raw_val = formatter(fact.value) if formatter else str(fact.value)

    if fact.source == Source.DOCUMENT:
        pct = int(round(fact.confidence * 100))
        if fact.confidence >= CONFIDENCE_THRESHOLD:
            provenance = f"(from document, {pct}% confidence, Verified)"
        else:
            provenance = f"(from document, {pct}% confidence)"
    else:
        provenance = "(self-reported)"

    return f"{raw_val} {provenance}"


def generate_application_pdf(profile: CitizenProfile, match: MatchResult) -> Path:
    """Generates a downloadable pre-filled application PDF for an eligible scheme."""
    unique_id = uuid.uuid4().hex[:8]
    output_pdf = OUTPUT_DIR / f"Application_{match.scheme_id}_{unique_id}.pdf"

    c = canvas.Canvas(str(output_pdf), pagesize=letter)
    width, height = letter

    # Header
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, height - 50, "GOVERNMENT SCHEME APPLICATION FORM")
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 75, f"Scheme: {match.scheme_name}")

    # Official Link
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 95, f"Official Portal: {match.official_url}")
    c.line(50, height - 105, width - 50, height - 105)

    # Citizen Particulars
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 130, "Citizen Particulars:")

    c.setFont("Helvetica", 9)
    y = height - 155

    known_data = [
        ("Applicant Age", format_fact_value(profile.age, lambda v: f"{v} Years")),
        ("Gender", format_fact_value(profile.gender, lambda v: str(v).capitalize())),
        ("Social Category", format_fact_value(profile.category, lambda v: str(v).upper())),
        ("Occupation", format_fact_value(profile.occupation, lambda v: str(v).replace('_', ' ').capitalize())),
        ("State", format_fact_value(profile.state)),
        ("District", format_fact_value(profile.district)),
        ("Annual Income", format_fact_value(profile.annual_income, lambda v: f"Rs {v:,}")),
        ("BPL Status", format_fact_value(profile.is_bpl, lambda v: "Yes" if v else "No")),
        ("Aadhaar Available", format_fact_value(profile.has_aadhaar, lambda v: "Yes" if v else "No")),
    ]

    for label, val in known_data:
        c.drawString(60, y, f"• {label}:")
        c.drawString(190, y, val)
        y -= 20

    # Required Documents Checklist
    y -= 15
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Mandatory Document Checklist for Submission:")
    y -= 25
    c.setFont("Helvetica", 10)
    for doc in match.documents_required:
        c.drawString(60, y, f"[  ]  {doc}")
        y -= 18

    # Submission footer
    y -= 20
    c.line(50, y, width - 50, y)
    y -= 25
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(50, y, "Generated autonomously by YojanaAgent against official criteria.")

    c.save()
    return output_pdf
