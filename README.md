# multi-agent

A modular, pattern-based multi-agent orchestration framework. Implements 5 pluggable architecture patterns, 6 standalone features, and 2 protocol integrations over a shared event-sourced core.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           PATTERNS LAYER                                │
│                                                                         │
│  ┌─────────┐  ┌─────────────┐  ┌───────────────────┐  ┌────────────┐  │
│  │  ReAct   │  │Plan & Execute│  │Orchestrator-Workers│  │ Hierarchical│  │
│  └────┬────┘  └──────┬──────┘  └─────────┬─────────┘  └──────┬─────┘  │
│       │              │                   │                   │         │
│  ┌────┴────┐  ┌──────┴──────┐           │                   │         │
│  │  Swarm  │  │  (handoff)  │           │                   │         │
│  └─────────┘  └─────────────┘           │                   │         │
├─────────────────────────────────────────┼───────────────────┼─────────┤
│                           FEATURES LAYER │                   │         │
│                                         │                   │         │
│  ┌──────────┐ ┌────────┐ ┌───────────┐ │                   │         │
│  │ CodeAct  │ │ Browser│ │Permissions │ │                   │         │
│  └────┬─────┘ └───┬────┘ └─────┬─────┘ │                   │         │
│       │           │            │       │                   │         │
│  ┌────┴─────┐ ┌───┴────┐ ┌────┴──────┐ │                   │         │
│  │ Memory   │ │Observe │ │ Durable   │ │                   │         │
│  └──────────┘ └────────┘ └───────────┘ │                   │         │
├─────────────────────────────────────────┼───────────────────┼─────────┤
│                     INTEGRATIONS LAYER  │                   │         │
│                                         │                   │         │
│        ┌─────────────────┐   ┌─────────────────────┐       │         │
│        │   MCP Client    │   │    A2A Client       │       │         │
│        │ (tool ecosystem)│   │ (agent-to-agent)    │       │         │
│        └────────┬────────┘   └──────────┬──────────┘       │         │
├─────────────────┼───────────────────────┼──────────────────┼─────────┤
│                 │        CORE LAYER     │                  │         │
│                 │                       │                  │         │
│  ┌──────┐ ┌────┴────┐ ┌──────┐ ┌───────┴────┐ ┌────────┐ │         │
│  │Event │ │ Thread  │ │ Tool │ │   Agent    │ │  LLM   │ │         │
│  └──────┘ └─────────┘ └──────┘ └────────────┘ └────────┘ │         │
│  ┌───────────┐ ┌──────────────┐ ┌──────────────┐         │         │
│  │ThreadStore│ │  Permissions │ │   Context    │         │         │
│  └───────────┘ └──────────────┘ └──────────────┘         │         │
└──────────────────────────────────────────────────────────┘─────────┘
```

### Layer Responsibilities

| Layer | What It Does | Key Principle |
|-------|-------------|---------------|
| **Core** | Shared types all layers depend on | Zero external deps (only pydantic) |
| **Integrations** | Protocol adapters for MCP + A2A | Each works independently |
| **Features** | Standalone capabilities usable anywhere | No dependency on patterns |
| **Patterns** | Orchestration flows that combine agents | Same core types work in all patterns |

---

## Core Layer

The foundation. Every module in the framework depends on these types.

### Event

The atomic unit — a diary entry for everything that happens.

```mermaid
classDiagram
    class Event {
        +EventType event_type
        +str content
        +str~None agent
        +dict metadata
        +datetime timestamp
    }
    class EventType {
        <<enum>>
        user_message
        assistant_message
        tool_call
        tool_result
        system_message
        error
    }
    Event --> EventType
```

### Thread

An append-only sequence of Events. The universal state container.

```mermaid
stateDiagram-v2
    [*] --> AddingEvents
    AddingEvents --> AddingEvents : add_event()
    AddingEvents --> Forked : fork()
    Forked --> AddingEvents : independent copy
    AddingEvents --> LLMMessages : to_llm_messages()
    AddingEvents --> XMLContext : to_xml_context()
