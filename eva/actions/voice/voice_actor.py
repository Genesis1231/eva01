"""
VoiceActor: 
    The loop that consumes speak/interrupt from ActionBuffer, plays via Speaker. 
    start_loop() -> runs forever, blocks
    stop() -> cancels loop and stops current speech
"""

import asyncio
from config import logger
from typing import Optional

from .speaker import Speaker
from ..buffer import ActionBuffer

class VoiceActor:
    """
    Voice Actor - Background loop that plays audio and can be interrupted.
    Background service that handles speech playback.
    Reads commands from the ActionBuffer.
    """
    def __init__(self, action_buffer: ActionBuffer, speaker: Optional[Speaker] = None):
        self.buffer = action_buffer
        self.speaker = speaker or Speaker()
        self.current_speech_task: Optional[asyncio.Task] = None
        self._running = False
        self._loop_task: Optional[asyncio.Task] = None

    async def start_loop(self):
        """Runs the voice actor loop forever."""
        self._loop_task = asyncio.current_task()
        self._running = True
        logger.info("Voice Actor loop started.")
        while self._running:
            try:
                command = await self.buffer.get()
                
                if command.type == "speak" and command.content:
                    # Cancel any existing speech
                    if self.current_speech_task and not self.current_speech_task.done():
                        self.current_speech_task.cancel()
                        if hasattr(self.speaker, 'stop_speaking'):
                            await self.speaker.stop_speaking()
                    
                    language = command.metadata.get("language", "en")
                    # Launch new speech in a background task
                    self.current_speech_task = asyncio.create_task(
                        self.speaker.speak(command.content, language)
                    )

                elif command.type == "interrupt":
                    # Instantly stop speaking
                    if self.current_speech_task and not self.current_speech_task.done():
                        self.current_speech_task.cancel()
                        if hasattr(self.speaker, 'stop_speaking'):
                            await self.speaker.stop_speaking()
                        logger.info("Voice actor interrupted speech.")
                        
            except asyncio.CancelledError:
                self._running = False
                if self.current_speech_task and not self.current_speech_task.done():
                    self.current_speech_task.cancel()
                break
            except Exception as e:
                logger.error(f"Voice Actor error: {e}")
                
    async def stop(self):
        """Stop the background loop."""
        self._running = False
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
        if self.current_speech_task and not self.current_speech_task.done():
            self.current_speech_task.cancel()
            if hasattr(self.speaker, 'stop_speaking'):
                await self.speaker.stop_speaking()
