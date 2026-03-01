from typing import TypedDict, Dict, List, Any
from enum import Enum

from client import WSLClient, MobileClient
from utils.agent import ChatAgent 
from utils.memory import Memory
from tools import ToolManager

class EvaStatus(Enum):
    """EVA operational status."""
    THINKING = "thinking" # EVA is thinking
    WAITING = "waiting" # EVA is waiting for client response
    ACTION = "action" # EVA is performing an action
    END = "end" # EVA is shutting down
    ERROR = "error" # EVA has encountered an error
    SETUP = "setup" # EVA is setting up
    
class EvaState(TypedDict):
    """Langraph EVA state."""
    status: EvaStatus
    agent: ChatAgent 
    toolbox: ToolManager 
    client: WSLClient | MobileClient
    memory : Memory
    sense : Dict | None
    action : List[Dict[str, Any]]
    action_results: List[Dict[str, Any]]
    num_conv: int

