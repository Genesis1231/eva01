from config import logger
import numpy as np

import cv2


class Webcam:
    """Minimal webcam interface — capture frames and release."""

    def __init__(self, camera_index: int = 0):
        self._camera_index = camera_index
        self.camera = self._initialize_camera()

    def _initialize_camera(self) -> cv2.VideoCapture:
        """Initialize the camera with V4L2/MJPG for WSL2 compatibility."""
        try:
            cam = cv2.VideoCapture(self._camera_index, cv2.CAP_V4L2)
            cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
            cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            if not cam.isOpened():
                raise ConnectionError(f"Error: Could not connect webcam {self._camera_index}!")
        except Exception as e:
            logger.error(f"Failed to initialize camera: {str(e)}")
            raise

        return cam

    def capture(self) -> np.ndarray:
        """Capture a single frame from the camera."""
        if not self.camera.grab():
            raise RuntimeError("Webcam: Failed to grab camera frame.")

        ret, frame = self.camera.retrieve()
        if not ret:
            raise RuntimeError("Webcam: Failed to retrieve camera frame.")
        return frame

    def release(self) -> None:
        """Release the camera device."""
        if self.camera is not None:
            self.camera.release()
