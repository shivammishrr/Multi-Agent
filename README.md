# Sarvagya

Sarvagya is an advanced open-source AI agent orchestration platform designed to solve complex tasks through multi-agent collaboration. Built on LangGraph and inspired by the capabilities of Manus AI, Sarvagya provides a robust framework for autonomous task planning and execution.

## Architecture

Sarvagya employs a modular architecture with several key components:

### Core Components

- **Agent System**: LangGraph-based agent workflow with specialized agents for planning and tool execution
- **Tool Management**: Secure Docker-in-Docker sandboxing for code execution and file operations
- **Orchestrator**: Manages task submission, execution, and state persistence
- **Redis Cache**: Provides state management, memory, and real-time updates via Pub/Sub

### Agents

- **SarvagyaAgent**: Main entry agent that receives user tasks
- **PlanningAgent**: Breaks down complex tasks into actionable steps
- **ToolAgent**: Executes specific tools to accomplish steps

### Tools

- **WebBrowserTool**: Web automation and content extraction
- **CodeExecutorTool**: Secure code execution in multiple languages
- **DataRetrievalTool**: Fetches data from various sources
- **FileSaverTool**: Secure file operations

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.9+

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the services using Docker Compose:
   ```bash
   docker-compose up -d
   ```

### Configuration

Copy the example environment file and update with your settings:

```bash
cp .env.example .env
```

Update the `.env` file with your LLM API keys and other configuration options.

## Usage

### API Endpoints

- `POST /tasks`: Submit a new task
- `GET /tasks/{task_id}/status`: Check task status
- `GET /tasks/{task_id}/result`: Get task results
- `DELETE /tasks/{task_id}`: Cancel a task
- `WebSocket /ws/tasks/{task_id}`: Real-time task updates

### Example

```python
import requests

# Submit a task
response = requests.post(
    "http://localhost:8000/tasks",
    json={"task_description": "Find the latest news about AI and summarize the top 3 articles"}
)

task_id = response.json()["task_id"]

# Check status
status = requests.get(f"http://localhost:8000/tasks/{task_id}/status").json()
print(f"Task status: {status['status']}")

# Get results when complete
result = requests.get(f"http://localhost:8000/tasks/{task_id}/result").json()
print(result)
```

## Development

### Project Structure

```
Sarvagya/
├── core/                      # Core functionalities
│   ├── agent_management/      # Agent implementations
│   ├── tool_management/       # Tool implementations
│   ├── prompts/               # LLM prompts
│   ├── schema.py              # Data models
│   └── orchestrator.py        # Task orchestration
├── ui/                        # User interfaces
│   ├── frontend/              # Next.js frontend
│   └── backend/               # FastAPI backend
├── tests/                     # Tests
├── docker-compose.yml         # Service definitions
├── Dockerfile.backend         # Backend container
├── Dockerfile.frontend        # Frontend container
└── requirements.txt           # Python dependencies
```

### Adding New Tools

Extend the `BaseTool` class and use the `@register_tool` decorator:

```python
from core.tool_management.base_tool import BaseTool
from core.tool_management.tool_manager import register_tool

@register_tool
class MyNewTool(BaseTool):
    name = "my_new_tool"
    description = "Description of what my tool does"
    requires_sandbox = True  # Set to True if needs Docker sandbox
    
    async def execute_async(self, **kwargs):
        # Implement your tool logic here
        return {"result": "Tool output"}
```

## Detailed File Information

### core/agent_management/
- `base_agent.py`: Abstract base class for agents. Defines think-act-observe cycle and state/memory handling.
- `sarvagya_agent.py`: Main entry agent, delegates user tasks to the planning agent.
- `planning_agent.py`: Decomposes tasks into actionable steps and assigns ToolAgents.
- `tool_agent.py`: Executes individual tool steps via the ToolManager.

### core/tool_management/
- `base_tool.py`: Abstract base class for tools; defines interface, permissions, and sandbox customization.
- `tool_manager.py`: Registers tools, manages Docker-in-Docker sandbox execution, and enforces permission checks.
- `web_browser_tool.py`: Web automation tool (Playwright stub); supports visit, extract, click, etc.
- `code_executor_tool.py`: Secure multi-language code execution tool in a sandbox.
- `data_retrieval_tool.py`: Retrieves data from APIs/web sources with stubbed responses.
- `file_saver_tool.py`: Secure file operations (read/write/list/delete) in a sandbox.

### core/prompts/
- `base_prompts.py`: System and role prompt templates for all agents and tools.

### core/schema.py
- Defines pydantic models: `Tool`, `ToolCall`, `ToolResult`, `Step`, `Plan`, and `AgentState`.

### core/orchestrator.py
- `Orchestrator`: Manages task lifecycle, Redis persistence, and Pub/Sub updates.
- Singleton access via `get_orchestrator()`.

### ui/backend/
- `api.py`: FastAPI app exposing REST endpoints and WebSocket handlers for task management.

### docker-compose.yml
- Defines services: `redis`, `backend`, `frontend`, and `dind` for sandboxing.

### Dockerfile.backend
- Builds Python backend with Docker CLI for sandbox execution.

### Dockerfile.frontend
- Builds Next.js frontend in a multi-stage Docker build.

### requirements.txt
- Lists all Python dependencies with pinned versions.

### README.md
- This file: high-level overview, usage, and detailed file information.

### LICENSE
- MIT License for the project.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Inspired by Manus AI and the OpenManus project
- Built with LangGraph, FastAPI, and Redis