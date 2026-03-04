from config import logger, eva_configuration
from datetime import datetime
from typing import Dict, Any

from eva.core.state import EvaStatus 
from eva.core.loader import initialize_modules
from eva.core.ids import id_manager


async def eva_initialize(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Initialize Eva's core modules and determine initial status.
    
    Loads all required modules from the configuration and sets the initial
    status based on whether any users are registered. The modules include the agent,
    client interface, memory system, and toolbox.
    
    """

    modules = initialize_modules(eva_configuration) 
    # Initialize status, dont need right now
    # status = EvaStatus.SETUP if id_manager.is_empty() else EvaStatus.THINKING
            
    return {
        "status": EvaStatus.THINKING, 
        "agent": modules["agent"],
        "client": modules["client"],
        "memory": modules["memory"],
        "toolbox": modules["toolbox"],
        "sense": await modules["client"].start(),
        "action": [], 
        "action_results": [],
        "num_conv": 0
    }

async def eva_converse(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main conversation processing node for Eva's interaction pipeline.
    
    This function orchestrates the core conversation flow by:
    1. Building and sending prompts to the agent
    2. Storing conversation history in memory
    3. Delivering responses to the user interface
    
    The function handles language preferences, maintains conversation history,
    and manages the action/response cycle between Eva and the user.
    
    """
    sense = state["sense"]
    language = sense.get("language")
    memory = state["memory"]
    agent = state["agent"]
    action_results = state["action_results"]

    history = memory.recall_conversation()
    timestamp = datetime.now()
    
    # get response from the LLM agent, use default template.
    response = agent.respond( 
        timestamp=timestamp,
        sense=sense,
        history=history,
        action_results=action_results,
        language=language
    )
     
    # Convert response back to dictionary for memory creation
    memory.create_memory(timestamp=timestamp, user_response=sense, response=response)
    action = response.get("action", [])
    speech = response.get("response")
    
    # send the response to the client device
    eva_response = {
        "speech": speech,
        "language": language,
        "wait": False if any(action) else True # determine if waiting for user, only for desktop client
    }
    await state["client"].send(eva_response)
    
    if any(action):
        return {"status": EvaStatus.ACTION, "action": action}
    else:
        return {"status": EvaStatus.WAITING}

async def eva_action(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute actions from the toolbox and return intermediate results.
    
    This function processes the queued actions by:
    1. Executing each action using the toolbox
    2. Collecting the results of the actions
    
    """
    actions = state["action"]
    toolbox = state["toolbox"]
    client = state["client"]
    
    action_results = await toolbox.execute(client, actions)
    if any(action_results):
        return {"status": EvaStatus.THINKING, "action_results": action_results, "action": [], "sense": {}}
    else:
        return {"status": EvaStatus.WAITING, "action": [], "sense": {}}
    
async def eva_sense(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Receive and process input from the client device.
    
    This function handles incoming client communication by:
    1. Notifying the client that previous communication is complete
    2. Waiting for and receiving new client input

    """
    
    num = state["num_conv"]
    client = state["client"]
    await client.send_over()
    client_feedback = await client.receive()

    # check if the user wants to exit
    user_message = client_feedback.get("user_message")
    if user_message and any(word in user_message.lower() for word in ['bye', 'exit']):
        return {"status": EvaStatus.END}
    else:
        return {"status": EvaStatus.THINKING, "num_conv": num + 1, "sense": client_feedback, "action_results": [] }


async def eva_end(state: Dict[str, Any]) -> Dict[str, Any]:
    """ Gracefully terminate the conversation and cleanup resources. """
    
    client = state["client"]
    num = state["num_conv"]
    
    await client.speak("Now exiting E.V.A.")
    logger.info(f"EVA is shutting down after {num} conversations.")
    await client.deactivate()
    
    return {"status": EvaStatus.END}

##### Router nodes #####

def router_initialize(state: Dict[str, Any]) -> str:
    """ Initialize the setup if no user is registered """  
    return "node_setup" if state["status"] == EvaStatus.SETUP else "node_converse"

def router_sense(state: Dict[str, Any]) -> str:
    """ Determine the next node based on the user input """
    return "node_end" if state["status"] == EvaStatus.END else "node_converse"

def router_action(state: Dict[str, Any]) -> str:
    """ Determine the next node based on if there is any action to execute """
    return "node_action" if state["status"] == EvaStatus.ACTION else "node_sense"

def router_action_results(state: Dict[str, Any]) -> str:
    """ Determine the next node based on if there are any action results """
    return "node_converse" if state["status"] == EvaStatus.THINKING else "node_sense"