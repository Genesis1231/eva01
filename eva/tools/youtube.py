"""
EVA's eyes for YouTube — search, discover, and watch videos.
"""

import asyncio
import html
import re
import urllib.request
from typing import Dict, List, Any

from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
import yt_dlp

from config import logger, eva_configuration as config
from eva.tools import ToolError
from eva.utils.prompt import load_prompt
from eva.utils.video_analyzer import VideoAnalyzer


_YDL_OPTS: Any = {"quiet": True, "extract_flat": True, "no_warnings": True}
_MAX_VIDEO_DURATION = 900  # 15 minutes — beyond this, use transcript
_analyzer: VideoAnalyzer | None = None
_summarizer = None


def _get_analyzer() -> VideoAnalyzer | None:
    global _analyzer
    if _analyzer is None:
        _analyzer = VideoAnalyzer()
    return _analyzer


def _get_summarizer():
    global _summarizer
    if _summarizer is None:
        _summarizer = init_chat_model(config.UTILITY_MODEL, max_tokens=150)
    return _summarizer


def _search(query: str) -> List[Dict[str, Any]]:
    """Blocking yt-dlp search — runs in a thread."""
    with yt_dlp.YoutubeDL(_YDL_OPTS) as ydl:
        results = ydl.extract_info(f"ytsearch5:{query}", download=False)
    return results.get("entries", [])


def _format_duration(seconds: float | None) -> str:
    if not seconds:
        return "?"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _format_views(count: int | None) -> str:
    if not count:
        return "?"
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    if count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)


def _fetch_metadata(url: str) -> Dict[str, Any]:
    """Fetch video metadata (duration, subs, etc.) without downloading."""
    opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


def _extract_transcript(info: Dict[str, Any]) -> str | None:
    """Download and clean VTT transcript. Returns plain text or None."""
    subs = info.get("subtitles", {})
    auto = info.get("automatic_captions", {})
    en_subs = subs.get("en") or auto.get("en")
    if not en_subs:
        return None

    vtt_url = next((s["url"] for s in en_subs if s["ext"] == "vtt"), None)
    if not vtt_url:
        return None

    try:
        raw = urllib.request.urlopen(vtt_url, timeout=10).read().decode("utf-8")
    except Exception as e:
        logger.error(f"Failed to download transcript: {e}")
        return None

    lines: list[str] = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line or line.startswith(("WEBVTT", "Kind:", "Language:")):
            continue
        if "-->" in line or re.match(r"^\d+$", line):
            continue
        clean = re.sub(r"<[^>]+>", "", line)
        if clean and (not lines or clean != lines[-1]):
            lines.append(clean)

    if not lines:
        return None

    return html.unescape(" ".join(lines))


async def _summarize_transcript(title: str, description: str, transcript: str) -> str:
    """Compress a long transcript into ~100 words via the utility model."""
    prompt = load_prompt("describe_transcript").format(
        title=title, description=description, transcript=transcript
    )
    try:
        response = await _get_summarizer().ainvoke(prompt)
        return str(response.content)
    except Exception as e:
        logger.error(f"Transcript summarization failed: {e}")
        return description[:500] + "..."


@tool
async def search_youtube(query: str) -> str:
    """
    Search YouTube for videos. Use short keyword queries (2-4 words).
    I use this to find videos — I get back titles and URLs to share or watch later.
    """
    try:
        videos = await asyncio.to_thread(_search, query)
    except Exception as e:
        raise ToolError(str(e), tool_name="youtube") from e

    if not videos:
        return f"I didn't find any videos for '{query}'."

    lines = []
    for v in videos:
        if not v.get("duration"):
            continue
        vid = v.get("id", "")
        title = v.get("title", "Untitled")
        channel = v.get("channel") or v.get("uploader", "Unknown")
        duration = _format_duration(v.get("duration"))
        views = _format_views(v.get("view_count"))
        url = f"https://www.youtube.com/watch?v={vid}"
        lines.append(f"- {title} by {channel} — {duration}, {views} views — {url}")

    return "I found some videos:\n" + "\n".join(lines)


@tool
async def watch_video(url: str) -> str:
    """
    Watch a video by URL.
    I use this when I want to know what's in a video or extract the content.
    """
    if not url:
        return "I need a URL to watch."

    is_youtube = "youtube.com" in url or "youtu.be" in url

    # YouTube: check duration, use transcript for long videos
    if is_youtube:
        try:
            info = await asyncio.to_thread(_fetch_metadata, url)
        except Exception as e:
            logger.error(f"Failed to fetch video metadata: {e}")
            raise ToolError(str(e), tool_name="watch_video") from e

        duration = info.get("duration") or 0
        title = info.get("title", "Untitled")

        if duration <= _MAX_VIDEO_DURATION:
            # Short video — analyze with Gemini
            return await _analyze_video(url)

        # Long video — use transcript, summarize before returning
        transcript = await asyncio.to_thread(_extract_transcript, info)
        dur_str = _format_duration(duration)
        description = info.get("description") or ""
        if transcript:
            summary = await _summarize_transcript(title, description, transcript)
            return f"I read the transcript of '{title}':\n\n{summary}"

        dur_str = _format_duration(duration)
        return f"This video is {dur_str}.Too long to watch. Description: {description[500:] if description else 'No description'}..."

    # Non-YouTube: just analyze directly
    return await _analyze_video(url)


async def _analyze_video(url: str) -> str:
    """Send video to Gemini for analysis."""
    try:
        analyzer = _get_analyzer()
        if analyzer is None:
            return "Video Analyzer is not available. Cannot watch video."

        summary, error = await analyzer.analyze(url)
    except Exception as e:
        logger.error(f"Video analysis failed for {url} — {e}")
        raise ToolError(str(e), tool_name="watch_video") from e

    if not summary:
        return f"I couldn't watch the video at {url}. {error}"

    return f"I just watched {url}\n\n{summary}"
