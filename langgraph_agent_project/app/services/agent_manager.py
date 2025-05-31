from typing import Any, Dict, Optional, List
# Assuming the compiled graph app is accessible
# This import path will depend on the final project structure and how it's run.
# from langgraph_agent_project.agents.example_agent.graph import agent_graph_app
# from langgraph_agent_project.agents.example_agent.state import AgentState # For type hinting

# For now, to make this module self-contained for creation,
# let's use a placeholder for agent_graph_app.
# In a real application, this would be imported or loaded dynamically.

# --- Placeholder for agent graph app (replace with actual import) ---
class MockAgentGraphApp:
    def invoke(self, input_dict: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        print(f"MockAgentGraphApp invoked with: {input_dict}")
        # Simulate a response based on input
        user_input = input_dict.get("input", "")
        messages = input_dict.get("messages", [])
        final_output = f"Mock response to '{user_input}'"
        messages.append(("ai", final_output))
        return {
            "input": user_input,
            "messages": messages,
            "final_output": final_output,
            "iterations": 1 # Mocked
        }

    async def ainvoke(self, input_dict: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        print(f"MockAgentGraphApp ainvoked with: {input_dict}")
        # Simulate an async response
        import asyncio
        await asyncio.sleep(0.05)
        user_input = input_dict.get("input", "")
        messages = input_dict.get("messages", [])
        final_output = f"Mock async response to '{user_input}'"
        messages.append(("ai", final_output))
        return {
            "input": user_input,
            "messages": messages,
            "final_output": final_output,
            "iterations": 1 # Mocked
        }

    def stream(self, input_dict: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        print(f"MockAgentGraphApp stream called with: {input_dict}")
        user_input = input_dict.get("input", "")
        messages = input_dict.get("messages", [])

        # Simulate streaming output
        yield {"thought_node": {"current_thought": "Thinking about the input..."}}
        yield {"tool_execution_node": {"tool_observation": "Mock tool result."}}
        final_output_chunk = f"Streamed mock response to '{user_input}'"
        messages.append(("ai", final_output_chunk))
        yield {"response_node": {"final_output": final_output_chunk, "messages": messages}}


# Replace this with actual import when structure is integrated
try:
    from langgraph_agent_project.agents.example_agent.graph import agent_graph_app
    # from langgraph_agent_project.agents.example_agent.state import AgentState # For type hints
except (ImportError, ModuleNotFoundError):
    print("AgentManager: Could not import actual agent_graph_app. Using MockAgentGraphApp.")
    agent_graph_app = MockAgentGraphApp()
# --- End Placeholder ---


class AgentManager:
    def __init__(self, graph_app: Optional[Any] = None):
        '''
        Initializes the AgentManager.
        Args:
            graph_app: A compiled LangGraph application.
                       If None, loads the default example agent.
        '''
        if graph_app is None:
            # In a more complex setup, this could discover agents in the 'agents/' dir
            # or load a specific agent based on configuration.
            self.agent_app = agent_graph_app # From import or placeholder
            print("AgentManager initialized with the default example_agent graph.")
        else:
            self.agent_app = graph_app
            print("AgentManager initialized with a provided graph app.")

        if self.agent_app is None:
            raise ValueError("AgentManager: No agent graph app loaded or provided.")

    def invoke_agent(self, user_input: str, conversation_history: Optional[List[tuple]] = None, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        '''
        Invokes the agent with user input and optional conversation history.

        Args:
            user_input: The user's latest message.
            conversation_history: A list of previous messages, e.g., [("human", "hi"), ("ai", "hello")].
                                  LangGraph's `AgentState` expects `List[BaseMessage]`.
                                  This method should handle conversion if necessary or expect BaseMessages.
                                  For now, assuming the graph's message list handles various formats.
            config: Optional configuration for the graph invocation (e.g., recursion_limit).

        Returns:
            The final state dictionary from the agent graph.
        '''
        if config is None:
            config = {"recursion_limit": 15} # Default recursion limit

        # Prepare the initial state for the graph
        # The 'messages' key in AgentState is typically managed by LangGraph using operator.add
        # It expects a list of BaseMessage objects (HumanMessage, AIMessage, ToolMessage, etc.)

        # For simplicity, let's assume the graph's entry point or a pre-processing step
        # handles the conversion of raw string inputs/history into BaseMessage objects if needed.
        # Or, the AgentState's 'input' field is used by the first node to create a HumanMessage.

        current_messages = conversation_history or []
        # Add the new user input as the latest message.
        # The graph's `thought_node` (or an initial preprocessor node) should convert this to a HumanMessage
        # and append to the state's `messages` list if that's the convention.
        # Or, the graph's `messages` field directly takes this.
        # The current AgentState uses `messages: Annotated[List[BaseMessage], operator.add]`
        # and `input: str`. The `thought_node` uses `state.get("input")`.
        # The `graph.py` example adds `("human", initial_input)` to messages.

        initial_graph_state = {
            "input": user_input,
            "messages": current_messages + [("human", user_input)], # Simplistic message history for now
            "scratchpad": [],
            "iterations": 0,
            # Other fields will be initialized to None or default by AgentState/TypedDict nature
        }

        print(f"AgentManager: Invoking agent with input='{user_input}', history_len={len(current_messages)}")
        final_state = self.agent_app.invoke(initial_graph_state, config)
        return final_state

    async def ainvoke_agent(self, user_input: str, conversation_history: Optional[List[tuple]] = None, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        '''Asynchronously invokes the agent.'''
        if config is None:
            config = {"recursion_limit": 15}

        initial_graph_state = {
            "input": user_input,
            "messages": (conversation_history or []) + [("human", user_input)],
            "scratchpad": [],
            "iterations": 0,
        }
        print(f"AgentManager: Asynchronously invoking agent with input='{user_input}', history_len={len(conversation_history or [])}")
        final_state = await self.agent_app.ainvoke(initial_graph_state, config)
        return final_state

    def stream_agent_responses(self, user_input: str, conversation_history: Optional[List[tuple]] = None, config: Optional[Dict[str, Any]] = None):
        '''Streams responses and intermediate steps from the agent.'''
        if config is None:
            config = {"recursion_limit": 15}

        initial_graph_state = {
            "input": user_input,
            "messages": (conversation_history or []) + [("human", user_input)],
            "scratchpad": [],
            "iterations": 0,
        }
        print(f"AgentManager: Streaming agent responses for input='{user_input}', history_len={len(conversation_history or [])}")
        for step_output in self.agent_app.stream(initial_graph_state, config):
            yield step_output


if __name__ == "__main__":
    print("--- AgentManager Test ---")
    manager = AgentManager() # Uses default agent (mock or actual if import works)

    print("\n--- Synchronous Invocation Test ---")
    test_input_sync = "Tell me a fun fact."
    # In a real app, conversation_history would be Langchain BaseMessage objects
    # For this test, using tuples as per the current method signature
    history_sync: List[tuple] = [("human", "Hi there!"), ("ai", "Hello! How can I help you today?")]

    final_state_sync = manager.invoke_agent(test_input_sync, conversation_history=history_sync)
    print(f"Sync Invocation Final Output: {final_state_sync.get('final_output')}")
    print(f"Sync Invocation Full Final State: {final_state_sync}")


    print("\n--- Asynchronous Invocation Test ---")
    import asyncio
    test_input_async = "What is the capital of France?"
    history_async: List[tuple] = []

    async def run_async_test():
        final_state_async = await manager.ainvoke_agent(test_input_async, conversation_history=history_async)
        print(f"Async Invocation Final Output: {final_state_async.get('final_output')}")
        print(f"Async Invocation Full Final State: {final_state_async}")

    asyncio.run(run_async_test())


    print("\n--- Streaming Test ---")
    test_input_stream = "Search for LangGraph tutorials."
    history_stream: List[tuple] = []

    print(f"Streaming for input: '{test_input_stream}'")
    for i, step in enumerate(manager.stream_agent_responses(test_input_stream, conversation_history=history_stream)):
        node_name = list(step.keys())[0]
        node_output = step[node_name]
        print(f"Stream Step {i+1} (Node: {node_name}):")
        # Print some key fields from the node's output part of the state
        if "current_thought" in node_output: print(f"  Thought: {node_output['current_thought']}")
        if "tool_name" in node_output: print(f"  Tool: {node_output['tool_name']}")
        if "tool_input" in node_output: print(f"  Tool Input: {node_output['tool_input']}")
        if "tool_observation" in node_output: print(f"  Observation: {node_output['tool_observation']}")
        if "final_output" in node_output: print(f"  Final Output: {node_output['final_output']}")
    print("Streaming finished.")
