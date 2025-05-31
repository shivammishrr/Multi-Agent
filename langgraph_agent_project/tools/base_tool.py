from abc import ABC, abstractmethod
from typing import Type, Optional, Any, Dict
from pydantic import BaseModel, Field

class BaseToolInput(BaseModel):
    # This can be subclassed by specific tools if they need structured input
    pass

class BaseToolOutput(BaseModel):
    # This can be subclassed by specific tools if they need structured output
    output: Any = Field(..., description="The direct output of the tool execution.")

class BaseTool(ABC):
    name: str = "base_tool"
    description: str = "A base tool that does nothing."
    args_schema: Type[BaseModel] = BaseToolInput # Pydantic model for arguments
    # output_schema: Type[BaseModel] = BaseToolOutput # Optional: If tools should also have a defined output schema

    # The `__init__` method can be used if tools need to be instantiated
    # with configuration, API keys, etc.
    # def __init__(self, config: Optional[Dict[str, Any]] = None):
    #     self.config = config or {}

    @abstractmethod
    def _run(self, **kwargs: Any) -> Dict[str, Any]:
        '''Synchronous execution of the tool.'''
        pass

    @abstractmethod
    async def _arun(self, **kwargs: Any) -> Dict[str, Any]:
        '''Asynchronous execution of the tool.'''
        pass

    def run(self, **kwargs: Any) -> Dict[str, Any]:
        # Input validation using Pydantic
        if self.args_schema:
            validated_args = self.args_schema(**kwargs)
            return self._run(**validated_args.model_dump())
        return self._run(**kwargs)

    async def arun(self, **kwargs: Any) -> Dict[str, Any]:
        if self.args_schema:
            validated_args = self.args_schema(**kwargs)
            return await self._arun(**validated_args.model_dump())
        return await self._arun(**kwargs)

    # For Langchain compatibility, tools often expose their schema for LLMs
    def get_langchain_tool_schema(self) -> Dict[str, Any]:
        # Simplified for now, Langchain has specific FormattedTool or @tool decorator
        # that generates a more detailed schema including function name, description, and args.
        if not self.args_schema or self.args_schema == BaseToolInput:
             # If no specific args_schema or it's the base empty one, treat as no specific args
            return {
                "name": self.name,
                "description": self.description,
                "parameters": {"type": "object", "properties": {}} # Or simply no "parameters" field
            }

        # Pydantic model_json_schema() gives a JSON schema
        schema = self.args_schema.model_json_schema()

        # We need to remove 'title' and 'description' from the top level of the schema
        # if they exist, as Langchain expects 'parameters' to directly contain 'type', 'properties', etc.
        parameters = {
            "type": schema.get("type", "object"),
            "properties": schema.get("properties", {}),
        }
        if "required" in schema:
            parameters["required"] = schema["required"]

        return {
            "name": self.name,
            "description": self.description,
            "parameters": parameters,
        }


if __name__ == '__main__':
    # Example of defining a custom tool
    class MyCustomToolInput(BaseToolInput):
        param1: str = Field(..., description="A required string parameter.")
        param2: int = Field(10, description="An optional integer parameter with a default value.")

    class MyCustomTool(BaseTool):
        name = "my_custom_tool"
        description = "A custom tool that demonstrates input validation."
        args_schema = MyCustomToolInput

        def _run(self, param1: str, param2: int = 10) -> Dict[str, Any]:
            print(f"MyCustomTool executed with: param1='{param1}', param2={param2}")
            return {"result": f"Processed {param1} and {param2}"}

        async def _arun(self, param1: str, param2: int = 10) -> Dict[str, Any]:
            print(f"MyCustomTool (async) executed with: param1='{param1}', param2={param2}")
            # Simulate async work
            # import asyncio
            # await asyncio.sleep(0.1)
            return {"result": f"Processed async {param1} and {param2}"}

    # Instantiate and run the tool
    tool = MyCustomTool()

    # Valid input
    print("Running with valid input:")
    result = tool.run(param1="hello")
    print(f"Result: {result}")

    result_def = tool.run(param1="world", param2=25)
    print(f"Result: {result_def}")

    print("\nSchema for Langchain:")
    print(tool.get_langchain_tool_schema())

    # Invalid input - Pydantic will raise ValidationError
    print("\nRunning with invalid input (missing param1):")
    try:
        tool.run(param2=5) # param1 is missing
    except Exception as e:
        print(f"Error: {e}")

    print("\nRunning with invalid input type (param2 not an int):")
    try:
        tool.run(param1="test", param2="not_an_integer")
    except Exception as e:
        print(f"Error: {e}")
