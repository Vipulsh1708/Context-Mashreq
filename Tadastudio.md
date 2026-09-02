# TADA Studio — Onboarding Documentation

> Transcribed from in-app onboarding walkthrough ("Step X of 13") screenshots.

---

## Step 1 of 13 — What is TADA Studio?

*Your first 5 minutes — the big picture*

TADA Studio (also called **Agentic Studio**) is a **no-code / low-code AI workflow builder**. It lets you design, execute, and monitor complex AI automations — without writing code — using a visual drag-and-drop canvas in your browser.

> **Analogy for beginners**
> Think of it like a flowchart designer (e.g. Microsoft Visio or Miro), except each box on your canvas is a real AI agent, tool, or decision — and when you click **Run**, that flowchart actually executes and produces real results.

### Who uses it and for what?

| Role | Use case |
|---|---|
| 👤 **Business Analyst** | Builds an "Invoice Reconciliation" workflow: extract data from PDF → query database → flag mismatches → send email report. |
| 🛠️ **Developer** | Wires up an AI that calls internal APIs, searches documents with RAG, and summarises results — exported as a Python script if needed. |
| 📊 **Data Team** | Runs LLM evaluations on workflow outputs, tracks quality metrics, and monitors traces in Phoenix. |
| ⚙️ **Ops Team** | Schedules automations, monitors execution history, manages user access, and deploys to AKS. |

### The three big capabilities

1. **Visual Workflow Builder** — A ReactFlow canvas where you drag nodes (AI agents, tools, conditions) and connect them with arrows. The canvas saves the layout as JSON.
2. **Multi-Agent Execution Engine** — The JSON graph is converted at runtime into a live **LangGraph StateGraph** — an AI orchestration framework from LangChain. LLMs, tools, and conditions run in the order you drew.
3. **Real-time Streaming + Observability** — Every step streams results back to the browser via WebSocket. All LLM calls are traced in **Arize Phoenix** (token counts, latencies, inputs/outputs).

> **Key repo examples**
> Check `examples/` — it contains real exported workflows like *Account Unlock Investigation Orchestration* and *Invoice Reconciliation* that show exactly what gets saved.

---

## Step 2 of 13 — Tech Stack Overview

*All the moving parts and how they fit together*

Before diving into code, here's a mental map of every technology layer and where it lives in the repository.

| Layer | Stack | Location |
|---|---|---|
| 💻 **Frontend** | Next.js 15 + React 19, ReactFlow, Tailwind CSS, TypeScript, BiomeJS | `frontend/` |
| 🔒 **Auth Proxy** | OAuth2-Proxy, Azure AD OIDC, JWT Bearer tokens | `oauth2-proxy.cfg` |
| ⚙️ **Backend** | Python 3.11, FastAPI, LangGraph, LangChain, Pydantic | `backend/` |
| 🗄️ **Database** | PostgreSQL 16 + pgvector, SQLAlchemy ORM, LangGraph checkpoints | `backend/models/` |
| 📡 **Observability** | Arize Phoenix (OTel), LLM trace + evals, custom trace viewer | `backend/services/phoenix/` |
| 🚀 **Infrastructure** | Docker Compose (dev), Kubernetes AKS (prod), Nginx reverse proxy | `docker-compose.dev.yml` |

### How data flows between layers

**Request path:**
Browser (ReactFlow) → HTTPS/WSS through Nginx → FastAPI `/api/*` → LangGraph Engine → PostgreSQL + pgvector

**Streaming path:**
LangGraph Node runs → WebSocket event → Browser updates UI **+** Phoenix OTel span

> **What is LangGraph?**
> LangGraph (by LangChain) lets you define AI workflows as a **directed graph** in Python. Each node in the graph is a Python function. It handles message passing, state management, conditional branching, and checkpointing natively. TADA Studio's backend builds a LangGraph `StateGraph` dynamically from whatever the user drew on canvas.

### Repository layout at a glance

| Folder | What lives here |
|---|---|
| `backend/api/` | 25+ FastAPI route modules — thin HTTP handlers |
| `backend/services/` | 38+ business logic services (graph builder, execution engine, nodes…) |
| `backend/models/` | SQLAlchemy ORM + Python dataclasses for workflows, executions, docs |
| `backend/tools/` | Built-in tool implementations (HTTP, database, web search, email…) |
| `frontend/src/app/` | Next.js App Router pages (workflow, executions, evaluations…) |
| `frontend/src/components/` | React components (canvas, nodes, panels, UI library) |
| `docs/` | Architecture decisions, agent guides, runbooks |
| `workspace/` | Local dev storage for saved graphs (gitignored) |

---

## Step 3 of 13 — The Visual Editor

*How the frontend canvas works under the hood*

When a user opens TADA Studio in the browser, they land on the **workflow builder**. This is a rich canvas where every interaction eventually translates to an HTTP call to the backend.

### Route entry point

The page is served by Next.js at `frontend/src/app/workflow/page.tsx`, which renders the **AgentBuilder** component.

### AgentBuilder — the orchestrator

