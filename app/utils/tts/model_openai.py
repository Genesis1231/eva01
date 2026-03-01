from config import logger
import os
from threading import Thread
import secrets
from typing import Optional

from openai import OpenAI
from utils.tts.audio_player import AudioPlayer

class OpenAISpeaker:
    """ 
    Audio speaker using OpenAI TTS
    
    Attributes:
        model (OpenAI): The OpenAI model.
        voice (str): The voice to use for the TTS model.
        player_stream (PyAudio): The audio stream.
    Methods:
        eva_speak: Speak the given text using OpenAI.
        generate_audio: Generate audio files from text using OpenAI TTS.
    """
    
    def __init__(self, voice: str = "nova") -> None:
        self.model: OpenAI = OpenAI()
        self.audio_player: AudioPlayer = AudioPlayer()
        self.voice: str = voice  # default OpenAI voice
        self.audio_thread: Optional[Thread] = None
            
    def eva_speak(self, text: str, language: Optional[str] = None, wait: bool = True) -> None:
        """ Speak the given text using OpenAI """  
                                
        try:
            response = self.model.audio.speech.create(
                model="tts-1",
                voice=self.voice,
                response_format="mp3",
                input=text
            )
   
        except Exception as e:
            logger.error(f"Error during text to speech synthesis: {e}")
            return None
        
        if self.audio_thread and self.audio_thread.is_alive():
            self.audio_thread.join()

        if wait:
            self.audio_player.play_openai_stream(response)
        else:
            self.audio_thread = Thread(target=lambda: self.audio_player.play_openai_stream(response), daemon=True)
            self.audio_thread.start()
                
    def generate_audio(self, text: str, media_folder: str) -> Optional[str]:
        """ Generate mp3 from text using OpenAI TTS """
        
        filename = f"{secrets.token_hex(16)}.mp3"
        file_path = os.path.join(media_folder, "audio", filename)
        
        try:
            response = self.model.audio.speech.create(
                model="tts-1",
                voice=self.voice,
                response_format="mp3",
                input=text
            )
            
            with open(file_path, 'wb') as f:
                response.write_to_file(file_path)
            
            return f"audio/{filename}"
        
        except Exception as e:
            logger.error(f"Error during text to speech synthesis: {e}")
            return None