```

```python
thread = Thread()
thread.add_event(Event(event_type=EventType.user_message, content="hello"))
thread.add_event(Event(event_type=EventType.assistant_message, content="hi"))
messages = thread.to_llm_messages()  # → OpenAI-compatible format
forked = thread.fork()                # → deep copy for branching
```

### Tool

A callable with a JSON Schema signature and a permission level.

```python
async def search_fn(query: str) -> ToolResult:
    return ToolResult(success=True, output=f"results for {query}")

tool = Tool(
    name="search",
    description="Search the web",
    parameters={"type": "object", "properties": {"query": {"type": "string"}}},
    function=search_fn,
    permission=PermissionLevel.ask,  # allow | deny | ask | bubble
)
```

### Agent

An agent configuration — personality, tools, and model.

```python
agent = Agent(
    name="researcher",
    system_prompt="You are a research assistant.",
    tools=[search_tool, code_tool],
    model="gpt-4o",
    max_turns=15,
)
```

### ThreadStore

Abstract persistence for threads.

```mermaid
classDiagram
    class ThreadStore {
        <<abstract>>
        +get(thread_id) Thread~None
        +save(thread_id, thread)
        +delete(thread_id)
        +list_ids() list~str~
    }
    class InMemoryStore {
        +dict _store
    }
    class SQLiteStore {
        +str db_path
        +_ensure_conn()
    }
    ThreadStore <|-- InMemoryStore
    ThreadStore <|-- SQLiteStore
```

---

## Patterns Layer

All patterns share the same contract: take agents + a task, produce a Thread.

### 1. ReAct

The foundation pattern. Single agent Think-Act-Observe loop with CodeAct as the default action mechanism and JSON tool calls as fallback.

```mermaid
sequenceDiagram
    participant U as User
    participant R as ReAct Loop
    participant LLM as LLM
    participant CA as CodeAct Sandbox
    participant JT as JSON Tools

    U->>R: task
    R->>LLM: system prompt + task + tool defs
    LLM-->>R: thought + tool_call (python code)
    R->>CA: execute(code)
    CA-->>R: stdout/stderr
    R->>LLM: observation
    LLM-->>R: thought + tool_call (json)
    R->>JT: execute(json)
    JT-->>R: result
    R->>LLM: observation
    LLM-->>R: final answer
    R->>U: completed Thread
```

```python
from multi_agent.patterns.react import react

thread = await react(
    task="Calculate 15 * 37",
    agent=Agent(name="assistant", model="groq/llama-4-scout-17b-16e-instruct"),
)
```

| Property | Value |
|----------|-------|
| Agents | Single agent |
| AI Calls | Sequential |
| Best for | Simple tool-use tasks |
| Max turns | Configurable (default 25) |
| Action mechanism | CodeAct (python) > JSON tools |

---

### 2. Plan & Execute

Planner (strong model) decomposes the task → Executor (cheaper model) runs each step → Replanner adjusts course based on results.

```mermaid
sequenceDiagram
    participant P as Planner (gpt-4o)
    participant E as Executor (gpt-4o-mini)
    participant LLM as LLM
    participant CA as CodeAct

    P->>LLM: decompose task into steps
    LLM-->>P: [step1, step2, step3]
    P->>E: execute step1
    E->>CA: run code
    CA-->>E: result
    E-->>P: step1 complete
    P->>LLM: replan? based on result
    LLM-->>P: adjusted steps
    P->>E: execute remaining steps
    E-->>P: all done
    P->>P: synthesize final answer
```

```python
from multi_agent.patterns.plan_execute import plan_and_execute

