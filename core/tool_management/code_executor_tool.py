from typing import Any, Dict, List, Optional, Union
import base64
import json
import os
import tempfile
import time
import io
import sys
import subprocess
from contextlib import redirect_stdout, redirect_stderr
from .base_tool import BaseTool
from ..tool_management.tool_manager import register_tool

@register_tool
class CodeExecutorTool(BaseTool):
    name = "code_executor"
    description = "Execute code in a secure, sandboxed environment with support for multiple languages"
    required_permissions = {"code_execution": True}
    requires_sandbox = True
    restrict_network = True  # By default, no network access for code execution
    
    parameters = {
        "code": {
            "type": "string",
            "description": "Code to execute"
        },
        "file_path": {
            "type": "string",
            "description": "Path to a file containing code to execute (alternative to 'code' parameter)",
            "default": ""
        },
        "language": {
            "type": "string",
            "description": "Programming language",
            "enum": ["python", "javascript", "typescript", "bash", "r", "ruby", "go", "java", "c", "cpp", "rust", "php"]
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
        },
        "dependencies": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of dependencies to install before execution",
            "default": []
        },
        "environment_variables": {
            "type": "object",
            "description": "Environment variables to set for execution",
            "default": {}
        },
        "working_directory": {
            "type": "string",
            "description": "Working directory for execution",
            "default": ""
        },
        "input_data": {
            "type": "string",
            "description": "Input data to provide to the program",
            "default": ""
        },
        "interactive": {
            "type": "boolean",
            "description": "Whether to run in interactive mode (for REPL-like execution)",
            "default": False
        },
        "output_format": {
            "type": "string",
            "description": "Format for the output",
            "enum": ["text", "json", "html", "markdown"],
            "default": "text"
        }
    }

    # Language-specific configurations
    LANGUAGE_CONFIGS = {
        "python": {
            "file_extension": ".py",
            "image": "python:3.11-slim",
            "install_cmd": ["pip", "install"],
            "execute_file_cmd": lambda file_path: ["python", file_path],
            "execute_code_cmd": lambda: ["python", "-c"],
        },
        "javascript": {
            "file_extension": ".js",
            "image": "node:18-alpine",
            "install_cmd": ["npm", "install"],
            "execute_file_cmd": lambda file_path: ["node", file_path],
            "execute_code_cmd": lambda: ["node", "-e"],
        },
        "typescript": {
            "file_extension": ".ts",
            "image": "node:18-alpine",
            "install_cmd": ["npm", "install", "-g", "typescript", "ts-node", "&&", "npm", "install"],
            "execute_file_cmd": lambda file_path: ["ts-node", file_path],
            "execute_code_cmd": lambda: ["ts-node", "-e"],
        },
        "bash": {
            "file_extension": ".sh",
            "image": "bash:5.1",
            "install_cmd": ["apt-get", "update", "&&", "apt-get", "install", "-y"],
            "execute_file_cmd": lambda file_path: [file_path],
            "execute_code_cmd": lambda: ["bash", "-c"],
        },
        "r": {
            "file_extension": ".r",
            "image": "r-base:4.2.0",
            "install_cmd": ["R", "-e", "install.packages(c('{}'), repos='https://cran.rstudio.com/')"],
            "execute_file_cmd": lambda file_path: ["Rscript", file_path],
            "execute_code_cmd": lambda: ["Rscript", "-e"],
        },
        "ruby": {
            "file_extension": ".rb",
            "image": "ruby:3.1-slim",
            "install_cmd": ["gem", "install"],
            "execute_file_cmd": lambda file_path: ["ruby", file_path],
            "execute_code_cmd": lambda: ["ruby", "-e"],
        },
        "go": {
            "file_extension": ".go",
            "image": "golang:1.19-alpine",
            "install_cmd": ["go", "get"],
            "execute_file_cmd": lambda file_path: ["go", "run", file_path],
            "execute_code_cmd": lambda: ["go", "run", "-e"],
        },
        "java": {
            "file_extension": ".java",
            "image": "openjdk:17-slim",
            "install_cmd": ["mvn", "install"],
            "execute_file_cmd": lambda file_path: ["java", file_path],
            "execute_code_cmd": lambda: ["java", "-e"],
        },
        "c": {
            "file_extension": ".c",
            "image": "gcc:11.2",
            "install_cmd": ["apt-get", "update", "&&", "apt-get", "install", "-y"],
            "execute_file_cmd": lambda file_path: ["bash", "-c", f"gcc {file_path} -o program && ./program"],
            "execute_code_cmd": lambda: ["bash", "-c", "gcc -x c - -o program && ./program"],
        },
        "cpp": {
            "file_extension": ".cpp",
            "image": "gcc:11.2",
            "install_cmd": ["apt-get", "update", "&&", "apt-get", "install", "-y"],
            "execute_file_cmd": lambda file_path: ["bash", "-c", f"g++ {file_path} -o program && ./program"],
            "execute_code_cmd": lambda: ["bash", "-c", "g++ -x c++ - -o program && ./program"],
        },
        "rust": {
            "file_extension": ".rs",
            "image": "rust:1.60-slim",
            "install_cmd": ["cargo", "install"],
            "execute_file_cmd": lambda file_path: ["bash", "-c", f"rustc {file_path} -o program && ./program"],
            "execute_code_cmd": lambda: ["bash", "-c", "rustc - -o program && ./program"],
        },
        "php": {
            "file_extension": ".php",
            "image": "php:8.1-cli",
            "install_cmd": ["composer", "require"],
            "execute_file_cmd": lambda file_path: ["php", file_path],
            "execute_code_cmd": lambda: ["php", "-r"],
        }
    }

    async def execute_async(self, 
                          code: str = "", 
                          file_path: str = "", 
                          language: str = "python", 
                          allow_network: bool = False, 
                          timeout: int = 30,
                          memory_limit: str = "512m",
                          dependencies: List[str] = None,
                          environment_variables: Dict[str, str] = None,
                          working_directory: str = "",
                          input_data: str = "",
                          interactive: bool = False,
                          output_format: str = "text"):
        """Execute code in a secure sandbox with enhanced features.
        
        Args:
            code: String containing code to execute
            file_path: Path to a file containing code to execute (alternative to code)
            language: Programming language to use
            allow_network: Whether to allow network access
            timeout: Execution timeout in seconds
            memory_limit: Memory limit for execution
            dependencies: List of dependencies to install before execution
            environment_variables: Environment variables to set for execution
            working_directory: Working directory for execution
            input_data: Input data to provide to the program
            interactive: Whether to run in interactive mode
            output_format: Format for the output
            
        Returns:
            Dictionary containing execution results
        """
        # Initialize default values
        dependencies = dependencies or []
        environment_variables = environment_variables or {}
        
        start_time = time.time()
        result = {
            "status": "executed", 
            "language": language,
            "execution_time": 0,
            "output": "",
            "errors": "",
            "memory_usage": "0m",
            "cpu_usage": "0%"
        }
        
        # Validate language support
        if language not in self.LANGUAGE_CONFIGS:
            return {
                "status": "error",
                "language": language,
                "output": f"Unsupported language: {language}. Supported languages: {', '.join(self.LANGUAGE_CONFIGS.keys())}",
                "execution_time": time.time() - start_time
            }
        
        # Get code from file if needed
        if file_path and not code:
            try:
                with open(file_path, 'r') as f:
                    code = f.read()
                result["source"] = f"file:{file_path}"
            except Exception as e:
                return {
                    "status": "error",
                    "language": language,
                    "output": f"Error reading file: {str(e)}",
                    "execution_time": time.time() - start_time
                }
        elif not code:
            return {
                "status": "error",
                "language": language,
                "output": "No code or file_path provided",
                "execution_time": time.time() - start_time
            }
        else:
            result["source"] = "direct_input"
        
        try:
            # Execute code based on language
            if language == "python":
                result = await self._execute_python(
                    code, file_path, timeout, dependencies, 
                    environment_variables, working_directory, 
                    input_data, interactive, result
                )
            else:
                result = await self._execute_external_language(
                    language, code, file_path, timeout, dependencies,
                    environment_variables, working_directory,
                    input_data, interactive, result
                )
            
            # Format output if needed
            if output_format != "text" and "output" in result:
                result["output"] = self._format_output(result["output"], output_format)
                
        except subprocess.TimeoutExpired:
            result["status"] = "timeout"
            result["output"] = f"Execution timed out after {timeout} seconds"
        except Exception as e:
            result["status"] = "error"
            result["output"] = f"Execution error: {str(e)}"
            # Include traceback for better debugging
            import traceback
            result["errors"] = traceback.format_exc()
        
        # Calculate execution time
        result["execution_time"] = time.time() - start_time
        
        return result
    
    async def _execute_python(self, code, file_path, timeout, dependencies, 
                            environment_variables, working_directory, 
                            input_data, interactive, result):
        """Execute Python code with enhanced features."""
        # Create a temporary directory for execution if needed
        temp_dir = None
        if dependencies or working_directory:
            temp_dir = tempfile.mkdtemp(prefix="python_exec_")
            os.chdir(temp_dir)
        
        try:
            # Install dependencies if needed
            if dependencies:
                for dep in dependencies:
                    try:
                        subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
                    except subprocess.CalledProcessError as e:
                        result["status"] = "error"
                        result["output"] = f"Failed to install dependency: {dep}"
                        result["errors"] = str(e)
                        return result
            
            # Set environment variables
            original_env = os.environ.copy()
            if environment_variables:
                os.environ.update(environment_variables)
            
            # Prepare for execution
            output_buffer = io.StringIO()
            error_buffer = io.StringIO()
            
            # Handle interactive mode
            if interactive:
                import code as pycode
                with redirect_stdout(output_buffer), redirect_stderr(error_buffer):
                    # Create an interactive console
                    console = pycode.InteractiveInterpreter()
                    console.runcode(compile(code, "<string>", "exec"))
            else:
                # Handle input data if provided
                original_stdin = sys.stdin
                if input_data:
                    sys.stdin = io.StringIO(input_data)
                
                with redirect_stdout(output_buffer), redirect_stderr(error_buffer):
                    # Execute the code
                    if file_path and os.path.exists(file_path):
                        # If it's a file, use exec with globals/locals for proper module handling
                        globals_dict = {'__file__': file_path}
                        exec(code, globals_dict)
                    else:
                        # Direct code execution
                        exec(code)
                
                # Restore stdin if needed
                if input_data:
                    sys.stdin = original_stdin
            
            # Collect output
            output = output_buffer.getvalue()
            errors = error_buffer.getvalue()
            
            if errors:
                result["errors"] = errors
            
            result["output"] = output
            
            # Restore environment
            os.environ.clear()
            os.environ.update(original_env)
            
        finally:
            # Clean up temporary directory if created
            if temp_dir and os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir)
        
        return result
    
    async def _execute_external_language(self, language, code, file_path, timeout, 
                                       dependencies, environment_variables, 
                                       working_directory, input_data, interactive, result):
        """Execute code in languages other than Python."""
        lang_config = self.LANGUAGE_CONFIGS[language]
        temp_file = None
        temp_dir = None
        
        try:
            # Create a temporary directory for execution if needed
            if dependencies or working_directory:
                temp_dir = tempfile.mkdtemp(prefix=f"{language}_exec_")
                os.chdir(temp_dir)
            
            # Install dependencies if needed
            if dependencies:
                install_cmd = lang_config["install_cmd"]
                if isinstance(install_cmd, list):
                    # For most languages, we can just append dependencies
                    cmd = install_cmd + dependencies
                    try:
                        subprocess.check_call(cmd)
                    except subprocess.CalledProcessError as e:
                        result["status"] = "error"
                        result["output"] = f"Failed to install dependencies: {', '.join(dependencies)}"
                        result["errors"] = str(e)
                        return result
            
            # Prepare for execution
            env = os.environ.copy()
            if environment_variables:
                env.update(environment_variables)
            
            # Execute based on whether we have a file or direct code
            if file_path and os.path.exists(file_path):
                cmd = lang_config["execute_file_cmd"](file_path)
            else:
                # Create a temporary file with the code
                temp_file = tempfile.NamedTemporaryFile(
                    suffix=lang_config["file_extension"], 
                    delete=False
                )
                temp_path = temp_file.name
                temp_file.write(code.encode())
                temp_file.close()
                
                # Make executable if needed (for bash scripts)
                if language == "bash":
                    os.chmod(temp_path, 0o755)
                
                cmd = lang_config["execute_file_cmd"](temp_path)
            
            # Execute the command
            process = subprocess.run(
                cmd,
                input=input_data.encode() if input_data else None,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env
            )
            
            # Collect output
            result["output"] = process.stdout
            if process.stderr:
                result["errors"] = process.stderr
            
            # Check return code
            if process.returncode != 0:
                result["status"] = "error"
                if not result["errors"]:
                    result["errors"] = f"Process exited with code {process.returncode}"
        
        finally:
            # Clean up temporary files
            if temp_file and os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
            
            # Clean up temporary directory if created
            if temp_dir and os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir)
        
        return result
    
    def _format_output(self, output, format_type):
        """Format the output according to the specified format."""
        if format_type == "json":
            try:
                # Try to parse as JSON first
                json.loads(output)
                return output  # Already valid JSON
            except json.JSONDecodeError:
                # Convert to JSON
                return json.dumps({"output": output})
        
        elif format_type == "html":
            # Wrap in HTML
            return f"<pre>{output}</pre>"
        
        elif format_type == "markdown":
            # Wrap in markdown code block
            return f"```\n{output}\n```"
        
        # Default is text, return as is
        return output
    
    def customize_sandbox(self, container_config: Dict[str, Any], **kwargs) -> None:
        """Customize the Docker sandbox for code execution with enhanced security and features."""
        language = kwargs.get("language", "python")
        code = kwargs.get("code", "")
        file_path = kwargs.get("file_path", "")
        allow_network = kwargs.get("allow_network", False)
        timeout = kwargs.get("timeout", 30)
        memory_limit = kwargs.get("memory_limit", "512m")
        dependencies = kwargs.get("dependencies", [])
        environment_variables = kwargs.get("environment_variables", {})
        working_directory = kwargs.get("working_directory", "")
        input_data = kwargs.get("input_data", "")
        
        # Validate language support
        if language not in self.LANGUAGE_CONFIGS:
            language = "python"  # Default to Python if unsupported
        
        lang_config = self.LANGUAGE_CONFIGS[language]
        
        # If file_path is provided, read code from the file
        if file_path and not code:
            try:
                with open(file_path, 'r') as f:
                    code = f.read()
            except Exception as e:
                code = f"echo 'Error reading file: {str(e)}'"
                language = "bash"  # Fallback to bash to display the error
        elif not code:
            code = "print('No code or file_path provided')"
        
        # Encode the code to avoid shell escaping issues
        encoded_code = base64.b64encode(code.encode()).decode()
        
        # Prepare volumes for file mounting
        volumes = {}
        
        # If using a file, mount it into the container
        if file_path:
            abs_path = os.path.abspath(file_path)
            container_path = f"/code/{os.path.basename(file_path)}"
            volumes[abs_path] = {"bind": container_path, "mode": "ro"}
        
        # If working directory is specified, mount it
        if working_directory:
            abs_working_dir = os.path.abspath(working_directory)
            volumes[abs_working_dir] = {"bind": "/workspace", "mode": "rw"}
        
        # Prepare environment variables
        env_vars = {
            "EXECUTION_TIMEOUT": str(timeout),
            "MEMORY_LIMIT": memory_limit,
            "ALLOW_NETWORK": "1" if allow_network else "0"
        }
        
        # Add user-specified environment variables
        if environment_variables:
            env_vars.update(environment_variables)
        
        # Prepare command based on language and execution mode
        if file_path:
            container_path = f"/code/{os.path.basename(file_path)}"
            command = lang_config["execute_file_cmd"](container_path)
        else:
            # For direct code execution
            temp_file = f"/tmp/code{lang_config['file_extension']}"
            setup_cmd = [
                "bash", "-c", 
                f"echo {encoded_code} | base64 -d > {temp_file} && chmod +x {temp_file}"
            ]
            exec_cmd = lang_config["execute_file_cmd"](temp_file)
            
            # Add dependency installation if needed
            if dependencies:
                if isinstance(lang_config["install_cmd"], list):
                    install_cmd = " ".join(lang_config["install_cmd"] + dependencies)
                    command = [
                        "bash", "-c", 
                        f"{install_cmd} && {' '.join(setup_cmd[2:])} && {' '.join(exec_cmd)}"
                    ]
                else:
                    command = setup_cmd + ["&&"] + exec_cmd
            else:
                command = setup_cmd + ["&&"] + exec_cmd
        
        # Update container configuration
        container_config.update({
            "image": lang_config["image"],
            "command": command,
            "network_mode": "bridge" if allow_network else "none",
            "mem_limit": memory_limit,
            "cpu_quota": 100000,  # 100% of CPU
            "stop_timeout": timeout,
            "environment": env_vars,
            "working_dir": "/workspace" if working_directory else "/code",
            "security_opt": ["no-new-privileges:true"],
            "cap_drop": ["ALL"],
            "ulimits": [{"name": "nofile", "soft": 1024, "hard": 2048}]
        })
        
        # Add volumes if needed
        if volumes:
            container_config["volumes"] = volumes
        
        # Handle input data if provided
        if input_data:
            container_config["stdin_open"] = True
            container_config["stdin_once"] = True
            # We would need to pipe the input data to the container in the actual execution
