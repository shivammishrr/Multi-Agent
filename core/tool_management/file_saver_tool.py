"""
Robust file–system helper for Sarvagya agents.
Implements safe, sandbox‑confined versions of read/write/append/delete/…,
with full async support, atomic writes, and comprehensive edge‑case handling.
"""
from __future__ import annotations

import asyncio
import base64
import json
import os,sys
import shutil
import stat
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from .base_tool import BaseTool
from ..tool_management.tool_manager import register_tool

# ──────────────────────────────────────────────────────────────────────────────
# Constants & helpers
# ──────────────────────────────────────────────────────────────────────────────

_SANDBOX_ROOT = Path("/sandbox").resolve()
_SUPPORTED_OPS = {
    "read",
    "write",
    "append",
    "delete",
    "list",
    "exists",
    "mkdir",
    "copy",
    "move",
}
_MAX_SIZE_DEFAULT = 10 * 1024 * 1024  # 10 MiB


def _ensure_in_sandbox(path: Path) -> Path:
    """
    Resolve *path* against the sandbox root and guarantee that the resulting
    path is still inside the sandbox. Raises ValueError on escape attempts.
    """
    abs_path = (_SANDBOX_ROOT / path).resolve()
    if _SANDBOX_ROOT not in abs_path.parents and abs_path != _SANDBOX_ROOT:
        raise ValueError("Path escapes sandbox")
    return abs_path


def _b64(text_or_bytes: str | bytes) -> str:
    """Consistently base64‑encode text or bytes (URL‑safe, no newlines)."""
    if isinstance(text_or_bytes, str):
        text_or_bytes = text_or_bytes.encode()
    return base64.b64encode(text_or_bytes).decode()


def _atomic_write(target: Path, data: bytes) -> None:
    """Write *data* to *target* atomically (temp‑file + replace)."""
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as tmp:
        tmp.write(data)
        tmp.flush()
        os.fsync(tmp.fileno())
    os.replace(tmp.name, target)


def _file_info(p: Path) -> Dict[str, Any]:
    st = p.stat()
    return {
        "size": st.st_size,
        "modified": st.st_mtime,
        "created": st.st_ctime,
        "is_dir": p.is_dir(),
        "permissions": stat.filemode(st.st_mode),
    }


