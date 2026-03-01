from config import logger
import os
import time
from threading import Thread
import secrets
from typing import Optional, List
from queue import Queue, Empty

from TTS.api import TTS
import nltk
import numpy as np
from torch import cuda
from pydub import AudioSegment

from utils.tts.audio_player import AudioPlayer

class CoquiSpeaker:
    """ 
    Audio speaker using Coqui TTS
    
    Attributes:
        model_name (str): The name of the TTS model to use.
        device (str): The device to use for the TTS model.
        model (TTS): The TTS model.
        player (AudioPlayer): The audio player.
        audio_queue (Queue): The audio queue.
        play_thread (Thread): The play thread.
    Methods:
        play: Play the audio.
        eva_speak: Speak the given text using Coqui TTS.
        stop_playback: Stop the playback.
        generate_audio: Generate audio files from text using Coqui TTS.
    """
    
    def __init__(self, language: str = "en")-> None:
        self.language: str = language
        self.play_thread: Optional[Thread] = None
        self.speakerID: Optional[str] = None
        self.device: str = "cuda" if cuda.is_available() else "cpu"
        
        self.audio_queue: Queue = Queue()    
        self.model: TTS = self._initialize_TTS()
        self.player: AudioPlayer = AudioPlayer()

    def _initialize_TTS(self) -> TTS:
        """ Initialize the TTS model """
            
        if self.language == "en":
            model_name = "tts_models/en/vctk/vits"
            self.speakerID = "p306"
        else:
            model_name = "tts_models/multilingual/multi-dataset/xtts_v2"
            self.speakerID = "Daisy Studious"
        
        return TTS(model_name=model_name).to(self.device)
        
    def play(self) -> None:
        while True:
            try:
                wav = self.audio_queue.get(timeout=0.1)  # 1 second timeout
                if wav is None:
                    break

                # newwav = np.array(wav) #speed up the audio
                # wav = pyrb.time_stretch(newwav, 16000, 1.1)                            
                self.player.play_audio(wav)
                time.sleep(0.3)  # pause between sentences
                self.audio_queue.task_done()
            except Empty:
                continue  # If queue is empty, continue the loop
    
    def _generate_speech(self, text: str, language: Optional[str]) -> List[np.ndarray]:
        """ Generate speech from text using Coqui TTS """
        
        language = "zh-cn" if language == "zh" else language # correct the language code for TTS model
        
        if self.language == "en":
            return self.model.tts(text=text, speaker=self.speakerID)
        else:
            return self.model.tts(text=text, speaker=self.speakerID, language=language)
    
    def eva_speak(self, text: str, language: Optional[str] = "en", wait: bool = True) -> None:
        """ Speak the given text using Coqui TTS """
        
        sentences = nltk.sent_tokenize(text)
        if not self.play_thread:
            self.play_thread = Thread(target=self.play, daemon=True)
            self.play_thread.start()
                    
        for sentence in sentences:
            wav = self._generate_speech(sentence, language)
            self.audio_queue.put(wav)
        
        if wait:
            self.audio_queue.put(None)
            self.stop_playback()
    
    def stop_playback(self) -> None:
        if self.play_thread:
            self.play_thread.join()
            self.play_thread = None
        
    def generate_audio(self, text: str, media_folder: str) -> Optional[str]:
        """ Generate mp3 from text using Coqui TTS """
        audio_files = []
        try:
            sentences = nltk.sent_tokenize(text)
            for sentence in sentences:
                wav = self._generate_speech(sentence)
                audio_data = (np.array(wav) * 32767).astype(np.int16)
                filename = f"{secrets.token_hex(16)}.mp3"
                
                # Create AudioSegment from raw audio data
                audio = AudioSegment(
                    audio_data.tobytes(),
                    frame_rate=22050,
                    sample_width=2,
                    channels=1
                )
                file_path = os.path.join(media_folder, "audio", filename)
                audio.export(file_path, format="mp3")
                audio_files.append(f"audio/{filename}")
                                
            return audio_files
    
        except Exception as e:
            logger.error(f"Error during text to speech synthesis: {e}")
            return None

    def __del__(self):
        self.stop_playback()
        
        if hasattr(self, 'model') and self.model is not None:
            del self.model
            self.model = None

        # Clear CUDA cache if using GPU
        if self.device == "cuda":
            cuda.empty_cache()
