from config import logger
from datetime import datetime
from typing_extensions import Optional

import numpy as np
import speech_recognition as sr

class Microphone:
    """
    A class for handling microphone input and speech detection.

    This class provides functionality to listen for audio input from a microphone and detect speech.
    It uses the speech_recognition library to handle the low-level audio processing and provides
    configurable parameters for speech detection sensitivity and timing limits.

    Attributes:
        recognizer.energy_threshold (int): 
            Energy level threshold used to detect speech vs silence.
            Higher values mean louder sounds are required to be considered speech.
        recognizer.dynamic_energy_threshold (bool): 
            If True, automatically adjusts the energy threshold
            based on ambient noise levels.
        max_listen_time (int): 
            Maximum number of seconds to listen for speech before timing out.
        speech_limit (int): Maximum duration in seconds allowed for a single speech segment.
            Helps manage input token usage by limiting very long inputs.
        phrase_time_limit (int): 
            Maximum duration in seconds allowed for a single phrase.
            Helps manage input token usage by limiting very long inputs.
        
    Examples:
        >>> # Initialize microphone and start listening
        >>> mic = Microphone()
        >>> audio_data = mic.listen()  # Returns numpy array of audio data if speech detected
    """

    def __init__(self)-> None:
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        self.recognizer.pause_threshold = 1.3 # for longer sentence
        self.recognizer.dynamic_energy_threshold = True    
        self.max_listen_time = 300 # Listen for 5 minutes maximum
        self.speech_limit = 60  # Speak for 1 minute maximum
        self.phrase_time_limit = 1 # for shorter sentence 

    def detect(self)->bool:
        """ Detect if there is any speech """
        
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
            self.recognizer.energy_threshold = 2000
            logger.info(f"Detecting for the speech...")
            while True:
                audio = self.recognizer.listen(source, phrase_time_limit=self.phrase_time_limit)
                try:
                    if audio and len(audio.frame_data) > 10:
                        return True

                except Exception as e:
                    raise Exception(f"Error: Failed to recognize audio: {str(e)}")
        
    def listen(self) -> Optional[np.ndarray]:
        """
        Listens for audio input from the microphone and returns the audio data as a numpy array.

        Returns:
            Optional[np.ndarray]: The audio data as a numpy array if speech is detected, otherwise None.
        """
    
        with self.microphone as source:
            print(f"({datetime.now().strftime('%H:%M:%S')}) EVA is listening audio now...", end="\r", flush=True)
            self.recognizer.adjust_for_ambient_noise(source)  # Adjust for ambient noise
            self.recognizer.energy_threshold = 1000
            audio_buffer = self.recognizer.listen(source, timeout=self.max_listen_time, phrase_time_limit=self.speech_limit)
            print("\033[K")  # Clear the current line using ANSI escape code
            
            try:
                raw_data = np.frombuffer(audio_buffer.get_raw_data(convert_rate=16000), dtype=np.int16)
                audiodata = raw_data.astype(np.float32) / 32768.0
                return audiodata
                
            except sr.WaitTimeoutError:
                logger.warning("Listener: No speech detected in the waiting period.")
                return None
            
            except Exception as e:
                logger.error(f"Listener: Failed to listen to audio: {str(e)}")
                return None