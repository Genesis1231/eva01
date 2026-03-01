from config import logger
from io import BytesIO
from typing_extensions import Dict, Optional, List

from PIL import Image
import base64
from pydub import AudioSegment
import numpy as np
import cv2

    
def convert_audio_data(mp3_data: str) -> Optional[np.ndarray]:
    """Convert the given MP3 data to an audio numpy array."""
    
    if not mp3_data:
        raise ValueError("No MP3 data provided")
    
    try:
        mp3_data = base64.b64decode(mp3_data)
        audio = AudioSegment.from_mp3(BytesIO(mp3_data))

        audio = audio.set_channels(1).set_frame_rate(16000)

        # Convert to numpy array
        samples = np.array(audio.get_array_of_samples())
        audio_data = samples.astype(np.float32) / np.iinfo(samples.dtype).max
    
    except Exception as e:
        logger.info(f"Error converting mp3 to audio data: {str(e)}")
        return None

    return audio_data

def convert_image_data(image_data: str) -> Optional[np.ndarray]:

    try:
        image_data = base64.b64decode(image_data)
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
        return img
    
    except Exception as e:
        logger.warning(f"Error converting image to numpy: {str(e)}")
        return None

def convert_to_mp3(audio_data) -> str:
    """Convert the given audio data to an MP3 format."""
    
    samples = (np.array(audio_data) * np.iinfo(np.int16).max).astype(np.int16)
    
    audio_segment = AudioSegment(
        samples.tobytes(), 
        frame_rate=22050, 
        sample_width=samples.dtype.itemsize, 
        channels=1
    )
    
    mp3_buffer = BytesIO()
    audio_segment.export(mp3_buffer, format="mp3")
    mp3_data = mp3_buffer.getvalue()
    
    # Encode the byte data to base64 string
    mp3_base64 = base64.b64encode(mp3_data).decode('utf-8')
        
    return mp3_base64


async def validate_data(message_json: Dict) -> bool:
    for data in message_json['data']:
        if data['type'] in ['frontImage', 'backImage']:
            if not validate_image_format(data['content']):
                return False
        
        elif data['type'] == 'audio':
            if not validate_audio_format(data['content']):
                return False
    
    return True

def validate_image_format(data) -> bool:
    try:
        data_bytes = base64.b64decode(data)
        img = Image.open(BytesIO(data_bytes))
        img.verify()   
        return True
    
    except (IOError, SyntaxError) as e:
        logger.error(f"Invalid image received: {e}")
        return False


def validate_audio_format(data) -> bool:
    if len(data) <= 0 or not any(data):
        return False
    
    return True