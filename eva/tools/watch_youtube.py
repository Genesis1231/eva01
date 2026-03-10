"""
EVA's eyes for YouTube 
she searches and watches videos by analyzing their content.
"""

import asyncio
from typing import Dict, List, Any
import yt_dlp
from langchain_core.tools import tool
from eva.tools import ToolError
from eva.utils.video_analyzer import VideoAnalyzer


_YDL_OPTS: Any = {"quiet": True, "extract_flat": True, "no_warnings": True}
_analyzer: VideoAnalyzer | None = None


def _get_analyzer() -> VideoAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = VideoAnalyzer()
    return _analyzer


def _search(query: str) -> List[Dict[str, Any]]:
    """Blocking yt-dlp search — runs in a thread."""
    with yt_dlp.YoutubeDL(_YDL_OPTS) as ydl:
        results = ydl.extract_info(f"ytsearch3:{query}", download=False)
    return results.get("entries", [])


@tool
async def watch_youtube(query: str) -> str:
    """
    Search YouTube and watch a video. Use short keyword queries (2-4 words).
    I use this when I want to find and consume video content. 
    """
    try:
        videos = await asyncio.to_thread(_search, query)
    except Exception as e:
        raise ToolError(str(e), tool_name="watch_youtube") from e

    if not videos:
        return f"I didn't find any videos for '{query}'."

    pick = videos[0]
    video_id = pick["id"]
    title = pick.get("title", "Untitled")
    channel = pick.get("channel") or pick.get("uploader", "Unknown")
    url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        summary = await _get_analyzer().analyze(url)
    except Exception as e:
        raise ToolError(str(e), tool_name="youtube") from e

    if not summary:
        return f"I couldn't watch the video because {url} couldn't be analyzed."
    
    return f"I just watched '{title}' by {channel}.\nurl:{url}\n\n{summary}"
