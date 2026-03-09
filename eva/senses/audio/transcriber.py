from typing import Dict, Optional, Callable, Tuple
from config import logger

class Transcriber:
    """
    The Transcriber class is responsible for transcribing audio clips using different models.
    
    Args:
        model_name (str): The name of the model to use for transcription. Default is "faster-whisper".
        language (str): The language code for transcription (e.g., "en").
    
    Examples:
        >>> transcriber = Transcriber(model_name="faster-whisper", language="en")
        >>> transcription = transcriber.transcribe(audioclip)
    """
    
    def __init__(self, model_name: str = "faster-whisper"):
        self._model_selection: str = model_name.upper()
        self.model = self._initialize_model()
        
        logger.debug(f"Transcriber: {self._model_selection} is ready.")
    
    def _get_model_factory(self) -> Dict[str, Callable]:
        return {
            "FASTER-WHISPER": self._create_fasterwhisper_model,
            "WHISPER": self._create_whisper_model,
        }
        
    def _create_fasterwhisper_model(self):
        from eva.senses.audio.model_fasterwhisper import FWTranscriber
        
        try:
            return FWTranscriber()
        except Exception as e:
            logger.error(f"Error: failed to load Faster Whisper Model: {e}")
            raise 
        
    def _create_whisper_model(self):
        from eva.senses.audio.model_whisper import WhisperTranscriber
        
        try:
            return WhisperTranscriber()
        except Exception as e:
            logger.error(f"Error: failed to load Whisper Model: {e}")
            raise 
        
    def _initialize_model(self):
        """ Initialize the selected transcription model """
        
        model_factory = self._get_model_factory()
        create_model = model_factory.get(self._model_selection)
        
        if create_model is None:
            raise ValueError(f"Error: Model {self._model_selection} is not supported")
        
        return create_model()
    

    def transcribe(self, audioclip) -> Optional[Tuple[str, str]]:
        """ Transcribe the given audio clip. """

        transcription = self.model.transcribe_audio(audioclip)
        if not transcription:
            return None

        text, language = transcription

        # Format content for the system
        content = f"{text.strip()}"

        return (content, language)

    def close(self) -> None:
        """Release the underlying model resources."""
        if hasattr(self.model, 'close'):
            self.model.close()
            logger.debug("Transcriber: Model released.")
