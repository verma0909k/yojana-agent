"""Pre-filled Application PDF Generator using ReportLab."""

from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from shared.config import OUTPUT_DIR
from shared.schemas import CitizenProfile, MatchResult


def generate_application_pdf(profile: CitizenProfile, match: MatchResult) -> Path:
    """Generates a downloadable pre-filled application PDF for an eligible scheme."""
    output_pdf = OUTPUT_DIR / f"Application_{match.scheme_id}.pdf"

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

    c.setFont("Helvetica", 11)
    y = height - 155
    known_data = [
        ("Applicant Age", f"{profile.age.value} Years" if profile.age.known else "N/A"),
        ("Gender", str(profile.gender.value).capitalize() if profile.gender.known else "N/A"),
        ("Social Category", str(profile.category.value).upper() if profile.category.known else "N/A"),
        ("Occupation", str(profile.occupation.value).replace('_', ' ').capitalize() if profile.occupation.known else "N/A"),
        ("State / District", f"{profile.state.value or 'N/A'}, {profile.district.value or 'N/A'}"),
        ("Annual Income", f"Rs {profile.annual_income.value:,}" if profile.annual_income.known else "N/A"),
        ("BPL Status", "Yes (Verified)" if profile.is_bpl.known and profile.is_bpl.value else "No"),
        ("Aadhaar Available", "Yes (Verified)" if profile.has_aadhaar.known and profile.has_aadhaar.value else "Pending"),
    ]

    for label, val in known_data:
        c.drawString(60, y, f"• {label}:")
        c.drawString(240, y, val)
        y -= 22

    # Required Documents Checklist
    y -= 15
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Mandatory Document Checklist for Submission:")
    y -= 25
    c.setFont("Helvetica", 11)
    for doc in match.documents_required:
        c.drawString(60, y, f"[  ]  {doc}")
        y -= 20

    # Submission footer
    y -= 20
    c.line(50, y, width - 50, y)
    y -= 25
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(50, y, "Generated autonomously by YojanaAgent - verified against official criteria.")

    c.save()
    return output_pdf
