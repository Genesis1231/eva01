"""
Cortex: EVA's language faculty.

Owns the LLM and prompt construction.
Brain calls cortex.respond(messages) — everything else is internal.
"""

from datetime import datetime
from typing import List, Set, Dict, Any
from langchain.chat_models import init_chat_model
from langchain_core.tools import BaseTool
from langchain_core.messages import (
    SystemMessage,
    AIMessage,
    BaseMessage,
)


from config import logger
from eva.senses.sense_buffer import SenseEntry
from eva.agent.constructor import PromptConstructor
from eva.core.people import PeopleDB


class Cortex:
    """EVA's language cortex — wraps LLM + prompt into a single respond() call."""

    _TEMPERATURE = 0.8  # creative but not too random

    def __init__(
        self,
        model_name: str,
        tools: list[BaseTool],
        people_db: PeopleDB,
    ) -> None:

        self.model_name = model_name
        self.constructor = PromptConstructor(people_db=people_db)
        self._llm = init_chat_model(
            model=model_name,
            temperature=self._TEMPERATURE
        ).bind_tools(tools)

        logger.debug(f"Cortex: {model_name} ready with {len(tools)} tools.")

    async def respond(
        self,
        messages: List[BaseMessage],
        present_people: Set[str],
        journal: str = "",
    ) -> AIMessage:
        """Construct prompt, trim messages, invoke LLM, return response."""
        
        # if sense is audio text, add to messages as HumanMessage; 
        # if it's text, add to system prompt as OBSERVATION
        timestamp = datetime.now().strftime("%A, %B %d, %Y at %I%p")
        system = self.constructor.build_system(
            timestamp=timestamp,
            memory=journal,
            present_people=present_people,
        )

        # Only add the kickoff prompt on the initial pass, not on ReAct continuations
        # (where the last message is a ToolMessage from a prior tool call)
        complete_prompt = [SystemMessage(content=system)] + messages
                         
        # logger.debug(f"Cortex received messages:\n{complete_prompt}\n")

        try:
            response = await self._llm.ainvoke(complete_prompt)
        except Exception as e:
            logger.error(f"LLM ainvoke failed: {e}")
            # Fallback to a safe AIMessage to prevent the agent from crashing
            response = AIMessage(content="[I am having trouble forming a coherent thought right now.]")

        # resource usage logging
        if usage := response.usage_metadata:
            logger.debug(
                f"LLM({self.model_name}) — "
                f"input: {usage.get('input_tokens', 0)/1000:.1f}k  "
                f"output: {usage.get('output_tokens', 0)/1000:.1f}k  "
                f"total: {usage.get('total_tokens', 0)/1000:.1f}k"
            )

        logger.debug(f"Cortex response: {response.content}\n")
        return response
