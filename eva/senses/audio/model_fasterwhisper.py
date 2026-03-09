from typing import List, Optional, Tuple, Union

import numpy as np
import torch
from faster_whisper import WhisperModel

from config import logger


class FWTranscriber:
    """
    Faster Whisper transcriber service.
    
    Attributes:
        language: The target language code (e.g., "en") or None for auto-detection.
        device: "cuda" or "cpu".
        model: The underlying WhisperModel instance.
    """

    def __init__(self, language: str = "en") -> None:
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.compute_type = "float16" if self.device == "cuda" else "int8"
        self.model: Optional[WhisperModel] = None
        
        # Handle "multilingual" or explicit language
        if language.upper() == "MULTILINGUAL":
            self.language = None
            self.model_name = "large-v3"
        else:
            self.language = language
            self.model_name = "distil-medium.en" if language == "en" else "large-v3"

    def init_model(self) -> None:
        """Lazy initialization of the WhisperModel."""
        if self.model is not None:
            return
    
        try:
            self.model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize Faster Whisper model: {e}")
            raise
        
        logger.debug(f"Initialized FW model '{self.model_name}' on {self.device}.")

    def transcribe_audio(
        self, 
        audio_clip: Union[np.ndarray, List[float]]
    ) -> Tuple[Optional[str], Optional[str]]:
        """Transcribe the given audio clip."""
        
        if self.model is None:
            logger.error("Faster Whisper model is not initialized.")
            return (None, None)

        if not isinstance(audio_clip, (np.ndarray, list)):
            logger.error(f"Invalid audio format: {type(audio_clip)}")
            return (None, None)

        if isinstance(audio_clip, list):
            audio_clip = np.array(audio_clip, dtype=np.float32)

        try:
            segments, info = self.model.transcribe(
                audio_clip,
                language=self.language,
                vad_filter=True,
                vad_parameters=dict(threshold=0.3)
            )

            # Consume generator to build full text
            text = "".join(segment.text for segment in segments).strip()
            
            # Determine return language
            # Use the detected language from info or the default language
            detected_lang = (info.language[:2].lower() if info.language else self.language)
            
            return (text, detected_lang)

        except Exception as e:
            logger.error(f"Failed to transcribe audio: {e}")
            return (None, None)

    def close(self) -> None:
        """Explicitly release resources."""
        if hasattr(self, 'model') and self.model:
            self.model.model.unload_model()
            del self.model
            self.model = None

        if self.device == "cuda":
            torch.cuda.empty_cache()

    def __del__(self) -> None:
        self.close()
