from config import logger
import threading
from pathlib import Path

import numpy as np
import cv2

from eva.senses.vision.describer import Describer
from eva.senses.vision.webcam import Webcam
from eva.senses.sense_buffer import SenseBuffer


class CameraSense:
    """Background vision thread — EVA's eyes.

    Continuously captures frames, detects scene changes,
    and writes descriptions to a shared input buffer.
    """

    def __init__(
        self,
        describer: Describer,
        source: int | str = 0,
        change_threshold: float = 0.4,
        glance_interval: float = 5.0,
    ):
        """
        Args:
            source: int for local V4L2 device, or URL string for network
                    stream (e.g. "http://198.18.0.1:5000/video" for WSL).
        """
        self.describer = describer
        self.webcam = Webcam(source)
        self.change_threshold = change_threshold
        self.glance_interval = glance_interval

        self._previous_frame: np.ndarray | None = None
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self, buffer: SenseBuffer) -> None:
        """Start the background camera thread, writing observations to buffer."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning("CameraSense: Already running.")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, args=(buffer,), daemon=True
        )
        self._thread.start()
        logger.info("CameraSense: Started.")

    def stop(self) -> None:
        """Stop the camera thread and release resources."""
        if self._thread is None or not self._thread.is_alive():
            return

        logger.info("CameraSense: Stopping...")
        self._stop_event.set()
        self._thread.join(timeout=10)
        self._thread = None
        self.webcam.release()
        logger.info("CameraSense: Stopped.")

    def _run(self, buffer: SenseBuffer) -> None:
        """Main loop: capture -> detect change -> describe -> write to buffer."""
        logger.info("CameraSense: Capture loop started.")

        while not self._stop_event.is_set():
            try:
                frame = self.webcam.capture()

                if self._has_scene_changed(frame):
                    logger.info("CameraSense: Scene change detected, describing...")
                    description = self._describe(frame)

                    if description:
                        buffer.push("observation", description)
                        logger.info(f"CameraSense: {description[:80]}...")

            except Exception as e:
                logger.error(f"CameraSense: Capture loop error — {e}")

            self._stop_event.wait(self.glance_interval)

        logger.info("CameraSense: Capture loop stopped.")

    def _has_scene_changed(self, frame: np.ndarray) -> bool:
        """Motion detection via grayscale pixel diff."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        if self._previous_frame is None:
            self._previous_frame = gray
            return True

        diff = cv2.absdiff(gray, self._previous_frame)
        changed_pixels = np.count_nonzero(diff > 10)
        change_ratio = changed_pixels / diff.size
        self._previous_frame = gray

        return change_ratio > self.change_threshold

    def _describe(self, frame: np.ndarray) -> str | None:
        """Describe frame using vision model with parallel face ID."""
        resized = cv2.resize(frame, (320, 240))
        return self.describer.describe("vision", resized)

    def capture_photo(self, save_path: str) -> None:
        """On-demand photo capture (for face registration etc)."""
        try:
            frame = self.webcam.capture()
            path = Path(save_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(path), frame)
            logger.info(f"CameraSense: Photo saved to {path}")
        except Exception as e:
            logger.error(f"CameraSense: Photo capture error — {e}")