File: `frontend/src/components/core/AgentBuilder.tsx`

This is the brain of the entire editing experience. It uses **ReactFlow** — an open-source React library for building node-based editors.

```javascript
// AgentBuilder.tsx (simplified)
import { useNodesState, useEdgesState } from "reactflow";

const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

// Drop a new node from the palette onto canvas
const onDrop = async (event) => {
  const nodeType = event.dataTransfer.getData("nodeType");
  const position = reactFlowInstance.screenToFlowPosition({x, y});
  await api.post("/api/graph/node/create", { nodeType, position, graphName });
};
```

### What happens when a user drags a node?

1. **User drags "Agent" from the node palette** — The sidebar palette shows all available node types. Dragging triggers a `dragstart` event with `nodeType = "AGENT"`.
2. **onDrop fires → POST /api/graph/node/create** — The frontend calculates the canvas position and calls the backend to create the node record in the database.
3. **Backend creates the EnhancedNodeData record** — Returns the new node's `uniq_id`, default config, and position.
4. **ReactFlow renders the node on canvas** — The node component (e.g. `AgentNode.tsx`) is rendered with the default config.
5. **User clicks the node → config panel opens** — A sidebar panel slides in allowing system prompt, model selection, tools, memory settings etc. Each change calls `PUT /api/graph/node/update`.

### The canvas toolbar (CanvasTopBar)

File: `frontend/src/components/core/CanvasTopBar.tsx`

| Button | What it does |
|---|---|
| ▶ Run | `POST /api/graph/execute` → opens WebSocket → starts streaming |
| ⏸ Pause | `POST /api/graph/stop/{id}` with `pause=true` → checkpoints state to DB |
| 💾 Save | `POST /api/graph/save` → stores graph JSON to `graph_definitions` table |
| ⬆️ Export JSON | Downloads the raw GraphData JSON — the same format stored in DB |
| 🔄 Export Python | Generates a runnable Python script for the workflow |
| 🗂️ Version History | Shows all saved versions via `graph_definitions.version` field |

### Other frontend routes

| URL path | Purpose |
|---|---|
| `/workflow` | Main builder canvas |
| `/executions` | History of all past runs |
| `/execution-viewer` | Replay / inspect a specific past run |
| `/evaluations` | Run LLM evaluations (quality scoring) |
| `/library` | Browse / import community workflows |
| `/chat` | Chat-mode interface for conversational workflows |
| `/guardrails` | Define safety policies (LLM Guard) |

---

## Step 4 of 13 — Node Types

*The building blocks you place on the canvas*

Every block you drag onto the canvas is a **Node**. Each node type has a specific behaviour defined by both a frontend React component (how it looks) and a backend executor (how it runs).

> **Where are node types defined?**
> `NodeType` enum lives in `backend/models/workflow/node.py`. Frontend components are in `frontend/src/components/nodes/`.

### Special / Control nodes

| Node | Description |
|---|---|
| 🟢 **START** | Entry point of every workflow. Receives initial user input. Every graph must have exactly one. |
| 🔴 **END** | Terminal node. Collects the final output from upstream nodes and returns it to the user. |
| 🔀 **CONDITION** | Branch the workflow based on a condition (e.g. "if amount > 1000, go to approval path"). |

### AI / Processing nodes

| Node | Description |
|---|---|
| 🤖 **AGENT** | LLM reasoning node. Has a system prompt, chosen model (GPT-4, Claude, etc.), and can call tools. |
| 🌐 **SUBWORKFLOW** | Embeds another entire workflow as a single node — enabling modular, reusable components. |
| 🔁 **FOR_EACH** | Iterates over a list of items, running downstream nodes for each element. |

### Tool / Integration nodes

| Node | Description |
|---|---|
| 📡 **HTTP_REQUEST** | Make any REST API call — GET, POST, PUT, DELETE — with custom headers and body. |
| 🗄️ **DATABASE_QUERY** | Run a SQL query against a connected database. Results flow to the next node. |
| 🔍 **DOCUMENT_SEARCH** | Vector similarity search (RAG) over uploaded documents using pgvector. |
| 🌍 **WEB_SEARCH** | Search the web and return results. Uses a configured search API. |
| ✉️ **EMAIL_SEND** | Send an email via Outlook/SMTP with content generated by upstream nodes. |
| 📁 **FILE_READ** | Read the contents of an uploaded or workspace file for processing. |
| 💻 **CODE_EXECUTOR** | Execute Python code inline. Useful for custom data transformations. |
| 🔌 **MCP_SERVER** | Connect to a Model Context Protocol server — extends the AI with custom external tools. |
| 📄 **DOCUMENT_LOAD** | Upload and chunk a document into the vector store for future RAG retrieval. |

### How the AGENT node works (most important)

The `AGENT` node is the heart of most workflows. When configured, you set:

- **System Prompt** — the instructions given to the LLM (can include `{{variable}}` templates from upstream node outputs)
- **LLM Config** — provider (Azure OpenAI, Anthropic, etc.), model name, temperature
- **Tools** — a list of tool nodes wired to this agent (the LLM decides when to call them)
- **Memory** — whether to include conversation history
- **Review** — whether a human must approve before it continues (human-in-the-loop)

