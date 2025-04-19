import abc
from typing import Any, Dict, Optional

class BaseAgent(abc.ABC):
    """
    Abstract base class for all agents in Sarvagya.
    Handles state, memory, and the think-act-observe cycle.
    """
    def __init__(self, agent_id: str, memory: Optional[Any] = None):
        self.agent_id = agent_id
        self.memory = memory or {}
        self.state: Dict[str, Any] = {}

    @abc.abstractmethod
    async def think(self, context: Dict[str, Any]) -> Any:
        """Analyze context and determine next action."""
        pass

    @abc.abstractmethod
    async def act(self, action: Any) -> Any:
        """Perform action (invoke tool, delegate, etc)."""
        pass

    @abc.abstractmethod
    async def observe(self, observation: Any) -> None:
        """Process results, update memory/state."""
        pass

    async def run_cycle(self, context: Dict[str, Any]) -> None:
        """Default think-act-observe loop."""
        action = await self.think(context)
        result = await self.act(action)
        await self.observe(result)
