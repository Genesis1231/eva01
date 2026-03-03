"""
KokoroSpeaker: Kokoro TTS model.
  eva_speak(text, language) -> generates PCM, plays via sounddevice
  generate_audio(text, language, media_folder) -> writes wav, returns relative path
  stop_playback() -> stops sounddevice
"""

import asyncio
import os
import secrets
from pathlib import Path
from typing import Optional

import soundfile as sf
from config import logger
from kokoro_onnx import Kokoro

from .audio_player import AudioPlayer

_MODEL_DIR = Path(__file__).resolve().parents[3] / "data" / "models" / "kokoro"
_LANG_MAP = {
    "en": "en-us", 
    "zh": "cmn", 
    "ja": "ja", 
    "fr": "fr-fr", 
    "it": "it", 
    "es": "es"
}

class KokoroSpeaker:
    """Local TTS using Kokoro (ONNX)."""

    def __init__(self, voice: str = "af_sarah") -> None:
        onnx_path = _MODEL_DIR / "kokoro-v1.0.onnx"
        voices_path = _MODEL_DIR / "voices-v1.0.bin"

        if not onnx_path.exists() or not voices_path.exists():
            raise FileNotFoundError(f"Kokoro model files not found in {_MODEL_DIR}. ")
        
        self.voice = voice
        self.audio_player = AudioPlayer()
        self._kokoro = Kokoro(str(onnx_path), str(voices_path))

    def _get_language(self, language: Optional[str]) -> str:
        return _LANG_MAP.get(language or "en", "en-us") if language else "en-us"

    async def eva_speak(self, text: str, language: Optional[str] = None) -> None:
        """Speak the given text using Kokoro TTS."""
        try:
            samples, sample_rate = await asyncio.to_thread(
                self._kokoro.create,
                text,
                voice=self.voice,
                speed=1.0,
                lang=self._get_language(language),
            )
            await asyncio.to_thread(
                self.audio_player.play_pcm,
                samples,
                sample_rate,
            )
        except Exception as e:
            logger.error(f"Error during Kokoro TTS: {e}")

    async def generate_audio(
        self, text: str, 
        language: Optional[str], 
        media_folder: str
    ) -> Optional[str]:
        """Generate wav from text and save to the media folder."""
        
        filename = f"{secrets.token_hex(16)}.wav"
        file_path = os.path.join(media_folder, "audio", filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        try:
            samples, sample_rate = await asyncio.to_thread(
                self._kokoro.create,
                text,
                voice=self.voice,
                speed=1.0,
                lang=self._lang(language),
            )
            await asyncio.to_thread(sf.write, file_path, samples, sample_rate)
            logger.info(f"Audio saved to: {file_path}")
        
            return f"audio/{filename}"
        
        except Exception as e:
            logger.error(f"Error during Kokoro TTS: {e}")
            return None

    async def stop_playback(self) -> None:
        """Stop the audio playback."""
        self.audio_player.stop_playback()
