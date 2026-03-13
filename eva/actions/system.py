"""
ActionSystem:
    EVA's motor network — handles the registration, lifecycle, 
    and graceful shutdown of all action components.
"""

import asyncio
from config import logger
from .action_buffer import ActionBuffer
from .base import BaseAction

class MotorSystem:
    def __init__(
        self, 
        action_buffer: ActionBuffer, 
        actions: list[BaseAction] | None = None
    ):
        self.buffer = action_buffer
        self.actions = actions or []

    def add_action(self, action: BaseAction) -> None:
        """Register an action to the motor network and bind it to the buffer."""        
        self.actions.append(action)

    async def start(self) -> None:
        """Start all registered local action components."""
        logger.debug("Starting MotorSystem...")

        # Start individual actions concurrently
        async def start_action(action: BaseAction):
            action.register(self.buffer)
            await action.start()

        start_tasks = [start_action(action) for action in self.actions]
        if start_tasks:
            await asyncio.gather(*start_tasks)

    async def shutdown(self) -> None:
        """Gracefully shutdown all registered local action components."""
        logger.debug("Shutting down Motor System...")

        # Stop all actions concurrently
        stop_tasks = [action.stop() for action in self.actions]
        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)
