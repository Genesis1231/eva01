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
    
    def __init__(self, speaker_model: str = "coqui", language: str = "en"):
        self._model_selection: str = speaker_model.upper()
        self._media_folder: str = self._get_data_path()
        self._language: str = language
        self.model = self._initialize_model()
        
        logger.info(f"Speaker: {self._model_selection} is ready.")
    
    def _get_model_factory(self) -> Dict[str, Callable]:
        return {
            "COQUI" : self._create_coqui_model,
            "ELEVENLABS" : self._create_elevenlab_model,
            "OPENAI" : self._create_openai_model,
        }
    
    def _create_coqui_model(self):
        from utils.tts.model_coqui import CoquiSpeaker
        
        try:
            return CoquiSpeaker(language=self._language)
        except Exception as e:
            raise Exception(f"Error: Failed to initialize Coqui TTS model {str(e)} ")

    def _create_elevenlab_model(self):
        from utils.tts.model_elevenlabs import ElevenLabsSpeaker
        
        try:
            return ElevenLabsSpeaker()
        except Exception as e:
            raise Exception(f"Error: Failed to initialize ElevenLabs model {str(e)} ")

    def _create_openai_model(self):
        from utils.tts.model_openai import OpenAISpeaker
        
        try:
            return OpenAISpeaker() # OpenAI does not need language selection
        except Exception as e:
            raise Exception(f"Error: Failed to initialize OpenAI model {str(e)}")
    
    def _initialize_model(self):
        model_factory = self._get_model_factory()
        model = model_factory.get(self._model_selection)
        if model is None:
            raise ValueError(f"Error: Model {self._model_selection} is not supported.")
        
        return model()

    def stop_speaking(self) -> None:
        """ Stop the speaker model """
        self.model.stop_playback()
        
    def speak(self, answer: str, language: Optional[str] = "en", wait: bool = True) -> None:
        """ Speak the given text using the selected speaker model """
        try:
            print(f"\n({datetime.now().strftime('%H:%M:%S')}) EVA: {answer}")
            self.model.eva_speak(answer, language, wait)
            
        except Exception as e:
            raise Exception(f"Error: Failed to speak {str(e)} ")
        
    def get_audio(self, text: str) -> str:
        """ Generate audio from text and save it to the media folder """
        return self.model.generate_audio(text, self._language, self._media_folder)
    
    def _get_data_path(self) -> Path:
        """Return the path to the voice database."""
        return Path(__file__).resolve().parents[2] / 'data' / 'media'
        