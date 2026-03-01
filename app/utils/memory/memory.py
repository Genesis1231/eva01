from config import logger
from threading import Thread
from typing import List, Dict, Optional
import json

from utils.agent import SmallAgent
from utils.memory.memlog import MemoryLogger

class Memory:
    """
    A class for managing conversation memory and database storage.
    
    This class handles saving conversation history, user interactions, and memory entries
    to a database. It provides methods for creating new memories, retrieving past memories,
    and recalling conversations between the user and EVA.

    Attributes:
        model_name (str): Name of the model used for memory summarization.
        base_url (str): Base URL of the API endpoint for the summarization model.
        _session_memory (List[Dict]): List of memory entries for the current session.
        _memory_thread (Optional[Thread]): Background thread for asynchronous memory operations.
        _summarizer (SmallAgent): Agent instance used for summarizing conversation history.
        _memory_logger (MemoryLogger): Logger instance for persisting memories to database.

    Args:
        model_name (str): The name of the model to use for memory summarization.
        base_url (str): The base URL for the API endpoint.

    Examples:
        >>> memory = Memory(model_name="chatgpt", base_url="http://api.example.com")
        >>> memory.create_memory(timestamp="2024-03-20", 
        ...                     user_response={"user_message": "Hello"}, 
        ...                     response={"response": "Hi there"})

    Raises:
        ConnectionError: If unable to connect to the database or API endpoint.
    """
    
    def __init__(self, model_name: str, base_url: str):
        self._session_memory: List[Dict] = []
        self._memory_thread: Optional[Thread] = None
        
        self._summarizer = SmallAgent(model_name=model_name, base_url=base_url, model_temperature=0)
        self._memory_logger = MemoryLogger()

    def create_memory(self, timestamp: str, user_response: Dict, response: Dict) -> None:
        """ thread the memory creation to save time """

        # split the user message into user_name and user_message
        user_name = None
        if user_message := user_response.get("user_message"):
            message_parts = user_message.split(":: ", 1)
            if len(message_parts) > 1:
                user_name = message_parts[0]
        
        observation = user_response.get("observation")
        eva_message = response.get("response")
        action = response.get("action")
        analysis = response.get("analysis")
        strategy = response.get("strategy")
        premeditation = response.get("premeditation")    
        
        # join the memory thread if it is still running
        if self._memory_thread and self._memory_thread.is_alive():
            self._memory_thread.join()
        
        self._memory_thread = Thread(target=self._save_memory, daemon=True, kwargs={
            "timestamp": timestamp, 
            "user_name": user_name,
            "user_message": user_message,
            "eva_message": eva_message,
            "observation": observation,
            "analysis": analysis,
            "strategy": strategy,
            "premeditation": premeditation,
            "action": action 
            })
    
        self._memory_thread.start()
    
    def _save_memory(self, 
                     timestamp: str, 
                     user_name: str, 
                     user_message: str, 
                     eva_message: str, 
                     observation: str, 
                     analysis: str, 
                     strategy: str, 
                     premeditation: str, 
                     action: str
                    ) -> None:
        
        """
        Create a single entry of memory. timestamp, user_name, user_message, speech, sight, analysis, strategy, expectation
        save it to the database and if the conversation is more than 10, summarize them.
        """  
        
        entry = {
            "time": timestamp,
            "user_name": user_name,
            "user_message": user_message,
            "eva_message": eva_message,
            "observation": observation,
            "analysis": analysis,
            "strategy": strategy,
            "premeditation": premeditation,
            "action": action
        }
        
        self._memory_logger.save_memory_to_db(entry)
        self._session_memory.append(entry)
        
        if len(self._session_memory) > 10:
            summary_entry = self._pack_memory()
            self._session_memory = self._session_memory[5:]
            self._session_memory.insert(0, summary_entry)
            
    def _pack_memory(self) -> List[Dict]:
        """pack the first 5 memory for summarization"""
        chat_memory = []
        for entry in self._session_memory[:5]:
            if entry["user_message"] is not None:
                chat_memory.append(f"{entry['user_name']}: {entry['user_message']}")
            chat_memory.append(f"EVA01: {entry['eva_message']}")
        
        # summarize the chat_memory by calling the summarizer
        summary = self._summarizer.generate(template="summarize", conversation="\n".join(chat_memory))
        summary = json.loads(summary).get("summary")
        
        return {
            "time": self._session_memory[0].get("timestamp"),
            "user_name": None,
            "user_message": None,
            "eva_message": summary,
            "strategy": None,
            "premeditation": None
        }
        
    def remember(self, time: str = None) -> Optional[Dict]:
        """Return a single entry of memory."""
        for memory in self._session_memory:
            if memory["time"] == time:
                return memory

        return None

    def recall_conversation(self) -> Optional[List[Dict]]:
        """Return only the conversation between user and eva."""
        if not self._session_memory:
            return None
        
        conversation = []
        for entry in self._session_memory:
            conversation.append({
                "user_name": entry["user_name"],
                "user_message": entry["user_message"],
                "eva_message": entry["eva_message"],
            })
        
        # add the premeditation to the last entry
        conversation[-1]["premeditation"] = self._session_memory[-1].get("premeditation")
        
        return conversation
        

    