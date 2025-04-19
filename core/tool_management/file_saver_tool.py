"""
File saver tool for Sarvagya.
Allows agents to save and read files securely.
"""
from typing import Any, Dict, Optional
import base64
import os
from .base_tool import BaseTool
from ..tool_management.tool_manager import register_tool

@register_tool
class FileSaverTool(BaseTool):
    name = "file_saver"
    description = "Save and read files securely"
    required_permissions = {"file_access": True}
    requires_sandbox = True
    restrict_network = True  # No network access needed for file operations
    
    parameters = {
        "operation": {
            "type": "string",
            "description": "File operation to perform",
            "enum": ["read", "write", "append", "delete", "list"],
        },
        "path": {
            "type": "string",
            "description": "Path to the file or directory"
        },
        "content": {
            "type": "string",
            "description": "Content to write (for write/append operations)"
        },
        "encoding": {
            "type": "string",
            "description": "File encoding",
            "default": "utf-8"
        },
        "binary": {
            "type": "boolean",
            "description": "Whether to treat the file as binary",
            "default": False
        }
    }

    async def execute_async(self, operation: str, path: str, 
                          content: Optional[str] = None,
                          encoding: str = "utf-8", binary: bool = False):
        """Perform file operations securely."""
        # This is a stub - in a real implementation, we'd use the sandbox
        if operation == "read":
            return {
                "status": "success",
                "operation": operation,
                "path": path,
                "content": f"<Simulated content of {path}>",
                "size": 1024
            }
        elif operation in ["write", "append"]:
            return {
                "status": "success",
                "operation": operation,
                "path": path,
                "size": len(content) if content else 0
            }
        elif operation == "delete":
            return {
                "status": "success",
                "operation": operation,
                "path": path
            }
        elif operation == "list":
            return {
                "status": "success",
                "operation": operation,
                "path": path,
                "entries": [
                    {"name": "file1.txt", "type": "file", "size": 1024},
                    {"name": "file2.txt", "type": "file", "size": 2048},
                    {"name": "subdir", "type": "directory"}
                ]
            }
        else:
            return {
                "status": "error",
                "operation": operation,
                "error": "Invalid operation"
            }
    
    def customize_sandbox(self, container_config: Dict[str, Any], **kwargs) -> None:
        """Customize the Docker sandbox for file operations."""
        operation = kwargs.get("operation", "read")
        path = kwargs.get("path", "/tmp/file.txt")
        content = kwargs.get("content", "")
        encoding = kwargs.get("encoding", "utf-8")
        binary = kwargs.get("binary", False)
        
        # Sanitize the path to prevent directory traversal
        safe_path = os.path.normpath(path).lstrip('/')
        safe_path = os.path.join('/sandbox', safe_path)
        
        # Create a Python script to handle file operations
        script = f"""
import os
import json
import base64

def main():
    operation = "{operation}"
    path = "{safe_path}"
    content = "{base64.b64encode(content.encode()).decode() if content else ''}"
    encoding = "{encoding}"
    binary = {str(binary).lower()}
    
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    result = {{"status": "success", "operation": operation, "path": path}}
    
    try:
        if operation == "read":
            mode = "rb" if binary else "r"
            with open(path, mode) as f:
                file_content = f.read()
                if not binary:
                    result["content"] = file_content
                else:
                    result["content"] = base64.b64encode(file_content).decode()
                result["size"] = len(file_content)
                
        elif operation == "write":
            mode = "wb" if binary else "w"
            with open(path, mode) as f:
                if content:
                    content_data = base64.b64decode(content) if binary else base64.b64decode(content).decode(encoding)
                    f.write(content_data)
                    result["size"] = len(content_data)
                
        elif operation == "append":
            mode = "ab" if binary else "a"
            with open(path, mode) as f:
                if content:
                    content_data = base64.b64decode(content) if binary else base64.b64decode(content).decode(encoding)
                    f.write(content_data)
                    result["size"] = len(content_data)
                
        elif operation == "delete":
            if os.path.exists(path):
                os.remove(path)
                
        elif operation == "list":
            if os.path.isdir(path):
                entries = []
                for entry in os.listdir(path):
                    entry_path = os.path.join(path, entry)
                    entry_info = {{"name": entry}}
                    if os.path.isdir(entry_path):
                        entry_info["type"] = "directory"
                    else:
                        entry_info["type"] = "file"
                        entry_info["size"] = os.path.getsize(entry_path)
                    entries.append(entry_info)
                result["entries"] = entries
            else:
                result = {{"status": "error", "operation": operation, "error": "Not a directory"}}
    except Exception as e:
        result = {{"status": "error", "operation": operation, "error": str(e)}}
    
    print(json.dumps(result))

if __name__ == "__main__":
    main()
"""
        
        # Update container configuration
        container_config.update({
            "image": "python:3.9-slim",
            "command": ["python", "-c", script],
            "volumes": {
                "/tmp/sandbox": {"bind": "/sandbox", "mode": "rw"}
            },
            "working_dir": "/sandbox",
        })
