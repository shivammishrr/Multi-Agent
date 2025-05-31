import io
import sys
import traceback
from contextlib import redirect_stdout, redirect_stderr
from typing import Type, Optional, Dict, Any
import asyncio

from pydantic import BaseModel, Field

from tools.base_tool import BaseTool, BaseToolInput, BaseToolOutput

class PythonExecuteToolInput(BaseToolInput):
    code: str = Field(..., description="The Python code snippet to execute.")
    # Potentially add a timeout parameter in the future

class PythonExecuteToolOutput(BaseToolOutput):
    stdout: Optional[str] = Field(default=None, description="The standard output from the executed code.")
    stderr: Optional[str] = Field(default=None, description="The standard error from the executed code, if any.")
    result: Optional[Any] = Field(default=None, description="The result of the last expression in the code, if any, or None.")
    # 'output' from BaseToolOutput can be a summary or concatenation if needed
    # 'error' from BaseToolOutput will be used for execution framework errors (not code's stderr)
    message: str = Field(..., description="A message indicating the outcome of the execution.")

class PythonExecuteTool(BaseTool):
    name: str = "python_code_executor"
    description: str = ( "Executes a given Python code snippet. WARNING: This tool uses exec() and is highly insecure. "
                         "It should NOT be used in production environments without extreme caution and robust sandboxing. "
                         "The code is executed in the current Python interpreter's environment.")
    args_schema: Type[BaseModel] = PythonExecuteToolInput
    return_schema: Type[BaseModel] = PythonExecuteToolOutput

    def _run(self, code: str) -> PythonExecuteToolOutput:
        # **SECURITY WARNING**:
        # Executing arbitrary code with exec() is a major security risk.
        # This implementation is for demonstration purposes in a controlled environment ONLY.
        # For any real-world application, a proper sandboxing mechanism (e.g., Docker containers,
        # restricted Python environments like restrictedpython, or a dedicated microservice) is ESSENTIAL.

        local_vars = {}
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        try:
            # Redirect stdout and stderr to capture them
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # Try to exec the code. If it's an expression, eval might be more appropriate for getting a result.
                # However, to support multi-line scripts, exec is generally used.
                # We can try to make the last line an expression and capture its result if possible.
                
                # Split code into lines and try to exec all but the last, then eval the last.
                lines = code.strip().split('\n')
                if not lines or not lines[0]: # Handle empty or only whitespace code
                    return PythonExecuteToolOutput(stdout="", stderr="", result=None, message="No code provided to execute.", output="No code provided.")

                exec_code_lines = lines[:-1]
                eval_line = lines[-1]

                if exec_code_lines:
                    exec_code_str = "\n".join(exec_code_lines)
                    compiled_exec_code = compile(exec_code_str, '<string>', 'exec')
                    exec(compiled_exec_code, globals(), local_vars) # Use globals() and local_vars for scope
                
                # Try to evaluate the last line as an expression
                execution_result = None
                try:
                    compiled_eval_code = compile(eval_line, '<string>', 'eval')
                    execution_result = eval(compiled_eval_code, globals(), local_vars)
                except SyntaxError:
                    # Last line is not an expression, or there were only exec lines.
                    # If eval_line was part of exec_code_lines (i.e. single line of non-expression code), re-exec it.
                    # Or if all code was meant for exec (multi-line statement).
                    if not exec_code_lines: # Single line was not an expression
                         compiled_single_exec = compile(eval_line, '<string>', 'exec')
                         exec(compiled_single_exec, globals(), local_vars)
                    # If there were prior exec lines, the last line (eval_line) might also be a statement.
                    # We need to exec it if it wasn't an expression.
                    elif eval_line: # Avoid re-executing empty string if code ends with newline
                        # This covers the case where the last line is a statement, not an expression.
                        temp_exec_code = compile(eval_line, '<string>', 'exec')
                        exec(temp_exec_code, globals(), local_vars)
                    # If code was purely exec, result remains None unless set by user in local_vars (e.g. local_vars['__result__']) 
                    execution_result = local_vars.get('__result__', None) 

            stdout_val = stdout_capture.getvalue()
            stderr_val = stderr_capture.getvalue()
            
            output_message = "Code executed successfully."
            if stderr_val:
                output_message += " However, there was output to stderr."

            return PythonExecuteToolOutput(
                stdout=stdout_val,
                stderr=stderr_val,
                result=execution_result,
                message=output_message,
                output=f"Stdout: {stdout_val[:200]}...\nStderr: {stderr_val[:200]}...\nResult: {str(execution_result)[:200]}..." # Summary for base output
            )

        except Exception as e:
            tb_str = traceback.format_exc()
            return PythonExecuteToolOutput(
                stdout=stdout_capture.getvalue(),
                stderr=f"{stderr_capture.getvalue()}\n{tb_str}",
                error=f"Execution failed: {type(e).__name__}: {e}", # Error for the tool framework
                message=f"Code execution failed with {type(e).__name__}."
            )
        finally:
            stdout_capture.close()
            stderr_capture.close()

    async def _arun(self, code: str) -> PythonExecuteToolOutput:
        try:
            return await asyncio.to_thread(self._run, code=code)
        except Exception as e:
            return PythonExecuteToolOutput(
                error=f"Async execution wrapper failed: {type(e).__name__}: {e}",
                message=f"Async execution wrapper failed with {type(e).__name__}."
            )
