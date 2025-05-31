from typing import Dict, List, Optional, Type, Any

from tools.base_tool import BaseTool

# Import concrete tool classes
from tools.file_system.file_saver_tool import FileSaverTool
from tools.file_system.directory_lister_tool import DirectoryListingTool
from tools.web_search.search_tool import WebSearchTool
from tools.code_execution.python_executor_tool import PythonExecuteTool
from tools.agent.terminate_tool import TerminateTool

# Potential for future dynamic loading/discovery
# For now, we explicitly list the tools to register.
DEFAULT_TOOLS_TO_REGISTER: List[Type[BaseTool]] = [
    FileSaverTool,
    DirectoryListingTool,
    WebSearchTool,
    PythonExecuteTool,
    TerminateTool,
]

class ToolRegistry:
    """Manages the registration and retrieval of tools available to the agent."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register_tool(self, tool_instance: BaseTool) -> None:
        """Registers a tool instance.

        Args:
            tool_instance: An instance of a class derived from BaseTool.

        Raises:
            ValueError: If a tool with the same name is already registered.
        """
        if not isinstance(tool_instance, BaseTool):
            raise TypeError(f"Tool must be an instance of BaseTool. Got {type(tool_instance)}")
        if tool_instance.name in self._tools:
            raise ValueError(f"Tool with name '{tool_instance.name}' is already registered.")
        self._tools[tool_instance.name] = tool_instance
        # print(f"Tool '{tool_instance.name}' registered.") # Optional: for debugging

    def register_tools(self, tool_classes: List[Type[BaseTool]]) -> None:
        """Instantiates and registers multiple tools from their classes."""
        for tool_class in tool_classes:
            try:
                # Assuming tools can be instantiated without arguments for now.
                # If tools require specific configurations at instantiation, this will need adjustment.
                tool_instance = tool_class()
                self.register_tool(tool_instance)
            except Exception as e:
                # Log or handle instantiation/registration errors
                print(f"Error registering tool {tool_class.__name__}: {e}") 

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Retrieves a tool by its name."""
        return self._tools.get(name)

    def get_all_tools(self) -> List[BaseTool]:
        """Returns a list of all registered tool instances."""
        return list(self._tools.values())

    def get_tool_names(self) -> List[str]:
        """Returns a list of names of all registered tools."""
        return list(self._tools.keys())

    def get_tool_schemas_for_llm(self) -> List[Dict]:
        """Returns a list of tool schemas formatted for LLM function calling."""
        return [tool.get_function_calling_schema() for tool in self._tools.values()]
    
    def get_langchain_tools(self) -> List[Any]: # Actual type would be langchain.tools.BaseTool or similar
        """Returns a list of LangChain-compatible tool objects."""
        lc_tools = []
        for tool in self._tools.values():
            try:
                lc_tools.append(tool.to_langchain_tool())
            except Exception as e:
                # Log or handle conversion errors
                print(f"Error converting tool '{tool.name}' to LangChain format: {e}")
        return lc_tools

# Global instance or factory function (depending on desired lifecycle management)
# For simplicity, a function to get a pre-populated registry:
def get_default_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register_tools(DEFAULT_TOOLS_TO_REGISTER)
    return registry

# Example Usage:
# if __name__ == '__main__':
#     registry = get_default_tool_registry()

#     print("Registered tool names:", registry.get_tool_names())

#     web_searcher = registry.get_tool("web_search_tool")
#     if web_searcher:
#         print("\nWeb Search Tool Retrieved:", web_searcher.name, web_searcher.description)
#         # Example of running a tool (mocked search)
#         search_results = web_searcher.run(query="What is AI?", num_results=1)
#         print("Search Results:", search_results)
    
#     print("\nLLM Schemas:")
#     for schema in registry.get_tool_schemas_for_llm():
#         import json
#         print(json.dumps(schema, indent=2))
    
#     print("\nLangChain Tools:")
#     lc_tools_list = registry.get_langchain_tools()
#     for lc_tool in lc_tools_list:
#         print(f"  - Name: {lc_tool.name}, Description: {lc_tool.description}, Args Schema: {lc_tool.args_schema}")

#     # Example of trying to register a duplicate tool
#     # try:
#     #     registry.register_tool(WebSearchTool()) # This should fail
#     # except ValueError as ve:
#     #     print(f"\nError as expected: {ve}")
