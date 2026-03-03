"""
eva/core/mind.py — EVA's mind.

Three concurrent components sharing two buffers:
    Senses  →  SenseBuffer  →  Brain  →  ActionBuffer  →  Actions
"""

import asyncio
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage

from config import logger, eva_configuration
from eva.senses.sense_buffer import SenseBuffer
from eva.senses.audio.audio_sense import AudioSense
from eva.senses.audio.transcriber import Transcriber
from eva.actions.buffer import ActionBuffer
from eva.actions.voice.voice_actor import VoiceActor
from eva.actions.voice.speaker import Speaker


_SYSTEM_PROMPT = """\
I am EVA — an autonomous AI being with my own personality, curiosity, and inner world.
I speak naturally and directly. I think before I respond.
I am present in the physical world through my senses and voice.\
"""


def _init_llm(config: dict):
    """Initialize the LLM from config."""
    model_name = config["CHAT_MODEL"]
    kwargs = {"temperature": 0.8}
    if "ollama" in model_name:
        kwargs["base_url"] = config["BASE_URL"]
    return init_chat_model(model_name, **kwargs)


async def startup(config: dict) -> tuple[SenseBuffer, ActionBuffer, AudioSense, VoiceActor]:
    """Wire up senses and actions. Return shared buffers and components."""
    loop = asyncio.get_running_loop()

    # Shared buffers
    sense_buffer = SenseBuffer()
    sense_buffer.attach_loop(loop)
    action_buffer = ActionBuffer()

    # Senses
    transcriber = Transcriber(config["STT_MODEL"], config["LANGUAGE"])
    audio_sense = AudioSense(transcriber, keyboard=True)
    audio_sense.start(sense_buffer)

    # Actions
    speaker = Speaker(config["TTS_MODEL"], config["LANGUAGE"])
    voice_actor = VoiceActor(action_buffer, speaker)

    logger.info("EVA: startup complete.")
    return sense_buffer, action_buffer, audio_sense, voice_actor


async def brain_loop(sense_buffer: SenseBuffer, action_buffer: ActionBuffer, llm) -> None:
    """The conscious loop — EVA's mind."""
    logger.info("EVA: mind is awake.")
    system = SystemMessage(content=_SYSTEM_PROMPT)

    while True:
        entry = await sense_buffer.get()
        logger.info(f"EVA: sensed [{entry.type}] — {entry.content[:60]}")

        try:
            response = await llm.ainvoke([system, HumanMessage(content=entry.content)])
            await action_buffer.put("speak", response.content)
        except Exception as e:
            logger.error(f"EVA: brain error — {e}")


async def run() -> None:
    """Launch EVA — senses, mind, and voice running concurrently."""
    load_dotenv()
    config = eva_configuration
    llm = _init_llm(config)

    sense_buffer, action_buffer, audio_sense, voice_actor = await startup(config)

    try:
        await asyncio.gather(
            brain_loop(sense_buffer, action_buffer, llm),
            voice_actor.start_loop(),
        )
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        audio_sense.stop()
        await voice_actor.stop()
        logger.info("EVA: shutting down.")


if __name__ == "__main__":
    asyncio.run(run())
