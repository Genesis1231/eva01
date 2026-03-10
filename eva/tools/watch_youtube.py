"""EVA's eyes for the internet — searches and queues YouTube videos."""

import asyncio
from typing import Dict, List, Any
import yt_dlp
from langchain_core.tools import tool
from eva.actions.action_buffer import ActionBuffer
from eva.tools import ToolError


_YDL_OPTS: Any = {"quiet": True, "extract_flat": True, "no_warnings": True}

def _search(query: str) -> List[Dict[str, Any]]:
    """Blocking yt-dlp search — runs in a thread."""
    
    with yt_dlp.YoutubeDL(_YDL_OPTS) as ydl:
        results = ydl.extract_info(f"ytsearch3:{query}", download=False)
    return results.get("entries", [])


def make_watch_tool(action_buffer: ActionBuffer):
    """Create a watch tool bound to the given ActionBuffer."""

    @tool(name_or_callable="watch_youtube")
    async def watch(query: str) -> str:
        """Search YouTube and watch a video. Use short keyword queries (2-4 words)."""
        try:
            videos = await asyncio.to_thread(_search, query)
        except Exception as e:
            raise ToolError(str(e), tool_name="youtube") from e

        if not videos:
            return f"I didn't find any videos for '{query}'."

        pick = videos[0]
        video_id = pick["id"]
        title = pick.get("title", "Untitled")
        channel = pick.get("channel") or pick.get("uploader", "Unknown")

        await action_buffer.put(
            "watch_youtube",
            video_id,
            {"title": title, "channel": channel},
        )
        return f"I am trying to watch '{title}' by {channel}."

    return watch
