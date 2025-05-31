import os
import pathlib
from typing import Type, Optional

import aiofiles
from pydantic import BaseModel, Field

from tools.base_tool import BaseTool, BaseToolInput, BaseToolOutput

class FileSaverToolInput(BaseToolInput):
    file_path: str = Field(..., description="The path to the file where content will be saved. Can be relative or absolute.")
    content: str = Field(..., description="The content to save to the file.")
    overwrite: bool = Field(default=False, description="Whether to overwrite the file if it already exists.")

class FileSaverToolOutput(BaseToolOutput):
    message: str = Field(..., description="A message indicating the result of the save operation.")
    file_path: Optional[str] = Field(default=None, description="The absolute path to the saved file.")

class FileSaverTool(BaseTool):
    name: str = "file_saver_tool"
    description: str = "Saves the given content to a specified file path. Ensures parent directories are created if they don't exist."
    args_schema: Type[BaseModel] = FileSaverToolInput
    return_schema: Type[BaseModel] = FileSaverToolOutput

    def _ensure_path_and_permission(self, file_path_str: str, overwrite: bool) -> pathlib.Path:
        # Convert to absolute path
        p_file_path = pathlib.Path(file_path_str).resolve()

        # Create parent directories if they don't exist
        # This was previously failing, but the directory `file_system` is now confirmed to exist.
        # The mkdir call here will ensure subdirectories *within* file_system can be created if specified in file_path.
        p_file_path.parent.mkdir(parents=True, exist_ok=True)

        if p_file_path.exists() and not overwrite:
            raise FileExistsError(f"File '{p_file_path}' already exists and overwrite is set to False.")
        
        # Check write permissions on the file if it exists (and overwrite is true), or on the parent directory if it doesn't.
        if p_file_path.exists():
            if not os.access(p_file_path, os.W_OK):
                raise PermissionError(f"No write permission for existing file: {p_file_path}")
        elif not os.access(p_file_path.parent, os.W_OK):
            # This check is crucial for when the file doesn't exist yet.
            raise PermissionError(f"No write permission for parent directory: {p_file_path.parent}")

        return p_file_path

    def _run(self, file_path: str, content: str, overwrite: bool = False) -> FileSaverToolOutput:
        try:
            p_file_path = self._ensure_path_and_permission(file_path, overwrite)
            
            with open(p_file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return FileSaverToolOutput(message=f"Content successfully saved to {p_file_path}", file_path=str(p_file_path))
        except FileExistsError as e:
            return FileSaverToolOutput(error=str(e), message=f"Failed to save file: {e}")
        except PermissionError as e:
            return FileSaverToolOutput(error=str(e), message=f"Failed to save file due to permissions: {e}")
        except Exception as e:
            return FileSaverToolOutput(error=str(e), message=f"An unexpected error occurred: {e}")

    async def _arun(self, file_path: str, content: str, overwrite: bool = False) -> FileSaverToolOutput:
        try:
            p_file_path = self._ensure_path_and_permission(file_path, overwrite)
            
            async with aiofiles.open(p_file_path, "w", encoding="utf-8") as f:
                await f.write(content)
            return FileSaverToolOutput(message=f"Content successfully saved asynchronously to {p_file_path}", file_path=str(p_file_path))
        except FileExistsError as e:
            return FileSaverToolOutput(error=str(e), message=f"Failed to save file: {e}")
        except PermissionError as e:
            return FileSaverToolOutput(error=str(e), message=f"Failed to save file due to permissions: {e}")
        except Exception as e:
            return FileSaverToolOutput(error=str(e), message=f"An unexpected error occurred: {e}")
