"""
Voice Actuator - Background loop that plays audio and can be interrupted.
"""
import asyncio
from config import logger
from typing import Optional

from eva.modules.tts.speaker import Speaker
from eva.actuators.buffer import ActionBuffer

class VoiceActuator:
    """
    Background service that handles speech playback.
    Reads commands from the ActionBuffer.
    """
    def __init__(self, action_buffer: ActionBuffer, speaker: Optional[Speaker] = None):
        self.buffer = action_buffer
        self.speaker = speaker or Speaker()
        self.current_speech_task: Optional[asyncio.Task] = None
        self._running = False

    async def start_loop(self):
        """Runs the voice actuator loop forever."""
        self._running = True
        logger.info("Voice Actuator loop started.")
        while self._running:
            try:
                command = await self.buffer.get()
                
                if command.type == "speak" and command.content:
                    # Cancel any existing speech
                    if self.current_speech_task and not self.current_speech_task.done():
                        self.current_speech_task.cancel()
                        self.speaker.stop_speaking()
                    
                    language = command.metadata.get("language", "en")
                    # Launch new speech in a background thread task
                    self.current_speech_task = asyncio.create_task(
                        asyncio.to_thread(self.speaker.speak, command.content, language, True)
                    )

                elif command.type == "interrupt":
                    # Instantly stop speaking
                    if self.current_speech_task and not self.current_speech_task.done():
                        self.current_speech_task.cancel()
                        self.speaker.stop_speaking()
                        logger.info("Voice Actuator interrupted speech.")
                        
            except asyncio.CancelledError:
                self._running = False
                break
            except Exception as e:
                logger.error(f"Voice Actuator error: {e}")
                
    def stop(self):
        """Stop the background loop."""
        self._running = False
        if self.current_speech_task and not self.current_speech_task.done():
            self.current_speech_task.cancel()
            self.speaker.stop_speaking()
