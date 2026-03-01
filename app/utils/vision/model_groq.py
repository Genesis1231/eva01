from config import logger
from typing import Optional
from groq import Groq

from utils.prompt import load_prompt

class GroqVision:
    def __init__(
        self,
        model_name: str = "llama-3.2-11b-vision-preview",
        temperature: float = 0.1
    ):
        self.client = Groq()
        self.model_name = model_name
        self.temperature = temperature

    def generate(self, template_name: str, image: str, **kwarg) -> Optional[str]:
        """ Generate image description from the model."""
        
        prompt_template = load_prompt(f"{template_name}_groq").format(**kwarg)
        try:
            response = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt_template},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image}",
                                },
                            },
                        ],
                    }
                ],
                model=self.model_name,
                temperature=self.temperature
            )

        except Exception as e:
            logger.error(f"Error: Failed to complete from groq: {str(e)}")
            return None
        
        return response.choices[0].message.content