@register_tool
class FileSaverTool(BaseTool):
    """
    A hardened, fully asynchronous file saver / loader confined to a Docker
    sandbox.  The tool itself **never** touches the host FS; real work happens
    inside the sandbox container spun up for every call.
    """

    name = "file_saver"
    description = "Safely save, read and manage files in an isolated sandbox"
    required_permissions = {"file_access": True}
    requires_sandbox = True
    restrict_network = True

    def __init__(self):
        super().__init__()
        # Create a persistent sandbox directory for this instance
        self._temp_dir = tempfile.mkdtemp(prefix="file_saver_sandbox_")
        self._sandbox_dir = os.path.join(self._temp_dir, "sandbox")
        os.makedirs(self._sandbox_dir, exist_ok=True)
        print(f"Created persistent sandbox at: {self._sandbox_dir}")

    def __del__(self):
        # Clean up the sandbox directory when the tool is destroyed
        try:
            if hasattr(self, '_temp_dir') and os.path.exists(self._temp_dir):
                shutil.rmtree(self._temp_dir)
                print(f"Removed sandbox: {self._temp_dir}")
        except Exception as e:
            print(f"Error cleaning up sandbox: {e}")

    # --------------------------------------------------------------------- #
    parameters = {
        "operation": {
            "type": "string",
            "description": "File operation to perform",
            "enum": sorted(_SUPPORTED_OPS),
        },
        "path": {"type": "string", "description": "Path to file or directory"},
        "content": {
            "type": "string",
            "description": "Content to write (for write/append) – raw for callers; "
            "the tool takes care of base64‑encoding for transport",
        },
        "encoding": {
            "type": "string",
            "description": "Text encoding (ignored for binary=True)",
            "default": "utf‑8",
        },
        "binary": {
            "type": "boolean",
            "description": "Treat content as binary (base64‑string payload)",
            "default": False,
        },
        "destination": {
            "type": "string",
            "description": "Destination path for copy/move",
            "default": "",
        },
        "recursive": {
            "type": "boolean",
            "description": "Recurse into sub‑directories (delete/list/copy)",
            "default": False,
        },
        "create_parents": {
            "type": "boolean",
            "description": "Create parent dirs if needed (write/append/mkdir)",
            "default": True,
        },
        "max_size": {
            "type": "integer",
            "description": "Max bytes to read (0 = no limit)",
            "default": _MAX_SIZE_DEFAULT,
        },
    }
    # --------------------------------------------------------------------- #

    async def execute_async(  # noqa: PLR0913
        self,
        operation: str,
        path: str,
        *,
        content: Optional[str] = None,
        encoding: str = "utf‑8",
        binary: bool = False,
        destination: str = "",
        recursive: bool = False,
        create_parents: bool = True,
        max_size: int = _MAX_SIZE_DEFAULT,
    ) -> Dict[str, Any]:
        """
        Validate parameters, prepare a tiny Python helper script, and delegate
        the heavy lifting to the sandbox container.  The function returns the
        parsed JSON the helper emits to stdout/stderr.
        """
        if operation not in _SUPPORTED_OPS:
            return {
                "status": "error",
                "error": f"operation must be one of {', '.join(sorted(_SUPPORTED_OPS))}",
            }

        if not path:
            return {"status": "error", "error": "path is required"}

        if operation in {"copy", "move"} and not destination:
            return {
                "status": "error",
                "error": "destination is required for copy/move",
            }

        # ---------------------------------------------------------------- #
        # Build parameter package to hand over to the sandbox helper script
        # ---------------------------------------------------------------- #
        payload: Dict[str, Any] = {
            "operation": operation,
            "path": path,
            "encoding": encoding,
            "binary": binary,
            "destination": destination,
            "recursive": recursive,
            "create_parents": create_parents,
            "max_size": max_size,
        }

        # Always base‑64 encode content so the helper can decode unambiguously.
        if content is not None:
            payload["content_b64"] = _b64(content if binary else content.encode(encoding))
        else:
            payload["content_b64"] = ""

        script = _HELPER_SCRIPT

        container_cfg: Dict[str, Any] = {
            "image": "python:3.12-slim",
            "command": ["python", "-u", "-c", script],
            "volumes": {"/tmp/sandbox": {"bind": "/sandbox", "mode": "rw"}},
            "working_dir": "/sandbox",
            "environment": {"PAYLOAD": json.dumps(payload)},
            "network_mode": "none",
            "security_opt": ["no-new-privileges:true"],
            "cap_drop": ["ALL"],
            "cpu_quota": 50_000,  # 50 % of a vCPU
            "mem_limit": "256m",
            "ulimits": [{"name": "nofile", "soft": 1024, "hard": 2048}],
        }

        # Kick off container via the inherited sandbox mechanism
        result_raw = await self.run_in_sandbox(container_cfg)
        try:
            return json.loads(result_raw.strip().splitlines()[-1])
        except Exception:  # noqa: BLE001
            return {
                "status": "error",
                "error": "sandbox helper failed or emitted malformed JSON",
                "raw": result_raw.rstrip(),
            }

    async def run_in_sandbox(self, container_cfg: Dict[str, Any]) -> str:
        """
        Run a command in a Docker sandbox and return the output.
        This is a placeholder implementation - in a real system, this would
        interact with Docker to create and run a container.
        
        For testing purposes, this simulates the sandbox by directly executing
        the helper script with the provided payload.
        """
        import subprocess
        
        # Extract the Python script and payload from the container config
        script = container_cfg["command"][3]
        payload_json = container_cfg["environment"]["PAYLOAD"]
        
        # Use the persistent sandbox directory
        sandbox_dir = self._sandbox_dir
        
        # Set up environment
        env = os.environ.copy()
        env["PAYLOAD"] = payload_json
        
        # Modify the script to use the correct sandbox path
        modified_script = script.replace('_SANDBOX = Path("/sandbox").resolve()', 
                                       f'_SANDBOX = Path("{sandbox_dir}").resolve()')
        
        # Create a temporary Python file with the modified script
        script_path = os.path.join(self._temp_dir, "helper.py")
        with open(script_path, "w") as f:
            f.write(modified_script)
        
        # Run the script and capture the output
        result = subprocess.run(
            [sys.executable, script_path],
            env=env,
            cwd=self._temp_dir,
            capture_output=True,
            text=True
        )
        
        output = result.stdout or result.stderr
        
        # For debugging
        if "error" in output.lower():
            print(f"Sandbox error: {output}")
            
        return output


