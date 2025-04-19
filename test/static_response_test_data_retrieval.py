import sys
import os
import asyncio

# Ensure the parent directory is in sys.path so 'core' can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tool_management.data_retrieval_tool import DataRetrievalTool

RESULT_DIR = os.path.join(os.path.dirname(__file__), 'result_fetch')
os.makedirs(RESULT_DIR, exist_ok=True)

def write_result(index, task, content, ext="txt"):
    filename = f"{index:02d}_{task}.{ext}"
    filepath = os.path.join(RESULT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[Saved: {filepath}]")

async def main():
    tool = DataRetrievalTool()
    # 1. API source (GitHub API)
    print("\n--- Testing API source (GitHub API) ---")
    result_api = await tool.execute_async(
        source="api",
        url="https://api.github.com/repos/python/cpython",
        method="GET",
        headers={"Accept": "application/vnd.github.v3+json"},
        query=""
    )
    print(result_api)
    write_result(1, "api_github", str(result_api), ext="json")

    # 2. Web source (Stack Overflow)
    print("\n--- Testing Web source (Stack Overflow) ---")
    result_web = await tool.execute_async(
        source="web",
        url="https://stackoverflow.com/questions"
    )
    print(result_web)
    web_content = result_web.get("data", {}).get("content", str(result_web)) if isinstance(result_web.get("data"), dict) else str(result_web)
    write_result(2, "web_stackoverflow", web_content, ext="html")

    # 3. Database source (Simulated Query)
    print("\n--- Testing Database source (Simulated Query) ---")
    result_db = await tool.execute_async(
        source="database",
        query="SELECT * FROM users WHERE id=1"
    )
    print(result_db)
    db_content = result_db.get("data", {}).get("result", str(result_db)) if isinstance(result_db.get("data"), dict) else str(result_db)
    write_result(3, "db_simulated", db_content)

    # 4. Error: missing url for API
    print("\n--- Testing error: missing url for API ---")
    result_error = await tool.execute_async(
        source="api"
    )
    print(result_error)
    write_result(4, "error_missing_url_api", str(result_error))

if __name__ == "__main__":
    asyncio.run(main())
