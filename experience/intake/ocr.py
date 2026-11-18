"""OCR & Vision Intake module for document photos (Aadhaar, Ration Card, Income Certificate, Marksheet)."""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from PIL import Image
from shared.config import GOOGLE_API_KEY
from shared.schemas import Category, CitizenProfile, Fact, Gender, Occupation, Source


class DocumentOCR:
    """Extracts citizen demographic facts from document images via Gemini Vision, Tesseract, or heuristic fallbacks."""

    def __init__(self):
        try:
            import pytesseract
            self.tesseract = pytesseract
        except ImportError:
            self.tesseract = None

    def extract_text(self, image_path: Path) -> str:
        """Extracts text using Gemini Vision if configured, then local Tesseract, else empty."""
        # 1. Try Gemini Vision if API key is present
        if GOOGLE_API_KEY:
            try:
                from google import genai
                client = genai.Client(api_key=GOOGLE_API_KEY)
                with open(image_path, "rb") as f:
                    image_bytes = f.read()
                response = client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=[
                        "Extract all text, demographic info (Name, DOB/Age, Gender, Income, Category, Document Type) from this Indian identity document:",
                        {"mime_type": "image/jpeg", "data": image_bytes}
                    ]
                )
                if response and response.text:
                    return response.text
            except Exception:
                pass

        # 2. Try local Tesseract OCR engine
        if self.tesseract:
            try:
                image = Image.open(image_path)
                text = self.tesseract.image_to_string(image)
                if text.strip():
                    return text
            except Exception:
                pass

        return ""

    def parse_profile_from_document(self, text: str, filename: str = "") -> dict[str, Any]:
        """Parses demographic fields from extracted OCR text or document filename."""
        extracted: dict[str, Any] = {}
        combined = f"{filename} {text}".lower()

        # 1. Document Type Detection: Aadhaar
        if any(w in combined for w in ["aadhaar", "uidai", "unique identification", "aadhar"]):
            extracted["has_aadhaar"] = True

        # 2. Document Type Detection: BPL / Ration Card
        if any(w in combined for w in ["ration", "bpl", "antyodaya", "nfsa", "food security"]):
            extracted["is_bpl"] = True

        # 3. Document Type Detection: Marksheet / Student
        if any(w in combined for w in ["marksheet", "grade", "cbse", "university", "college", "degree", "diploma"]):
            extracted["occupation"] = Occupation.STUDENT

        # 4. Gender detection
        if any(w in combined for w in ["female", "mahila", "woman", "daughter", "d/o", "w/o"]):
            extracted["gender"] = Gender.FEMALE
        elif any(w in combined for w in ["male", "purush", "man", "son of", "s/o"]):
            extracted["gender"] = Gender.MALE

        # 5. Age / DOB extraction from OCR text
        # Look for Year of Birth: 1985 or DOB: 14/08/1995
        dob_match = re.search(r'\b(dob|birth|year of birth|yob)\D*(\d{2}[/-]\d{2}[/-]\d{4}|\d{4})\b', combined)
        if dob_match:
            try:
                dob_str = dob_match.group(2)
                birth_year = int(dob_str.split("/")[-1].split("-")[-1]) if len(dob_str) > 4 else int(dob_str)
                current_year = datetime.now().year
                calc_age = current_year - birth_year
                if 1 <= calc_age <= 110:
                    extracted["age"] = calc_age
            except Exception:
                pass

        # 6. Income extraction
        inc_match = re.search(r'\b(annual income|income|aay|salana)\D*(\d{4,7})\b', combined)
        if inc_match:
            try:
                extracted["annual_income"] = int(inc_match.group(2))
            except Exception:
                pass

        # 7. Category extraction
        for cat_name, cat_enum in [("obc", Category.OBC), ("sc", Category.SC), ("st", Category.ST), ("ews", Category.EWS)]:
            if re.search(rf'\b{cat_name}\b', combined):
                extracted["category"] = cat_enum
                break

        return extracted
