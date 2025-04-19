"""
Main orchestrator for Sarvagya.
Handles agent initialization, task management, and state persistence.
"""
import asyncio
import uuid
from typing import Dict, List, Optional, Any
import redis

from core.agent_management.langgraph_agents import create_agent_graph, create_agent_state
from core.schema import AgentState


class Orchestrator:
    """
    Central orchestrator for Sarvagya.
    Manages agent workflows, task queues, and state persistence.
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """Initialize the orchestrator with Redis connection."""
        self.redis_client = redis.Redis.from_url(redis_url)
        self.active_tasks: Dict[str, Any] = {}
        self.agent_graph, self.nodes = create_agent_graph()
    
    async def submit_task(self, task_description: str) -> str:
        """
        Submit a new task to be processed by Sarvagya.
        
        Args:
            task_description: The description of the task to be performed
            
        Returns:
            task_id: Unique identifier for the task
        """
        # Generate a unique task ID
        task_id = str(uuid.uuid4())
        
        # Create initial state
        state = create_agent_state(task_id, task_description)
        
        # Store initial state in Redis
        self._save_state(task_id, state)
        
        # Start task processing in background
        asyncio.create_task(self._process_task(task_id, state))
        
        return task_id
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get the current status of a task.
        
        Args:
            task_id: The unique identifier of the task
            
        Returns:
            status: Dictionary containing task status information
        """
        # Retrieve state from Redis
        state = self._load_state(task_id)
        
        if not state:
            return {"error": "Task not found"}
        
        # Return relevant status information
        return {
            "task_id": state.task_id,
            "status": state.status,
            "current_step": state.current_step.id if state.current_step else None,
            "progress": f"{state.plan.current_step_idx + 1}/{len(state.plan.steps)}" if state.plan else "0/0",
            "error": state.error
        }
    
    async def get_task_result(self, task_id: str) -> Dict[str, Any]:
        """
        Get the complete result of a task.
        
        Args:
            task_id: The unique identifier of the task
            
        Returns:
            result: Dictionary containing the complete task result
        """
        # Retrieve state from Redis
        state = self._load_state(task_id)
        
        if not state:
            return {"error": "Task not found"}
        
        # Return the complete state (or a subset of it)
        return {
            "task_id": state.task_id,
            "task_description": state.task_description,
            "status": state.status,
            "messages": state.messages,
            "tool_results": [result.dict() for result in state.tool_results],
            "error": state.error
        }
    
    async def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """
        Cancel a running task.
        
        Args:
            task_id: The unique identifier of the task
            
        Returns:
            result: Dictionary indicating success or failure
        """
        # Check if task exists
        state = self._load_state(task_id)
        
        if not state:
            return {"error": "Task not found"}
        
        # Cancel the task if it's in the active tasks
        if task_id in self.active_tasks:
            # Mark as cancelled in the state
            state.status = "cancelled"
            self._save_state(task_id, state)
            
            # Remove from active tasks
            self.active_tasks.pop(task_id, None)
            
            return {"status": "cancelled", "task_id": task_id}
        else:
            return {"error": "Task is not active"}
    
    async def _process_task(self, task_id: str, initial_state: AgentState) -> None:
        """
        Process a task using the agent graph.
        
        Args:
            task_id: The unique identifier of the task
            initial_state: The initial state for the task
        """
        try:
            # Add to active tasks
            self.active_tasks[task_id] = True
            
            # Run the agent graph with streaming updates
            for state in self.agent_graph.stream(initial_state):
                # Save intermediate state to Redis
                self._save_state(task_id, state)
                
                # Publish update to Redis pubsub
                self._publish_update(task_id, state)
            
            # Get final state
            final_state = self.agent_graph.get_state()
            
            # Save final state
            self._save_state(task_id, final_state)
            
            # Publish final update
            self._publish_update(task_id, final_state)
            
        except Exception as e:
            # Handle errors
            state = self._load_state(task_id)
            if state:
                state.status = "failed"
                state.error = str(e)
                self._save_state(task_id, state)
                self._publish_update(task_id, state)
        finally:
            # Remove from active tasks
            self.active_tasks.pop(task_id, None)
    
    def _save_state(self, task_id: str, state: AgentState) -> None:
        """Save agent state to Redis."""
        # Convert state to JSON
        state_json = state.json()
        
        # Save to Redis
        self.redis_client.set(f"sarvagya:task:{task_id}:state", state_json)
        
        # Set expiration (30 days)
        self.redis_client.expire(f"sarvagya:task:{task_id}:state", 60 * 60 * 24 * 30)
    
    def _load_state(self, task_id: str) -> Optional[AgentState]:
        """Load agent state from Redis."""
        # Get from Redis
        state_json = self.redis_client.get(f"sarvagya:task:{task_id}:state")
        
        if not state_json:
            return None
        
        # Convert from JSON
        return AgentState.parse_raw(state_json)
    
    def _publish_update(self, task_id: str, state: AgentState) -> None:
        """Publish state update to Redis pubsub."""
        # Convert state to JSON
        state_json = state.json()
        
        # Publish to Redis pubsub
        self.redis_client.publish(f"sarvagya:updates:{task_id}", state_json)
        
        # Also publish to a global updates channel
        self.redis_client.publish("sarvagya:updates", state_json)


# Singleton instance
_instance = None

def get_orchestrator(redis_url: str = "redis://localhost:6379/0") -> Orchestrator:
    """Get the singleton Orchestrator instance."""
    global _instance
    if _instance is None:
        _instance = Orchestrator(redis_url)
    return _instance
