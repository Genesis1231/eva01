from config import logger
import numpy as np
import base64
import threading
from functools import partial
from queue import Queue
from typing import Dict, Callable

import cv2
from eva.senses.vision.identifier import Identifier


class Describer:
    def __init__(
        self, 
        model_name: str = "llava-phi3", 
        base_url: str = 'http://localhost:11434/',
        identifier: Identifier = None
    ):
        self._model_selection: str = model_name.upper()
        self._base_url: str = base_url

        self.identifier = Identifier()
        self.model = self._initialize_model()

        logger.debug(f"Describer: {self._model_selection} is ready.")

    def _get_model_factory(self) -> Dict[str, Callable]:
        return {
            "LLAMA" : partial(self._create_ollama_model, "llama3.2-vision"),
            "OPENAI" : self._create_openai_model,
            "GROQ" : self._create_groq_model
        }

    def _create_ollama_model(self, model_name: str):
        from .model_ollama import OllamaVision
        return OllamaVision(model_name, self._base_url)

    def _create_openai_model(self):
        from .model_openai import OpenAIVision
        return OpenAIVision()

    def _create_groq_model(self):
        from .model_groq import GroqVision
        return GroqVision()

    def _initialize_model(self):
        model_factory = self._get_model_factory()
        model = model_factory.get(self._model_selection)
        if model is None:
            raise ValueError(f"Model {self._model_selection} is not supported")
        return model()

    def _convert_base64(self, image_data: np.ndarray | str) -> str:
        if isinstance(image_data, str):
            return image_data
            
        _, buffer = cv2.imencode('.jpg', image_data)
        return base64.b64encode(buffer).decode('utf-8')

    def analyze_screenshot(self, image_data: np.ndarray | str, query: str) -> str | None:
        image_base64 = self._convert_base64(image_data)

        try:
            result = self.model.generate(template_name="screenshot",
                                        image=image_base64,
                                        query=query)
        except Exception as e:
            logger.error(f"Failed to describe screenshot: {str(e)}")
            return None

        return result

    def describe(self, template_name: str, image_data: np.ndarray | str) -> str | None:
        ### Queue for the name of the object in the image ###
        
        name_queue = Queue()
        
        thread = threading.Thread(target=self.identifier.identify, args=(image_data, name_queue))
        thread.start()

        sight = None
        try:
            image_base64 = self._convert_base64(image_data)
            sight = self.model.generate(template_name=template_name,
                                        image=image_base64)
        except Exception as e:
            logger.error(f"Failed to describe image: {str(e)}")
            # Do not return here; we must join the thread and clear the queue

        name = name_queue.get()
        thread.join()

        if sight is None:
            return None

        return sight if name == "unknown" else f"{sight} I recognize it's {name}."
