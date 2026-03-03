"""
OpenAISpeaker: OpenAI TTS model.
  eva_speak(text, language) -> streams audio directly via LocalAudioPlayer
  generate_audio(text, language, media_folder) -> writes mp3, returns relative path
  stop_playback() -> no-op (stream cannot be interrupted mid-play)
"""

from config import logger
import os
import asyncio
from threading import Thread
import secrets
from typing import Optional

from openai import AsyncOpenAI
from openai.helpers import LocalAudioPlayer

class OpenAISpeaker:
    """Audio speaker using OpenAI TTS."""

    def __init__(self, voice: str = "nova") -> None:
        self.model: AsyncOpenAI = AsyncOpenAI()
        self.audio_player: LocalAudioPlayer = LocalAudioPlayer()
        self.voice: str = voice  # default OpenAI voice
        self.audio_thread: Optional[Thread] = None

    async def eva_speak(self, text: str, language: Optional[str] = None) -> None:
        """ Speak the given text using OpenAI """

        # Run blocking OpenAI call in thread
        try:
            async with self.model.audio.speech.with_streaming_response.create(
                model="gpt-4o-mini-tts",
                voice=self.voice,
                input=text,
                instructions="Speak in a very cheerful tone.",
                response_format="pcm",
            ) as response:
                await self.audio_player.play(response)

        except Exception as e:
            logger.error(f"Error during text to speech synthesis: {e}")

    async def generate_audio(self, text: str, language: Optional[str], media_folder: str) -> Optional[str]:
        """ Generate mp3 from text using OpenAI TTS """

        filename = f"{secrets.token_hex(16)}.mp3"
        file_path = os.path.join(media_folder, "audio", filename)

        def _generate():
            response = self.model.audio.speech.create(
                model="gpt-4o-mini-tts",
                voice=self.voice,
                response_format="mp3",
                input=text
            )
            response.write_to_file(file_path)

        try:
            await asyncio.to_thread(_generate)
            return f"audio/{filename}"

        except Exception as e:
            logger.error(f"Error during text to speech synthesis: {e}")
            return None

    async def stop_playback(self) -> None:
        """Stop the audio playback."""
        try:
            self.audio_player.stop_playback()
        except Exception:
            pass
