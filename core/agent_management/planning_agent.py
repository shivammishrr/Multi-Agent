from typing import Any, Dict, Optional
from .base_agent import BaseAgent

class PlanningAgent(BaseAgent):
    """
    Decomposes complex tasks into actionable steps and assigns them to ToolAgents.
    """
    def __init__(self, agent_id: str, tool_agent_cls: type, memory: Optional[Any] = None):
        super().__init__(agent_id, memory)
        self.tool_agent_cls = tool_agent_cls

    async def think(self, context: Dict[str, Any]) -> Any:
        # Break down the task into steps (stub)
        task = context.get('task')
        steps = [task]  # Placeholder: assume 1 step
        return {'steps': steps}

    async def act(self, action: Any) -> Any:
        # Assign each step to a ToolAgent (stub: one step)
        results = []
        for step in action['steps']:
            agent = self.tool_agent_cls(agent_id=f"tool_agent_{step}")
            result = await agent.run_cycle({'step': step})
            results.append(result)
        return results

    async def observe(self, observation: Any) -> None:
        self.memory['last_results'] = observation
