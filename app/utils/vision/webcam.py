import os
from config import logger
import time
import numpy as np
from multiprocessing import Process, Manager

import cv2

class Webcam:
    """
    A class that watches a camera feed for movement and captures images if movement is detected.
    Then it describes the image using the Ollama llava-phi3.

    Attributes:
        camera_index (int): The index of the camera to use.
        camera (cv2.VideoCapture): The camera object.
        watching (bool): Flag indicating if the watcher is currently watching for movement.
        process (multiprocessing.Process): The process object for watching the camera feed.


    """
    
    def __init__(self, camera_index: int = 0):
        self._camera_index = camera_index
        self.manager = Manager()
        self.observation = self.manager.list()
        self.watching = self.manager.Value('b', False)        
        self.camera = self._initialize_camera()
        self.process = None

        
    def _initialize_camera(self) -> cv2.VideoCapture:
        """ Initialize the camera object. """
        
        # currently this setup is for WSL2
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
    
    def get_observation(self, wait: bool = False) -> str:
        # default we dont have to wait
           
        if not self.observation and not wait:
            return "nothing"
            start_time = time.time()

        start_time = time.time()
        timeout = 20 # maximum wait time to get observation in seconds 
        
        while True:
            sight = self.observation
            if sight or (time.time() - start_time > timeout):
                break
            time.sleep(1)
            
        return self.observation[-1] if self.observation else "nothing"
    
    def start_watch(self) -> bool:
        if self.process is None and not self.watching.value:
            try:
                self.watching.value = True
                self.process = Process(target=self.watch_camera, args=(self.watching, self.observation))
                self.process.daemon = True
                self.process.start()
            except Exception as e:
                raise RuntimeError(f"Error: Failed to start the watcher: {e}")
            
            logger.info("Watcher: Start watching for movement.")
            return True
        else:
            logger.warning("Watcher: Already watching.")
            return False
        
    def watch_camera(self, watching, vison : list = []):
        previous_frame = None
        try:
            while watching.value:
                self.camera.grab()
                ret, frame = self.camera.read()
                if not ret:
                    raise RuntimeError("Error: Failed to capture image.")
                
                current_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                # current_frame = cv2.GaussianBlur(current_frame, (21, 21), 0)
                        
                if previous_frame is None:
                    previous_frame = current_frame
                    frame_area = current_frame.size
                    continue
                
                frame_diff = cv2.absdiff(previous_frame, current_frame)

                # Count the number of changed pixels
                changed_pixels = np.sum(frame_diff > 10)
                change_percentage = changed_pixels / frame_area
                
                logger.info(f"{changed_pixels, frame_area, change_percentage}")
                
                if change_percentage > 0.4:
                    timestamp = time.strftime("%Y%m%d-%H%M%S")
                    filepath = os.path.join(os.path.dirname(__file__), "images", f"movement_{timestamp}.jpg") 
                    cv2.imwrite(filepath, current_frame)
                    sleep_time = 20
                    
                    timecontent = self.image_analyzer.describe(current_frame)
                    vison.append(timecontent)
                    
                    logger.info(f"Watcher: Movement detected and image captured at {timestamp}")
                else:
                    sleep_time = 60
                
                previous_frame = current_frame
                time.sleep(sleep_time)
            
        except KeyboardInterrupt:
            logger.warning("Interrupted by user keyboard")
        except Exception as e:
            raise RuntimeError(f"Error: Failed to calculate the difference: {e}")
        finally:
            self.camera.release()
    
    def capture(self) -> np.ndarray:
        """ Capture an image from the camera. """
        
        # Grab latest frame to avoid buffering delay
        if not self.camera.grab():
            raise RuntimeError("Watcher: Failed to grab camera frame.")
            
        ret, frame = self.camera.retrieve()
        if not ret:
            raise RuntimeError("Watcher: Failed to retrieve camera frame.")
        return frame
    
    def stop_watch(self) -> None:
        if self.process:
            self.watching.value = False
            self.process.join()
            self.process = None
        self.camera.release()

