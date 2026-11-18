"""Tests for Phase 6: ApplicationAgent, ApplicationTracker, and End-to-End Application Workflow."""

import os
import pathlib
import pytest

from brain.application_agent import ApplicationAgent
from experience.dashboard.application_tracker import ApplicationTracker
from experience.personas.demo_profiles import get_student_persona
from shared.schemas import (
    CitizenProfile,
    Fact,
    Occupation,
)


@pytest.fixture
def temp_tracker(tmp_path: pathlib.Path):
    db_file = tmp_path / "test_tracker.db"
    return ApplicationTracker(db_path=db_file)


def test_application_tracker_crud(temp_tracker: ApplicationTracker):
    """Verify SQLite lifecycle tracking for scheme applications."""
    # 1. Create task
    task = temp_tracker.create_task(
        citizen_id="citizen_99",
        scheme_id="pm-kisan",
        scheme_name="PM Kisan",
        documents_ready=["Aadhaar Card"],
        documents_missing=["Land Records"],
        status="DRAFT",
        official_portal_url="https://pmkisan.gov.in",
        notes="Initial draft created"
    )
    task_id = task["task_id"]
    assert task_id.startswith("app_")
    assert task["status"] == "DRAFT"
    assert task["documents_ready"] == ["Aadhaar Card"]

    # 2. Get task
    fetched = temp_tracker.get_task(task_id)
    assert fetched is not None
    assert fetched["scheme_name"] == "PM Kisan"

    # 3. List tasks
    citizen_tasks = temp_tracker.list_tasks(citizen_id="citizen_99")
    assert len(citizen_tasks) == 1

    # 4. Update status
    updated = temp_tracker.update_task_status(
        task_id=task_id,
        status="READY_TO_SUBMIT",
        notes="Land records uploaded"
    )
    assert updated["status"] == "READY_TO_SUBMIT"
    assert "Land records uploaded" in updated["notes"]

    # 5. Delete task
    assert temp_tracker.delete_task(task_id) is True
    assert temp_tracker.get_task(task_id) is None


def test_application_agent_document_readiness(temp_tracker: ApplicationTracker):
    """Verify document readiness analysis comparing citizen documents with scheme requirements."""
    agent = ApplicationAgent(tracker=temp_tracker)
    scheme = agent.get_scheme("pm-kisan")

    # Only Aadhaar
    readiness1 = agent.evaluate_document_readiness(scheme, available_documents=["Aadhaar Card"])
    assert readiness1["is_ready"] is False
    assert "Aadhaar Card" in readiness1["ready"]
    assert len(readiness1["missing"]) >= 1

    # All documents
    readiness2 = agent.evaluate_document_readiness(
        scheme,
        available_documents=["Aadhaar Card", "Land ownership document / Khasra-Khatauni", "Bank account passbook"]
    )
    assert readiness2["is_ready"] is True
    assert len(readiness2["missing"]) == 0
    assert readiness2["readiness_pct"] == 100.0


def test_application_agent_package_generation(temp_tracker: ApplicationTracker):
    """Verify end-to-end application package generation with PDF prefill and tracker record."""
    agent = ApplicationAgent(tracker=temp_tracker)
    student = get_student_persona()

    package = agent.prepare_application_package(
        scheme_id="nsp-national-scholarship-portal",
        profile=student,
        available_documents=["Aadhaar Card", "Bank Account Details", "Student ID Card"],
        citizen_id="student_ananya_01",
        generate_pdf=True,
    )

    assert package["scheme_id"] == "nsp-national-scholarship-portal"
    assert package["task_id"].startswith("app_")
    assert package["pdf_path"] is not None
    assert os.path.exists(package["pdf_path"])
    assert "https://scholarships.gov.in" in package["submission_url"]
    assert "Review the generated pre-filled application form" in package["action_guidance"]

    # Verify task in tracker
    stored_task = temp_tracker.get_task(package["task_id"])
    assert stored_task is not None
    assert stored_task["citizen_id"] == "student_ananya_01"

    # Cleanup generated PDF
    pathlib.Path(package["pdf_path"]).unlink(missing_ok=True)


def test_application_agent_lifecycle_progression(temp_tracker: ApplicationTracker):
    """Verify transitioning application status through complete lifecycle."""
    agent = ApplicationAgent(tracker=temp_tracker)
    student = get_student_persona()

    pkg = agent.prepare_application_package(
        scheme_id="nsp-national-scholarship-portal",
        profile=student,
        citizen_id="student_lifecycle",
        generate_pdf=False,
    )
    task_id = pkg["task_id"]

    # Progress to READY_TO_SUBMIT
    t1 = agent.update_status(task_id, new_status="READY_TO_SUBMIT", notes="Documents verified")
    assert t1["status"] == "READY_TO_SUBMIT"

    # Progress to SUBMITTED
    t2 = agent.update_status(task_id, new_status="SUBMITTED", notes="Submitted at scholarships.gov.in, ref: NSP2026-9876")
    assert t2["status"] == "SUBMITTED"
    assert "NSP2026-9876" in t2["notes"]
