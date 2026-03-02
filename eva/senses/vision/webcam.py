from config import logger
import numpy as np
import cv2


class Webcam:

    def __init__(self, source: int | str = 0):
        """
        Args:
            source: int for local V4L2 device (e.g. 0), or URL string for
                    network stream (e.g. "http://198.18.0.1:5000/video").
        """
        self._source = source
        self.camera = self._initialize_camera()

    def _initialize_camera(self) -> cv2.VideoCapture:
        try:
            if isinstance(self._source, str):
                # Network stream (WSL → Windows host MJPEG bridge)
                cam = cv2.VideoCapture(self._source, cv2.CAP_FFMPEG)
            else:
                # Local V4L2 device
                cam = cv2.VideoCapture(self._source, cv2.CAP_V4L2)
                cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            if not cam.isOpened():
                raise ConnectionError(f"Could not connect to camera: {self._source}")
        except Exception as e:
            logger.error(f"Failed to initialize camera: {str(e)}")
            raise

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
