import requests
import os
import time
from datetime import datetime
from pathlib import Path
from config import logger
from typing import List, Dict, Optional

import cv2
import numpy as np

class MidjourneyServer():
    """
    A class for sending prompts to discord midjourney and getting the image url.
    simple implementation to retrieve images from midjourney.
    
    Attributes:
        *These IDs need to be extracted from the discord midjourney channel*
        application_id: The application id of the midjourney server.
        guild_id: The guild id of the midjourney server.
        channel_id: The channel id of the midjourney server.
        version: The version of the midjourney server.
        id: The id of the midjourney server.
        authorization: The authorization of the midjourney server.
        _image_dir: The directory to save the images.
        _prev_message_id: The previous message id.
        
    """
    def __init__(self):
        self.application_id = os.environ.get("MJ_Application_ID")
        self.guild_id = os.environ.get("MJ_Guild_ID")
        self.channel_id = os.environ.get("MJ_Channel_ID")
        self.version = os.environ.get("MJ_Version")
        self.id = os.environ.get("MJ_ID")
        self.authorization = os.environ.get("MJ_Authorization")
        
        self._url = "https://discord.com/api/v9/interactions"
        self._msg_url = f'https://discord.com/api/v9/channels/{self.channel_id}/messages'
        self._headers = {
            'Authorization': self.authorization,
            'Content-Type': 'application/json',
        }
        
        # get the image directory and the message id
        self._image_dir = self._get_temp_dir()        
        self.prev_message_id = self._load_previous(self._msg_url, self._headers)
    
    @staticmethod
    def _get_temp_dir() -> str:
        """Get or create the EVA temp directory"""
        
        temp_dir = Path.home() / '.eva' / 'images'
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        return str(temp_dir)
    
    @staticmethod
    def _load_previous(msg_url: str, headers: Dict) -> Optional[str]:
        """Load the previous message id"""
        try:
            with requests.get(msg_url, headers=headers) as response:
                response.raise_for_status()
                messages = response.json()
                if messages:
                    return messages[0].get('id')
        except Exception as e:
            logger.error(f"Error loading previous message: {e}")
            
        return None
        
    def _get_data(self, prompt: str)-> Dict:
        """ Get the data for the discord request """
        return {
            "type": 2,
            "application_id": self.application_id,
            "guild_id": self.guild_id,
            "channel_id": self.channel_id,
            "session_id": "d7cf82a1fbdb21dc5b06b47eeb2ed32d",
            "data": {
                "version": self.version,
                "id": self.id,
                "name": "imagine",
                "type": 1,
                "options": [
                    {
                        "type": 3,
                        "name": "prompt",
                        "value": prompt
                    }
                ],
                "application_command": {
                    "id": self.id,
                    "application_id": self.application_id,
                    "version": self.version,
                    "default_member_permissions": None,
                    "type": 1,
                    "nsfw": False,
                    "name": "imagine",
                    "description": "Create images with Midjourney",
                    "dm_permission": True,
                    "contexts": None,
                    "options": [
                        {
                            "type": 3,
                            "name": "prompt",
                            "description": "The prompt to imagine",
                            "required": True
                        }
                    ]
                },
                "attachments": []
            },
        }
        
    def send_message(self, prompt: str) -> Optional[List[str]]:
        """ Send a prompt to discord and get the image url """
        try:
            with requests.post(self._url, headers=self._headers, json=self._get_data(prompt)) as response:
                response.raise_for_status()
        except requests.RequestException as e:
            return None

        logger.debug(f"Sent midjourney prompt: {prompt}")
        
        for i in range(60):
            time.sleep(1)
            print(f"({datetime.now().strftime('%H:%M:%S')}) Waiting for midjourney to generate image ... {i}s", end="\r")
            
            try:
                with requests.get(self._msg_url, headers=self._headers) as response:
                    response.raise_for_status()
                    messages = response.json()
                    if not messages or messages[0]['id'] == self.prev_message_id or not messages[0]['components'][0]['components']:
                        continue
                    
                    image_url = messages[0]['attachments'][0]['proxy_url']
                    with requests.get(image_url) as image_response:
                        image_response.raise_for_status()
                        image_data = image_response.content
                    break
            except (KeyError, IndexError):
                continue
            except Exception as e:
                logger.error(f"Error getting image: {e}")
                return None
        else:
            logger.error("Timeout waiting for creating image.")
            return None

        self.prev_message_id = messages[0]['id']
        return self._process_image(image_data, self.prev_message_id)


    def _process_image(self, image_data: bytes, image_id: str) -> List[str]:
        """Process the image data and save it"""
        
        try:
            png_data = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(png_data, cv2.IMREAD_COLOR)
            
            height, width = img.shape[:2]
            mid_h, mid_w = height // 2, width // 2
        
            # Split the image into 4 parts without enlarging the image
            # we can enlarge the image with additional functions
            parts = [img[:mid_h, :mid_w], img[:mid_h, mid_w:], 
                     img[mid_h:, :mid_w], img[mid_h:, mid_w:]]
            
            
            base_filename = os.path.join(self._image_dir, image_id)
            image_paths = [f"{base_filename}_{i+1}.jpg" for i in range(4)]
            
            for i, part in enumerate(parts):
                cv2.imwrite(image_paths[i], part)
   
            return image_paths
        
        except Exception as e:
            logger.error(f"Error processing image after generation: {e}")
            return None
    