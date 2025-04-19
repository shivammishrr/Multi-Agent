import asyncio
from core.tool_management.code_executor_tool import CodeExecutorTool

async def test_code_executor_tool():
    executor = CodeExecutorTool()
    # result = await executor.execute_async(code="print('Hello, world!')", language="python")
    result = await executor.execute_async(file_path = "tests/test_java.java", language="java")
    print(result)

if __name__ == "__main__":
    asyncio.run(test_code_executor_tool())