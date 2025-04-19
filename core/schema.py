"""
Core schema definitions for Sarvagya.
"""
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field


class Tool(BaseModel):
    """Tool definition."""
    name: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ToolCall(BaseModel):
    """Tool call with inputs."""
    tool_name: str
    tool_input: Dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """Result of a tool execution."""
    tool_name: str
    output: Any
    error: Optional[str] = None


class Step(BaseModel):
    """A single step in a plan."""
    id: str
    description: str
    tool_name: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    status: str = "pending"  # pending, in_progress, completed, failed
    result: Optional[Any] = None


class Plan(BaseModel):
    """A plan consisting of multiple steps."""
    task_id: str
    task_description: str
    steps: List[Step] = Field(default_factory=list)
    current_step_idx: int = 0


class AgentState(BaseModel):
    """State maintained throughout an agent's execution."""
    task_id: str
    task_description: str
    plan: Optional[Plan] = None
    current_step: Optional[Step] = None
    working_memory: Dict[str, Any] = Field(default_factory=dict)
    long_term_memory: Dict[str, Any] = Field(default_factory=dict)
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    tool_results: List[ToolResult] = Field(default_factory=list)
    error: Optional[str] = None
    status: str = "in_progress"  # in_progress, completed, failed
    
    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation history."""
        self.messages.append({"role": role, "content": content})
    
    def add_tool_result(self, result: ToolResult) -> None:
        """Add a tool result to the history."""
        self.tool_results.append(result)
        
    def update_plan(self, plan: Plan) -> None:
        """Update the current plan."""
        self.plan = plan
        
    def advance_to_next_step(self) -> Optional[Step]:
        """Move to the next step in the plan."""
        if not self.plan or self.plan.current_step_idx >= len(self.plan.steps) - 1:
            return None
        
        self.plan.current_step_idx += 1
        self.current_step = self.plan.steps[self.plan.current_step_idx]
        return self.current_step
