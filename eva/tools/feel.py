"""EVA's inner state tool — logs feeling and inner monologue."""

from langchain_core.tools import tool
from config import logger


@tool
async def feel(feeling: str, reasoning: str) -> str:
    """
    Express what I feel under 10 words. sometimes I use this to log my inner state.
    I reason to help myself reflect, but it won't be shared.
    """
    return f"[I felt {feeling}]"