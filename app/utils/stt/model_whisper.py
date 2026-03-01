import tempfile
from config import logger
from typing import Optional, List
from numpy import ndarray

from openai import OpenAI
import scipy.io.wavfile as sf

class WhisperTranscriber:
    """
    OpenAI Whisper transcriber
    
    Attributes:
        language: The language to transcribe the audio in.
        model: The OpenAI model.
        temp_path: The path to the temporary file before sending to OpenAI.
    Methods:
        transcribe_audio: Transcribe the given audio clip using the OpenAI Whisper model.   
    """
    
    def __init__(self, language: str = "en"):
        self.model: OpenAI = OpenAI()
        self.sample_rate: int = 16000
        self.language: str = language
    
    def transcribe_audio(self, audioclip) -> tuple[Optional[str], Optional[str]]:
        """ Transcribe the given audio clip using the OpenAI Whisper model """

        if not isinstance(audioclip, (List, ndarray)):
            raise ValueError("Invalid audio format provided for transcription.")
        
        try:
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=True) as temp_file:
                sf.write(temp_file.name, self.sample_rate, audioclip)

                with open(temp_file.name, 'rb') as audio_file:
                    api_params = {
                        "model": "whisper-1",
                        "file": audio_file,
                        "prompt": "specify punctuation",
                        "response_format": "verbose_json",
                    }
                
                    if self.language != "multilingual":
                        api_params["language"] = self.language
                        
                    response = self.model.audio.transcriptions.create(**api_params)
                
                # return the language of the audio if it is multilingual
                language = response.language if self.language == "multilingual" else self.language
                
        except Exception as e:
            logger.error(f"Error: Failed to transcribe audio with OpenAI Whisper: {str(e)}")
            return None, None
        
        return response.text, language