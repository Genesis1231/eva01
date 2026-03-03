"""
eva/core/mind.py — EVA's mind.

Three concurrent components sharing two buffers:
    Senses  →  SenseBuffer  →  Brain  →  ActionBuffer  →  Actions
"""

import asyncio
from dotenv import load_dotenv

from config import logger, eva_configuration
from eva.agent.chatagent import ChatAgent
from eva.senses.sense_buffer import SenseBuffer
from eva.senses.audio.audio_sense import AudioSense
from eva.senses.audio.transcriber import Transcriber
from eva.actions.buffer import ActionBuffer
from eva.actions.voice.voice_actor import VoiceActor
from eva.actions.voice.speaker import Speaker


async def startup(config: dict) -> tuple[SenseBuffer, ActionBuffer, AudioSense, VoiceActor, ChatAgent]:
    """Wire up senses, brain, and actions. Return shared buffers and components."""
    loop = asyncio.get_running_loop()

    # Shared buffers
    sense_buffer = SenseBuffer()
    sense_buffer.attach_loop(loop)
    action_buffer = ActionBuffer()

    # Senses
    transcriber = Transcriber(config["STT_MODEL"], config["LANGUAGE"])
    audio_sense = AudioSense(transcriber, keyboard=True)
    audio_sense.start(sense_buffer)

    # Brain
    agent = ChatAgent(config["CHAT_MODEL"], config["BASE_URL"], config["LANGUAGE"])

    # Actions
    speaker = Speaker(config["TTS_MODEL"], config["LANGUAGE"])
    voice_actor = VoiceActor(action_buffer, speaker)

    logger.info("EVA: startup complete.")
    return sense_buffer, action_buffer, audio_sense, voice_actor, agent


async def brain_loop(sense_buffer: SenseBuffer, action_buffer: ActionBuffer, agent: ChatAgent) -> None:
    """The conscious loop — EVA's mind."""
    logger.info("EVA: mind is awake.")

    while True:
        entry = await sense_buffer.get()
        logger.info(f"EVA: sensed [{entry.type}] — {entry.content[:60]}")

        try:
            if entry.type == "audio":
                sense = {"user_message": entry.content}
            else:
                sense = {"observation": entry.content}

            response = await agent.arespond(sense=sense)
            text = response.get("response", "")
            if text:
                await action_buffer.put("speak", text)

        except Exception as e:
            logger.error(f"EVA: brain error — {e}")


async def run() -> None:
    """Launch EVA — senses, mind, and voice running concurrently."""
    load_dotenv()
    config = eva_configuration

    sense_buffer, action_buffer, audio_sense, voice_actor, agent = await startup(config)

    try:
        await asyncio.gather(
            brain_loop(sense_buffer, action_buffer, agent),
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
