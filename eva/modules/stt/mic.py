import threading
from typing import Optional

from config import logger
import numpy as np
import sounddevice as sd

_CHANNELS = 1
_SAMPLE_RATE = 16000
_MIN_RECORD_SECONDS = 0.2

class Microphone:
    """
    Pure audio capture and processing utility.

    Handles microphone input, recording, and audio format conversion.
    No user interaction logic - focused solely on audio operations.
    """

    def __init__(self) -> None:
        self._recording = False
        self._frames: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._stream: Optional[sd.InputStream] = None

    @staticmethod
    def _to_float32_audio(raw_audio: Optional[np.ndarray]) -> Optional[np.ndarray]:
        """Convert int16 PCM for audio processing."""
        if raw_audio is None or raw_audio.size == 0:
            return None
        return raw_audio.astype(np.float32) / 32768.0

    def start_recording(self) -> bool:
        """Start audio recording stream."""
        with self._lock:
            if self._recording:
                return True

            self._frames = []

            def on_audio(indata, frame_count, time_info, status) -> None:
                """Audio stream callback."""
                if status:
                    logger.debug(f"Audio stream status: {status}")

                if self._recording:
                    self._frames.append(indata.copy())

            try:
                self._stream = sd.InputStream(
                    samplerate=_SAMPLE_RATE,
                    channels=_CHANNELS,
                    dtype="int16",
                    callback=on_audio,
                )
                self._stream.start()
                self._recording = True
                return True
            except Exception as exc:
                logger.error(f"Failed to start audio recording: {exc}")
                return False

    def stop_recording(self) -> Optional[np.ndarray]:
        """Stop recording and return captured audio."""
        with self._lock:
            if not self._recording:
                return None

            self._recording = False

            try:
                self._stream.stop()
                self._stream.close()
            except Exception as exc:
                logger.error(f"Error stopping audio stream: {exc}")
                return None

            if not self._frames:
                logger.debug("No audio frames captured")
                return None

            # Concatenate all frames
            pcm = np.concatenate(self._frames, axis=0).flatten()
            
        # Check minimum duration
        if len(pcm) < _SAMPLE_RATE * _MIN_RECORD_SECONDS:
            logger.debug(f"Recording too short: < {_MIN_RECORD_SECONDS}s")
            return None
        
        return self._to_float32_audio(pcm)