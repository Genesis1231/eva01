from config import logger
import numpy as np
import base64
import threading
from functools import partial
from queue import Queue
from typing import Dict, Callable

import cv2
from utils.vision.identifier import Identifier


class Describer:
    """
    A class that processes and describes images using various vision models.

    This class provides a unified interface for different vision models (Ollama, OpenAI, Groq)
    and handles image processing, person identification, and natural language descriptions.

    Attributes:
        model: The initialized vision model instance for image description.
        identifier (Identifier): Component for identifying individuals in images.
        name_queue (Queue): Thread-safe queue for passing identification results.

    Args:
        model_name (str, optional): The name of the vision model to use. Defaults to "llava-phi3".
        base_url (str, optional): The base URL for the model API. Defaults to 'http://localhost:11434/'.

    Raises:
        ValueError: If an unsupported model is specified.

    Examples:
        >>> describer = Describer(model_name="llava-phi3")
        >>> description = describer.describe("general", image_data)
        >>> analysis = describer.analyze_screenshot(image_data, "What's in this image?")
    """
    
    def __init__(self, model_name: str = "llava-phi3", base_url: str = 'http://localhost:11434/'):
        self._model_selection: str = model_name.upper()
        self._base_url: str = base_url
        self.name_queue = Queue()
        
        self.identifier = Identifier()
        self.model = self._initialize_model()

        logger.info(f"Describer: {self._model_selection} is ready.")
        
    def _get_model_factory(self) -> Dict[str, Callable]:
        return {
            "LLAVA-PHI3" : partial(self._create_ollama_model, "llava-phi3"),
            "LLAMA" : partial(self._create_ollama_model, "llama3.2-vision"),
            "OPENAI" : self._create_openai_model,
            "GROQ" : self._create_groq_model
        }
        
    def _create_ollama_model(self, model_name: str):
        from utils.vision.model_ollama import OllamaVision
        
        return OllamaVision(model_name, self._base_url)
    
    def _create_openai_model(self):
        from utils.vision.model_openai import OpenAIVision
        
        return OpenAIVision()
    
    def _create_groq_model(self):
        from utils.vision.model_groq import GroqVision
        
        return GroqVision()
    
    def _initialize_model(self):
        model_factory = self._get_model_factory()
        model = model_factory.get(self._model_selection)
        if model is None:
            raise ValueError(f"Error: Model {self._model_selection} is not supported")

        return model()
    
    def _convert_base64(self, image_data: np.ndarray | str) -> str:
        """ Convert image data to base64. """
        
        if isinstance(image_data, np.ndarray):
            _, buffer = cv2.imencode('.jpg', image_data)
            image_data = base64.b64encode(buffer).decode('utf-8')
        
        return image_data
    
    def analyze_screenshot(
        self, 
        image_data: np.ndarray | str, 
        query: str
    ) -> str | None:
        
        """ Describe a screenshot using the vision model. """
        
        image_base64 = self._convert_base64(image_data)
        
        try:
            result = self.model.generate(template_name="screenshot",
                                        image=image_base64,
                                        query=query)
        except Exception as e:
            logger.error(f"Error: Failed to describe screenshot: {str(e)}")
            return None
        
        return result
        
    def describe(
        self, 
        template_name: str, 
        image_data: np.ndarray | str
    ) -> str | None:
        
        """ 
        Describe an image using the configured vision model.

        Args:
            template_name (str): The template to use for generating the description.
            image_data (Union[np.ndarray, str]): The image to describe, either as a numpy array
                or base64 encoded string.

        Returns:
            Optional[str]: A natural language description of the image, or None if processing fails.
                If a known person is identified, their name is appended to the description.

        """
        
        try:    
            thread = threading.Thread(target=self.identifier.identify, args=(image_data, self.name_queue))
            thread.start()
            
            image_base64 = self._convert_base64(image_data)
            sight = self.model.generate(template_name=template_name,
                                        image=image_base64)
        except Exception as e:
            logger.error(f"Error: Failed to describe image: {str(e)}")
            return None
        
        name = self.name_queue.get()
        thread.join()
        
        return sight if name == "unknown" else sight + f" I recognize it's {name}."
    