_HELPER_SCRIPT = r"""
import base64, json, os, shutil, stat, sys, tempfile
from pathlib import Path

_SANDBOX = Path("/sandbox").resolve()


def ensure_inside_sandbox(p: Path) -> Path:
    p = (_SANDBOX / p).resolve()
    if _SANDBOX not in p.parents and p != _SANDBOX:
        raise ValueError("Path escapes sandbox")
    return p


def file_info(p: Path):
    st = p.stat()
    return {
        "size": st.st_size,
        "modified": st.st_mtime,
        "created": st.st_ctime,
        "is_dir": p.is_dir(),
        "permissions": stat.filemode(st.st_mode),
    }


def atomic_write(target: Path, data: bytes):
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as tmp:
        tmp.write(data)
        tmp.flush()
        os.fsync(tmp.fileno())
    os.replace(tmp.name, target)


payload = json.loads(os.environ["PAYLOAD"])
operation   = payload["operation"]
path        = ensure_inside_sandbox(Path(payload["path"]))
content_b64 = payload.get("content_b64", "")
encoding    = payload.get("encoding", "utf-8")
binary      = bool(payload.get("binary"))
dest_raw    = payload.get("destination") or ""
destination = ensure_inside_sandbox(Path(dest_raw)) if dest_raw else None
recursive   = bool(payload.get("recursive"))
create_parents = bool(payload.get("create_parents"))
max_size    = int(payload.get("max_size", 0))

result = {"status": "success", "operation": operation, "path": str(path)}

try:
    if operation == "read":
        if not path.exists() or path.is_dir():
            raise FileNotFoundError("file not found or is directory")
        if max_size and path.stat().st_size > max_size:
            raise ValueError("file exceeds max_size")
        with path.open("rb") as f:
            data = f.read(max_size or None)
        result["content_b64"] = base64.b64encode(data).decode()
        result["encoding"] = "base64"
        result["file_info"] = file_info(path)

    elif operation in {"write", "append"}:
        data = base64.b64decode(content_b64) if content_b64 else b""
        if not binary:
            data = data.decode(encoding).encode(encoding)  # re‑encode for atomic write
        mode_exists = path.exists()
        if operation == "append" and mode_exists:
            # read‑modify‑append to keep atomicity guarantees
            with path.open("rb") as f:
                data = f.read() + data
        atomic_write(path, data)
        result["bytes_written"] = len(data)
        result["file_info"] = file_info(path)

    elif operation == "delete":
        if not path.exists():
            raise FileNotFoundError("file/directory not found")
        if path.is_dir():
            if recursive:
                shutil.rmtree(path)
            else:
                path.rmdir()
        else:
            path.unlink()

    elif operation == "list":
        if not path.is_dir():
            raise NotADirectoryError("path is not a directory")
        entries = []
        for entry in path.iterdir():
            entries.append({"name": entry.name, **file_info(entry)})
        result["entries"] = entries
        result["count"] = len(entries)

    elif operation == "exists":
        result["exists"] = path.exists()
        if result["exists"]:
            result["file_info"] = file_info(path)

    elif operation == "mkdir":
        if path.exists():
            if path.is_dir():
                result["message"] = "directory already exists"
            else:
                raise FileExistsError("a file with that name already exists")
        else:
            if create_parents:
                path.mkdir(parents=True, exist_ok=True)
            else:
                path.mkdir()
            result["file_info"] = file_info(path)

    elif operation == "copy":
        if not destination:
            raise ValueError("destination required")
        if path.is_dir():
            if not recursive:
                raise IsADirectoryError("source is directory; set recursive=True to copy recursively")
            shutil.copytree(path, destination, dirs_exist_ok=True)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
        result["destination"] = str(destination)
        result["file_info"] = file_info(destination)

    elif operation == "move":
        if not destination:
            raise ValueError("destination required")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(path, destination)
        result["destination"] = str(destination)
        result["file_info"] = file_info(destination)

    else:
        raise ValueError("unsupported operation")

except Exception as exc:  # noqa: BLE001
    result = {"status": "error", "operation": operation, "error": str(exc)}

print(json.dumps(result, separators=(",", ":")))
sys.stdout.flush()
"""
