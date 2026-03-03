"""Speaker factory: selects TTS model (edge/openai/elevenlabs/kokoro) and delegates. Exports: Speaker.
  speak(answer, language) -> streams audio via model.eva_speak
  get_audio(text) -> writes mp3 to media folder, returns relative path
  stop_speaking() -> delegates to model.stop_playback
"""

from datetime import datetime
from config import logger
from typing import Dict, Callable, Optional
from pathlib import Path

class Speaker:
    """
    The Speaker class is responsible for initializing and managing the text-to-speech models.
    It provides methods to create different speaker models and speak the given text.

    Attributes:
        model_selection (str): The selected speaker model name.
        model_factory (dict): A dictionary mapping model names to their corresponding creation methods.
        model: The initialized speaker model instance.
    Methods:
        _initialize_model: Initialize the selected speaker model.
        _get_model_factory: Get the model factory dictionary.
        speak: Speak the given text using the selected speaker model.
    """
    
    def __init__(self, speaker_model: str = "edge", language: str = "en")-> None:
        self._model: str = speaker_model.upper()
        self._media_folder: str = self._get_data_path()
        self._language: str = language
        
        self.model = self._initialize_model()
        
        logger.info(f"Speaker: {self._model} is ready.")
    
    def _get_model_factory(self) -> Dict[str, Callable]:
        return {
            "EDGE"       : self._create_edge_model,
            "ELEVENLABS" : self._create_elevenlab_model,
            "OPENAI"     : self._create_openai_model,
            "KOKORO"     : self._create_kokoro_model,
        }

    def _create_edge_model(self):
        from .model_edge import EdgeSpeaker

        try:
            return EdgeSpeaker()
        except Exception as e:
            raise Exception(f"Error: Failed to initialize Edge TTS model {str(e)}")

    def _create_elevenlab_model(self):
        from .model_elevenlabs import ElevenLabsSpeaker
        
        try:
            return ElevenLabsSpeaker()
        except Exception as e:
            raise Exception(f"Error: Failed to initialize ElevenLabs model {str(e)} ")

    def _create_openai_model(self):
        from .model_openai import OpenAISpeaker
        
        try:
            return OpenAISpeaker()
        except Exception as e:
            raise Exception(f"Error: Failed to initialize OpenAI model {str(e)}")

    def _create_kokoro_model(self):
        from .model_kokoro import KokoroSpeaker
        
        try:
            return KokoroSpeaker()
        except Exception as e:
            raise Exception(f"Error: Failed to initialize Kokoro model {str(e)}")
    
    def _initialize_model(self):
        model_factory = self._get_model_factory()
        model = model_factory.get(self._model)
        if model is None:
            raise ValueError(f"Error: Model {self._model} is not supported.")
        
        return model()

    async def stop_speaking(self) -> None:
        """ Stop the speaker model """
        await self.model.stop_playback()
        
    async def speak(self, answer: str, language: Optional[str] = "en"):
        """ Speak the given text using the selected speaker model """
        try:
            print(f"\n({datetime.now().strftime('%H:%M:%S')}) EVA: {answer}")
            await self.model.eva_speak(answer, language)
            
        except Exception as e:
            raise Exception(f"Error: Failed to speak {str(e)} ")
        
    async def get_audio(self, text: str) -> str:
        """ Generate audio from text and save it to the media folder """
        return await self.model.generate_audio(text, self._language, self._media_folder)
    
    def _get_data_path(self) -> Path:
        """Return the path to the voice database."""
        return Path(__file__).resolve().parents[3] / 'data' / 'media'
        