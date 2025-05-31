from typing import List, Optional, TypedDict, Annotated
from langchain_core.messages import BaseMessage
import operator

# The issue mentions Pydantic model, LangGraph often uses TypedDict for state.
# Let's use TypedDict as it's more common in LangGraph examples,
# but ensure it's clear how Pydantic could be used if preferred for validation within nodes.
# Pydantic can be used for messages or tool inputs/outputs stored within the state.

class AgentState(TypedDict):
    # Input from the user
    input: str

    # History of messages. This will be managed by LangGraph's message handling.
    # We might add specific logic to append to this list in nodes.
    messages: Annotated[List[BaseMessage], operator.add]

    # Intermediate thoughts or reasoning steps of the agent
    scratchpad: List[str] # Could also be List[BaseMessage] or a more structured log

    # For ReAct style agents:
    # Current thought or action plan
    current_thought: Optional[str] = None

    # Selected tool and its arguments, if a tool is to be called
    tool_name: Optional[str] = None
    tool_input: Optional[dict] = None # Arguments for the tool

    # Observation or result from the last tool execution
    tool_observation: Optional[str] = None # Or could be a more structured object

    # The final answer or output from the agent
    final_output: Optional[str] = None

    # Error messages, if any occurred during processing
    error_message: Optional[str] = None

    # Number of iterations or steps taken, useful for loop control
    iterations: int

# Example of how you might use Pydantic for parts of the state if needed:
# from pydantic import BaseModel, Field
# class ToolCall(BaseModel):
#     name: str
#     arguments: dict
# class AgentStatePydantic(BaseModel):
#     input_query: str = Field(..., alias="input")
#     message_history: List[BaseMessage] = Field(default_factory=list, alias="messages")
#     current_tool_calls: Optional[List[ToolCall]] = None
#     # etc.

if __name__ == '__main__':
    # Example instantiation (TypedDicts are dictionaries at runtime)
    initial_state: AgentState = {
        "input": "Hello, agent!",
        "messages": [], # operator.add means new messages lists will be concatenated
        "scratchpad": [],
        "current_thought": None,
        "tool_name": None,
        "tool_input": None,
        "tool_observation": None,
        "final_output": None,
        "error_message": None,
        "iterations": 0,
    }
    print("Initial Agent State Example:")
    for key, value in initial_state.items():
        print(f"  {key}: {value}")

    # Example of how messages might be appended (illustrative)
    from langchain_core.messages import HumanMessage, AIMessage

    current_messages = initial_state.get("messages", [])
    new_messages = [HumanMessage(content="What is LangGraph?")]

    # Simulating LangGraph's `operator.add` effect on 'messages'
    updated_messages = current_messages + new_messages
    initial_state["messages"] = updated_messages

    ai_response_messages = [AIMessage(content="LangGraph is a library for building stateful, multi-actor applications with LLMs.")]
    initial_state["messages"] = initial_state["messages"] + ai_response_messages

    print("\nUpdated Agent State (after adding messages):")
    for key, value in initial_state.items():
        if key == "messages":
            print(f"  {key}:")
            for msg in value:
                print(f"    {msg.type}: {msg.content}")
        else:
            print(f"  {key}: {value}")

    initial_state["iterations"] +=1
    print(f"  iterations: {initial_state['iterations']}")