thread = await plan_and_execute(
    task="Build a web scraper that extracts all links from a page",
    planner_agent=Agent(name="planner", model="gpt-4o"),
    executor_agent=Agent(name="executor", model="gpt-4o-mini"),
)
```

| Property | Value |
|----------|-------|
| Agents | 2 (Planner + Executor) or same |
| AI Calls | Planner → Executor × steps → Replanner |
| Best for | Multi-step tasks, research, code generation |
| Max iterations | Configurable (default 3 replan cycles) |

---

### 3. Orchestrator-Workers (Fan-Out)

Orchestrator splits task → N workers run in parallel → Synthesizer combines results. Inspired by Manus Clone Fan-Out for wide research.

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant W1 as Worker 1
    participant W2 as Worker 2
    participant W3 as Worker N
    participant S as Synthesizer

    O->>O: decompose into sub-tasks
    O->>W1: sub-task A
    O->>W2: sub-task B
    O->>W3: sub-task C
    par Workers in parallel
        W1->>W1: run ReAct
        W2->>W2: run ReAct
        W3->>W3: run ReAct
    end
    W1-->>O: result A
    W2-->>O: result B
    W3-->>O: result C
    O->>S: synthesize
    S-->>O: final answer
```

```python
from multi_agent.patterns.orchestrator_workers import orchestrator_workers

thread = await orchestrator_workers(
    task="Research the top 5 AI frameworks in 2026",
    num_workers=5,
)
```

| Property | Value |
|----------|-------|
| Agents | 1 Orchestrator + N Workers (any count) |
| AI Calls | Parallel × N + synthesize |
| Best for | Parallel research, data processing, wide exploration |
| Parallelism | asyncio.gather — true concurrent LLM calls |

---

### 4. Hierarchical (Supervisor)

Supervisor delegates to specialized workers (Researcher, Coder, etc.) and synthesizes their results. Each worker is an independent Agent with its own system prompt.

```mermaid
sequenceDiagram
    participant S as Supervisor
    participant LLM as LLM
    participant R as Researcher
    participant C as Coder
    participant V as Verifier

    S->>LLM: who should do what?
    LLM-->>S: researcher:research topic, coder:implement
    S->>R: research the topic
    activate R
    R->>R: run ReAct loop
    R-->>S: research results
    deactivate R
    S->>C: implement the solution
    activate C
    C->>C: run ReAct loop
    C-->>S: code
    deactivate C
    S->>V: verify the solution
    Note over S: workers are typed agents<br/>with different system prompts
    S->>S: synthesize all results
```

```python
from multi_agent.patterns.hierarchical import hierarchical

thread = await hierarchical(
    task="Create a Python CLI tool",
    supervisor_agent=Agent(name="supervisor", model="gpt-4o"),
    workers=[
        Agent(name="researcher", model="gpt-4o-mini", system_prompt="Research best practices"),
        Agent(name="coder", model="gpt-4o-mini", system_prompt="Write clean Python code"),
        Agent(name="verifier", model="gpt-4o-mini", system_prompt="Check for bugs"),
    ],
)
```

| Property | Value |
|----------|-------|
| Agents | 1 Supervisor + N typed Workers |
| AI Calls | Sequential (each worker runs its own ReAct) |
| Best for | Multi-skill tasks needing specialized sub-agents |
| Worker type | Each worker has its own system prompt + tools |

---

### 5. Swarm (Handoff)

Triage agent routes the task → Specialist handles it → Decides to hand off or finish. Inspired by OpenAI Agents SDK handoff pattern.

```mermaid
sequenceDiagram
    participant T as Triage
    participant R as Researcher
    participant C as Coder
    participant LLM as LLM

    T->>LLM: who should handle this?
    LLM-->>T: researcher
    T->>R: task
    R->>R: run ReAct loop
    R->>LLM: is this done or handoff?
    LLM-->>R: needs coding, handoff to coder
    R->>C: continue from researcher
    C->>C: run ReAct loop
    C->>LLM: done?
    LLM-->>C: done
    C->>C: final answer
```

