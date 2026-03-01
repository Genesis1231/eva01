import time
import requests
from datetime import datetime
from config import logger
from typing import Type, Dict, List, Optional, Any

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool


class MusicianInput(BaseModel):
    """Input for music tool."""
    query: str = Field(description="prompt for Musician tool, should be within 20 words.")
    instrumental: bool = Field(description="Whether the song is instrumental, should only be 'True' or 'False' ")

class Musician(BaseTool):
    """ 
    Tool for creating music.
    Requires a Suno-API docker running on the base_url. Install from https://github.com/gcui-art/suno-api
    Methods:
        generate_music: Generate music using Suno-API.
        get_info: Get music information using Suno-API.
        _run: Main method to run the tool.
        run_client: Method to display the results in the client.
     
    """
    name: str = "music_maker"
    description: str = "Tool for creating music. Input should include the genre, theme, vibe and lyric direction of a song."
    type: str = "chat" # can be used in chatbot
    client: str = "none" # can be used in all clients
    args_schema: Type[BaseModel] = MusicianInput

    @staticmethod
    def generate_music(base_url: str, payload: Dict) -> List[Dict]:
        try:
            url = f"{base_url}/api/generate"
            response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'})
            return response.json()
        
        except Exception as e:
            logger.error(f"Error: Failed to generate music: {str(e)}")
            return []

    @staticmethod
    def get_info(base_url: str, audio_ids: str) -> List[Dict]:
        try:
            url = f"{base_url}/api/get?ids={audio_ids}"
            response = requests.get(url)
            return response.json()
        
        except Exception as e:
            logger.error(f"Error: Failed to get music info: {str(e)}")
            return []
        
    def _run(
        self,
        query: str,
        instrumental: bool,
        base_url: str = 'http://localhost:3000' # The url for the Suno-API docker
    ) -> Dict:
        payload = {
            "prompt": query,
            "make_instrumental": instrumental,
            "wait_audio": False
        }
        
        try:
            idx = self.generate_music(base_url, payload)
            for i in range(120):
                data = self.get_info(base_url, idx[0]['id'])
                if data[0]["status"] == 'streaming':
                    title = data[0]["title"]
                    desc = data[0]["tags"]
                    url = data[0]["audio_url"]
                    cover_url = data[0]["image_url"]
                    break
                time.sleep(1)
                print(f"({datetime.now().strftime('%H:%M:%S')}) Waiting for Suno to generate music ... {i}s", end="\r")
            else:
                logger.error(f"Error: Failed to create music: Request timeout")
                return {"error": f"Could not create music after waiting for a while."}
                
            content = f"I have created a song called '{title}'. The style is {desc}."

        except Exception as e:
            logger.error(f"Error: Failed to create music: {str(e)}")
            return {"error": f"Could not create music due to {str(e)}. DO NOT try again."}

        return {"action": content, "url": url, "cover_url": cover_url, "title": title}
 
    def run_client(self, client: Any, **kwargs) -> Optional[Dict]:
        return client.stream_music(url=kwargs.get("url"), cover_url=kwargs.get("cover_url"), title=kwargs.get("title"))
