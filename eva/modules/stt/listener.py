import select
import sys
import termios
import tty
import threading
import queue
import asyncio
from pathlib import Path
from typing import Optional, Tuple

import soundfile as sf

from config import logger
from .mic import Microphone
from .transcriber import Transcriber

class PCListener:
    """Push-to-talk listener for PC/Laptop.

    Runs input detection and transcription in separate threads to allow
    continuous listening while processing previous audio.
    """

    _SPACE = 0x20
    _ESC = 0x1B
    _RELEASE_SILENCE_S = 0.6  # seconds of silence that signals key release
    _SAMPLE_RATE = 16000

    def __init__(self, model_name: str = "faster-whisper", language: str = "en") -> None:
        self.microphone = Microphone()
        self.transcriber = Transcriber(model_name, language)
        self.data_path = Path(__file__).resolve().parents[3] / "data" / "voids"
        
        # Queues for inter-thread communication
        self.audio_queue = queue.Queue()
        self.result_queue = queue.Queue()
        
        # Control flags
        self.running = False
        self.stop_event = threading.Event()
        
        # Threads
        self.input_thread: Optional[threading.Thread] = None
        self.process_thread: Optional[threading.Thread] = None

        # Start threads automatically
        self.start()

    def start(self):
        """Start the background listening and processing threads."""
        if self.running:
            return

        self.running = True
        self.stop_event.clear()

        self.input_thread = threading.Thread(target=self._input_loop, daemon=True)
        self.process_thread = threading.Thread(target=self._process_loop, daemon=True)

        self.input_thread.start()
        self.process_thread.start()
        logger.info("PCListener: Background threads started")

    def stop(self):
        """Stop background threads."""
        self.running = False
        self.stop_event.set()
        
        if self.input_thread:
            self.input_thread.join(timeout=1.0)
        if self.process_thread:
            self.process_thread.join(timeout=1.0)
            
        logger.info("PCListener: Stopped")

    def listen(
        self,
        save_file: Optional[str] = None
    ) -> Optional[tuple[Optional[str], Optional[str]]]:
        """
        Blocking method to get the next transcription result.
        Compatible with legacy synchronous code.
        """
        try:
            # Wait for a result from the queue
            text, lang, audio_data = self.result_queue.get()
            if text is None:
                return None
            
            if save_file and audio_data is not None:
                path = str(self.data_path / f"{save_file}.wav")
                sf.write(path, audio_data, samplerate=_SAMPLE_RATE)
                
            return text, lang
        except KeyboardInterrupt:
            return None

    async def listen_async(self) -> Optional[tuple[Optional[str], Optional[str]]]:
        """
        Async method to get the next transcription result.
        Non-blocking for the event loop.
        Returns None if the listener has stopped.
        """
        while self.running and not self.stop_event.is_set():
            try:
                # Non-blocking check
                text, lang, _ = self.result_queue.get_nowait()
                return text, lang
            
            except queue.Empty:
                await asyncio.sleep(0.1)
                
        return None

    def _input_loop(self):
        """Thread 1: Monitors keyboard (SPACE) and records audio."""
        print("... Press SPACE to talk to EVA...", end="\r", flush=True)
        
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        
        try:
            tty.setraw(fd)
            
            while not self.stop_event.is_set():
                # Check for key press with short timeout to allow checking stop_event
                if self._await_space_press_step():
                    if not self.microphone.start_recording():
                        logger.error("PCListener: microphone failed to start")
                        continue

                    print("Recording... release to send...", end="\r", flush=True)
                    
                    # Wait for release
                    self._await_space_release()
                    
                    # Stop recording
                    audio_data = self.microphone.stop_recording()
                    print("... Press SPACE to talk, release to send ... ", end="\r", flush=True)

                    if audio_data is not None:
                        self.audio_queue.put(audio_data)
                    else:
                        logger.warning("PCListener: recording too short or failed")

        except Exception as e:
            logger.error(f"PCListener input loop error: {e}")
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            print("\033[K\033[K", end="", flush=True) # Clear line

    def _process_loop(self):
        """Thread 2: Consumes audio and runs transcription."""
        while not self.stop_event.is_set():
            try:
                # Wait for audio data (blocking with timeout to check stop_event)
                audio_data = self.audio_queue.get(timeout=0.5)
                
                # Transcribe
                transcription = self.transcriber.transcribe(audio_data)
                
                if transcription:
                    text, lang = transcription
                    self.result_queue.put((text, lang, audio_data))
                else:
                    logger.warning("PCListener: no speech detected")
                    
                self.audio_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"PCListener process loop error: {e}")

    def _await_space_press_step(self) -> bool:
        """
        Check for SPACE press once with a short timeout.
        Returns True if SPACE pressed, False if timeout or other key.
        """
        if select.select([sys.stdin], [], [], 0.1)[0]:
            byte = sys.stdin.buffer.read(1)[0]
            if byte == _SPACE:
                return True
            if byte == _ESC:
                self.stop_event.set()
                return False
        return False

    def _await_space_release(self) -> None:
        """Block until SPACE is released."""
        while select.select([sys.stdin], [], [], _RELEASE_SILENCE_S)[0]:
            sys.stdin.buffer.read(1)
