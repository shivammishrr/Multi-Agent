import os
import pathlib
from typing import Type, List, Dict, Any, Optional

from pydantic import BaseModel, Field

from tools.base_tool import BaseTool, BaseToolInput, BaseToolOutput

class DirectoryListingToolInput(BaseToolInput):
    directory_path: str = Field(default=".", description="The path to the directory to list. Defaults to the current directory.")
    recursive: bool = Field(default=False, description="Whether to list contents recursively.")
    max_depth: Optional[int] = Field(default=None, description="Maximum depth for recursive listing. Only used if recursive is True. None means no limit.")

class FileSystemItem(BaseModel):
    name: str
    path: str
    type: str # 'file' or 'directory'
    size_bytes: Optional[int] = None # Only for files
    children_count: Optional[int] = None # Only for directories if not recursive, or total items if recursive

class DirectoryListingToolOutput(BaseToolOutput):
    items: List[FileSystemItem] = Field(default=[], description="A list of files and directories found.")
    item_count: int = Field(0, description="Total number of items listed.")
    message: Optional[str] = None

class DirectoryListingTool(BaseTool):
    name: str = "directory_listing_tool"
    description: str = "Lists the contents (files and subdirectories) of a specified directory."
    args_schema: Type[BaseModel] = DirectoryListingToolInput
    return_schema: Type[BaseModel] = DirectoryListingToolOutput

    def _list_contents(self, dir_path: pathlib.Path, current_depth: int, max_depth: Optional[int], recursive: bool) -> List[FileSystemItem]:
        listed_items = []
        if max_depth is not None and current_depth > max_depth:
            return listed_items

        try:
            for entry in os.scandir(dir_path):
                item_path = pathlib.Path(entry.path)
                item_type = "directory" if entry.is_dir() else "file"
                item = FileSystemItem(
                    name=entry.name,
                    path=str(item_path.resolve()),
                    type=item_type
                )
                if item_type == "file":
                    try:
                        item.size_bytes = entry.stat().st_size
                    except OSError:
                        item.size_bytes = None # Could not stat file
                elif item_type == "directory":
                    # For non-recursive, count immediate children. For recursive, this could be more complex.
                    # We'll keep it simple for now.
                    try:
                        item.children_count = len(os.listdir(item_path))
                    except OSError:
                        item.children_count = None
                
                listed_items.append(item)

                if recursive and entry.is_dir():
                    listed_items.extend(self._list_contents(item_path, current_depth + 1, max_depth, recursive))
        except PermissionError:
            # Could add a specific error item to the list if desired
            pass # Silently ignore permission errors for now, or log them
        except FileNotFoundError:
            pass # Directory itself not found
        return listed_items

    def _run(self, directory_path: str = ".", recursive: bool = False, max_depth: Optional[int] = None) -> DirectoryListingToolOutput:
        try:
            p_dir_path = pathlib.Path(directory_path).resolve()
            if not p_dir_path.is_dir():
                return DirectoryListingToolOutput(error=f"Path '{p_dir_path}' is not a valid directory or does not exist.", message=f"Path '{p_dir_path}' is not a valid directory or does not exist.")

            if not os.access(p_dir_path, os.R_OK):
                 return DirectoryListingToolOutput(error=f"No read permission for directory: {p_dir_path}", message=f"No read permission for directory: {p_dir_path}")

            all_items = self._list_contents(p_dir_path, current_depth=0, max_depth=max_depth if recursive else 0, recursive=recursive)
            
            return DirectoryListingToolOutput(
                items=all_items,
                item_count=len(all_items),
                message=f"Successfully listed contents of '{p_dir_path}'."
            )
        except Exception as e:
            return DirectoryListingToolOutput(error=str(e), message=f"An unexpected error occurred: {e}")

    async def _arun(self, directory_path: str = ".", recursive: bool = False, max_depth: Optional[int] = None) -> DirectoryListingToolOutput:
        # For now, file system operations are typically blocking in standard Python.
        # True async listing would require a library like aiofiles for directory scanning if available,
        # or running the sync version in a thread pool.
        # We'll use the sync version for simplicity for now.
        # Consider using asyncio.to_thread for a more robust async implementation.
        import asyncio
        try:
            # Run the synchronous method in a separate thread
            return await asyncio.to_thread(self._run, directory_path=directory_path, recursive=recursive, max_depth=max_depth)
        except Exception as e:
            return DirectoryListingToolOutput(error=str(e), message=f"An unexpected error occurred during async execution: {e}")

# Example Usage (for testing purposes):
# if __name__ == '__main__':
#     import asyncio
#     lister_tool = DirectoryListingTool()

#     # Test current directory, non-recursive
#     result_current = lister_tool.run()
#     print(f"Current Directory (non-recursive): Found {result_current.item_count} items.")
#     # for item in result_current.items:
#     #     print(f"  - {item.name} ({item.type}, Size: {item.size_bytes} bytes, Children: {item.children_count})")

#     # Test with a specific path, recursive
#     # Create a dummy structure for testing recursive listing
#     test_recursive_dir = pathlib.Path("./test_list_dir_recursive")
#     test_recursive_dir.mkdir(exist_ok=True)
#     (test_recursive_dir / "file1.txt").write_text("hello")
#     (test_recursive_dir / "subdir1").mkdir(exist_ok=True)
#     (test_recursive_dir / "subdir1" / "file2.txt").write_text("world")
#     (test_recursive_dir / "subdir1" / "subsubdir").mkdir(exist_ok=True)
#     (test_recursive_dir / "subdir1" / "subsubdir" / "file3.md").write_text("# Test")

#     result_recursive = lister_tool.run(directory_path=str(test_recursive_dir), recursive=True)
#     print(f"\nRecursive Listing for '{test_recursive_dir}': Found {result_recursive.item_count} items.")
#     for item in result_recursive.items:
#         print(f"  - {item.path} ({item.type}, Size: {item.size_bytes} bytes)")
    
#     # Test recursive with max_depth
#     result_depth_limited = lister_tool.run(directory_path=str(test_recursive_dir), recursive=True, max_depth=1)
#     print(f"\nRecursive Listing (max_depth=1) for '{test_recursive_dir}': Found {result_depth_limited.item_count} items.")
#     for item in result_depth_limited.items:
#         print(f"  - {item.path} ({item.type}, Size: {item.size_bytes} bytes)")

#     async def main_async_test():
#         result_async = await lister_tool.arun(directory_path=str(test_recursive_dir), recursive=True, max_depth=0)
#         print(f"\nAsync Recursive Listing (max_depth=0) for '{test_recursive_dir}': Found {result_async.item_count} items.")
#         for item in result_async.items:
#             print(f"  - {item.path} ({item.type}, Size: {item.size_bytes} bytes)")
    
#     asyncio.run(main_async_test())
