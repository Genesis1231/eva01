from config import logger
import time
import threading
import numpy as np
from pathlib import Path

import cv2
from .describer import Describer
from .webcam import Webcam
from eva.core.input_buffer import InputBuffer


class CameraService:
    """Background camera service — captures frames, detects motion, pushes observations to InputBuffer."""

    def __init__(
        self,
        model_name: str,
        base_url: str,
        input_buffer: InputBuffer = None,
        glance_interval: float = 3.0
    ):
        self.describer: Describer = Describer(model_name, base_url)
        self.device: Webcam = Webcam()
        self.input_buffer: InputBuffer = input_buffer
        self.glance_interval: float = glance_interval

        self._previous_frame: np.ndarray | None = None
        self._change_threshold: float = 0.4

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def _is_diff_frame(self, frame: np.ndarray) -> bool:
        """ Check if the frame has changed significantly """

        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        if self._previous_frame is None:
            self._previous_frame = gray_frame
            return True

        frame_diff = cv2.absdiff(gray_frame, self._previous_frame)
        changed_pixels = np.count_nonzero(frame_diff > 10)
        change_percentage = changed_pixels / frame_diff.size
        self._previous_frame = gray_frame

        return change_percentage > self._change_threshold

    def _capture_loop(self) -> None:
        """Main background loop — capture, detect motion, describe, push to buffer."""
        logger.info("CameraService: Background capture loop started.")

        while not self._stop_event.is_set():
            try:
                frame = self.device.capture()

                if self._is_diff_frame(frame):
                    logger.info("CameraService: Motion detected, describing scene...")
                    resized = cv2.resize(frame, (320, 240))
                    observation = self.describer.describe("vision", resized)

                    if observation and self.input_buffer:
                        self.input_buffer.push("observation", observation)
                        logger.info(f"CameraService: Observation pushed — {observation[:80]}...")

            except Exception as e:
                logger.error(f"CameraService: Capture loop error — {str(e)}")

            self._stop_event.wait(self.glance_interval)

        logger.info("CameraService: Background capture loop stopped.")

    def start(self) -> None:
        """Launch the background capture thread."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning("CameraService: Already running.")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        logger.info("CameraService: Started.")

    def stop(self) -> None:
        """Signal the capture loop to stop and wait for the thread to finish."""
        if self._thread is None or not self._thread.is_alive():
            return

        logger.info("CameraService: Stopping...")
        self._stop_event.set()
        self._thread.join(timeout=10)
        self._thread = None
        logger.info("CameraService: Stopped.")

    def glance(self) -> str | None:
        """Single synchronous glance — for backward compatibility with WSLClient."""
        try:
            frame = self.device.capture()
            if frame is not None:
                if self._is_diff_frame(frame):
                    frame = cv2.resize(frame, (320, 240))
                    return self.describer.describe("vision", frame)
        except Exception as e:
            logger.error(f"CameraService: Glance error — {str(e)}")

        return None

    def capture_photo(self, save_file: str) -> None:
        """Capture a frame and save it to the pids data directory."""
        try:
            frame = self.device.capture()
            if frame is not None:
                data_path = self._get_data_path() / f"{save_file}.jpg"
                cv2.imwrite(str(data_path), frame)
                logger.info(f"CameraService: Frame saved to {data_path}")
        except Exception as e:
            logger.error(f"CameraService: Photo capture error — {str(e)}")

    def _get_data_path(self) -> Path:
        """Return the path to the pid data directory."""
        return Path(__file__).resolve().parents[3] / 'data' / 'pids'

    def deactivate(self) -> None:
        """Stop the background thread and release the camera."""
        self.stop()
        if self.device is not None:
            self.device.release()