```python
from multi_agent.patterns.swarm import swarm

thread = await swarm(
    task="Research and implement a bisect algorithm",
    agents=[
        Agent(name="triage", system_prompt="Route tasks", max_turns=1),
        Agent(name="researcher", system_prompt="Research algorithms"),
        Agent(name="coder", system_prompt="Write Python code"),
    ],
)
```

| Property | Value |
|----------|-------|
| Agents | N agents with handoff routing |
| AI Calls | Sequential with handoff decisions |
| Best for | Customer support, multi-domain queries |
| Max handoffs | Configurable (default 5) |

---

### Pattern Comparison

```mermaid
graph TB
    subgraph "Pattern Selection Guide"
        direction TB
        Q1{Task needs<br/>multiple steps?}
        Q1 -- No --> Q2{Task needs<br/>parallel work?}
        Q1 -- Yes --> Q3{Steps known<br/>upfront?}
        Q3 -- Yes --> PlanExec[Plan & Execute]
        Q3 -- No --> ReAct[ReAct]
        Q2 -- No --> Q4{Single domain?}
        Q4 -- Yes --> ReAct
        Q4 -- No --> Q5{Typed agents?}
        Q5 -- Yes --> Hierarchical
        Q5 -- No --> Swarm
        Q2 -- Yes --> FanOut[Orchestrator-Workers]
    end
```

| Pattern | When To Use | When NOT To Use |
|---------|------------|-----------------|
| **ReAct** | Simple tool use, ≤10 steps, single agent | Multi-hour tasks, complex multi-agent coordination |
| **Plan & Execute** | Research, multi-step coding, unknown terrain | Very simple tasks (ReAct is faster) |
| **Orchestrator-Workers** | Parallel research, bulk data processing | Sequential tasks (adds overhead) |
| **Hierarchical** | Need typed specialists, different models per role | Simple routing (Swarm is lighter) |
| **Swarm** | Customer support routing, multi-domain queries | Deep tree of sub-tasks (Hierarchical better) |

---

## Features Layer

Standalone capabilities that any pattern (or any external code) can use.

### CodeAct

Python code execution in a restricted sandbox. Primary action mechanism for all patterns — ~30% fewer steps than JSON-only tool calling.

```python
from multi_agent.features.codeact import CodeActSandbox

sandbox = CodeActSandbox()
result = await sandbox.run("""
import math
print(math.factorial(10))
""")
print(result.output)  # → 3628800
```

Security model:
- `allow_imports=False` (default): Import statements are blocked
- `allow_imports=True` + `allowed_modules=["math"]`: Only listed modules can be imported
- `exec()` in restricted namespace with limited builtins
- `reset()` clears namespace between runs

### Browser

Playwright-based web browsing with DOM tree extraction and element index interaction. Follows the browser-use approach.

```mermaid
graph LR
    A[Agent] -->|browser_navigate| B[Playwright]
    B -->|extract DOM| C[Semantic Tree]
    C -->|numbered elements| A
    A -->|browser_click 5| B
    A -->|browser_type 3 "query"| B
    A -->|browser_screenshot| B
    B -->|screenshot b64| A
```

```python
from multi_agent.features.browser import BrowserTool

browser = BrowserTool(headless=True)
result = await browser.navigate("https://example.com")
print(result["title"])       # → "Example Domain"
print(result["elements"])    # → 6
print(result["page"][:200])  # → "[0] <body>Example Domain..."
```

5 browser tools exposed to agents:

| Tool | Permission | Purpose |
|------|-----------|---------|
| `browser_navigate` | allow | Go to a URL, returns page tree |
| `browser_click` | ask | Click element by index |
| `browser_type` | ask | Type text into input by index |
| `browser_scroll` | allow | Scroll up/down |
| `browser_screenshot` | allow | Return base64 screenshot |

### Permissions

Human-in-the-loop for dangerous operations. Four levels per tool.

