import os
import tempfile
from io import BytesIO
from threading import Thread
from typing import Union, Optional

import sounddevice as sd
import soundfile as sf
import numpy as np
import mpv

class AudioPlayer:
    """
    A class to play audio data.
    
    Attributes:
    device (str): The device used to play audio.
    sample_rate (int): The sample rate of the audio data.
    speaking (bool): A flag to indicate if audio is currently speaking.
    audio_thread (threading.Thread): A thread to play audio.
    
    Methods:
    play_audio: Play audio data from a file or numpy array.
    play_mp3_stream: Play an mp3 stream.
    stream: Stream an mp3 url.
    
    """
    def __init__(self):
        self._sample_rate: int = 22050
        self._audio_thread: Optional[Thread] = None
        self.player: mpv.MPV = mpv.MPV()
            
    def play_audio(self, audio_data: Optional[Union[str, np.ndarray]], from_file: bool = False)-> None:
        if audio_data is None:
            return
        
        try:
            if from_file:
                if not os.path.exists(audio_data):
                    raise FileNotFoundError(f"File not found: {audio_data}")
                
                audio_data, sample_rate = sf.read(audio_data) 
                
                # Ensure audio data is in float32 format for compatibility with sounddevice
                if audio_data.dtype != np.float32:
                    # Normalize the data by the maximum value of its type
                    max_val = np.iinfo(audio_data.dtype).max if np.issubdtype(audio_data.dtype, np.integer) else 1.0
                    audio_data = (audio_data / max_val).astype(np.float32)
            else:
                sample_rate = self._sample_rate
            
            # Play the audio
            sd.play(audio_data, sample_rate)
            sd.wait()
            
        except Exception as e:
            raise Exception(f"Error: Failed to play audio: {e}")
        
    def _play_mp3_stream(self, mp3_url: str)-> None:
        try:
            player = mpv.MPV(ytdl=True)
            player.volume = 50
            player.play(mp3_url)
            player.wait_for_playback()
            
            # clean up
            player.terminate()
            
        except Exception as e:
            raise Exception(f"Error: Failed to play mp3 stream: {e}")
       
    def stream(self, url: str)-> None:
        if not url:
            return
        
        if self._audio_thread and self._audio_thread.is_alive():
            self._audio_thread.join()
            
        self._audio_thread = Thread(target=self._play_mp3_stream, daemon=True, args=(url,))
        self._audio_thread.start()
    
    
    def play_openai_stream(self, audio_stream) -> None:
        """Play audio directly from OpenAI's streaming response"""
        try:
            # Create a temporary file to store the audio
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                # Collect chunks and write to temp file
                for chunk in audio_stream.iter_bytes():
                    temp_file.write(chunk)
                temp_file_path = temp_file.name

            # Play the temporary file
            self.player.play(temp_file_path)
            self.player.wait_for_playback()
            
            # Clean up
            os.unlink(temp_file_path)
            
        except Exception as e:
            raise Exception(f"Error: Failed to play OpenAI stream: {e}")

    def __del__(self) -> None:
        if self._audio_thread and self._audio_thread.is_alive():
            self._audio_thread.join()
