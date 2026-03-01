from config import logger
import numpy as np
from pathlib import Path

import cv2
from utils.vision.describer import Describer
from utils.vision.webcam import Webcam


class Watcher:
    """
    A class that manages computer vision functionality for capturing and analyzing images.

    The Watcher class provides an interface for capturing video frames from input devices
    and analyzing their content using computer vision models. It implements motion detection
    between consecutive frames and generates natural language descriptions of visual scenes
    when significant changes are detected.

    Attributes:
        describer (Describer): Computer vision model that generates natural language descriptions
            of image content.
        device (Webcam): Video capture device interface for obtaining image frames.
        _previous_frame (np.ndarray | None): Previously captured grayscale frame buffer used for
            frame-to-frame motion detection comparisons.
        _change_threshold (float): Minimum percentage of changed pixels between consecutive frames
            required to trigger a new scene description, range [0.0, 1.0].


    """
    
    def __init__(self, model_name: str, base_url: str):
        self.describer: Describer = Describer(model_name, base_url)
        self.device: Webcam = Webcam() # this could support multiple input devices, use an initialize function to select the device later
        
        self._previous_frame: np.ndarray | None = None
        self._change_threshold: float = 0.4
        
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
        
        # logger.info(f"Watcher: Frame change detected. Percentage: {change_percentage}") 
        # only  return a description if there is significant change.
        return change_percentage > self._change_threshold
    
    def glance(self) -> str | None:
        """ Capture and analyze a single frame, returning a description if significant change is detected """
        
        try:
            frame = self.device.capture()
            if frame is not None:
                if self._is_diff_frame(frame):
                    frame = cv2.resize(frame, (320, 240))
                    return self.describer.describe("vision", frame)
        except Exception as e:
            logger.error(f"Error capturing/analyzing frame: {str(e)}")
        
        return None
    
    def capture(self, save_file: str) -> None:
        """ Capture a frame and save it to the pid database """
        try:
            frame = self.device.capture()
            if frame is not None:
                data_path = self._get_data_path() / f"{save_file}.jpg"
                cv2.imwrite(data_path, frame)
                logger.info(f"Watcher: Frame saved to {data_path}")

        except Exception as e:
            logger.error(f"Error capturing/analyzing frame: {str(e)}")

    def _get_data_path(self) -> Path:
        """Return the path to the memory log database."""
        return Path(__file__).resolve().parents[2] / 'data' / 'pids'
    
    def deactivate(self) -> None:
        """ Deactivate the watching device. """
        if self.device is not None:
            self.device.stop_watch()
