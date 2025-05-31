from typing import Dict, List, Type, Optional, Any
from .base_tool import BaseTool

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register_tool(self, tool_instance: BaseTool) -> None:
        if tool_instance.name in self._tools:
            # Potentially allow overwriting or raise a more specific error
            print(f"Warning: Tool '{tool_instance.name}' is already registered. Overwriting.")
        self._tools[tool_instance.name] = tool_instance
        print(f"Tool '{tool_instance.name}' registered.")

    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        return self._tools.get(tool_name)

    def get_all_tools(self) -> List[BaseTool]:
        return list(self._tools.values())

    def get_tool_schemas_for_llm(self) -> List[Dict[str, Any]]:
        '''
        Returns a list of tool schemas formatted for LLM function/tool calling.
        This typically follows OpenAI's function calling schema.
        '''
        schemas = []
        for tool_name, tool_instance in self._tools.items():
            # Assuming BaseTool has a method to return its schema in the desired format
            schemas.append(tool_instance.get_langchain_tool_schema())
        return schemas

# Example Usage:
if __name__ == "__main__":
    from .base_tool import BaseToolInput # For example tool
    from pydantic import Field # Added for ToolTwoInput example

    # Define a couple of example tools for testing the registry
    class ToolOne(BaseTool):
        name = "tool_one"
        description = "The first example tool."
        args_schema = BaseToolInput # No specific args

        def _run(self, **kwargs: Any) -> Dict[str, Any]:
            return {"message": "Tool One executed successfully"}
        async def _arun(self, **kwargs: Any) -> Dict[str, Any]:
            return {"message": "Tool One executed asynchronously"}

    class ToolTwoInput(BaseToolInput):
        query: str = Field(..., description="A query string for Tool Two")

    class ToolTwo(BaseTool):
        name = "tool_two"
        description = "The second example tool, takes a query."
        args_schema = ToolTwoInput

        def _run(self, query: str) -> Dict[str, Any]:
            return {"result": f"Tool Two processed query: '{query}'"}
        async def _arun(self, query: str) -> Dict[str, Any]:
            return {"result": f"Tool Two processed query asynchronously: '{query}'"}

    # Initialize registry and register tools
    registry = ToolRegistry()
    tool_one_instance = ToolOne()
    tool_two_instance = ToolTwo()

    registry.register_tool(tool_one_instance)
    registry.register_tool(tool_two_instance)

    # Retrieve a tool
    retrieved_tool_one = registry.get_tool("tool_one")
    if retrieved_tool_one:
        print(f"Retrieved tool: {retrieved_tool_one.name}, Description: {retrieved_tool_one.description}")
        # Example of running it (assuming no args needed for tool_one)
        print(retrieved_tool_one.run())

    retrieved_tool_two = registry.get_tool("tool_two")
    if retrieved_tool_two:
        print(f"Retrieved tool: {retrieved_tool_two.name}, Description: {retrieved_tool_two.description}")
        # Example of running it (tool_two needs 'query' arg)
        try:
            print(retrieved_tool_two.run(query="test query for tool two"))
        except Exception as e:
            print(f"Error running tool_two: {e}")


    # Get all tool schemas for LLM
    print("\nLLM Tool Schemas:")
    schemas = registry.get_tool_schemas_for_llm()
    import json
    print(json.dumps(schemas, indent=2))

    # Attempt to get a non-existent tool
    non_existent_tool = registry.get_tool("non_existent_tool")
    print(f"Trying to retrieve 'non_existent_tool': {non_existent_tool}")