```mermaid
graph TD
    T[Tool Called] --> P{Permission Level}
    P -->|allow| E[Execute immediately]
    P -->|deny| B[Block with message]
    P -->|ask| U[Prompt user]
    U -->|a| E
    U -->|aa| S[Save as always allow]
    U -->|d| B
    U -->|dd| D[Save as always deny]
    U -->|b| R[Bubble to parent agent]
    S --> E
```

```python
from multi_agent.features.permissions import PermissionConfig, PermissionCLI

config = PermissionConfig(rules=[
    Rule(pattern="*", permission=PermissionLevel.allow),
    Rule(pattern="browser_click", permission=PermissionLevel.ask),
    Rule(pattern="rm", permission=PermissionLevel.deny),
])
config.save()  # persists to .permissions.json

cli = PermissionCLI(config)
tool.permission = PermissionLevel.ask
wrapped = await cli.wrap_tool(tool)
```

### Memory

Plug in different memory backends. Adapter pattern — swap implementations without changing code.

```python
from multi_agent.features.memory import InMemoryMemory, Mem0Memory

# Development
memory = InMemoryMemory()

# Production with Mem0 (open-source)
memory = Mem0Memory(api_key="...")

await memory.store("user1", "prefers Python over JavaScript")
results = await memory.search("Python")
```

| Adapter | License | Storage | Best For |
|---------|---------|---------|----------|
| `InMemoryMemory` | MIT | Dict in RAM | Development, testing |
| `Mem0Memory` | MIT | Mem0 cloud/server | Production memory |
| *(future) Letta* | Apache 2.0 | Self-managed DB | Long-term persistent memory |
| *(future) Zep* | Apache 2.0 | Temporal graph | Time-based retrieval |

### Observability

OpenTelemetry-inspired tracing with span export.

```python
from multi_agent.features.observability import OTelTracer, ConsoleExporter

tracer = OTelTracer(service_name="my-agent")
tracer.add_exporter(ConsoleExporter())

async with tracer.span("llm_call", {"model": "gpt-4o"}):
    result = await llm.chat(...)
    span.add_event("tool_call", {"tool": "python"})

tracer.export()
# → === TRACE (2 spans) ===
# →   llm_call: 1240ms (1 events)
```

### Durable Execution

Persist and resume long-running agent executions.

```python
from multi_agent.features.durable import InMemoryExecutor

async def my_long_step() -> str:
    # ... many LLM calls ...
    return "done"

executor = InMemoryExecutor(persist_path="executions.json")
execution = await executor.run(my_long_step)
print(execution.status)  # → "completed"
print(execution.id)      # → "uuid"
```

---

## Integrations Layer

### MCP (Model Context Protocol)

Consume tools from any MCP server — 2,300+ available in the ecosystem.

```mermaid
graph LR
    A[Agent] -->|tool call| MC[MCP Client]
    MC -->|JSON-RPC 2.0| MS[MCP Server]
    MS -->|stdio or HTTP| MC
    MC -->|ToolResult| A
```

```python
from multi_agent.integrations.mcp import MCPClient

mcp = MCPClient(command="npx @anthropic/mcp-filesystem-server /path")
await mcp.connect()
print(mcp.tools)  # → [Tool("read_file"), Tool("write_file"), ...]
```

- Stdio transport for local MCP servers
- HTTP/Streamable HTTP for remote servers
- Tools surfaced as standard `Tool` objects (permission = `ask` by default)

### A2A (Agent-to-Agent Protocol)

Interact with remote agents via the Agent-to-Agent protocol (v1.0.0, May 2026).

```mermaid
graph LR
    A1[Local Agent] -->|A2A Client| A2[Remote Agent]
    A2 -->|/.well-known/agent-card.json| A1
    A1 -->|POST /a2a/tasks| A2
    A2 -->|task result| A1
```

