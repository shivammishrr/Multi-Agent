"""
LangGraph-based agent implementation for Sarvagya.
"""
from typing import Dict, List, Tuple, Any, Optional, TypedDict, Annotated, Literal
import uuid
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

from core.schema import AgentState, Plan, Step, ToolResult
from core.prompts.base_prompts import (
    SARVAGYA_SYSTEM_PROMPT, 
    PLANNING_SYSTEM_PROMPT,
    TOOL_AGENT_SYSTEM_PROMPT,
    REACT_SYSTEM_PROMPT
)
from core.tool_management.tool_manager import ToolManager


# Default LLM configuration
DEFAULT_MODEL = "gpt-4"
DEFAULT_TEMPERATURE = 0.1


def create_llm(model_name: str = DEFAULT_MODEL, temperature: float = DEFAULT_TEMPERATURE):
    """Create an LLM instance with the given parameters."""
    return ChatOpenAI(model=model_name, temperature=temperature)


class SarvagyaNode:
    """Main entry node that receives user tasks and coordinates the workflow."""
    
    def __init__(self, llm=None):
        self.llm = llm or create_llm()
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SARVAGYA_SYSTEM_PROMPT),
            ("human", "{task_description}"),
        ])
        
    def __call__(self, state: AgentState) -> AgentState:
        """Process the user task and decide on next steps."""
        # If this is a new task, initialize the state
        if not state.messages:
            state.add_message("system", SARVAGYA_SYSTEM_PROMPT)
            state.add_message("human", state.task_description)
            
            # Generate initial response acknowledging the task
            chain = self.prompt | self.llm
            response = chain.invoke({"task_description": state.task_description})
            state.add_message("ai", response.content)
            
            # Set status to indicate we need planning
            state.working_memory["next"] = "planning"
            
        return state


class PlanningNode:
    """Node responsible for creating and updating task plans."""
    
    def __init__(self, llm=None):
        self.llm = llm or create_llm()
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", PLANNING_SYSTEM_PROMPT),
            ("human", "Task: {task_description}\n\nCreate a step-by-step plan to accomplish this task."),
        ])
        
    def __call__(self, state: AgentState) -> AgentState:
        """Create or update a plan for the current task."""
        # If we don't have a plan yet, create one
        if not state.plan:
            chain = self.prompt | self.llm
            response = chain.invoke({"task_description": state.task_description})
            
            # Parse the response to extract steps (simplified for now)
            # In a real implementation, we'd use structured output parsing
            plan_steps = []
            for i, line in enumerate(response.content.split("\n")):
                if line.strip().startswith("Step") or line.strip()[0].isdigit():
                    plan_steps.append(
                        Step(
                            id=f"step_{i}",
                            description=line.strip(),
                            status="pending"
                        )
                    )
            
            # Create the plan
            plan = Plan(
                task_id=state.task_id,
                task_description=state.task_description,
                steps=plan_steps,
                current_step_idx=0
            )
            
            state.update_plan(plan)
            if plan.steps:
                state.current_step = plan.steps[0]
            
            # Store the planning result
            state.add_message("ai", f"I've created a plan with {len(plan.steps)} steps.")
            
            # Set next node to tool selection
            state.working_memory["next"] = "tool_selection"
        else:
            # Plan exists, check if we need to update it
            # (simplified - in real implementation we'd have logic to revise the plan)
            state.working_memory["next"] = "tool_selection"
            
        return state


