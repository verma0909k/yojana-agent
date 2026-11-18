"""OCR Intake module for document photos (Aadhaar, Ration Card, Income Certificate)."""

from pathlib import Path
from typing import Any, Optional
from PIL import Image
from yojanaagent.shared.schemas import CitizenProfile, Fact, Source


class DocumentOCR:
    """Extracts citizen demographic facts from document images."""

    def __init__(self):
        try:
            import pytesseract
            self.tesseract = pytesseract
        except ImportError:
            self.tesseract = None

    def extract_text(self, image_path: Path) -> str:
        """Extracts raw text from an image using Tesseract or PIL fallback."""
        if not self.tesseract:
            return ""
        try:
            image = Image.open(image_path)
            return self.tesseract.image_to_string(image)
        except Exception:
            return ""

    def parse_profile_from_document(self, text: str) -> dict[str, Any]:
        """Heuristic parser to extract common fields from document text."""
        extracted = {}
        text_lower = text.lower()

        # Aadhaar detection
        if "government of india" in text_lower or "aadhaar" in text_lower or "unique identification" in text_lower:
            extracted["has_aadhaar"] = True

        # Gender detection
        if "female" in text_lower or "mahila" in text_lower:
            extracted["gender"] = "female"
        elif "male" in text_lower or "purush" in text_lower:
            extracted["gender"] = "male"

        # BPL / Ration Card detection
        if "bpl" in text_lower or "antyodaya" in text_lower or "nfsa" in text_lower:
            extracted["is_bpl"] = True

        return extracted