```python
from multi_agent.integrations.a2a import A2AClient, AgentCard
from multi_agent.integrations.a2a.server import A2AServer

# Client
client = A2AClient("http://remote-agent:8080")
card = await client.get_card()
result = await client.send_task("research quantum computing")

# Server
async def handler(task, metadata):
    return f"Processed: {task}"

server = A2AServer(
    AgentCard(name="my-agent", skills=["research", "code"]),
    handler=handler,
)
card_dict = server.get_card_dict()
task_result = await server.handle_task({"task": "analyze data"})
```

---

## File Tree

```
multi_agent/
├── __init__.py
│
├── core/                          # Shared foundation (zero hard deps)
│   ├── event.py                   # Event, EventType
│   ├── thread.py                  # Thread — append-only event sequence
│   ├── tool.py                    # Tool, PermissionLevel, ToolResult
│   ├── agent.py                   # Agent — name, prompt, tools, model
│   ├── llm.py                     # LLMClient ABC + LiteLLMClient
│   ├── store.py                   # ThreadStore ABC + InMemory + SQLite
│   └── context.py                 # XML/Markdown formatters
│
├── patterns/                      # Orchestration flows
│   ├── react.py                   # Single agent think-act-observe
│   ├── plan_execute.py            # Planner → Executor → Replanner
│   ├── orchestrator_workers.py    # Fan-out/fan-in with asyncio.gather
│   ├── hierarchical.py            # Supervisor → typed workers
│   └── swarm.py                   # Triage → handoff → specialist
│
├── features/                      # Standalone capabilities
│   ├── codeact/
│   │   └── sandbox.py             # Python exec sandbox
│   ├── browser/
│   │   └── browser.py             # Playwright DOM tree + element indices
│   ├── permissions/
│   │   ├── config.py              # Rule-based permission config
│   │   └── cli.py                 # Interactive allow/deny/ask CLI
│   ├── memory/
│   │   └── adapters.py            # InMemory + Mem0 adapters
│   ├── observability/
│   │   └── tracer.py              # OTel-style spans + exporters
│   └── durable/
│       └── executor.py            # Execution persistence
│
├── integrations/                  # Protocol adapters
│   ├── mcp/
│   │   └── client.py              # MCP stdio + HTTP client
│   └── a2a/
│       ├── card.py                # Agent Card model
│       ├── client.py              # A2A task client
│       └── server.py              # A2A task server
│
├── opencode.json                  # Plugin configuration
├── pyproject.toml                 # Package config
└── README.md
```

---

## Quick Start

```bash
pip install -e ".[dev]"
```

```python
import asyncio
from multi_agent.core.agent import Agent
from multi_agent.patterns.react import react

async def main():
    thread = await react(
        task="Calculate 15 * 37 and print the answer.",
        agent=Agent(
            name="assistant",
            model="groq/meta-llama/llama-4-scout-17b-16e-instruct",
            system_prompt="You are helpful. Use python tool for math.",
        ),
    )
    for event in thread.events:
        print(f"[{event.event_type.value}] {event.content}")

asyncio.run(main())
```

Set your API key:

```bash
export GROQ_API_KEY="gsk_..."
# or
export OPENAI_API_KEY="sk-..."
```

---

## Testing

```bash
# All unit tests (87 tests)
python -m pytest tests/ -v

# Exclude browser integration tests
python -m pytest tests/ -v --ignore=tests/test_browser.py

# Run a specific pattern test
python -m pytest tests/test_react.py -v
```

---

## Design Principles

1. **Event-sourced everything** — Every action is an Event in a Thread. Enables replay, fork, save/resume.
2. **CodeAct first** — Python code execution beats JSON tool calls by ~30% fewer steps. JSON is the fallback.
3. **Patterns share the same state** — All patterns write to the same `Thread` type. Switch patterns mid-task.
4. **No framework lock-in** — Core has zero external deps. Each layer imports only from layers below.
5. **Pluggable** — Add a pattern by implementing `run(agents, task) -> Thread`. Add a feature by implementing its interface.
6. **Permissions on tools** — Allow, Deny, Ask, Bubble. Human-in-the-loop for dangerous operations.
