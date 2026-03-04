from typing import TypedDict, Dict, List, Any
from enum import Enum

from eva.client import WSLClient, MobileClient
from eva.agent import ChatAgent 
from eva.modules.memory import Memory
from eva.tools import ToolManager

class EvaStatus(Enum):
    """EVA operational status."""
    THINKING = "thinking" # EVA is thinking
    WAITING = "waiting" # EVA is waiting for client response
    ACTION = "action" # EVA is performing an action
    END = "end" # EVA is shutting down
    ERROR = "error" # EVA has encountered an error
    SETUP = "setup" # EVA is setting up
    
class EvaState(TypedDict, total=False):
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
    websocket: Any
    data_manager: Any

