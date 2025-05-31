from abc import ABC, abstractmethod
from typing import Type, Optional, Any, Dict

from pydantic import BaseModel, Field

class BaseToolInput(BaseModel):
    """Base model for tool inputs. Tools should subclass this and add their specific fields."""
    pass

class BaseToolOutput(BaseModel):
    """Base model for tool outputs. Tools should subclass this and add their specific fields."""
    output: Optional[Any] = None
    error: Optional[str] = None
    # Potentially add other common fields like 'raw_output', 'status_code', etc.

class BaseTool(ABC, BaseModel):
    """Abstract base class for all tools.

    Each tool must define:
    - name: A unique name for the tool.
    - description: A clear description of what the tool does and when to use it.
    - args_schema: A Pydantic model defining the input arguments for the tool.
    - return_schema: A Pydantic model defining the output of the tool (optional, defaults to BaseToolOutput).
    "

    name: str = Field(..., description="Unique name for the tool.")
    description: str = Field(..., description="Description of what the tool does and when to use it.")
    args_schema: Type[BaseModel] = Field(default=BaseToolInput, description="Pydantic model defining the input arguments for the tool.")
    return_schema: Type[BaseModel] = Field(default=BaseToolOutput, description="Pydantic model defining the output of the tool.")

    class Config:
        arbitrary_types_allowed = True

    @abstractmethod
    def _run(self, **kwargs: Any) -> BaseToolOutput:
        """Execute the tool synchronously.

        This method should be implemented by subclasses to perform the actual work.
        Input arguments are passed as keyword arguments, validated against args_schema.
        """
        pass

    @abstractmethod
    async def _arun(self, **kwargs: Any) -> BaseToolOutput:
        """Execute the tool asynchronously.

        This method should be implemented by subclasses for tools that can perform I/O-bound operations asynchronously.
        Input arguments are passed as keyword arguments, validated against args_schema.
        If the tool does not support async execution, it can raise NotImplementedError or call the sync version.
        """
        pass

    def run(self, **kwargs: Any) -> Dict[str, Any]:
        """Validates input, runs the tool, validates output, and returns a dictionary."""
        try:
            # Validate inputs using the tool's specific args_schema
            validated_args = self.args_schema(**kwargs)
        except Exception as e: # Catches Pydantic validation errors and others
            # Consider logging the error here
            # Return a dictionary matching the structure expected by LangGraph/LangChain tool nodes
            return {"tool_output": None, "error": f"Input validation error for tool '{self.name}': {e}"}

        try:
            tool_output_model = self._run(**validated_args.model_dump())
            # Validate output against the tool's return_schema (if defined and not BaseToolOutput)
            if self.return_schema and self.return_schema != BaseToolOutput:
                validated_output = self.return_schema(**tool_output_model.model_dump())
                return validated_output.model_dump()
            return tool_output_model.model_dump() # Return as dict

        except NotImplementedError:
             return {"tool_output": None, "error": f"Tool '{self.name}' does not support synchronous execution."}
        except Exception as e:
            # Consider logging the error here
            return {"tool_output": None, "error": f"Error during execution of tool '{self.name}': {e}"}

    async def arun(self, **kwargs: Any) -> Dict[str, Any]:
        """Validates input, runs the tool asynchronously, validates output, and returns a dictionary."""
        try:
            validated_args = self.args_schema(**kwargs)
        except Exception as e:
            return {"tool_output": None, "error": f"Input validation error for tool '{self.name}': {e}"}

        try:
            tool_output_model = await self._arun(**validated_args.model_dump())
            if self.return_schema and self.return_schema != BaseToolOutput:
                validated_output = self.return_schema(**tool_output_model.model_dump())
                return validated_output.model_dump()
            return tool_output_model.model_dump()
        except NotImplementedError:
            # Fallback to sync run if arun is not implemented but run is
            # This is a common pattern but can be removed if strict async is required
            try:
                tool_output_model = self._run(**validated_args.model_dump())
                if self.return_schema and self.return_schema != BaseToolOutput:
                    validated_output = self.return_schema(**tool_output_model.model_dump())
                    return validated_output.model_dump()
                return tool_output_model.model_dump()
            except Exception as e:
                return {"tool_output": None, "error": f"Error during fallback sync execution of tool '{self.name}': {e}"}
        except Exception as e:
            return {"tool_output": None, "error": f"Error during async execution of tool '{self.name}': {e}"}

    def to_langchain_tool(self):
        """Converts this tool to a LangChain compatible tool.
           This is a basic conversion; more sophisticated mapping might be needed based on LangChain's Tool/StructuredTool specifics.
        """
        from langchain_core.tools import Tool as LangChainTool # Lazy import

        # For simplicity, directly using the synchronous run method.
        # If async is preferred and supported by the LangChain integration, arun could be used.
        def sync_wrapper(tool_input):
            if isinstance(tool_input, dict):
                return self.run(**tool_input)
            elif isinstance(tool_input, str) and self.args_schema.model_fields.keys() == {'input'}:
                # Simple case: if args_schema is just {'input': ...}, pass string directly
                return self.run(input=tool_input)
            else:
                # Fallback or raise error: LangChain might pass a string, Pydantic expects kwargs.
                # This part needs careful handling based on how LangChain invokes tools.
                # For now, assume it needs a single string input and the tool's schema expects 'input'.
                if len(self.args_schema.model_fields) == 1 and next(iter(self.args_schema.model_fields.keys())) == 'input':
                    return self.run(input=str(tool_input))
                raise ValueError(f"Tool '{self.name}' expects a dictionary input matching its schema, or a single string for an 'input' field. Received: {type(tool_input)}")

        async def async_wrapper(tool_input):
            if isinstance(tool_input, dict):
                return await self.arun(**tool_input)
            elif isinstance(tool_input, str) and self.args_schema.model_fields.keys() == {'input'}:
                return await self.arun(input=tool_input)
            else:
                if len(self.args_schema.model_fields) == 1 and next(iter(self.args_schema.model_fields.keys())) == 'input':
                    return await self.arun(input=str(tool_input))
                raise ValueError(f"Tool '{self.name}' expects a dictionary input matching its schema, or a single string for an 'input' field. Received: {type(tool_input)}")

        return LangChainTool(
            name=self.name,
            func=sync_wrapper, # LangChain's 'func' expects a sync callable
            coroutine=async_wrapper, # LangChain's 'coroutine' expects an async callable
            description=self.description,
            args_schema=self.args_schema
        )

    # Helper to get the JSON schema for function calling
    def get_function_calling_schema(self) -> Dict[str, Any]:
        """Returns the JSON schema for the tool's input arguments, suitable for LLM function calling."""
        if not self.args_schema or self.args_schema == BaseToolInput:
            # If no specific args_schema is defined, or it's the default empty one,
            # then the tool takes no arguments according to the schema.
            # OpenAI function calling expects an empty object for parameters in this case.
            return {
                "name": self.name,
                "description": self.description,
                "parameters": {"type": "object", "properties": {}, "required": []}
            }
        
        # Pydantic's model_json_schema() produces a schema that's mostly compatible.
        # We might need to adjust it slightly if OpenAI has very specific requirements
        # not covered by Pydantic's default output (e.g., top-level 'type' must be 'object').
        schema = self.args_schema.model_json_schema()
        
        # Ensure the top-level schema type is 'object' as expected by some function calling APIs.
        if "type" not in schema:
            schema["type"] = "object" # Should typically be present from Pydantic
        
        return {
            "name": self.name,
            "description": self.description,
            "parameters": schema
        }
