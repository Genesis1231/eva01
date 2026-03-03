"""
PromptConstructor:
    Constructs and formats prompts for the chat agent.
    Assembles various components into structured prompts by combining:
    - Persona and instruction templates loaded from files
    - Conversation history
    - observations and inputs
"""

from config import logger
from pydantic import BaseModel, Field
from eva.utils.prompt import load_prompt

class PromptConstructor:
    """
    PromptConstructor class:
    
    Attributes:
        persona_prompt (str): The persona prompt loaded from the persona.md file.
        instruction_prompt (str): The instruction prompt loaded from the instructions.md file.
    """
    
    def __init__(self):
        self.persona_prompt: str = load_prompt("persona") # default persona prompt
        self.instruction_prompt: str = load_prompt("instructions") # default instructions prompt
        

    def build_prompt(
        self,
        timestamp : str, 
        sense: str, 
    ) -> str:
        """
        PromptBuilder class:
    
        """
 
        PROMPT_TEMPLATE = (
             "<PERSONA>\n"
            f"{self.persona_prompt}\n"
             "</PERSONA>\n\n"
             "<CONTEXT>\n"
            f"<current_time>{timestamp}</current_time>\n"
            f"{sense}\n"
             "</CONTEXT>\n\n"
             "<INSTRUCTIONS>\n"
            f"{self.instruction_prompt}\n"
             "</INSTRUCTIONS>"
        )
    
        logger.debug(PROMPT_TEMPLATE)
        return PROMPT_TEMPLATE
