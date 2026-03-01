import os
from config import logger
from typing import Optional, List
from numpy import ndarray

from torch import cuda
from faster_whisper import WhisperModel

class FWTranscriber:
    """
    Faster Whisper transcriber
    
    Attributes:
        language: The language to transcribe the audio in.
        device: The device to use for the model.
        model: The Faster Whisper model.
    Methods:
        transcribe_audio: Transcribe the given audio clip using the Faster Whisper model.
    """
    
    def __init__(self, language: str = "en"):
        self.language: str = language
        self.device: str = "cuda" if cuda.is_available() else "cpu"
        self.model: WhisperModel = self._initialize_model()
    
    def _initialize_model(self):
        """ Get the appropriate model based on the language """
        
        model_name = "distil-medium.en" if self.language == "en" else "large-v3"
        
        # If the language is set to "multilingual", do not specify a language.
        if self.language.upper() == "MULTILINGUAL":
            self.language = None
            
        return WhisperModel(model_name, device=self.device, compute_type="float16")
    
    def transcribe_audio(self, audioclip) -> tuple[Optional[str], Optional[str]]:
        """ Transcribe the given audio clip using the Faster Whisper model """
        
        if not isinstance(audioclip, (List, ndarray)):
            raise ValueError("Invalid audio format provided for transcription.")
        
        try:
            segments, info = self.model.transcribe(
                audioclip,
                language=self.language,
                vad_filter=True,
                vad_parameters=dict(
                    threshold=0.3,
                )
            )
            
            transcription = "".join(segment.text for segment in segments)
            
            if self.language is None and info.language_probability > 0.8:
                transcription_language = info.language
            else:
                transcription_language = self.language
                
        except Exception as e:
            logger.error(f"Failed to transcribe audio: {str(e)}")
            return None, None
        
        return transcription, transcription_language

    def __del__(self):
        """ clean up the transcriber """
        if hasattr(self, 'model') and self.model is not None:
            del self.model
            self.model = None
            
        # Clear CUDA cache if using GPU
        if self.device == "cuda":
            cuda.empty_cache()
