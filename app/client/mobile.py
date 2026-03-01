import os
import threading
import asyncio
from config import logger
import time
import json
import secrets

from typing import Dict, List

from utils.tts import Speaker
from utils.stt import Transcriber
from utils.vision import Describer
from client.connection import ConnectionManager

class MobileClient:
    def __init__(self):   
        self.session_id = None
        self.server_thread = None
        
        self.server: ConnectionManager = None
        self.speaker: Speaker = None

    def initialize_modules(self, stt_model: Transcriber, vision_model: Describer, tts_model: Speaker) -> None:
        """Initialize the modules for mobile client"""
        self.server = ConnectionManager(stt_model, vision_model)
        self.speaker = tts_model
        self.initialize_client()

    def initialize_client(self) -> None:
        try:
            self.server_thread = threading.Thread(target=self.server.run_server, daemon=True)
            self.server_thread.start()

        except Exception as e:
            raise Exception(f"Error initializing server: {str(e)}")

    def send_data(self, data_str: str) -> None:
        """Send data to the Mobile client through FastAPI"""
        async def send_message():
            await self.server.send_message(data_str)

        try:
            asyncio.run(send_message())
        except RuntimeError as e:
            logger.error(f"Error in sending message: {str(e)}")
            
        
    def send(self, data: Dict) -> None:
        """process the data and send to the Mobile client"""
        if not data:
            logger.warning("No data is sent to client.")
            return

        speech_text = data["speech"]
        audio_path = self.speaker.get_audio(speech_text)
        
        data_json = { 
                "session_id": self.session_id, 
                "type": "audio", 
                "content": audio_path,
                "text": speech_text
        }

        print(f"Sending data to client: {json.dumps(data_json, indent=2)}")
        self.send_data(json.dumps([data_json]))
    
    def send_over(self) -> None:
        """inform the client the current data package is over"""
        data_json = {
            "type": "over",
            "content": self.generate_session_id(),
        }
        
        self.send_data(json.dumps(data_json))
        
    def receive(self) -> Dict:
        """Receive data from the Mobile client"""
        while True:
            user_input = self.server.get_message()            
            if user_input:
                break
            
            time.sleep(1)
            continue
                
        self.session_id = user_input.get("session_id")
        
        observation = user_input.get("observation", "<|same|>")
        message, language = user_input.get("user_message", (None, None))
            
        return {
            "user_message": message,
            "observation": observation,
            "language": language
        }
        
    def start(self) -> Dict:
        """Start the client and wait for the client to initialize"""
        while True:
            user_input = self.server.get_message()
            
            if not user_input:
                time.sleep(1)
                continue
            
            observation = user_input.get("observation")
            if observation:
                break
            
        self.session_id = user_input.get("session_id")
        
        return {"observation": observation}

    def generate_session_id(self) -> str:
        """Generate a session id for the client"""
        return secrets.token_urlsafe(16)
    
    def __del__(self):
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join()
        
    def __repr__(self) -> str:
        return "MobileClient"
    
    def load_html(self, template: str, **kwargs) -> str:
        """Load the html from the html directory"""
        
        dir = os.path.dirname(__file__)
        html_path = os.path.join(dir, "html", f"{template}.html")
        
        try:
            with open(html_path, 'r') as f:
                html = f.read().strip()

        except FileNotFoundError:
            raise FileNotFoundError(f"template file {html_path} not found.")

        for key, value in kwargs.items():
            html = html.replace(f"<{key}>", value)

        return html
    
    def stream_music(self, mp3_url: str, cover_url: str, title: str) -> None:
        """Stream a music and cover image to mobile client"""
        try: 
            page = self.load_html(template="music", image_url=cover_url, music_title=title)
            data_json = [{
                "session_id": self.session_id, 
                "type": "mp3",
                "content": mp3_url,
            },
            {
                "type": "html",
                "content": page
            }]
        
            self.send_data(json.dumps(data_json))
            return {"user_message": f"Media Player:: The song '{title}' is playing."}
        
        except Exception as e:
            logger.error(f"Error: Failed to stream to client: {str(e)}")
            return {}
        
    def launch_youtube(self, id: str, title: str) -> bool:
        """Stream the youtube video to the client"""
        try:
            page = self.load_html("youtube", video_id=id, video_title=title)
            data_json = {
                "session_id": self.session_id, 
                "type": "html",
                "content": page
            }
            
            self.send_data(json.dumps(data_json))
            return {"observation": "The video player is launched."}
        
        except Exception as e:
            logger.error(f"Error: Failed to stream youtube video to client: {str(e)}")
            return {}
          
    def launch_epad(self, html: str) -> Dict:
        try:
            page = self.load_html("blank", full_html=html)
            data_json = {
                "session_id": self.session_id, 
                "type": "html",
                "content": page
            }
            
            self.send_data(json.dumps(data_json))
            return {"observation": "The epad is launched."}
        except Exception as e:
            logger.error(f"Error: Failed to launch epad to client: {str(e)}")
            return {}