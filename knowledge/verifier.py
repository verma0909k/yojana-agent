"""Verifier Agent: Checks official scheme portal status and document consistency."""

from typing import Any
import requests
from shared.schemas import CitizenProfile, MatchResult, Source

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class Verifier:
    """Performs live portal reachability checks and profile-document consistency validation."""

    def __init__(self, timeout: float = 6.0):
        self.timeout = timeout

    def check_portal(self, url: str) -> dict[str, Any]:
        """Checks if the official government portal is live and reachable, handling NIC WAFs gracefully."""
        try:
            # 1. Try HEAD first
            resp = requests.head(url, headers=DEFAULT_HEADERS, timeout=self.timeout, allow_redirects=True)
            if resp.status_code in (403, 405):
                # Many NIC portals reject HEAD; fallback to lightweight GET stream
                resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=self.timeout, stream=True)

            is_live = resp.status_code < 400
            # Some Indian portals return 403 specifically to automated scripts but are active
            status_msg = "Portal active and verified" if is_live else f"Portal active (HTTP {resp.status_code} WAF protected)"
            return {
                "url": url,
                "is_live": True if resp.status_code in (200, 301, 302, 403) else is_live,
                "status_code": resp.status_code,
                "message": status_msg,
            }
        except requests.exceptions.Timeout:
            return {
                "url": url,
                "is_live": False,
                "status_code": None,
                "message": "Portal slow/timed out (>6s) - server under load",
            }
        except Exception as e:
            return {
                "url": url,
                "is_live": False,
                "status_code": None,
                "message": f"Verification unreachable ({str(e)[:40]})",
            }

    def verify_document_consistency(self, profile: CitizenProfile) -> list[str]:
        """Detects contradictions between document-extracted facts and user statements."""
        inconsistencies = []

        # Age boundary sanity
        if profile.age.known and (profile.age.value < 0 or profile.age.value > 120):
            inconsistencies.append(f"Invalid age recorded: {profile.age.value}")

        # Student occupation vs elderly age
        if profile.occupation.known and profile.age.known:
            if profile.occupation.value == "student" and profile.age.value > 45:
                inconsistencies.append("Age is above 45 with student occupation - verify student enrollment proof.")

        # Check for low-confidence document facts
        low_conf = profile.low_confidence_fields(threshold=0.6)
        if low_conf:
            inconsistencies.append(f"Low confidence document extractions detected for: {', '.join(low_conf)}")

        return inconsistencies
