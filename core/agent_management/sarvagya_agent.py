from typing import Any, Dict, Optional
from .base_agent import BaseAgent

class SarvagyaAgent(BaseAgent):
    """
    Main entry agent for the Sarvagya platform. Receives user tasks and delegates to PlanningAgent.
    """
    def __init__(self, agent_id: str, planning_agent: 'PlanningAgent', memory: Optional[Any] = None):
        super().__init__(agent_id, memory)
        self.planning_agent = planning_agent

    async def think(self, context: Dict[str, Any]) -> Any:
        # Receives user task, decides to delegate to planning agent
        return {'delegate_to_planning': context.get('user_task')}

    async def act(self, action: Any) -> Any:
        # Delegates the task to the PlanningAgent
        return await self.planning_agent.run_cycle({'task': action['delegate_to_planning']})

    async def observe(self, observation: Any) -> None:
        # Updates memory/state with results from PlanningAgent
        self.memory['last_result'] = observation
