"""
EVA's mind.

Three concurrent components sharing two buffers:
    Senses  →  SenseBuffer  →  Brain  →  ActionBuffer  →  Actions
"""

import asyncio
from dotenv import load_dotenv
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from config import logger, eva_configuration, DATA_DIR, Config

from .graph import Brain
from .memory import MemoryDB
from .people import PeopleDB
from .journal import JournalDB
from .db import SQLiteHandler
from eva.senses import (
    SenseBuffer, 
    AudioSense, 
    CameraSense,
    Transcriber,
    SpeakerIdentifier,
    Describer,
    FaceIdentifier
)
from eva.actions import ActionBuffer, VoiceActor, Screen, MotorSystem
from eva.actions.voice.speaker import Speaker


async def assemble(
    config: Config, 
    db: SQLiteHandler, 
    checkpointer: AsyncSqliteSaver | None = None
):
    """Wire up senses, brain, and actions. Return shared buffers and components."""

    logger.debug("Assembling EVA's core components...")
    loop = asyncio.get_running_loop()

    # Shared buffers
    action_buffer = ActionBuffer()
    sense_buffer = SenseBuffer()
    sense_buffer.attach_loop(loop)

    # People & Memory
    people_db = PeopleDB(db)
    journal_db = JournalDB(db)
    await asyncio.gather(
        people_db.init_db(),
        journal_db.init_db(),
    )
    memory_db = MemoryDB(config.UTILITY_MODEL, people_db, journal_db)
    
    # Initialize vision sense
    camera_sense = None
    face_identifier = None
    if config.CAMERA is not False:
        describer = Describer(config.VISION_MODEL)
        face_identifier = FaceIdentifier(people_db)
        camera_sense = CameraSense(
            describer=describer, 
            identifier=face_identifier, 
            source=config.CAMERA
        )

    # Audio components
    speaker = Speaker(config.TTS_MODEL, config.LANGUAGE)
    transcriber = Transcriber(config.STT_MODEL)
    speaker_identifier = SpeakerIdentifier(people_db)

    # Initialize heavy models concurrently to reduce startup latency.
    init_tasks = [
        asyncio.to_thread(speaker.init_model),
        asyncio.to_thread(transcriber.init_model),
        asyncio.to_thread(speaker_identifier.init_model),
    ]
    if face_identifier is not None:
        init_tasks.append(asyncio.to_thread(face_identifier.init_model))
    await asyncio.gather(*init_tasks)
    
    # Actions — register handlers on the shared buffer
    voice_actor = VoiceActor(speaker)
    screen = Screen()
    motor_system = MotorSystem(
        action_buffer, 
        actions=[voice_actor, screen]
    )
 
    # initialize transcriber and audio sense

    audio_sense = AudioSense(
        transcriber,
        speaker_identifier=speaker_identifier,
        on_interrupt=lambda: voice_actor.speaker.stop_speaking(),
        is_speaking=lambda: voice_actor.is_speaking,
    )
    audio_sense.start(sense_buffer)

    if camera_sense is not None and camera_sense.is_available:
        camera_sense.start(sense_buffer)

    # Brain — owns tools + workflow, Cortex owns LLM + prompt
    brain = Brain(
        model_name=config.CHAT_MODEL,
        action_buffer=action_buffer,
        people_db=people_db,
        memory=memory_db,
        checkpointer=checkpointer,
    )

    return sense_buffer, action_buffer, motor_system, audio_sense, camera_sense, brain


async def breathe(sense_buffer: SenseBuffer, brain: Brain) -> None:
    """The conscious loop — EVA's mind."""

    while True:
        entry = await sense_buffer.get()

        try:
            await brain.invoke(entry)
        except Exception as e:
            logger.error(f"EVA: brain error — {e}")

async def wake() -> None:
    """Launch EVA — senses, mind, and voice running concurrently."""
    logger.debug("Eva is waking up...")
    load_dotenv()

    # Ensure DB directory exists
    graph_db = DATA_DIR / "database" / "eva_graph.db"
    graph_db.parent.mkdir(parents=True, exist_ok=True)
    eva_db = SQLiteHandler()

    async with AsyncSqliteSaver.from_conn_string(str(graph_db)) as checkpointer:
        sense_buffer, action_buffer, motor_system, audio_sense, camera_sense, brain = await assemble(
            config=eva_configuration, 
            db=eva_db, 
            checkpointer=checkpointer
        )

        try:
            await motor_system.start()
            await asyncio.gather(
                breathe(sense_buffer, brain),
                action_buffer.start_loop(),
            )
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            await brain.shutdown()  

            audio_sense.stop()
            if camera_sense is not None:
                await camera_sense.stop()
                
            await motor_system.shutdown()
            await action_buffer.stop()
            await eva_db.close_all()

if __name__ == "__main__":
    asyncio.run(wake())
