from __future__ import annotations

import ast
import io
import sys
import traceback
from contextlib import redirect_stdout, redirect_stderr
from typing import Any

from pydantic import BaseModel

from multi_agent.core.tool import ToolResult


class CodeActSandbox(BaseModel):
    allow_imports: bool = False
    allowed_modules: list[str] | None = None
    timeout: int = 30
    _namespace: dict[str, Any] = {}
    _imports_cache: dict[str, Any] = {}

    def _check_code(self, code: str) -> None:
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise ValueError(f"Syntax error: {e}") from e

        if not self.allow_imports:
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    raise ValueError("Import statements are disabled in restricted mode")

    def _exec_safe(self, code: str) -> tuple[str, str]:
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        restricted_builtins = {
            "abs": abs, "all": all, "any": any, "bin": bin, "bool": bool,
            "chr": chr, "complex": complex, "dict": dict, "dir": dir,
            "divmod": divmod, "enumerate": enumerate, "filter": filter,
            "float": float, "format": format, "frozenset": frozenset,
            "getattr": getattr, "hasattr": hasattr, "hash": hash,
            "hex": hex, "id": id, "int": int, "isinstance": isinstance,
            "issubclass": issubclass, "iter": iter, "len": len,
            "list": list, "map": map, "max": max, "min": min,
            "next": next, "object": object, "oct": oct, "ord": ord,
            "pow": pow, "print": print, "range": range,
            "repr": repr, "reversed": reversed, "round": round,
            "set": set, "slice": slice, "sorted": sorted,
            "str": str, "sum": sum, "tuple": tuple, "type": type,
            "zip": zip, "True": True, "False": False, "None": None,
            "Exception": Exception, "ValueError": ValueError,
            "TypeError": TypeError, "KeyError": KeyError,
            "IndexError": IndexError, "StopIteration": StopIteration,
            "__import__": self._safe_import if self.allow_imports else None,
        }

        safe_globals = {
            "__builtins__": restricted_builtins,
        }

        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            try:
                exec(code, safe_globals, self._namespace)
            except Exception:
                stderr_capture.write(traceback.format_exc())

        return stdout_capture.getvalue(), stderr_capture.getvalue()

    def _safe_import(self, name: str, *args: Any, **kwargs: Any) -> Any:
        if self.allowed_modules is not None and name not in self.allowed_modules:
            raise ImportError(f"Module '{name}' is not in the allowed list")
        if name in self._imports_cache:
            return self._imports_cache[name]
        module = __import__(name, *args, **kwargs)
        self._imports_cache[name] = module
        return module

    async def run(self, code: str) -> ToolResult:
        try:
            self._check_code(code)
        except ValueError as e:
            return ToolResult(success=False, output=str(e))

        stdout, stderr = self._exec_safe(code)
        output = ""
        if stdout:
            output += stdout
        if stderr:
            if output:
                output += "\n"
            output += stderr
        if not output:
            output = "(no output)"

        return ToolResult(
            success=not stderr,
            output=output,
            metadata={"stdout": stdout, "stderr": stderr},
        )

    def reset(self) -> None:
        self._namespace.clear()