class ToolSelectionNode:
    """Node responsible for selecting the appropriate tool for the current step."""
    
    def __init__(self, llm=None, tool_manager=None):
        self.llm = llm or create_llm()
        self.tool_manager = tool_manager or ToolManager()
        
        # Get available tools
        self.available_tools = self.tool_manager.list_tools()
        
        tool_descriptions = "\n".join([
            f"- {tool.name}: {tool.description}" 
            for tool in self.available_tools
        ])
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", f"{TOOL_AGENT_SYSTEM_PROMPT}\n\nAvailable tools:\n{tool_descriptions}"),
            ("human", "Current step: {step_description}\n\nSelect the most appropriate tool for this step and specify the required parameters."),
        ])
        
    def __call__(self, state: AgentState) -> AgentState:
        """Select the appropriate tool for the current step."""
        if not state.current_step:
            state.error = "No current step to process"
            state.working_memory["next"] = "error"
            return state
            
        # If the step already has a tool assigned, skip selection
        if state.current_step.tool_name:
            state.working_memory["next"] = "tool_execution"
            return state
            
        # Select a tool for the current step
        chain = self.prompt | self.llm
        response = chain.invoke({"step_description": state.current_step.description})
        
        # Parse the response to extract tool name and parameters
        # (simplified - in real implementation we'd use structured output parsing)
        tool_name = None
        tool_input = {}
        
        # Very basic parsing - in production we'd use a more robust approach
        for line in response.content.split("\n"):
            if "Tool:" in line:
                tool_name = line.split("Tool:")[1].strip()
            elif ":" in line and not line.startswith("Tool:"):
                key, value = line.split(":", 1)
                tool_input[key.strip()] = value.strip()
        
        # Update the current step with the selected tool
        if tool_name:
            state.current_step.tool_name = tool_name
            state.current_step.tool_input = tool_input
            state.current_step.status = "in_progress"
            
            # Update the plan
            if state.plan:
                state.plan.steps[state.plan.current_step_idx] = state.current_step
                
            state.add_message("ai", f"I'll use the {tool_name} tool for this step.")
            state.working_memory["next"] = "tool_execution"
        else:
            state.error = "Failed to select a tool for the current step"
            state.working_memory["next"] = "error"
            
        return state


class ToolExecutionNode:
    """Node responsible for executing tools."""
    
    def __init__(self, tool_manager=None):
        self.tool_manager = tool_manager or ToolManager()
        
    def __call__(self, state: AgentState) -> AgentState:
        """Execute the selected tool for the current step."""
        if not state.current_step or not state.current_step.tool_name:
            state.error = "No tool selected for the current step"
            state.working_memory["next"] = "error"
            return state
            
        try:
            # Execute the tool
            result = self.tool_manager.execute_tool(
                state.current_step.tool_name,
                **state.current_step.tool_input
            )
            
            # Update the step with the result
            state.current_step.result = result
            state.current_step.status = "completed"
            
            # Add the result to the state
            tool_result = ToolResult(
                tool_name=state.current_step.tool_name,
                output=result
            )
            state.add_tool_result(tool_result)
            
            # Update the plan
            if state.plan:
                state.plan.steps[state.plan.current_step_idx] = state.current_step
            
            state.add_message("ai", f"Tool execution complete. Result: {result}")
            
            # Move to the next step or finish
            next_step = state.advance_to_next_step()
            if next_step:
                state.working_memory["next"] = "tool_selection"
            else:
                state.working_memory["next"] = "finish"
                
        except Exception as e:
            state.error = f"Tool execution failed: {str(e)}"
            state.current_step.status = "failed"
            state.working_memory["next"] = "error"
            
        return state


class ErrorHandlingNode:
    """Node for handling errors during execution."""
    
    def __init__(self, llm=None):
        self.llm = llm or create_llm()
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an error handling specialist. Your job is to analyze errors and suggest recovery actions."),
            ("human", "An error occurred: {error}\n\nCurrent state: {state_summary}\n\nSuggest how to proceed."),
        ])
        
    def __call__(self, state: AgentState) -> AgentState:
        """Handle errors and decide how to proceed."""
        if not state.error:
            # No error to handle, continue with the workflow
            return state
            
        # Create a summary of the current state
        state_summary = f"Task: {state.task_description}"
        if state.plan:
            state_summary += f"\nPlan progress: Step {state.plan.current_step_idx + 1} of {len(state.plan.steps)}"
        if state.current_step:
            state_summary += f"\nCurrent step: {state.current_step.description}"
            
        # Get recovery suggestions
        chain = self.prompt | self.llm
        response = chain.invoke({
            "error": state.error,
            "state_summary": state_summary
        })
        
        # Add the error and recovery suggestion to the state
        state.add_message("ai", f"Error: {state.error}\n\nRecovery plan: {response.content}")
        
        # For now, we'll just continue with the next step if possible
        # In a more sophisticated implementation, we'd have better error recovery
        if state.plan and state.plan.current_step_idx < len(state.plan.steps) - 1:
            state.advance_to_next_step()
            state.working_memory["next"] = "tool_selection"
        else:
            state.status = "failed"
            state.working_memory["next"] = "finish"
            
        # Clear the error
        state.error = None
        
        return state


