"""
AudioPlayer: Audio playback for streams and files. All methods are blocking — wrap with asyncio.to_thread() in async contexts.
  stream(path) -> plays file/url via mpv, blocks until done
  play_generator(generator) -> true streaming via MPV stdin
  play_pcm(samples, sample_rate) -> plays raw PCM via sounddevice
  stop_playback() -> stops any playing audio
"""

import os
import subprocess
import tempfile
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
    play_generator: Stream python generator directly.
    stop_playback: Interrupt all playback.
    """
    def __init__(self):
        self.player: Optional[mpv.MPV] = None
        self._process: Optional[subprocess.Popen] = None
        self._stop_event: bool = False

    def stop_playback(self) -> None:
        """Stop all active audio playback immediately."""
        self._stop_event = True

        # Stop mpv python player
        try:
            # Recreate player to fully stop current playback
            if hasattr(self, 'player') and self.player:
                self.player.terminate()
                self.player = None
        except Exception:
            pass
            
        # Stop mpv streaming subprocess
        if self._process:
            try:
                self._process.terminate()
            except Exception:
                pass
            self._process = None

    def play_pcm(self, samples, sample_rate: int) -> None:
        """Play raw PCM (numpy float32 array) via sounddevice. Blocks until done."""
        sd.play(samples, sample_rate)
        sd.wait()
    
            
    def play_sd_file(
        self,
        audio_data: Optional[Union[str, np.ndarray]],
        sample_rate: int = 22050,
    ) -> None:
        """Play audio from a file path or numpy array. Blocks until done."""
        if audio_data is None:
            return

        if isinstance(audio_data, str):
            if not os.path.exists(audio_data):
                raise FileNotFoundError(f"File not found: {audio_data}")
            audio_data, sample_rate = sf.read(audio_data)

        if audio_data.dtype != np.float32:
            max_val = np.iinfo(audio_data.dtype).max if np.issubdtype(audio_data.dtype, np.integer) else 1.0
            audio_data = (audio_data / max_val).astype(np.float32)

        sd.play(audio_data, sample_rate)
        sd.wait()
        
       
    def stream(self, path: str) -> None:
        """Blocking: plays file/url via mpv. Wrap with asyncio.to_thread() in async contexts."""
        if not path:
            return
        try:
            self.player = mpv.MPV()
            self.player.play(path)
            self.player.wait_for_playback()
            self.player.terminate()
            self.player = None
        except Exception as e:
            raise Exception(f"Error: Failed to play stream: {e}")
    
    
    def play_generator(self, generator) -> None:
        """Play an iterable stream of audio chunks directly via MPV stdin (true streaming)."""
        
        self._stop_event = False
        self._process = subprocess.Popen(
            ["mpv", "--no-cache", "--no-terminal", "--", "fd://0"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        
        try:
            for chunk in generator:
                if self._stop_event:
                    break
                if chunk and self._process.poll() is None:
                    self._process.stdin.write(chunk)
                    self._process.stdin.flush()
        except (BrokenPipeError, OSError):
            pass
        finally:
            if self._process and self._process.stdin:
                self._process.stdin.close()
            if self._process:
                self._process.terminate()
                self._process.wait()
            self._process = None
            

