from typing import Any, Dict
import base64
from .base_tool import BaseTool
from ..tool_management.tool_manager import register_tool

@register_tool
class CodeExecutorTool(BaseTool):
    name = "code_executor"
    description = "Execute code in a secure, sandboxed environment"
    required_permissions = {"code_execution": True}
    requires_sandbox = True
    restrict_network = True  # By default, no network access for code execution
    
    parameters = {
        "code": {
            "type": "string",
            "description": "Code to execute"
        },
        "language": {
            "type": "string",
            "description": "Programming language",
            "enum": ["python", "javascript", "bash", "r"]
        },
        "allow_network": {
            "type": "boolean",
            "description": "Whether to allow network access",
            "default": False
        },
        "timeout": {
            "type": "integer",
            "description": "Execution timeout in seconds",
            "default": 30
        },
        "memory_limit": {
            "type": "string",
            "description": "Memory limit (e.g., '512m')",
            "default": "512m"
        }
    }

    async def execute_async(self, code: str, language: str = "python", 
                          allow_network: bool = False, timeout: int = 30,
                          memory_limit: str = "512m"):
        """Execute code in a secure sandbox."""
        # This would be implemented with Docker-in-Docker in production
        return {
            "status": "executed", 
            "language": language, 
            "output": f"<Simulated output for {language} code>",
            "execution_time": 0.5  # Simulated execution time in seconds
        }
    
    def customize_sandbox(self, container_config: Dict[str, Any], **kwargs) -> None:
        """Customize the Docker sandbox for code execution."""
        language = kwargs.get("language", "python")
        code = kwargs.get("code", "print('Hello, world!')")
        allow_network = kwargs.get("allow_network", False)
        timeout = kwargs.get("timeout", 30)
        memory_limit = kwargs.get("memory_limit", "512m")
        
        # Encode the code to avoid shell escaping issues
        encoded_code = base64.b64encode(code.encode()).decode()
        
        # Select the appropriate image based on language
        images = {
            "python": "python:3.9-slim",
            "javascript": "node:16-alpine",
            "bash": "bash:5.1",
            "r": "r-base:4.1.0"
        }
        
        # Select the appropriate command based on language
        commands = {
            "python": ["python", "-c", f"import base64, json; exec(base64.b64decode('{encoded_code}').decode()); print(json.dumps({{'status': 'executed', 'output': 'Simulated output'}}));"],
            "javascript": ["node", "-e", f"console.log(JSON.stringify({{status: 'executed', output: 'Simulated output'}}));"],
            "bash": ["bash", "-c", f"echo '{{\"status\": \"executed\", \"output\": \"Simulated output\"}}'"],
            "r": ["Rscript", "-e", f"cat(jsonlite::toJSON(list(status='executed', output='Simulated output')))"]
        }
        
        # Update container configuration
        container_config.update({
            "image": images.get(language, "python:3.9-slim"),
            "command": commands.get(language, commands["python"]),
            "network_mode": "bridge" if allow_network else "none",
            "mem_limit": memory_limit,
            "cpu_quota": 100000,  # 100% of CPU
            "stop_timeout": timeout
        })
