import os
from config import logger
from typing_extensions import Dict, List, Optional

from utils.tts import Speaker, AudioPlayer
from utils.vision import Watcher
from utils.stt import PCListener
from utils.extension import Window
from utils.extension.html import load_html

class WSLClient:
    """
    Class for eva to interact with the desktop client.
    Attributes:
        speaker: The speaker object to speak the response to the client.
        watcher: The watcher object to watch the client.
        listener: The listener object to listen to the client.
        player: The audio player object to stream the music to the client.
        window: The window object to launch the html to the client.

    """
    def __init__(self):
        self.player = AudioPlayer()
        self.window = Window()
        
        self.speaker: Optional[Speaker] = None
        self.watcher: Optional[Watcher] = None
        self.listener: Optional[PCListener] = None
                
    def initialize_modules(self, stt_model: PCListener, vision_model: Watcher, tts_model: Speaker) -> None:
        """ Initialize the modules for the client """
        self.speaker = tts_model
        self.watcher = vision_model
        self.listener = stt_model
    
    def send(self, data: Dict[str, str]) -> None:
        """ Send the data to the client """

        self.speaker.speak(
            data.get("speech"), 
            data.get("language"), 
            data.get("wait")
        )
        
    def receive(self, save_file: str=None) -> Dict:
        """ Receive the data from the client """
        
        observation = self.watcher.glance()
        message, language = self.listener.listen(save_file)
        
        return {
            "user_message": message,
            "observation": observation,
            "language": language
        }
    
    def start(self) -> Dict:
        """ Start the client """
        
        observation = self.watcher.glance()
        # html = load_html("hello.html", message="Hello there!")
        # self.window.launch_html(html)
        
        return {"observation": observation}

    def speak(self, response: str, wait: bool= True) -> None:
        """ Speak a single response to the client """
        
        self.speaker.speak(response, wait)
    
    def stream_music(self, url: str, cover_url: str, title: str) -> str:
        """ Client tool function, Stream the media to the client """
        try:
            html = load_html("music.html", image_url=cover_url, music_title=title)
            self.window.launch_html(html)
            self.player.stream(url)
            
            return f"The song '{title}' is playing."
        
        except Exception as e:
            logger.error(f"Failed to stream to client: {str(e)}")
            return "Client Error: Failed to launch the media player."

    def launch_youtube(self, id: str, title: str) -> str:
        """ Client tool function, Stream the youtube video to the client """
        try:
            html = load_html("youtube.html", video_id=id, video_title=title)
            self.window.launch_html(html)
        
        except Exception as e:
            logger.error(f"Failed to launch youtube video to client: {str(e)}")
            return "Client Error: The video player could not be launched properly."
    
    def launch_epad(self, html: str) -> Optional[str]:
        """ Client tool function, Launch the epad with HTML to the client """
        try:
            html = load_html("blank.html", full_html=html)
            self.window.launch_html(html)
            
            return None
        except Exception as e:
            logger.error(f"Failed to launch epad to client: {str(e)}")
            return "Client Error: The epad could not be launched properly." 
    
    def launch_gallery(self, image_urls: List) -> Optional[str]:
        """ Client tool function, Display the image to the client """
        
        html = "\n".join([f"<div class='slide'><img src='{url}'></div>" for url in image_urls])

        try:
            html = load_html("gallery.html", image_block=html)
            self.window.launch_html(html)
            
            return None
        
        except Exception as e:
            logger.error(f"Error: Failed to display images: {str(e)}")
            return "Client Error: The images could not be displayed."
        
    def deactivate(self) -> None:
        self.watcher.deactivate()
            
    def send_over(self) -> None:
        pass
    
