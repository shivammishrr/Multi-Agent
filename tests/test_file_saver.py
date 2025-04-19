import asyncio, base64, sys, os, json

from core.tool_management.file_saver_tool import FileSaverTool

async def demo():
    fs = FileSaverTool()
    
    # Create directory
    mkdir_result = await fs.execute_async("mkdir", "demo")
    print(f"mkdir result: {json.dumps(mkdir_result, indent=2)}")
    
    # Write file
    write_result = await fs.execute_async("write", "demo/hi.txt", content="👋", binary=False)
    print(f"write result: {json.dumps(write_result, indent=2)}")
    
    # Read file
    read_result = await fs.execute_async("read", "demo/hi.txt")
    print(f"read result: {json.dumps(read_result, indent=2)}")
    
    # If successful, decode and print content
    if read_result.get("status") == "success" and "content_b64" in read_result:
        print("File content:", base64.b64decode(read_result["content_b64"]).decode())
    else:
        print("Error reading file:", read_result.get("error", "Unknown error"))

asyncio.run(demo())