class FinishNode:
    """Node for finalizing the task execution."""
    
    def __init__(self, llm=None):
        self.llm = llm or create_llm()
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a task completion specialist. Your job is to summarize the results of a task."),
            ("human", "Task: {task_description}\n\nSummarize the results and provide a conclusion."),
        ])
        
    def __call__(self, state: AgentState) -> AgentState:
        """Finalize the task and provide a summary."""
        # Generate a summary of the task execution
        chain = self.prompt | self.llm
        response = chain.invoke({"task_description": state.task_description})
        
        # Add the summary to the state
        state.add_message("ai", response.content)
        
        # Mark the task as completed
        state.status = "completed"
        
        return state


def create_agent_graph() -> Tuple[StateGraph, Dict[str, Any]]:
    """Create the LangGraph workflow for Sarvagya."""
    # Create the nodes
    sarvagya_node = SarvagyaNode()
    planning_node = PlanningNode()
    tool_selection_node = ToolSelectionNode()
    tool_execution_node = ToolExecutionNode()
    error_handling_node = ErrorHandlingNode()
    finish_node = FinishNode()
    
    # Create the graph
    workflow = StateGraph(AgentState)
    
    # Add the nodes
    workflow.add_node("sarvagya", sarvagya_node)
    workflow.add_node("planning", planning_node)
    workflow.add_node("tool_selection", tool_selection_node)
    workflow.add_node("tool_execution", tool_execution_node)
    workflow.add_node("error", error_handling_node)
    workflow.add_node("finish", finish_node)
    
    # Add the edges
    workflow.add_edge("sarvagya", "planning")
    
    # Dynamic routing based on the "next" field in working_memory
    workflow.add_conditional_edges(
        "planning",
        lambda state: state.working_memory.get("next", "tool_selection"),
        {
            "tool_selection": "tool_selection",
            "error": "error",
            "finish": "finish"
        }
    )
    
    workflow.add_conditional_edges(
        "tool_selection",
        lambda state: state.working_memory.get("next", "tool_execution"),
        {
            "tool_execution": "tool_execution",
            "error": "error"
        }
    )
    
    workflow.add_conditional_edges(
        "tool_execution",
        lambda state: state.working_memory.get("next", "tool_selection"),
        {
            "tool_selection": "tool_selection",
            "error": "error",
            "finish": "finish"
        }
    )
    
    workflow.add_conditional_edges(
        "error",
        lambda state: state.working_memory.get("next", "tool_selection"),
        {
            "tool_selection": "tool_selection",
            "finish": "finish"
        }
    )
    
    # Finish node ends the workflow
    workflow.add_edge("finish", END)
    
    # Compile the graph
    app = workflow.compile()
    
    return app, {
        "sarvagya": sarvagya_node,
        "planning": planning_node,
        "tool_selection": tool_selection_node,
        "tool_execution": tool_execution_node,
        "error": error_handling_node,
        "finish": finish_node
    }


def create_agent_state(task_id: str, task_description: str) -> AgentState:
    """Create a new agent state for a task."""
    return AgentState(
        task_id=task_id,
        task_description=task_description
    )


def run_agent(task_description: str) -> AgentState:
    """Run the Sarvagya agent on a task and return the final state."""
    # Create a unique task ID
    task_id = str(uuid.uuid4())
    
    # Create the initial state
    state = create_agent_state(task_id, task_description)
    
    # Create the agent graph
    graph, _ = create_agent_graph()
    
    # Run the workflow
    for s in graph.stream(state):
        # In a real implementation, we might want to stream updates
        # to a UI or log progress
        pass
    
    # Return the final state
    return graph.get_state()
