"""EVA's reading tool — fetches and digests content from the web."""

import asyncio

from langchain_core.tools import tool
from typing import Literal

from config import logger
from eva.tools import ToolError

_firecrawl = None
_MAX_CHARS = 15_000  # ~4k tokens — keeps Opus context manageable
_EXCLUDE_TAGS = ["nav", "footer", "header", "aside", ".sidebar", "#ad", ".cookie"]


def _get_firecrawl():
    global _firecrawl
    if _firecrawl is None:
        from firecrawl import Firecrawl

        _firecrawl = Firecrawl()
    return _firecrawl


@tool
async def read(source: Literal["webpage"], url: str) -> str:
    """
    I use this to read and digest content. Select the exact source:
    - 'webpage': read a webpage and extract its content
    """

    if source == "webpage":
        return await _read_webpage(url)

    return f"I don't see '{source}' available to read."


async def _read_webpage(url: str) -> str:
    try:
        result = await asyncio.to_thread(
            _get_firecrawl().scrape, url,
            formats=["markdown"],
            only_main_content=True,
            exclude_tags=_EXCLUDE_TAGS,
        )
        content = result.markdown or ""
        if not content:
            return f"I couldn't extract content from {url}."

        title = getattr(result, "metadata", None)
        title = title.title if title and hasattr(title, "title") else ""

        # Truncate if too long — Firecrawl already cleaned the content
        if len(content) > _MAX_CHARS:
            content = content[:_MAX_CHARS] + "\n\n[Content truncated]"

        return f"I read '{title}' ({url}):\n\n{content}"
    except Exception as e:
        logger.error(f"read webpage error: {e}")
        raise ToolError(str(e), tool_name="read") from e
