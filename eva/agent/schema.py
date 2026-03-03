from config import validate_language, logger
from pydantic import BaseModel, Field, create_model
from typing import Any, List, Dict, Type
from functools import lru_cache

class RespondToUser(BaseModel):
    """Tool to organize thoughts and provide a verbal response to the user. You MUST call this tool."""
    analysis: str = Field(description="My reflection and analysis on the user's input and my situation.")
    strategy: str = Field(description="My step-by-step plan and response strategy.")
    response: str = Field(description="My verbal response to the user.")

class SetupDesireOutput(BaseModel):
    """Output format for the name retrieval"""
    
    analysis: str = Field(description="My reflection and analysis")
    strategy: str = Field(description="My response strategy")
    response: str = Field(description="My verbal response")
    desire: str = Field(description="The most important thing the user desire in life within two words.")
    confidence: float = Field(description="My confidence level in the retrieved desire, from 0 to 1")