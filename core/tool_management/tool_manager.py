"""
Tool management system for Sarvagya.
Handles tool registration, discovery, and secure execution.
"""
from typing import Any, Dict, List, Optional, Type, Union
import asyncio
import docker
from pydantic import BaseModel

from .base_tool import BaseTool


class ToolDescription(BaseModel):
    """Description of a tool for discovery."""
    name: str
    description: str
    parameters: Dict[str, Any]


class ToolManager:
    """
    Registry and invoker for all tools. Handles sandboxed execution and permission checks.
    """
    _registry: Dict[str, Type[BaseTool]] = {}
    _docker_client = None

    def __init__(self):
        # Initialize Docker client for sandbox execution
        try:
            self._docker_client = docker.from_env()
        except Exception as e:
            print(f"Warning: Docker client initialization failed: {e}")
            print("Tools requiring sandboxing will not be available.")

    @classmethod
    def register_tool(cls, tool_cls: Type[BaseTool]) -> None:
        """Register a tool class with the manager."""
        cls._registry[tool_cls.name] = tool_cls
        print(f"Registered tool: {tool_cls.name}")

    @classmethod
    def get_tool_class(cls, name: str) -> Optional[Type[BaseTool]]:
        """Get a tool class by name."""
        return cls._registry.get(name)

    def list_tools(self) -> List[ToolDescription]:
        """List all available tools with their descriptions."""
        tools = []
        for name, tool_cls in self._registry.items():
            # Create an instance to get parameter info
            tool = tool_cls()
            tools.append(
                ToolDescription(
                    name=name,
                    description=getattr(tool_cls, "description", "No description available"),
                    parameters=getattr(tool, "parameters", {})
                )
            )
        return tools

    async def execute_tool_async(self, tool_name: str, **kwargs) -> Any:
        """Execute a tool asynchronously."""
        tool_cls = self.get_tool_class(tool_name)
        if not tool_cls:
            raise ValueError(f"Tool '{tool_name}' not registered.")
        
        tool = tool_cls()
        
        # Check if tool requires sandboxing
        if getattr(tool, "requires_sandbox", False):
            return await self._execute_in_sandbox(tool, **kwargs)
        else:
            # Execute directly
            return await tool.execute_async(**kwargs)

    def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """Execute a tool synchronously."""
        # Use asyncio to run the async method in a synchronous context
        return asyncio.run(self.execute_tool_async(tool_name, **kwargs))

    async def _execute_in_sandbox(self, tool: BaseTool, **kwargs) -> Any:
        """Execute a tool in a Docker sandbox."""
        if not self._docker_client:
            raise RuntimeError("Docker client not available for sandboxed execution")
        
        # Prepare the Docker container configuration
        container_config = {
            "image": "python:3.9-slim",  # Base image
            "command": ["python", "-c", "import json; print(json.dumps({'result': 'Sandbox execution stub'}))"],
            "detach": True,
            "remove": True,
            # Security constraints
            "mem_limit": "512m",
            "cpu_quota": 50000,  # 50% of CPU
            "network_mode": "none" if tool.restrict_network else "bridge",
            "cap_drop": ["ALL"],
            "security_opt": ["no-new-privileges:true"],
        }
        
        # Add tool-specific customizations
        tool.customize_sandbox(container_config, **kwargs)
        
        try:
            # Create and start the container
            container = self._docker_client.containers.run(**container_config)
            
            # Wait for completion and get logs
            result = container.logs().decode('utf-8').strip()
            
            # Parse the result (assuming JSON output)
            import json
            return json.loads(result)
        except Exception as e:
            raise RuntimeError(f"Sandbox execution failed: {str(e)}")


# Auto-registration decorator
def register_tool(cls):
    """Decorator to auto-register tools with the ToolManager."""
    ToolManager.register_tool(cls)
    return cls
