"""EVA's window to the internet — searches the web via Perplexity Sonar."""

import re
from config import logger
from langchain_core.tools import tool
from langchain_perplexity import ChatPerplexity
from eva.tools import ToolError

_llm_perplexity: ChatPerplexity | None = None

def _get_llm() -> ChatPerplexity:
    global _llm_perplexity
    if _llm_perplexity is None:
        _llm_perplexity = ChatPerplexity(temperature=0.1, max_tokens=1024, timeout=30)
    return _llm_perplexity

@tool
async def web_search(query: str) -> str:
    """Search the web with a query. I use this when I need to look something up."""
    try:
        response = await _get_llm().ainvoke(query)
        return re.sub(r"\[\d+\]", "", str(response.content))
    except Exception as e:
        logger.error(f"web search error: {e}")
        raise ToolError(str(e), tool_name="web search") from e