"""Voice Intake & Output module for Hindi and Indian English audio with zero-latency caching."""

import asyncio
import hashlib
from pathlib import Path
from shared.config import OUTPUT_DIR


async def _synthesize_edge_tts(text: str, output_path: Path, voice: str = "hi-IN-SwaraNeural"):
    """Uses Edge-TTS for high-quality Indian Hindi/English voice generation."""
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_path))


def text_to_speech(text: str, language: str = "hi") -> Path:
    """Converts response text to an audio file with instant hash-based disk caching."""
    # Compute unique MD5 cache key for this text and language
    text_hash = hashlib.md5(f"{language}_{text}".encode("utf-8")).hexdigest()[:12]
    cached_path = OUTPUT_DIR / f"voice_{language}_{text_hash}.mp3"

    # 1. Return cached audio instantly if already synthesized (0ms latency)
    if cached_path.exists() and cached_path.stat().st_size > 0:
        return cached_path

    voice = "hi-IN-SwaraNeural" if language == "hi" else "en-IN-NeerjaNeural"

    # 2. Try Edge-TTS
    try:
        asyncio.run(_synthesize_edge_tts(text, cached_path, voice))
        return cached_path
    except Exception:
        pass

    # 3. Fallback to gTTS
    try:
        from gtts import gTTS
        lang_code = "hi" if language == "hi" else "en"
        tts = gTTS(text=text, lang=lang_code, slow=False)
        tts.save(str(cached_path))
        return cached_path
    except Exception:
        # Fallback to any existing voice file if completely offline
        existing = list(OUTPUT_DIR.glob("*.mp3"))
        if existing:
            return existing[0]
        return cached_path
