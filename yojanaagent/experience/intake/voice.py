"""Voice Intake & Output module for Hindi and Indian English audio."""

import asyncio
from pathlib import Path
from yojanaagent.shared.config import OUTPUT_DIR


async def _synthesize_edge_tts(text: str, output_path: Path, voice: str = "hi-IN-SwaraNeural"):
    """Uses Edge-TTS for high-quality Indian Hindi/English voice generation."""
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_path))


def text_to_speech(text: str, language: str = "hi") -> Path:
    """Converts response text to an audio file for multimodal output."""
    output_path = OUTPUT_DIR / f"response_{language}.mp3"

    voice = "hi-IN-SwaraNeural" if language == "hi" else "en-IN-NeerjaNeural"

    try:
        asyncio.run(_synthesize_edge_tts(text, output_path, voice))
        return output_path
    except Exception:
        # Fallback to gTTS
        try:
            from gtts import gTTS
            lang_code = "hi" if language == "hi" else "en"
            tts = gTTS(text=text, lang=lang_code, slow=False)
            tts.save(str(output_path))
            return output_path
        except Exception:
            return output_path
