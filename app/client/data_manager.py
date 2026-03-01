from config import logger
import json
import asyncio
from typing_extensions import Dict, Optional, List
import secrets

from utils.stt.transcriber import Transcriber
from utils.vision.describer import Describer
from client.functions import convert_audio_data 

class DataManager:
    """
    A class for managing data flow and processing in the client application.
    
    This class handles incoming data streams, processes various types of data (audio, images, etc.),
    and manages asynchronous queues for data processing. It integrates with speech-to-text and
    vision models to process audio and image data respectively.

    Attributes:
        session_data (asyncio.Queue): Queue for storing session data to be processed
        session_data_list (List[Dict]): List to store processed session data
        transcriber (Transcriber): Model for speech-to-text transcription
        img_describer (Describer): Model for image description/analysis
        processing_task (Optional[asyncio.Task]): Task for processing the data queue
    """
    
    def __init__(self, stt_model: Transcriber, vision_model: Describer) -> None:
        self.session_data = asyncio.Queue()
        self.session_data_list : List[Dict] = []
        
        self.transcriber: Transcriber = stt_model
        self.img_describer: Describer = vision_model
        self.processing_task = None
        
    async def start_queue(self) -> None:
        """Start the processing task."""
        self.processing_task = asyncio.create_task(self._process_queue())
        
    async def stop(self) -> None:
        """Stop the processing task."""
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
                
            except asyncio.CancelledError:
                pass
            
    async def process_message(self, message: str, client_id: Optional[str] = None) -> str:
        """Process incoming messages and handle them accordingly."""
        message_json = json.loads(message)
        session_id = message_json.get("session_id")
        message_type = message_json.get("type")
                
        response_data = {
            "session_id" : session_id,
            "type" : f"validation-{message_type}",
            "content" : "success"
            }
        
        await self.session_data.put(message_json) # put data in the queue for process
        
        return json.dumps(response_data)
    
    async def _process_queue(self) -> None:
        """Process the data in the queue."""
        while True:
            try:
                data = await self.session_data.get()
                if data is None:
                    continue

                data_type = data["type"]
                content = data["content"]
                
                result = None
                
                # process the data based on the data type
                match data_type:
                    case "audio":
                        audio_data = convert_audio_data(content)
                        result = self.transcriber.transcribe(audio_data)
                    
                    case "frontImage" | "backImage":
                        result = self.img_describer.describe("vision", content)
                    
                    case "over":
                        result = "success"
                    
                    case _:
                        logger.error(f"Unsupported data type: {data_type}")
                        result = "error"
                        return

                data["content"] = result
                self.session_data_list.append(data)
                logger.debug(f"Session data: {self.session_data_list}")
                await asyncio.sleep(0.5)
                
            except asyncio.CancelledError:
                logger.info("Processing queue cancelled")
                break
            except Exception as e:
                logger.error(f"Error in processing data queue: {e}", exc_info=True)
                continue
            
    def _generate_session_id(self) -> str:
        """Generate a session id for the client."""
        return secrets.token_urlsafe(16)
    
    def get_session_data(self) -> str:
        """Get the session data for the server."""
        data_json = { 
                        "session_id": self._generate_session_id(), 
                        "type": "receive_start", 
                        "content": "success"
        }
        
        return json.dumps(data_json)

    def get_first_data(self) -> Optional[Dict]:
        """Get the first session data in the list."""
        
        if not self.session_data_list:
            return None
        
        # identify the first session
        # Find first session with type "over" and get its session_id
        try:
            idx = next(i for i, session in enumerate(self.session_data_list) if session.get("type") == "over")
            first_session_data = {"session_id": self.session_data_list[idx]["session_id"]}
        except StopIteration:
            return None

        # mapping the data type to the data name
        type_mapping = {
            'frontImage': 'observation',
            'backImage': 'view',
            'audio': 'user_message'
        }
        
        # get the data from the first session
        for i in range(idx):
            data_type = self.session_data_list[i].get('type')
            if data_type in type_mapping:
                first_session_data[type_mapping[data_type]] = self.session_data_list[i].get('content')
        
        self.session_data_list = self.session_data_list[idx+1:]  # Remove processed data after processing
        
        return first_session_data
            

                





