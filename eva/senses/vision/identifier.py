from config import logger
import os
import base64
from pathlib import Path
from queue import Queue
from typing import Dict, List

try:
    from eva.core.ids import id_manager
except Exception:
    id_manager = None
    logger.warning("Identifier: id_manager not available, face naming disabled.")

#import face_recognition as fr
import numpy as np
import cv2

class Identifier:
    def __init__(self):
        self._pid_list = None
        self._ids: List[Dict] = self.initialize_ids()
        logger.debug(f"Identifier: Ready. {len(self._ids)} IDs loaded.")

    def initialize_ids(self) -> List[Dict]:
        self._pid_list = id_manager.get_pid_list() if id_manager else {}
        pid_directory = Path(__file__).resolve().parents[3] / 'data' / 'pids'
        if not pid_directory.exists():
            pid_directory.mkdir(parents=True)

        photo_ids = {}

        for filename in os.listdir(pid_directory):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                filepath = os.path.join(pid_directory, filename)
                try:
                    id = str(len(photo_ids) + 1).zfill(3)
                    name = os.path.splitext(filename)[0]
                    image = fr.load_image_file(filepath)
                    face_encoding = fr.face_encodings(image)

                    if face_encoding:
                        photo_ids[id] = (name, face_encoding[0])
                    else:
                        logger.warning(f"Identifier: No faces found in {filename}")

                except Exception as e:
                    raise Exception(f"Error processing {filename}: {str(e)}")

        return photo_ids

    def _base64_to_numpy(self, base64_str: str) -> np.ndarray:
        img_array = np.frombuffer(base64.b64decode(base64_str), dtype=np.uint8)
        return cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    def identify(self, frames: np.ndarray | str, name_queue: Queue) -> None:
        if isinstance(frames, str):
            frames = self._base64_to_numpy(frames)

        try:
            frames = cv2.cvtColor(cv2.resize(frames, (0, 0), fx=0.5, fy=0.5), cv2.COLOR_BGR2RGB)

            face_locations = fr.face_locations(frames)
            face_encodings = fr.face_encodings(frames, face_locations)

            names = []
            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                for name, face_id in self._ids.values():
                    matches = fr.compare_faces([face_id], face_encoding)
                    if True in matches and self._pid_list and name in self._pid_list:
                        names.append(self._pid_list[name])
                        break

        except Exception as e:
            logger.error(f"Identifier: Failed to identify faces: {str(e)}")
            return

        name = "unknown" if not names else ", ".join(names)

        if name_queue:
            name_queue.put(name)
