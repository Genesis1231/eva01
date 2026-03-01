from config import logger
import os
import base64
from pathlib import Path
from queue import Queue
from typing import Dict, List

from core.ids import id_manager
import face_recognition as fr
import numpy as np
import cv2

class Identifier:
    """
    Class to identify individuals from frames using face recognition.

    Attributes:
        _ids (dict): A dictionary containing the photo IDs and corresponding face encodings.

    Methods:
        initialize_ids(): Initializes the photo IDs and face encodings.
        _base64_to_numpy(base64_str): Converts a base64 string to a numpy array.
        identify(frames): Identifies individuals from the given frames.
    """
    def __init__(self):
        self._pid_list = None
        self._ids: List[Dict] = self.initialize_ids()
        logger.info(f"Identifier: Personal Identifier is Ready. {len(self._ids)} IDs loaded.")
        
    def initialize_ids(self)-> List[Dict]:
        """ Load the photo IDs and corresponding face encodings. """
        
        self._pid_list = id_manager.get_pid_list()
        pid_directory = Path(__file__).resolve().parents[2] / 'data' / 'pids'
        if not pid_directory.exists():
            pid_directory.mkdir(parents=True)
            
        photo_ids = {}
        
        for filename in os.listdir(pid_directory):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                filepath = os.path.join(pid_directory, filename)
                try:
                    id = str(len(photo_ids) + 1).zfill(3)
                    # Extract name from filename (assuming format: "id_name.extension")
                    name = os.path.splitext(filename)[0]
                    image = fr.load_image_file(filepath)
                    face_encoding = fr.face_encodings(image)
                    
                    if face_encoding:
                        photo_ids[id] = (name, face_encoding[0])
                    else:
                        logger.warning(f"Photo Identifier: No faces found in the image: {filename}")
                        
                except Exception as e:
                    raise Exception(f"Error processing {filename}: {str(e)}")
        
        return photo_ids
    
    def _base64_to_numpy(self, base64_str: str)-> np.ndarray:
        """ Convert a base64 string to a numpy array. """
        img_array = np.frombuffer(base64.b64decode(base64_str), dtype=np.uint8)
        return cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    
    def identify(
        self, 
        frames: np.ndarray | str, 
        name_queue: Queue
    ) -> None:
        
        """ Identify individuals from the given frames. """
        
        if isinstance(frames, str):
            frames = self._base64_to_numpy(frames)
        
        try:
            frames = cv2.cvtColor(cv2.resize(frames, (0, 0), fx=0.5, fy=0.5), cv2.COLOR_BGR2RGB)

            face_locations = fr.face_locations(frames)
            face_encodings = fr.face_encodings(frames, face_locations)

            names = []
            # Compare the captured face encoding with known face encodings
            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                for name, face_id in self._ids.values():
                    matches = fr.compare_faces([face_id], face_encoding)
                    if True in matches and name in self._pid_list:
                        names.append(self._pid_list[name])
                        break
                    
        except Exception as e:
            logger.error(f"Identifier: Failed to identify faces: {str(e)}")
            return
        
        name = "unknown" if not names else ", ".join(names)
        
        if name_queue:
            name_queue.put(name)
            

