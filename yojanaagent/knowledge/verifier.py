"""Verifier Agent: Checks official scheme portal status and document consistency."""

from typing import Any
import requests
from yojanaagent.shared.schemas import CitizenProfile, MatchResult, Source


class Verifier:
    """Performs live portal reachability checks and profile-document consistency validation."""

    def __init__(self, timeout: float = 3.0):
        self.timeout = timeout

    def check_portal(self, url: str) -> dict[str, Any]:
        """Checks if the official government portal is live and reachable."""
        try:
            resp = requests.head(url, timeout=self.timeout, allow_redirects=True)
            is_live = resp.status_code < 400
            return {
                "url": url,
                "is_live": is_live,
                "status_code": resp.status_code,
                "message": "Portal active and verified" if is_live else f"Portal returned HTTP {resp.status_code}",
            }
        except Exception as e:
            return {
                "url": url,
                "is_live": False,
                "status_code": None,
                "message": f"Verification check timed out or unreachable ({str(e)})",
            }

    def verify_document_consistency(self, profile: CitizenProfile) -> list[str]:
        """Detects contradictions between document-extracted facts and user statements."""
        inconsistencies = []

        # Example check: Age boundary sanity
        if profile.age.known and (profile.age.value < 0 or profile.age.value > 120):
            inconsistencies.append(f"Invalid age recorded: {profile.age.value}")

        # Example check: Student occupation vs high age
        if profile.occupation.known and profile.age.known:
            if profile.occupation.value == "student" and profile.age.value > 45:
                inconsistencies.append("Age is above 45 with student occupation - verify student enrollment proof.")

        # Check for low-confidence document facts
        low_conf = profile.low_confidence_fields(threshold=0.6)
        if low_conf:
            inconsistencies.append(f"Low confidence document extractions detected for: {', '.join(low_conf)}")

        return inconsistencies
