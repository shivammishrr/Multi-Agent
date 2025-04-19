from typing import Any, Dict, Optional
from .base_agent import BaseAgent
from core.tool_management.tool_manager import ToolManager

class ToolAgent(BaseAgent):
    """
    Executes a single tool step via the ToolManager.
    """
    def __init__(self, agent_id: str, memory: Optional[Any] = None):
        super().__init__(agent_id, memory)
        self.tool_manager = ToolManager()

    async def think(self, context: Dict[str, Any]) -> Any:
        # Decide which tool to use for the step (stub: use tool name in step)
        step = context.get('step')
        return {'tool_name': step.get('tool_name'), 'tool_args': step.get('tool_args', {})}

    async def act(self, action: Any) -> Any:
        # Invoke the tool using ToolManager
        return await self.tool_manager.execute_tool(action['tool_name'], **action['tool_args'])

    async def observe(self, observation: Any) -> None:
        self.memory['tool_result'] = observation
