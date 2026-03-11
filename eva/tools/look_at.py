"""EVA's look_at tool — visual perception of webpages and images."""

import asyncio
import base64
import shutil
import tempfile
from pathlib import Path

from html2image import Html2Image
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

from config import logger, eva_configuration as config
from eva.tools import ToolError
from eva.utils.prompt import load_prompt

_vision = None
_VIEWPORT = (1280, 800)


def _pick_browser() -> str:
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        path = shutil.which(name)
        if path:
            return path
    raise RuntimeError("No Chrome/Chromium binary found in PATH.")


def _screenshot(url: str) -> str:
    """Take a viewport screenshot, return base64-encoded PNG."""
    with tempfile.TemporaryDirectory() as tmp:
        hti = Html2Image(
            browser_executable=_pick_browser(),
            output_path=tmp,
            size=_VIEWPORT,
            custom_flags=[
                "--headless=new",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--hide-scrollbars",
            ],
        )
        hti.screenshot(url=url, save_as="shot.png")
        png_path = Path(tmp) / "shot.png"
        if not png_path.exists():
            raise FileNotFoundError("Screenshot failed — no image produced.")
        return base64.b64encode(png_path.read_bytes()).decode()


def _get_vision():
    global _vision
    if _vision is None:
        _vision = init_chat_model(config.VISION_MODEL, temperature=0.1)
    return _vision


@tool
async def look_at(url: str) -> str:
    """I look at a webpage or image to see what's there before I decide to read or act on it."""
    try:
        b64 = await asyncio.to_thread(_screenshot, url)

        prompt = load_prompt("look_at").format(title="", url=url)
        message = HumanMessage(content=[
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
        ])
        response = await _get_vision().ainvoke([message])
        description = str(response.content)

        return f"I looked at {url}:\n\n{description}"
    except Exception as e:
        logger.error(f"look_at error: {e}")
        raise ToolError(str(e), tool_name="look_at") from e
