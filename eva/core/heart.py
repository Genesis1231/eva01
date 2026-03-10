"""
EVA's heartbeat — gives her initiative when idle.

When no external stimulus arrives for `interval` seconds, Heart pushes
a "thought" into SenseBuffer. The existing breathe() loop picks it up
and the Brain decides what to do with it.
"""

import asyncio
from datetime import datetime
from typing import Callable

from config import logger
from eva.core.tasks import TaskDB
from eva.senses.sense_buffer import SenseBuffer
from eva.utils.prompt import load_prompt


class Heart:

    def __init__(
        self, 
        sense_buffer: SenseBuffer, 
        task_db: TaskDB, 
        interval: int, 
        is_busy: Callable[[], bool] | None = None
    ):
        self.sense_buffer = sense_buffer
        self.task_db = task_db
        self.interval = interval  # 0 = disabled
        self._is_busy = is_busy or (lambda: False)

    async def start(self) -> None:
        """Beat forever — push a thought when EVA is idle."""
        if not self.interval:
            logger.debug("Heart: heartbeat disabled (interval=0)")
            return
        
        logger.debug(f"Heart: beating every {self.interval}s when idle")
        while True:
            await asyncio.sleep(self.interval)
            if self._is_idle():
                prompt = await self._pulse()
                self.sense_buffer.push(type="thought", content=prompt)
                logger.debug("Heart: a pulse sent to the brain...")

    def _is_idle(self) -> bool:
        if self._is_busy():
            return False
        elapsed = (datetime.now() - self.sense_buffer.last_external_at).total_seconds()
        return elapsed >= self.interval

    async def _pulse(self) -> str:
        """Build the inner-voice prompt for this heartbeat."""
        tasks = await self.task_db.summary()
        return load_prompt("HEARTBEAT").format(tasks=tasks)
