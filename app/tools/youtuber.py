import json
from config import logger
from random import choice
from typing import Type, Dict, Optional

from pydantic import BaseModel, Field
from langchain_community.tools import BaseTool
from youtube_search import YoutubeSearch

class YoutubeInput(BaseModel):
    query: str = Field(description="Input for Youtube tool, no more than 4 words.")
    
class Youtuber(BaseTool):
    """
    Tool that queries YouTube, supports both video and shorts.
    Methods:
        _run: Main method to run the tool.
        run_client: Method to display the video in the client.
    
    """
    name: str = "youtube_search"
    description: str = "Tool for searching youtube videos. the input should be short keyword query."
    type: str = "conversational"
    client: str = "all"
    args_schema: Type[BaseModel] = YoutubeInput

    @staticmethod
    def _get_video_id(video_data: Dict) -> str:
        """ Get the video id from the url """
        
        url = video_data.get("url_suffix")
        video_id = url.split("shorts/")[1] if "shorts" in url else url.split('?v=')[1].split('&')[0]
        return video_id
    
    def _run(
        self,
        query: Optional[str] = None,
    ) -> Dict:
        """ Main method to run the tool """
        if not query:
            logger.error("No query was provided.")
            return {"error": "Error: No query provided for youtube tool, please try again."}

        try:
            results = YoutubeSearch(query).to_json()
        except Exception as e:
            logger.error(f"Failed to find video: {str(e)}.")
            return {"error": f"Error: Failed to get Youtube video due to {str(e)}."}
    
        if not results:
            return {"error": f"No search results with query: {query}, please revise and try again."}
        
        video_data = choice(json.loads(results)["videos"])
        video_id = self._get_video_id(video_data)
        video_title = video_data.get("title")
        
        content = f"I have found a video on YouTube by {video_data.get('channel')} and published {video_data.get('publish_time')}."
        return  {"action": content, "url" : video_id, "title": video_title}

    def run_client(self, client, **kwargs: Dict) -> Optional[Dict]:
        return client.launch_youtube(id=kwargs.get("url"), title=kwargs.get("title"))
