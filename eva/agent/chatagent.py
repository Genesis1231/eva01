"""
ChatAgent: EVA's language model interface.

Handles model initialization, prompt construction, tool binding, and async inference.
"""

from config import logger
from typing import Dict, Any, List
from datetime import datetime

from langchain_core.messages import SystemMessage, HumanMessage
from langchain.chat_models import init_chat_model 

from .schema import RespondToUser
from .constructor import PromptConstructor


class ChatAgent:
    """EVA's chat agent — wraps a language model with tool binding and structured response extraction."""

    def __init__(
        self,
        model_name: str = "ollama:llama3.1:70b",
        base_url: str = "http://localhost:11434",
        language: str = "en",
    ) -> None:
        self.model_name = model_name
        self.base_url = base_url
        self.language = language

        self.constructor = PromptConstructor()
        self._initialize_model()

    def _initialize_model(self):

        kwargs: Dict[str, Any] = {"temperature": 0.8}
        if "ollama" in self.model_name:
            kwargs.update({
                "base_url": self.base_url,
                "keep_alive": "1h",
                "format": "json"
            })

        try:
            self._llm = init_chat_model(self.model_name, **kwargs)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize model {self.model_name}: {e}")

        # Bind RespondToUser as the default response tool; rebind via set_tools() if needed
        self._llm_with_tools = self._llm.bind_tools([RespondToUser])
        logger.debug(f"ChatAgent: {self.model_name} is ready.")

    def set_tools(self, tools: List[Any]) -> None:
        """Bind additional tools alongside RespondToUser. Call before arespond() if tools change."""
        self._llm_with_tools = self._llm.bind_tools([RespondToUser] + tools)

    async def arespond(self, sense: str = "") -> Dict[str, Any]:
        """Invoke the agent and return the structured RespondToUser response."""
        
        system, human = self.constructor.build_prompt(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
            sense=sense,
        )

        messages = [SystemMessage(content=system), HumanMessage(content=human)]

        try:
            response = await self._llm_with_tools.ainvoke(messages)
            logger.debug(f"ChatAgent: response — \n{response.model_dump_json(indent=2)}")

            #Usage count
            usage = response.usage_metadata
            logger.debug(f"LLM({self.model_name}) Usage - Input tokens: {usage['input_tokens']/1000:.2f}k, Output tokens: {usage['output_tokens']/1000:.2f}k, Total tokens: {usage['total_tokens']/1000:.2f}k")

            for tool_call in (response.tool_calls or []):
                if tool_call["name"] == "RespondToUser":
                    return tool_call["args"]

            return {"response": response.content}

        except Exception as e:
            logger.error(f"ChatAgent error: {e}")
            raise
