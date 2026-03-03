"""
EdgeSpeaker: Edge TTS model.
  eva_speak(text, language) -> synthesizes to temp file, plays via AudioPlayer
  generate_audio(text, language, media_folder) -> writes mp3, returns relative path
  stop_playback() -> stops AudioPlayer
"""

import asyncio
import os
import secrets
import tempfile
from threading import Thread
from typing import Optional

import edge_tts
from config import logger

from .audio_player import AudioPlayer

# Maps language codes to the best default Edge TTS voice for that language.
# Run `edge-tts --list-voices` to see all available options.
# LANGUAGE_VOICES: dict[str, str] = {
#     "en": "en-US-AriaNeural",
#     "zh": "zh-CN-XiaoxiaoNeural",
#     "ja": "ja-JP-NanamiNeural",
#     "ko": "ko-KR-SunHiNeural",
#     "fr": "fr-FR-DeniseNeural",
#     "de": "de-DE-KatjaNeural",
#     "es": "es-ES-ElviraNeural",
# }

DEFAULT_VOICE = "en-US-AriaNeural"

class EdgeSpeaker:
    """
    Edge TTS speaker.
    Supports multiple languages via a language-to-voice mapping.
    """

    def __init__(self, voice: str = DEFAULT_VOICE) -> None:
        self.voice = voice
        self.audio_player = AudioPlayer()
        self.audio_thread: Optional[Thread] = None

    def _voice_for(self, language: Optional[str]) -> str:
        """Get the appropriate voice for the given language."""
        # For now, just return the default voice
        # Could be extended with language-specific voice mapping
        return self.voice

    def _synthesize(self, text: str, voice: str) -> str:
        """Synthesize text to a temp mp3 file and return its path."""
        
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            temp_path = f.name
            
        asyncio.run(edge_tts.Communicate(text, voice).save(temp_path))
        
        return temp_path


    async def eva_speak(self, text: str, language: Optional[str] = None) -> None:
        """Speak the given text using Edge TTS."""
        try:
            voice = self._voice_for(language)
            file_path = await asyncio.to_thread(self._synthesize, text, voice)

            if self.audio_thread and self.audio_thread.is_alive():
                self.audio_thread.join()
            
            self.audio_thread = await asyncio.to_thread(self.audio_player.play_file, file_path)

        except Exception as e:
            logger.error(f"Error during Edge TTS synthesis: {e}")

    async def generate_audio(self, text: str, language: Optional[str], media_folder: str) -> Optional[str]:
        """Generate mp3 from text and save to the media folder."""
        
        filename = f"{secrets.token_hex(16)}.mp3"
        file_path = os.path.join(media_folder, "audio", filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        try:
            voice = self._voice_for(language)
            
            def _generate():
                asyncio.run(edge_tts.Communicate(text, voice).save(file_path))
                
            await asyncio.to_thread(_generate)
            
            logger.info(f"Audio file saved to: {file_path}")
            return f"audio/{filename}"

        except Exception as e:
            logger.error(f"Error during Edge TTS synthesis: {e}")
            return None

    async def stop_playback(self) -> None:
        """Stop audio playback."""
        try:
            self.audio_player.stop_playback()
        except Exception:
            pass