---

## Step 5 of 13 — Workflow Data Model

*How a workflow is stored — from database to Python objects*

Everything you draw on the canvas is eventually saved as **JSON in PostgreSQL**. Let's trace that from the database table all the way to the Python dataclass.

### Database tables (two tables per workflow)

> **`workflows` table — the container**
> Holds the logical workflow entity: its name, owner, sharing settings, and a pointer to the current version.

```python
# backend/models/workflows/workflow.py
class Workflow(Base):
    __tablename__ = "workflows"
    id                  = UUID          # primary key
    name                = String(255)   # "Invoice Reconciliation"
    description         = Text
    created_by_user_id  = ForeignKey("users.id")
    latest_version      = Integer       # tracks version number
    http_trigger_token  = String        # for API-triggered runs
```

> **`graph_definitions` table — the actual graph**
> Stores the versioned JSON of the entire graph. Every Save creates a new version row.

```python
# backend/models/workflows/graph_definition.py
class GraphDefinition(Base):
    __tablename__   = "graph_definitions"
    id              = UUID
    workflow_id     = ForeignKey("workflows.id")
    definition_json = JSON       # ← THE WHOLE GRAPH LIVES HERE
    version         = Integer    # 1, 2, 3…
    is_latest       = Boolean    # only one row is "latest"
    file_hash       = String(64) # SHA256 – change detection
```

### Python dataclasses — what `definition_json` maps to

When the backend loads a graph from DB, the JSON is deserialized into Python dataclasses:

```python
# GraphData – the top-level object
@dataclass
class GraphData:
    name: str                          # "Invoice Reconciliation"
    nodes: List[EnhancedNodeData]      # all nodes on canvas
    connections: List[Connection]      # all arrows between nodes
    workflow_id: Optional[str]

# EnhancedNodeData – a single node on the canvas
@dataclass
class EnhancedNodeData:
    uniq_id: str                              # unique node ID (e.g. "agent_001")
    name: str                                 # display name ("Summariser")
    type: NodeType                            # AGENT, CONDITION, HTTP_REQUEST…
    nexts: List[str]                          # IDs of connected downstream nodes
    position: Position                        # x, y on the canvas
    agent_config: Optional[AgentConfig]
    llm_config: Optional[LLMConfig]
    condition_config: Optional[ConditionConfig]
    tool_config: Optional[ToolConfig]
    mcp_config: Optional[MCPServerConfig]
```

### Configuration dataclasses

| Dataclass | Contains |
|---|---|
| **LLMConfig** | Provider (azure_openai, openai, anthropic), model name, temperature, max tokens |
| **AgentConfig** | System prompt, tools list, memory settings, review/approval config, output schema |
| **ConditionConfig** | Condition expression (LLM-evaluated or rule-based), branch target mapping |
| **MCPServerConfig** | MCP server URL, auth type, list of tool names to expose to the agent |

### What a real saved graph looks like (JSON excerpt)

```json
{
  "name": "Invoice Reconciliation",
  "nodes": [
    {
      "uniq_id": "start_001", "name": "START",
      "type": "START", "nexts": ["agent_001"],
      "position": {"x": 100, "y": 200}
    },
    {
      "uniq_id": "agent_001", "name": "Extract Invoice Data",
      "type": "AGENT", "nexts": ["db_001"],
      "llm_config": { "provider": "azure_openai", "model": "gpt-4o" },
      "agent_config": { "system_prompt": "Extract invoice number, amount..." }
    },
    {
      "uniq_id": "db_001", "name": "Query ERP Database",
      "type": "DATABASE_QUERY", "nexts": ["end_001"]
    }
  ]
}
```

> **See real examples**
> Open `examples/Account Unlock Investigation Orchestration_2026-04-08T14-18-36.json` for a full exported workflow with multiple agents, conditions, and tool nodes.

---

## Step 6 of 13 — The API Layer

*How the frontend talks to the backend (FastAPI routes)*

The backend is a **FastAPI** application. All HTTP endpoints are defined under `backend/api/` and grouped into 25+ modules by feature area.

### Application entry point

File: `backend/app.py` — this is where FastAPI starts, routers are registered, and middleware is applied (CORS, logging, auth, etc.).

### The thin-handler pattern

Every route follows the same pattern: routes are **thin HTTP wrappers** that immediately delegate to handler functions containing the actual business logic.

```python
# backend/api/graph/routes.py – THIN route
@router.get("/list")
async def list_graphs(current_user: Dict = Depends(get_current_user)):
    return await graph_crud.handle_list_graphs(current_user)
```

```python
# backend/api/graph/handlers/graph_crud.py – BUSINESS LOGIC
async def handle_list_graphs(current_user: Dict) -> Dict:
    user_id = get_user_identifier(current_user)
    graphs = get_graph_manager().list_graphs(user_id)
    return {"success": True, "graphs": graphs}
```

### Key graph API endpoints

