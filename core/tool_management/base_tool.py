import abc
from typing import Any, Dict, Optional

class BaseTool(abc.ABC):
    """
    Abstract base class for all tools. Defines the interface for tool execution and permission declaration.
    """
    name: str = "base_tool"
    description: str = "Base tool class"
    required_permissions: Dict[str, Any] = {}
    requires_sandbox: bool = False
    restrict_network: bool = True
    parameters: Dict[str, Dict[str, Any]] = {}

    @abc.abstractmethod
    async def execute_async(self, **kwargs) -> Any:
        """Run the tool with given arguments asynchronously."""
        pass
    
    def execute(self, **kwargs) -> Any:
        """Synchronous wrapper for execute_async."""
        import asyncio
        return asyncio.run(self.execute_async(**kwargs))

    @classmethod
    def get_permissions(cls) -> Dict[str, Any]:
        """Return permissions required by this tool."""
        return cls.required_permissions
    
    def customize_sandbox(self, container_config: Dict[str, Any], **kwargs) -> None:
        """Customize the Docker sandbox configuration for this tool.
        
        Override this method to add tool-specific customizations to the Docker container.
        """
        pass
