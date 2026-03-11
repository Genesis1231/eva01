"""EVA's reading tool — fetches and digests content from the web."""

import asyncio

from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from typing import Literal

from config import logger, eva_configuration as config
from eva.tools import ToolError
from eva.utils.prompt import load_prompt

_firecrawl = None
_summarizer = None
_COMPRESS_THRESHOLD = 2000  # chars — below this, return directly
_MAX_CHARS = 30_000  # fetch limit before compression


def _get_firecrawl():
    global _firecrawl
    if _firecrawl is None:
        from firecrawl import Firecrawl

        _firecrawl = Firecrawl()
    return _firecrawl


def _get_summarizer():
    global _summarizer
    if _summarizer is None:
        _summarizer = init_chat_model(config.UTILITY_MODEL, max_tokens=500)
    return _summarizer


@tool
async def read(source: Literal["webpage"], url: str, query: str = "") -> str:
    """
    I use this to read and digest content. Select the exact source:
    - 'webpage': read a webpage and extract its content
    """

    if source == "webpage":
        return await _read_webpage(url, query)

    return f"There is no '{source}' to read."


async def _read_webpage(url: str, query: str) -> str:
    try:
        result = await asyncio.to_thread(
            _get_firecrawl().scrape, url, formats=["markdown"]
        )
        content = result.markdown or ""
        if not content:
            return f"I couldn't extract content from {url}."

        title = getattr(result, "metadata", None)
        title = title.title if title and hasattr(title, "title") else ""

        # Short content — return directly
        if len(content) <= _COMPRESS_THRESHOLD:
            return f"I read '{title}' ({url}):\n\n{content}"

        # Long content — compress with utility model
        content = content[:_MAX_CHARS]
        summary = await _compress(title, url, content, query)
        return f"I read '{title}' ({url}):\n\n{summary}"
    except Exception as e:
        logger.error(f"read webpage error: {e}")
        raise ToolError(str(e), tool_name="read") from e


async def _compress(title: str, url: str, content: str, query: str) -> str:
    prompt = load_prompt("describe_webpage").format(
        title=title, url=url, content=content, query=query or title
    )
    try:
        response = await _get_summarizer().ainvoke(prompt)
        return str(response.content)
    except Exception as e:
        logger.error(f"webpage compression failed: {e}")
        return content[:2000] + "\n\n[Compression failed — showing truncated content]"
