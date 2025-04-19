"""
Data retrieval tool for Sarvagya.
Allows agents to fetch data from various sources.
"""
from typing import Any, Dict, Optional
from .base_tool import BaseTool
from ..tool_management.tool_manager import register_tool

@register_tool
class DataRetrievalTool(BaseTool):
    name = "data_retrieval"
    description = "Retrieve data from various sources (APIs, web, databases)"
    required_permissions = {"network": True, "data_access": True}
    requires_sandbox = True
    restrict_network = False  # Needs network access
    
    parameters = {
        "source": {
            "type": "string",
            "description": "Data source (api, web, database)",
            "enum": ["api", "web", "database"]
        },
        "url": {
            "type": "string",
            "description": "URL for API or web sources"
        },
        "query": {
            "type": "string",
            "description": "Query string or parameters"
        },
        "headers": {
            "type": "object",
            "description": "HTTP headers for API requests"
        },
        "method": {
            "type": "string",
            "description": "HTTP method for API requests",
            "enum": ["GET", "POST", "PUT", "DELETE"],
            "default": "GET"
        }
    }

    async def execute_async(self, source: str, url: Optional[str] = None, 
                          query: Optional[str] = None, headers: Optional[Dict] = None,
                          method: str = "GET"):
        """Retrieve data from the specified source."""
        # This is a stub - in a real implementation, we'd make actual requests
        return {
            "status": "success",
            "source": source,
            "data": f"<Simulated data from {source}: {url or query}>",
            "metadata": {
                "timestamp": "2025-04-19T12:30:00Z",
                "size": 1024
            }
        }
    
    def customize_sandbox(self, container_config: Dict[str, Any], **kwargs) -> None:
        """Customize the Docker sandbox for data retrieval."""
        source = kwargs.get("source", "api")
        url = kwargs.get("url", "")
        query = kwargs.get("query", "")
        method = kwargs.get("method", "GET")
        
        # Use a container with appropriate tools installed
        container_config.update({
            "image": "curlimages/curl:7.78.0",
            "command": [
                "sh", "-c", 
                f"""echo '{{"status": "success", "source": "{source}", "data": "<Simulated data from {source}: {url or query}>", "metadata": {{"timestamp": "2025-04-19T12:30:00Z", "size": 1024}}}}'"""
            ],
            "network_mode": "bridge",  # Allow network access
        })