| Method + Path | What it does |
|---|---|
| `GET /api/graph/list` | Returns all workflows for the logged-in user |
| `POST /api/graph/create` | Creates a new empty workflow |
| `GET /api/graph/{name}` | Loads a specific workflow (latest version) |
| `POST /api/graph/save` | Saves current graph JSON (creates new version) |
| `DELETE /api/graph/{name}` | Soft-deletes a workflow |
| `POST /api/graph/execute` | 🚀 Triggers execution — the big one |
| `POST /api/graph/stop/{id}` | Stops or pauses a running execution |
| `POST /api/graph/node/create` | Adds a node to the graph |
| `PUT /api/graph/node/update` | Updates node configuration |
| `DELETE /api/graph/node/delete` | Removes a node |
| `POST /api/graph/connection/create` | Adds an edge (arrow) between two nodes |

### Dependency Injection

All shared services (GraphManager, ExecutionEngine, etc.) are accessed via a central DI container — no service is instantiated directly in a route.

```python
# backend/services/dependency_injection/__init__.py
from backend.services.dependency_injection import (
    get_graph_manager,        # GraphManager instance
    get_execution_engine,     # ExecutionEngine instance
    get_execution_history_service,
)

# Usage in any handler or service
graph_mgr = get_graph_manager()
engine = get_execution_engine()
```

### Standard response format

| Type | Format |
|---|---|
| ✅ Success | `{"success": true, "message": "...", "data": {...}}` |
| ❌ Error | FastAPI `HTTPException` → `{"detail": "Error message"}` |

---

## Step 7 of 13 — Graph Building Pipeline

*How JSON becomes a live LangGraph StateGraph*

When you click **Run**, the backend loads your workflow JSON and runs it through a **build pipeline** that produces a LangGraph `StateGraph` — which is the actual executable AI program.

> **Key file:** `backend/services/graph/builder.py` — the `GraphBuilder` class contains `build()` which does all of this.

### The full build pipeline

1. **GraphData JSON** (from PostgreSQL) → Loaded from `graph_definitions` table
2. **`_analyze_nodes()`** (count agents, tools, conditions) → Determines complexity, enables optimizations
3. **StateGraph created** `StateGraph(WorkflowState)` → Empty LangGraph graph with our state schema
4. **Find START/END** (locate special nodes) → START sets the entry point; END collects output
5. **`_add_nodes()`** (register each node) → Each node → async Python function registered in StateGraph
6. **EdgeBuilder** `add_edges()` → Arrows → edges (normal, conditional, parallel)
7. **`compile()`** + PostgresCheckpointer → Returns compiled app — ready to stream-execute

### How a node becomes a Python function

```python
# builder.py – for an AGENT node
def create_node_function(node: EnhancedNodeData):
    async def node_fn(state: WorkflowState) -> WorkflowState:
        executor = NodeExecutorRegistry.get_executor(node.type)
        return await executor.execute(node, state, graph, execution_id)
    return node_fn

# Register as a LangGraph node
workflow.add_node(node.uniq_id, create_node_function(node))
```

### Edge types (EdgeBuilder)

File: `backend/services/graph/edge_builder.py`

| Edge type | When used | LangGraph call |
|---|---|---|
| Normal edge | A → B (simple flow) | `workflow.add_edge(a, b)` |
| Conditional edge | CONDITION node branching | `workflow.add_conditional_edges(src, fn, map)` |
| Parallel edges | Fan-out to multiple nodes | Multiple `add_edge` calls |
| Review loop | Human approval → continue | Agent → review → agent |

### PostgresCheckpointer — enabling pause/resume

> **Why this is powerful:**
> When you click Pause, LangGraph saves the complete workflow state to PostgreSQL (keyed by `execution_id`). When you click Resume, it loads that snapshot and continues exactly where it left off — even if days have passed.

---

## Step 8 of 13 — Node Execution Engine

*What happens when each node actually runs*

Once the graph is compiled, each node executes when LangGraph reaches it. Execution is handled by the **NodeExecutorRegistry** — a strategy pattern where every node type has a dedicated executor class.

### WorkflowState — the state flowing through every node

File: `backend/services/workflow/state/schemas.py`

Every node receives the full state and returns an updated slice of it. This is how data passes between nodes.

```python
class WorkflowState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    # ↑ LangChain message history (user, AI, tool messages)

    node_outputs: Annotated[Dict[str, NodeOutput], merge_node_outputs]
    # ↑ Each node's output – downstream nodes read from here

    results: Annotated[List[NodeResult], merge_results]
    current_node: Annotated[Optional[str], last_value_reducer]
    execution_id: str
    execution_order: Annotated[int, max_execution_order]
    metadata: Annotated[WorkflowMetadata, merge_metadata]
    memory_context: Optional[MemoryContext]              # conversation history
    orchestration_context: Optional[OrchestrationContext]
```

> **Template variables**
> When you write `{{agent_001.output}}` in a node's system prompt, it gets replaced with the actual output of node `agent_001` from `state.node_outputs` at runtime.

### NodeExecutorRegistry

