from config import logger
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from utils.prompt import load_prompt

class PromptConstructor:
    """
    A class that constructs and formats prompts for the chat agent.

    Assembles various components into structured prompts by combining:
    - Persona and instruction templates loaded from files
    - Conversation history with user and assistant messages
    - User observations and inputs
    - Results from previous actions
    
    The prompt structure uses XML tags to clearly separate different input sections,
    making it easier for LLMs to parse and understand the context. Each section is
    formatted consistently to maintain a standardized prompt format.
    """
    
    def __init__(self):
        self.persona_prompt: str = load_prompt("persona") # default persona prompt
        self.instruction_prompt: str = load_prompt("instructions") # default instructions prompt
        
    @staticmethod
    def _format_history(history: List[Dict] | None) -> str:
        """ format the the chat history into string for LLM """
        if not history:
            return ""
    
        messages = []
        messages.append("<CONVERSATION_HISTORY>")
        
        for chat in history:
            for role, message in [("user", chat.get("user_message")),
                                  ("assistant", chat.get("eva_message")),
                                  ("memory", chat.get("premeditation"))
                                  ]:
                if not message:
                    continue
            
                if role == "memory":
                    message = f"<assistant>I remember {message} </assistant>"
                else:
                    message = f"<{role}>{message}</{role}>"
                
                messages.append(message)
                
        messages.append("</CONVERSATION_HISTORY>")
        return "\n".join(messages)

    @staticmethod
    def _format_observation(observation: str | None) -> str:
        """ Format the observation into string for LLM """
        return "" if not observation else f"I see <observation> {observation} </observation>"

    @staticmethod
    def _format_message(user_message: str | None) -> str:
        """ Format the user message into string for LLM """
        return "" if not user_message else f"I hear {user_message}"

    @staticmethod
    def _format_action_results(results: List[Dict[str, Any]]) -> str:
        """ Format the action results into string for LLM """
        if not results:
            return ""
    
        action_results = []
        action_results.append("<action_results>I found the following information from my previous actions:")
        
        # simple way to format the results
        for result_item in results:
            result = result_item.get("result")
            if not result:
                continue
            
            if isinstance(result, List):
                for item in result:
                    if isinstance(item, dict):
                        formatted_items = [f"{k}: {v}" for k, v in item.items() if "url" not in k.lower()]
                        action_results.append("\n".join(formatted_items))
                    else:
                        action_results.append(str(item))
            elif isinstance(result, Dict):
                formatted_items = [f"{k}: {v}" for k, v in result.items() if "url" not in k.lower()]
                action_results.append("\n".join(formatted_items))
            else:
                action_results.append(str(result))
            
            if additional_info:=result_item.get("additional"):
                action_results.append(additional_info)
            
        action_results.append("</action_results>")
        return "\n".join(action_results)

    def build_prompt(
        self,
        template: str | None,
        timestamp : str, 
        sense: Dict, 
        history: List[Dict[str, str]], 
        action_results: List[Dict[str, Any]]
    ) -> str:
        """
        Builds the prompt for LLM.
        Args:
            template (str | None): Name of the system prompt template file to load. If None, uses default system prompt.
            timestamp (str): Current timestamp for context.
            sense (Dict): Dictionary containing sensory information like user messages and observations.
            history (List[Dict[str, str]]): List of conversation history entries.
            action_results (List[Dict[str, Any]]): Results from previous actions taken by the agent.
        Returns:
            str: The fully constructed prompt string for the language model.
    
        """
        
        instructions = self.instruction_prompt if template is None else load_prompt(template)
        user_message = self._format_message(sense.get("user_message"))
        observation = self._format_observation(sense.get("observation"))
        action_results = self._format_action_results(action_results)
        history_prompt = self._format_history(history)
        
        PROMPT_TEMPLATE = f"""  
            <PERSONA>
            {self.persona_prompt}
            </PERSONA>
            
            <TOOLS>
            I have the following tools available for action:
            {{tools}}
            </TOOLS>
            
            {history_prompt}
            
            <CONTEXT>
            <current_time>{timestamp}</current_time>
            {observation} 
            {user_message} 
            {action_results}
            </CONTEXT>

            <INSTRUCTIONS>
            {instructions}
            </INSTRUCTIONS>
            
            Based on the above context and instructions, craft appropriate output with the following Json format.
            
            <FORMATTING>
            {{format_instructions}}
            </FORMATTING>
    
            <ASSISTANT>
        """
    
        logger.debug(PROMPT_TEMPLATE) 
        return PROMPT_TEMPLATE
