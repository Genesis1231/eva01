import tempfile
from config import logger
from typing import Optional, List
from numpy import ndarray

from groq import Groq
import scipy.io.wavfile as sf

class GroqTranscriber:   
    def __init__(self, language: str = "en"):
        self.language: str = language
        self.model: Groq = Groq()
        self._sample_rate: int = 16000
     
    def transcribe_audio(self, audioclip) -> tuple[Optional[str], Optional[str]]:
        """ Transcribe the given audio clip using the OpenAI Whisper model """
        
        if not isinstance(audioclip, (List, ndarray)):
            raise ValueError("Invalid audio format provided for transcription.") 
        
        model_name = "distil-whisper-large-v3-en" if self.language == "en" else "whisper-large-v3-turbo"
        
        try:
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=True) as temp_file:
                sf.write(temp_file.name, self._sample_rate, audioclip)
                with open(temp_file.name, 'rb') as audio_file:
                    api_params = {
                        "model": model_name,
                        "file": audio_file,
                        "response_format": "verbose_json",
                        "prompt": "Specify punctuations.",
                    }
                    
                    if self.language != "multilingual":
                        api_params["language"] = self.language
                    
                    response = self.model.audio.transcriptions.create(**api_params)
                    
                # return the language of the audio if it is multilingual
                language = response.language if self.language == "multilingual" else self.language
        
        except Exception as e:
            logger.error(f"Error: Failed to transcribe audio: {str(e)}")
            return None, None

        return response.text, language