File: `backend/services/nodes/registry.py`

```python
# Strategy pattern – register executor per node type
NodeExecutorRegistry.register(
    NodeType.AGENT,
    factory=lambda: AgentNodeExecutor(history_svc, ws_notifier)
)
NodeExecutorRegistry.register(NodeType.HTTP_REQUEST, factory=...)
NodeExecutorRegistry.register(NodeType.DATABASE_QUERY, factory=...)

# At runtime – called automatically by the graph
executor = NodeExecutorRegistry.get_executor(node.type)
result = await executor.execute(node, state, graph, execution_id)
```

### All executors

| Executor | Node type | What it does |
|---|---|---|
| `AgentNodeExecutor` | AGENT | Calls LLM via LangChain, handles tool calls, streams tokens |
| `ConditionNodeExecutor` | CONDITION | Evaluates condition expression, returns target branch ID |
| `HttpNodeExecutor` | HTTP_REQUEST | Makes HTTP call with configurable method/headers/body |
| `DatabaseNodeExecutor` | DATABASE_QUERY | Executes SQL, returns rows as structured data |
| `EmailNodeExecutor` | EMAIL_SEND | Sends email via SMTP/Outlook integration |
| `FileNodeExecutor` | FILE_READ | Reads file content from workspace |
| `CodeNodeExecutor` | CODE_EXECUTOR | Runs Python code in a sandboxed environment |
| `ForEachNodeExecutor` | FOR_EACH | Iterates a list, runs sub-nodes per element |
| `DocumentLoadNodeExecutor` | DOCUMENT_LOAD | Chunks + embeds document into pgvector |
| `ReviewNodeFunctionFactory` | REVIEW | Pauses execution, waits for human approval |

### Inside AgentNodeExecutor (step by step)

1. **Build input** — `InputBuilder` resolves all `{{variable}}` templates in the system prompt using values from `state.node_outputs`.
2. **Notify frontend — node is starting** — WebSocket event → `{ type: "node_update", status: "running" }` — the node on canvas starts pulsing.
3. **Call the LLM** — LangChain agent with bound tools executes. If the LLM decides to call a tool, the tool executor runs, result goes back to LLM, and it continues (tool loop).
4. **Phoenix auto-instruments the LLM call** — An OTel span is created with prompt, completion, token counts, and latency — exported to Phoenix.
5. **Record to database** — A `node_executions` row is inserted with input, output, duration, and status.
6. **Return state update** — `{"node_outputs": {"agent_001": {"raw": "...", "structured": {...}}}}` — merged into WorkflowState for downstream nodes.

---

## Step 9 of 13 — Real-time Streaming

*How you see progress on the canvas as it happens*

One of TADA Studio's key UX features is that you watch your workflow execute **live** — nodes light up as they run, outputs appear in real time. This is powered by **WebSockets**.

### WebSocket endpoint

File: `backend/api/websocket/execution.py`

```python
@execution_router.websocket("/api/ws/execution/{execution_id}")
async def websocket_execution(websocket: WebSocket, execution_id: str):
    await connection_manager.connect(websocket, execution_id)
    # Replay buffered events for reconnecting clients
    await buffer.replay_buffered_messages(execution_id, websocket)
    # Keep alive and forward live events
    async for message in live_event_stream:
        await websocket.send_json(message)
```

### The notifier — called at every execution event

File: `backend/services/websocket/notifier.py`

```python
# WebSocketExecutionNotifier – called by WorkflowExecutor
await ws_notifier.on_execution_start(execution_id, graph_name)
await ws_notifier.on_node_start(execution_id, node_id, node_name, node_type)
await ws_notifier.on_node_complete(execution_id, node_id, output, duration)
await ws_notifier.on_execution_complete(execution_id, result)
```

### WebSocket message types

| Event type | When sent | Frontend action |
|---|---|---|
| `started` | Execution begins | Shows "Running..." indicator |
| `node_update` (running) | Node starts | Node on canvas pulses / highlights |
| `node_update` (completed) | Node finishes | Node turns green, output shown in panel |
| `node_update` (failed) | Node errors | Node turns red, error shown |
| `completed` | Workflow finishes | ResultDrawer opens with final answer |
| `paused` | Checkpoint saved | UI shows "Paused — resume available" |
| `stopped` | User stopped it | UI resets |

### Message buffering (for reconnections)

> **Reconnect-safe:**
> All events are buffered for **60 seconds**. If your browser tab refreshes mid-execution, the WebSocket replays all buffered events on reconnect — so you never miss a node completing.

### LangGraph astream() — the execution loop

```python
# WorkflowExecutor._execute_streaming()
async for chunk in compiled_app.astream(
    initial_state,
    config={"configurable": {"thread_id": execution_id}}
):
    # chunk = state update from one node completing
    node_name = extract_node_name(chunk)

    await ws_notifier.on_node_start(execution_id, node_name, ...)
    # ... the node runs as part of astream() ...
    await ws_notifier.on_node_complete(execution_id, node_name, chunk[node_name])

    # Check for pause/stop signals between nodes
    if pause_requested:
        break  # checkpoint is automatic via PostgresCheckpointer
```

