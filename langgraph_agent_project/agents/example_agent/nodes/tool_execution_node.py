from typing import Dict, Any
# from ..state import AgentState
# from ....tools.tool_registry import ToolRegistry # This needs to be set up
# from ....tools.base_tool import BaseTool

try:
    from ..state import AgentState
except ImportError:
    from langgraph_agent_project.agents.example_agent.state import AgentState

# Mock ToolRegistry and BaseTool for now, as they are outside this agent's directory
# In a real setup, these would be imported from the project's core/tools directories.
# This node will need access to the application's tool registry.

class MockBaseTool: # Simplified mock
    def __init__(self, name="mock_tool"): self.name = name
    def run(self, **kwargs) -> Dict[str, Any]:
        print(f"Mock tool {self.name} run with {kwargs}")
        return {"output": f"Mock result from {self.name} for input {kwargs}"}

class MockToolRegistry: # Simplified mock
    def __init__(self): self._tools = {"mock_weather_tool": MockBaseTool("mock_weather_tool"), "web_search": MockBaseTool("web_search")}
    def get_tool(self, name: str): return self._tools.get(name)

# Global or passed-in tool registry
# For this placeholder, we'll instantiate a mock one.
# In the compiled graph, the actual registry would be accessible, likely via partial function application.
_tool_registry = MockToolRegistry() # Replace with actual registry access later

def tool_execution_node(state: AgentState) -> Dict[str, Any]:
    '''
    Executes the selected tool using the ToolRegistry and ToolExecutor (concept).
    Requires: tool_name, tool_input from state.
    Updates: tool_observation, error_message (if tool execution fails).
    '''
    print("--- Running Tool Execution Node ---")
    tool_name = state.get("tool_name")
    tool_input = state.get("tool_input", {})

    if not tool_name:
        print("Error: No tool selected for execution.")
        return {"error_message": "No tool was selected for execution."}

    print(f"Attempting to execute tool: '{tool_name}' with input: {tool_input}")

    # tool_executor = ToolExecutor(registry=...) # Langchain has a ToolExecutor
    # For now, directly get and run the tool from our mock registry.

    tool_instance = _tool_registry.get_tool(tool_name)

    if not tool_instance:
        print(f"Error: Tool '{tool_name}' not found in registry.")
        return {
            "tool_observation": f"Error: Tool '{tool_name}' not found.",
            "error_message": f"Tool '{tool_name}' not found in registry.",
            # "messages": state.get("messages", []) + [("system", f"Error: Tool '{tool_name}' not found.")] # Add system message for error
        }

    try:
        # Tools are expected to return a dictionary.
        # Langchain's ToolExecutor often returns a string directly. Adapt as needed.
        # Our BaseTool.run returns a Dict[str, Any] which might be like {"output": "Actual tool output string"}
        # The observation should typically be a string that the LLM can process.

        # Ensure tool_input is a dictionary
        if not isinstance(tool_input, dict):
            # This case should ideally be handled by Pydantic validation in BaseTool.run
            print(f"Warning: tool_input is not a dict: {tool_input}. Trying to use it as kwargs.")
            # If tool_input was a string, this would fail. Assume it's at least dict-like.
            # This depends on how tool_input is populated by previous nodes.
            # For safety, ensure it's always a dict.
            if tool_input is None: tool_input = {}


        result: Dict[str, Any] = tool_instance.run(**tool_input) # Pass tool_input as kwargs

        # The 'tool_observation' should be what the LLM sees.
        # This might be the raw output, or a summary, or a specific field from the result.
        # For now, let's assume the tool's result dictionary has an 'output' key with the string observation.
        observation = result.get("output", str(result))

        print(f"Tool '{tool_name}' executed successfully. Observation: {observation}")
        return {
            "tool_observation": observation,
            "error_message": None, # Clear any previous error
            # "messages": state.get("messages", []) + [("tool_output", observation)] # Or use Langchain's ToolMessage
        }
    except Exception as e:
        print(f"Error executing tool '{tool_name}': {e}")
        error_obs = f"Error executing tool {tool_name}: {str(e)}"
        return {
            "tool_observation": error_obs, # Provide error as observation
            "error_message": str(e),
            # "messages": state.get("messages", []) + [("system", f"Error: {error_obs}")]
        }
