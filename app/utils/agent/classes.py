from config import validate_language, logger
from pydantic import BaseModel, Field, create_model
from typing import Any, List, Dict, Type
from functools import lru_cache

class AgentOutput(BaseModel):
    """Base output format for the agent's responses"""
    analysis: str = Field(description="My reflection and analysis")
    strategy: str = Field(description="My response strategy")
    response: str = Field(description="My verbal response")  # Base description
    premeditation: str = Field(description="My predetermined information")
    action: List[Dict[str, Any]] = Field(
        description="The name of the tools I choose and the args for input."
    )
    
    @classmethod
    @lru_cache(maxsize=5)
    def with_language(cls, base_language: str, language: str | None) -> Type["AgentOutput"]:
        """Create a new AgentOutput class with language-specific response description"""
        if not base_language:
            raise ValueError("base_language cannot be empty")
            
        language = validate_language(language) or base_language
        
        verbal_language = (
            f"(ONLY IN NATIVE {language.upper()})"
            if language.upper() not in ("ENGLISH", "MULTILINGUAL")
            else ""
        )
        
        # Create a new class with properly annotated field override
        return create_model(
            f"AgentOutput_{language}",
            __base__=(cls,),
            response=(str, Field(description=f"My verbal response {verbal_language}"))
        )

class SetupNameOutput(BaseModel):
    """Output format for the name retrieval"""
    
    analysis: str = Field(description="My reflection and analysis")
    strategy: str = Field(description="My response strategy")
    response: str = Field(description="My verbal response")
    name: str = Field(description="The user's name or alias")
    confidence: float = Field(description="My confidence level in the retrieved name, from 0 to 1")
    
class SetupDesireOutput(BaseModel):
    """Output format for the name retrieval"""
    
    analysis: str = Field(description="My reflection and analysis")
    strategy: str = Field(description="My response strategy")
    response: str = Field(description="My verbal response")
    desire: str = Field(description="The most important thing the user desire in life within two words.")
    confidence: float = Field(description="My confidence level in the retrieved desire, from 0 to 1")