### Frontend: ExecutionPanelFinal

File: `frontend/src/components/panels/execution/ExecutionPanelFinal.tsx`

This component opens when you click Run. It:
- Connects to `wss://backend/api/ws/execution/{execution_id}`
- Renders a live timeline of node execution status
- Shows each node's output as it arrives
- Displays token counts and durations per node
- Links to the Phoenix trace for deep inspection

---

## Step 10 of 13 — Database & Persistence

*How everything gets stored — tables, ORM, and vector search*

TADA Studio uses **PostgreSQL 16 with pgvector** as its sole database. SQLAlchemy is the ORM. LangGraph also uses the same DB for its checkpoint system.

### Docker Compose database service

```yaml
# docker-compose.dev.yml
postgres:
  image: pgvector/pgvector:pg16   # pgvector enables vector similarity search
  ports: ["6666:5432"]
  environment:
    POSTGRES_DB: langgraph
    POSTGRES_USER: postgres
    POSTGRES_PASSWORD: postgres
```

### Key database tables

| Table | Model file | Stores |
|---|---|---|
| `workflows` | `models/workflows/workflow.py` | Workflow metadata (name, owner, trigger token) |
| `graph_definitions` | `models/workflows/graph_definition.py` | Versioned graph JSON (the actual workflow) |
| `graph_executions` | `models/execution/graph_execution.py` | Every run — status, input, output, timing |
| `node_executions` | (referenced in execution services) | Per-node execution records for each run |
| `users` | `models/auth/` | User accounts synced from Azure AD |
| `workflow_memberships` | `models/workflows/membership.py` | Sharing RBAC — owner/editor/viewer per workflow |
| `documents` | `models/documents/` | Uploaded documents metadata |
| `document_chunks` | (pgvector) | Vector embeddings — 1536-dim for RAG search |
| `system_settings` | | Runtime config (Phoenix toggle, model list…) |

### GraphExecution — full execution audit trail

```python
class GraphExecution(Base):
    id                      = UUID
    graph_id                = str          # which graph ran
    graph_name              = str
    graph_definition        = JSON         # snapshot of graph at time of run
    websocket_execution_id  = str          # for WebSocket correlation
    thread_id               = str          # LangGraph checkpoint key
    status                  = str          # running/completed/failed/paused
    start_time               = DateTime
    end_time                 = DateTime
    duration_seconds        = Float
    input_data                = JSON        # what the user sent
    output_data                = JSON        # final result + Phoenix trace link
    trigger_type              = str        # editor/api/evaluation/chat
    user_id                 = str
```

### pgvector — RAG (Document Search)

> **How RAG works in TADA:**
> 1. User uploads a PDF via DOCUMENT_LOAD node → document is chunked and each chunk is embedded (converted to a vector using an embedding model)
> 2. Vectors are stored in `document_chunks` with pgvector
> 3. DOCUMENT_SEARCH node receives a query string → embeds it → finds the top-K most similar chunks using cosine similarity
> 4. Results are passed to an AGENT node as context

### LangGraph checkpoints in PostgreSQL

LangGraph's `PostgresCheckpointer` creates its own tables (prefixed `checkpoints_*`) in the same database. This enables:
- **Pause** — serialize full WorkflowState to DB
- **Resume** — deserialize state, continue from next node
- **Human-in-loop** — wait indefinitely for human approval

---

## Step 11 of 13 — Infrastructure & Deployment

*From local Docker to production Kubernetes*

TADA Studio runs in two modes: local development via **Docker Compose**, and production via **Azure Kubernetes Service (AKS)**.

### Local development stack (docker-compose.dev.yml)

| Service | Port | Purpose |
|---|---|---|
| `postgres` | 6666:5432 | pgvector/pg16 — all application data |
| `postgres-init` | — | One-time job: creates the `phoenix` database |
| `backend` | 8880:8000 | FastAPI app with hot-reload (volume-mounted) |
| `frontend` | 3330:3000 | Next.js dev server with Turbopack |
| `llm-guard` | 8802:8002 | LLM Guard API — input/output safety scanning |

```bash
# Start everything locally
docker compose -f docker-compose.dev.yml up -d --build

# Access points:
# Frontend: http://localhost:3330
# Backend API: http://localhost:8880
# Database: localhost:6666 (postgres / postgres)
```

### Key environment variables (backend)

```
DEVELOPMENT_MODE=true
SKIP_AUTH=true                   # bypass Azure AD in dev
DEV_USER_EMAIL=dev@example.com   # dev user identity
ROOT_PATH=/api
LLM_GUARD_MODE=api
LOG_LEVEL=DEBUG
```

### Production architecture

