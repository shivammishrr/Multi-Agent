from typing import Dict, Any
# from ..state import AgentState
try:
    from ..state import AgentState
except ImportError:
    from langgraph_agent_project.agents.example_agent.state import AgentState

def tool_selection_node(state: AgentState) -> Dict[str, Any]:
    '''
    (Optional Node)
    Processes LLM output (e.g., from thought_node) to identify a tool and its arguments.
    This node is useful if the LLM doesn't directly output structured tool calls
    that can be immediately used by tool_execution_node.

    Updates: tool_name, tool_input.
    '''
    print("--- Running Tool Selection Node ---")
    current_thought = state.get("current_thought", "")
    print(f"Current thought for tool selection: {current_thought}")

    # Mock logic:
    # In a real scenario, this node would:
    # 1. Parse `current_thought` or a specific field from the LLM response.
    # 2. Identify if a tool is requested and what its arguments are.
    # 3. This might involve regex, string matching, or another LLM call for formatting.

    # For this placeholder, we assume thought_node already decided `tool_name` and `tool_input`
    # if a tool is needed. So this node might just validate or pass through.
    # If thought_node directly sets tool_name and tool_input, this node might not be needed
    # or could be used for more complex parsing if the LLM output is just natural language.

    if state.get("tool_name"):
        print(f"Tool '{state.get('tool_name')}' already selected by a previous node. Passing through.")
        return {} # No changes, assuming previous node set tool_name and tool_input

    # Example: If LLM output was just "I should use web_search for 'LangGraph tutorials'"
    # This node would parse that to: tool_name="web_search", tool_input={"query": "LangGraph tutorials"}
    if "search for" in current_thought.lower():
        # Crude parsing example
        query_part = current_thought.lower().split("search for", 1)[-1].strip().replace("'", "")
        print(f"Tool Selection: Identified request to search for '{query_part}'.")
        return {
            "tool_name": "web_search", # Assuming web_search tool is registered
            "tool_input": {"query": query_part, "num_results": 2}
        }
    else:
        print("Tool Selection: No specific tool identified from thought, or tool already selected.")
        # This implies either no tool is needed, or the previous node (e.g. thought_node)
        # has already populated tool_name and tool_input.
        return {}
