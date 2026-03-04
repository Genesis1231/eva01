"""
Webcam is a module for capturing frames from a camera.
"""

from config import logger
import numpy as np
import cv2

class Webcam:
    """
    Webcam class
    
    Args:
        source: int for local V4L2 device (e.g. 0), or URL string for
                network stream (e.g. "http://198.18.0.1:5000/video").
    Methods:
        capture() -> np.ndarray: Capture a single frame from the camera.
        release() -> None: Release the camera.
    """
    def __init__(self, source: int | str = 0):

        self._source = source
        self.camera = self._initialize_camera()

    def _initialize_camera(self) -> cv2.VideoCapture:
        """Initialize the camera with network compatibility."""
        
        logger.debug(f"Initializing camera: {self._source}")
        try:
            if isinstance(self._source, str):
                # Network stream
                cam = cv2.VideoCapture(self._source, cv2.CAP_FFMPEG)
            else:
                # Local V4L2 device
                cam = cv2.VideoCapture(self._source, cv2.CAP_V4L2)
                cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            if not cam.isOpened():
                raise ConnectionError(f"Could not connect to camera: {self._source}")
        except Exception as e:
            logger.warning(f"Camera unavailable ({self._source}): {e}")
            return None

        return cam

    def capture(self) -> np.ndarray:
        if not self.camera.grab():
            raise RuntimeError("Webcam: Failed to grab frame.")

        ret, frame = self.camera.retrieve()
        if not ret:
            raise RuntimeError("Webcam: Failed to retrieve frame.")
        return frame

    def release(self) -> None:
        if self.camera is not None:
            self.camera.release()