**Internet** (Users' browser) → **Nginx** (Reverse proxy, TLS termination) → **OAuth2-Proxy** (Azure AD OIDC, JWT validation) → **FastAPI** (K8s pod, `agent-designer` ns)

### Kubernetes deployment

| Target | K8s context | Namespace |
|---|---|---|
| UAT | `SHAREDSERVICES-01-AKS-UAT` | `agent-designer` |
| Production | `SHAREDSERVICES-01-AKS-PROD` | `agent-designer` |

> **Deployment rule:**
> Always restart UAT first and confirm healthy before restarting production. See `docs/for-agents/RELEASE_AND_DEPLOYMENT.md` for full instructions.

### CI/CD Pipelines

| Pipeline | Details |
|---|---|
| **Backend** | `azure-pipelines-backend.yml` — runs Ruff linting, pytest tests, builds Docker image, pushes to ACR, triggers AKS rollout |
| **Frontend** | `azure-pipelines-frontend.yml` — runs ESLint/BiomeJS, type-check, npm build, builds Docker image, pushes to ACR |

### Nginx configuration

Nginx routes requests by path prefix:
- `/api/*` → proxied to FastAPI backend
- `/ws/*` → WebSocket upgrade to backend
- `/*` → served by Next.js frontend
- `/phoenix/*` → Arize Phoenix UI (port 6006)

---

## Step 12 of 13 — Auth & Observability

*Security, access control, and LLM trace monitoring*

### Authentication — two modes

| Mode | Details |
|---|---|
| **Production — Azure AD** | OAuth2-Proxy sits in front of all traffic. It validates Azure AD OIDC tokens and forwards trusted headers (`X-Auth-Request-Email`) to the backend. 7-day session cookies. |
| **Development — SKIP_AUTH** | Set `SKIP_AUTH=true` in `.env`. The backend returns a hardcoded dev user. No Azure AD required locally. |

```python
# backend/api/auth/dependencies.py
SKIP_AUTH = os.getenv("SKIP_AUTH", "false").lower() in {"1", "true"}

async def get_current_user(request: Request) -> Dict:
    if SKIP_AUTH:
        return {"email": DEV_USER_EMAIL, "name": DEV_USER_NAME}
    # Production: extract from X-Auth-Request-Email or JWT Bearer
    email = request.headers.get("X-Auth-Request-Email")
    return await sync_user_from_claims(email)
```

### RBAC — Workflow Sharing

The `workflow_memberships` table gives each user a role per workflow: `owner`, `editor`, `viewer`.

API endpoints use `require_workflow_access()` and `require_scope()` decorators to enforce these roles.

### Observability — Arize Phoenix

Every LLM call in TADA Studio is automatically traced using **OpenTelemetry** and exported to **Arize Phoenix** — an open-source LLM observability platform.

**Phoenix service files:**

| File | Purpose |
|---|---|
| `services/phoenix/config.py` | Reads Phoenix URL and enabled flag from DB/env |
| `services/phoenix/instrumentation.py` | OTel bootstrap — `GatedSpanExporter` wrapper |
| `services/phoenix/tracing.py` | Context managers for wrapping executions in root spans |
| `services/phoenix/evaluators.py` | Faithfulness, tool selection quality evaluators |
| `services/phoenix/dataset_sync.py` | Syncs execution data to Phoenix experiments |

### What gets traced per execution

```python
with phoenix_workflow_context(
    graph_name=graph.name,
    execution_id=execution_id,
    user_id=user_id,
):
    # Every LangChain / LLM call inside is auto-instrumented:
    # - Input messages + system prompt
    # - Output text + structured output
    # - Prompt token count + completion token count
    # - Model name and provider
    # - Tool call name + arguments (if tools were called)
    # - Latency per LLM call
    # - Errors with full stack trace
```

### Deep-link trace reference

After execution completes, a Phoenix trace deep-link is stored in `graph_executions.output_data`:

```python
result["phoenix_trace_ref"] = {
    "project": phoenix_ctx.project_name,
    "trace_id": phoenix_ctx.trace_id,
}
```

The frontend's execution panel shows a "View in Phoenix" button that opens this trace directly in the Phoenix UI (running on port 6006).

---

## Step 13 of 13 — E2E Flow — "Click Run"

*Every line of code that executes from button click to final output*

This is the full story — from the moment you click ▶ Run on the canvas to seeing your results in the browser. Follow along with the actual file references.

1. **User clicks Run**
   `CanvasTopBar.tsx` → `onRun()` fires.
   Frontend calls `POST /api/graph/execute` with `{ graph_name, initial_input }`.
   Simultaneously opens WebSocket: `wss://backend/api/ws/execution/{new_execution_id}`

2. **Auth validation**
   FastAPI `Depends(require_active_user)` runs. Validates JWT Bearer token or oauth2-proxy headers.
   In dev: `SKIP_AUTH=true` passes through immediately.

3. **`execution.handle_execute_graph()`**
   `backend/api/graph/handlers/execution.py`
   Generates `execution_id` (format: `exec_TIMESTAMP_GRAPHNAME`).
   Loads graph from DB via `get_graph_manager().get_graph(name, user_id)`.
   Fires `asyncio.create_task(engine.execute_graph(...))` — **returns immediately** to the HTTP caller.
   Response: `{"success": true, "execution_id": "exec_..."}`

4. **ExecutionEngine → WorkflowExecutor**
   `backend/services/execution/engine.py` delegates to `backend/services/execution/workflow_executor.py`.
   The 6-phase execution lifecycle begins.

5. **Phase 1 — Initialize Execution Context**
   `ExecutionHistoryService.create_graph_execution()` → INSERT into `graph_executions` table.
   `active_executions[execution_id] = {status: "running"}` stored in memory.
   `ws_notifier.on_execution_start()` → WebSocket: `{type: "started"}`
   → Frontend: "Running..." indicator appears.

6. **Phase 1.5 — Guardrails Check**
   If the workflow has safety policies: `GuardrailsEngine.resolve_unified(workflow_id)`.
   Input is sent to LLM Guard API (port 8802) for content scanning.
   If flagged → execution fails with a guardrail violation message.

7. **Phase 2 — Process START Node**
   Finds the START node in the graph. Extracts `initial_input`.
   Emits `on_node_start` / `on_node_complete` for START node.
   → Frontend: START node turns green on canvas.

8. **Phase 3 — Build & Compile Graph**
   `backend/services/graph/builder.py` → `GraphBuilder.build()`
   1. Analyze nodes → 2. Create StateGraph → 3. Find START/END → 4. Add nodes → 5. Add edges (EdgeBuilder) → 6. Compile with PostgresCheckpointer.
   Returns a compiled LangGraph app ready to stream.

9. **Phase 4 — Execute Streaming (the main loop)**
   Wrapped in `phoenix_root_span()` for OTel tracing.
   For each node in the execution order:
   - `ws_notifier.on_node_start()` → Frontend: node pulses/highlights
   - `NodeExecutorRegistry.get_executor(type).execute(node, state)` runs:
     - AGENT: InputBuilder → resolve templates → LLM call → (tool loop if tools called) → parse output
     - CONDITION: evaluate expression → return branch target
     - HTTP: make HTTP request → return response
     - All LLM calls → Phoenix auto-instruments → OTel span exported
   - `ws_notifier.on_node_complete(output)` → Frontend: node turns green, output shown
   - `ExecutionHistoryService` records NodeExecution row in DB

10. **Phase 5 — Handle Control**
    If **Pause**: `asyncio.Task` is cancelled. LangGraph checkpoint saved to PostgreSQL. Status → "paused".
    If **Stop**: Task cancelled. Status → "stopped".
    If **Guardrail violation mid-run**: Status → "failed".
    If **Human Review node**: Execution waits indefinitely for approval WebSocket message.

11. **Phase 6 — Finalize Execution**
    END node output extracted via `FinalOutputExtractor`.
    `ExecutionHistoryService.update_graph_execution(status="completed", output_data=...)`
    Phoenix trace deep-link built and stored in `output_data`.
    `ws_notifier.on_execution_complete(result)` → WebSocket: `{type: "completed"}`

12. **Frontend shows results**
    `ResultDrawer.tsx` opens with the final answer.
    `ExecutionPanelFinal.tsx` shows per-node timeline with durations and token counts.
    User can click any node to inspect its exact input/output.
    "View in Phoenix" button links to the full LLM trace.

13. **Post-execution (if chat mode)**
    If triggered from the Chat interface: `ChatMemoryService.store_chat_memory()` saves the conversation turn for future context.

### Quick Reference — Key files for E2E

**Frontend**

| Purpose | File |
|---|---|
| Canvas editor | `components/core/AgentBuilder.tsx` |
| Run button | `components/core/CanvasTopBar.tsx` |
| Live execution panel | `panels/execution/ExecutionPanelFinal.tsx` |
| Result display | `panels/result/ResultDrawer.tsx` |
| Node components | `components/nodes/` |

**Backend — API**

| Purpose | File |
|---|---|
| FastAPI app | `backend/app.py` |
| Graph routes | `api/graph/routes.py` |
| Execute handler | `api/graph/handlers/execution.py` |
| WebSocket endpoint | `api/websocket/execution.py` |

**Backend — Services**

| Purpose | File |
|---|---|
| Graph builder | `services/graph/builder.py` |
| Edge builder | `services/graph/edge_builder.py` |
| Execution engine | `services/execution/engine.py` |
| Workflow executor | `services/execution/workflow_executor.py` |
| Node registry | `services/nodes/registry.py` |
| WS notifier | `services/websocket/notifier.py` |

**Models & Infra**

| Purpose | File |
|---|---|
| Workflow state | `services/workflow/state/schemas.py` |
| Graph data model | `models/workflow/graph.py` |
| Execution model | `models/execution/graph_execution.py` |
| Dev compose | `docker-compose.dev.yml` |
| Auth config | `oauth2-proxy.cfg` |

> **You've completed the guide!**
> You now understand TADA Studio end-to-end — from drawing a node on the canvas to watching it execute via LangGraph and stream results back over WebSocket. The best next step is to open the codebase and trace the `POST /api/graph/execute` flow yourself, starting at `backend/api/graph/handlers/execution.py`.

---

*(Document complete — all 13 steps of the TADA Studio onboarding guide transcribed.)*
