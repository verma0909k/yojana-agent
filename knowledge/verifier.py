"""Verifier Agent: Checks official scheme portal status and document consistency."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import time
from typing import Any, Optional
import requests
from shared.schemas import CitizenProfile, MatchResult, Source

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def get_portal_badge_text(check: Optional[dict[str, Any]]) -> str:
    """Returns portal status badge text: 'Reachable, checked HH:MM' / 'Could not verify, open manually' / 'Not checked'."""
    if not check:
        return "Not checked"
    status = check.get("status")
    checked_at = check.get("checked_at")
    if status == "reachable":
        return f"Reachable, checked {checked_at}" if checked_at else "Reachable"
    elif status in ("blocked", "unreachable", "offline"):
        return "Could not verify, open manually"
    return "Not checked"


class Verifier:
    """Performs live portal reachability checks and profile-document consistency validation."""

    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}

    def check_portal(self, url: str) -> dict[str, Any]:
        """Checks if the official government portal is live and reachable, handling NIC WAFs gracefully."""
        now_ts = time.time()
        if url in self._cache:
            cached_ts, cached_result = self._cache[url]
            if now_ts - cached_ts < 3600:
                return cached_result

        checked_at = datetime.now().strftime("%H:%M")
        http_code: Optional[int] = None
        status = "offline"

        try:
            resp = None
            try:
                resp = requests.head(url, headers=DEFAULT_HEADERS, timeout=self.timeout, allow_redirects=True)
                if resp.status_code in (403, 405) or resp.status_code >= 400:
                    try:
                        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=self.timeout, stream=True)
                    except Exception:
                        pass
            except (requests.exceptions.RequestException, Exception):
                # Fallback to GET
                resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=self.timeout, stream=True)

            if resp is not None:
                http_code = resp.status_code
                if 200 <= http_code < 400:
                    status = "reachable"
                elif http_code in (403, 405):
                    status = "blocked"
                else:
                    status = "unreachable"
            else:
                status = "unreachable"

        except requests.exceptions.Timeout:
            status = "unreachable"
            http_code = None
        except (requests.exceptions.ConnectionError, requests.exceptions.SSLError):
            status = "offline"
            http_code = None
        except Exception:
            status = "offline"
            http_code = None

        result = {
            "url": url,
            "status": status,
            "http_code": http_code,
            "checked_at": checked_at,
            "is_live": status == "reachable",
            "message": f"Status: {status} (HTTP {http_code})" if http_code else f"Status: {status}",
        }
        self._cache[url] = (now_ts, result)
        return result

    def check_portals_concurrently(self, urls: list[str], max_urls: int = 5) -> dict[str, dict[str, Any]]:
        """Check up to top 5 schemes concurrently."""
        target_urls = urls[:max_urls]
        if not target_urls:
            return {}

        results = {}
        with ThreadPoolExecutor(max_workers=min(len(target_urls), 5)) as executor:
            future_to_url = {executor.submit(self.check_portal, u): u for u in target_urls}
            for future in future_to_url:
                u = future_to_url[future]
                try:
                    results[u] = future.result()
                except Exception:
                    results[u] = {
                        "url": u,
                        "status": "offline",
                        "http_code": None,
                        "checked_at": datetime.now().strftime("%H:%M"),
                        "is_live": False,
                        "message": "Status: offline",
                    }
        return results

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
