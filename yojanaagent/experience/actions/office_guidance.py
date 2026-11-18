"""Nearest Common Service Center (CSC) and Gram Panchayat / District office guidance."""

from typing import Any
from yojanaagent.shared.schemas import CitizenProfile


def get_csc_office_guidance(profile: CitizenProfile) -> dict[str, Any]:
    """Provides specific physical office submission guidance based on state and district."""
    state = profile.state.value if profile.state.known else "your state"
    district = profile.district.value if profile.district.known else "your district"
    is_rural = profile.is_rural.value if profile.is_rural.known else True

    primary_office = "Gram Panchayat / Village Secretariat & Nearest CSC Digital Seva Kendra" if is_rural else "Tehsil Office / Municipal Corporation / CSC Seva Kendra"

    return {
        "primary_office": primary_office,
        "location": f"{district}, {state}",
        "csc_locator_url": "https://locator.csccloud.in",
        "instructions": (
            f"If applying offline, visit the nearest {primary_office} in {district}. "
            "Carry original Aadhaar card, bank passbook, and land/income records for biometric e-KYC verification."
        )
    }
