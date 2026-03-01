from config import logger
from ollama import Client
from typing import Optional

from utils.prompt import load_prompt

class OllamaVision:
    """
    Ollama Vision model class.
    
    Attributes:
        model_name: str, the name of the model to use.
        base_url: str, the base URL of the Ollama server.
        keep_alive: str, the keep alive time for the connection to the server.
        temperature: float, the temperature for the model.
    Methods:
        generate: Generate image description from the model.
    """
    def __init__(
        self, 
        model_name: str, 
        base_url: str,
        keep_alive: str = "1h",
        temperature: float = 0.1
    ):
        self.client = Client(base_url)
        self.model = model_name
        self.keep_alive = keep_alive
        self.temperature = temperature
        
    def generate(self, template_name: str, image: str, **kwargs) -> Optional[str]:
        """ Generate image description from the model."""
        
        prompt_template = load_prompt(f"{template_name}_ollama").format(**kwargs)
        
        try:
            response = self.client.generate(
                model=self.model,
                keep_alive=self.keep_alive,
                prompt=prompt_template, 
                images=[image],
                options=dict(temperature=self.temperature)
            )
   
        except Exception as e:
            logger.error(f"Error generating image description with {self.model}: {e}")
            return None

        return response['response']
