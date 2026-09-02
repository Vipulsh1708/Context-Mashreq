# Architecture Diagrams

This document provides detailed visual representations of Agentic Studio's architecture, showing how components interact and
data flows through the system.

## System Context Diagram

```text
┌──────────────────────────────────────────────────────────────────┐
│                          External Users                          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│  │   Workflow   │  │    System    │  │   Business   │            │
│  │   Builders   │  │  Integrators │  │    Users     │            │
│  └──────────────┘  └──────────────┘  └──────────────┘            │
└───────────────┬───────────────┬────────────────┬─────────────────┘
                │               │                │
                │   Browser     │   HTTP/REST    │   API Clients
                │               │                │
┌───────────────▼───────────────▼────────────────▼────────────────┐
│                                                                 │
│                    Agentic Studio Platform                       │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐     │
│  │              Frontend (Next.js + React)                │     │
│  │  • Visual Workflow Builder (ReactFlow)                 │     │
│  │  • Execution Monitoring                                │     │
│  │  • User Management                                     │     │
│  └──────────────────────┬─────────────────────────────────┘     │
│                         │ HTTP + WebSocket                      │
│  ┌──────────────────────▼─────────────────────────────────┐     │
│  │              Backend (FastAPI + Python)                │     │
│  │  • REST APIs (20+ modules)                             │     │
│  │  • WebSocket Servers                                   │     │
│  │  • Business Logic (30+ services)                       │     │
│  └──────────────────────┬─────────────────────────────────┘     │
│                         │                                       │
│  ┌──────────────────────▼─────────────────────────────────┐     │
│  │              Data Layer (PostgreSQL)                   │     │
│  │  • Graph Definitions                                   │     │
│  │  • Execution History                                   │     │
│  │  • User Data                                           │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                 │
└────────────┬──────────────┬──────────────┬──────────────────────┘
             │              │              │
    ┌────────▼──────┐  ┌───▼────────┐  ┌──▼─────────────┐
    │  LLM Services │  │  External  │  │     Email      │
    │  Azure OpenAI │  │    APIs    │  │   Providers    │
    │    OpenAI     │  │  Search    │  │   Outlook      │
    │   Anthropic   │  │  Document  │  │    MailSlurp   │
    │               │  │    MCP     │  |    MailGun     │
    └───────────────┘  └────────────┘  └────────────────┘
```

## Backend Component Architecture

```text
┌────────────────────────────────────────────────────────────────────┐
│                         Backend Application                        │
│                                                                    │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                    API Layer (backend/api/)                   │ │
│  │                                                               │ │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐        │ │
│  │  │    Graph    │  │   Execution  │  │ HTTP Execution │        │ │
│  │  │   (CRUD)    │  │  (History)   │  │   (Streaming)  │        │ │
│  │  └─────────────┘  └──────────────┘  └────────────────┘        │ │
│  │                                                               │ │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐        │ │
│  │  │    Auth     │  │   Documents  │  │   Datasources  │        │ │
│  │  │   (OAuth)   │  │   (Upload)   │  │   (Connect)    │        │ │
│  │  └─────────────┘  └──────────────┘  └────────────────┘        │ │
│  │                                                               │ │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐        │ │
│  │  │    Email    │  │    Memory    │  │   Monitoring   │        │ │
│  │  │(Checkpoints)│  │ (Conversatn) │  │    (Health)    │        │ │
│  │  └─────────────┘  └──────────────┘  └────────────────┘        │ │
│  │                                                               │ │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐        │ │
│  │  │    Trace    │  │   Workflow   │  │   WebSocket    │        │ │
│  │  │ (LangSmith) │  │  (Publish)   │  │   (Realtime)   │        │ │
│  │  └─────────────┘  └──────────────┘  └────────────────┘        │ │
│  │                                                               │ │
│  │  + 10 more modules (tools, wiki, checkpoints, etc.)           │ │
│  └─────────────────────────┬─────────────────────────────────────┘ │
│                            │                                       │
│                            │ Direct Function Calls                 │
│                            │                                       │
│  ┌─────────────────────────▼─────────────────────────────────────┐ │
│  │              Services Layer (backend/services/)               │ │
│  │                                                               │ │
│  │  ┌───────────────────────────────────────────────────────┐    │ │
│  │  │         Core Services (Dependency Injected)           │    │ │
│  │  │  ┌─────────────────┐  ┌──────────────────────────┐    │    │ │
│  │  │  │  GraphManager   │  │   ExecutionEngine        │    │    │ │
│  │  │  │  (Singleton)    │  │   (Singleton)            │    │    │ │
│  │  │  └─────────────────┘  └──────────────────────────┘    │    │ │
│  │  └───────────────────────────────────────────────────────┘    │ │
│  │                                                               │ │
│  │  ┌───────────────────────────────────────────────────────┐    │ │
│  │  │          Domain Services (30+ modules)                │    │ │
│  │  │                                                       │    │ │
│  │  │  Execution Domain:                                    │    │ │
│  │  │  ├─ execution/state    - State tracking               │    │ │
│  │  │  ├─ execution/paused   - Pause/resume                 │    │ │
│  │  │  ├─ execution/history  - Execution records            │    │ │
│  │  │  ├─ execution/nodes    - Node executors               │    │ │
│  │  │  └─ execution/agent    - Agent execution              │    │ │
│  │  │                                                       │    │ │
│  │  │  Graph Domain:                                        │    │ │
│  │  │  ├─ graph/storage      - DB persistence               │    │ │
│  │  │  ├─ graph/tools        - Tool management              │    │ │
│  │  │  └─ graph/agent_tools  - Agent tool binding           │    │ │
│  │  │                                                       │    │ │
│  │  │  Document Domain:                                     │    │ │
│  │  │  ├─ document/processors - File processing             │    │ │
│  │  │  ├─ document/formatters - Format conversion           │    │ │
│  │  │  └─ document/cache      - Processing cache            │    │ │
│  │  │                                                       │    │ │
│  │  │  Email Domain:                                        │    │ │
│  │  │  ├─ email/providers    - Provider abstraction         │    │ │
│  │  │  ├─ email/polling      - Background checking          │    │ │
│  │  │  └─ email/manager      - High-level operations        │    │ │
│  │  │                                                       │    │ │
│  │  │  Infrastructure:                                      │    │ │
│  │  │  ├─ database          - ORM & sessions                │    │ │
│  │  │  ├─ config            - Configuration mgmt            │    │ │
│  │  │  ├─ dependency_injection - DI container               │    │ │
│  │  │  ├─ memory            - Conversation memory           │    │ │
│  │  │  ├─ metrics           - Telemetry collection          │    │ │
│  │  │  └─ trace             - LangSmith integration         │    │ │
│  │  │                                                       │    │ │
│  │  │  + 15 more domains (see services directory)           │    │ │
│  │  └───────────────────────────────────────────────────────┘    │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

## Workflow Execution Architecture

```text
┌───────────────────────────────────────────────────────────────────┐
│                    Workflow Execution System                      │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │           Execution Entry Points (API Layer)                │  │
│  │                                                             │  │
│  │  ┌──────────────┐  ┌───────────────┐  ┌────────────────┐  │ │  │
│  │  │   HTTP Sync  │  │  HTTP Async   │  │   WebSocket    │  │ │  │
│  │  │   (Blocking) │  │  (Background) │  │   (Streaming)  │  │ │  │
│  │  └──────┬───────┘  └───────┬───────┘  └────────┬───────┘  │ │  │
│  └─────────┼──────────────────┼───────────────────┼──────────┘ │  │
│            │                  │                   │            │  │
│            └──────────────────┼───────────────────┘            │  │
│                               │                                │  │
│  ┌─────────────────────────────▼──────────────────────────────┐ │ │
│  │              ExecutionEngine (Core Service)                │ │ │
│  │                                                            │ │ │
│  │  • Validates workflow definition                           │ │ │
│  │  • Initialises execution context                           │ │ │
│  │  • Builds LangGraph state machine                          │ │ │
│  │  • Manages execution lifecycle                             │ │ │
│  └─────────────────────────────┬──────────────────────────────┘ │ │
│                                │                                │ │
│  ┌─────────────────────────────▼──────────────────────────────┐ │ │
│  │              LangGraph StateGraph Engine                   │ │ │
│  │                                                            │ │ │ 
│  │  ┌─────────────┐         ┌─────────────┐                   │ │ │
│  │  │   Nodes     │────────▶│    State    │                   │ │ │
│  │  │  Execution  │         │  Management │                   │ │ │
│  │  └─────────────┘         └─────────────┘                   │ │ │
│  │         │                       │                          │ │ │
│  │         │                       │                          │ │ │
│  │  ┌──────▼────────┐       ┌─────▼────────┐                  │ │ │
│  │  │   Edges &     │       │ Checkpointer │                  │ │ │
│  │  │  Conditions   │       │  (Postgres)  │                  │ │ │
│  │  └───────────────┘       └──────────────┘                  │ │ │
│  └─────────────────────────────┬──────────────────────────────┘ │ │
│                                │                                │ │
│  ┌─────────────────────────────▼──────────────────────────────┐ │ │
│  │              Node Executors (Services Layer)               │ │ │
│  │                                                             │ │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────┐       │ │
│  │  │   Agent    │  │    Tool    │  │   Condition    │       │ │
│  │  │  Executor  │  │  Executor  │  │   Evaluator    │       │ │
│  │  └─────┬──────┘  └─────┬──────┘  └────────┬───────┘       │ │
│  └────────┼───────────────┼──────────────────┼───────────────┘ │
│           │               │                  │                 │
│  ┌────────▼───────────────▼──────────────────▼───────────────┐ │
│  │              External Integrations                         │ │
│  │                                                             │ │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────┐       │ │
│  │  │    LLMs    │  │   Tools    │  │   Email/API    │       │ │
│  │  │ OpenAI etc │  │ Search etc │  │   Callbacks    │       │ │
│  │  └────────────┘  └────────────┘  └────────────────┘       │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              Persistence & Monitoring                       │ │
│  │                                                             │ │
│  │  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐ │ │
│  │  │   Execution    │  │   Checkpoints  │  │   Traces     │ │ │
│  │  │    History     │  │   (State)      │  │ (LangSmith)  │ │ │
│  │  │  (PostgreSQL)  │  │  (PostgreSQL)  │  │   (Cloud)    │ │ │
│  │  └────────────────┘  └────────────────┘  └──────────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

## Node Execution Pipeline

```
┌────────────────────────────────────────────────────────────┐
│                  Node Execution Flow                       │
│                                                            │
│  1. Graph Traversal                                        │
│     ┌──────────────────────────────────────────┐          │
│     │  LangGraph determines next node          │          │
│     │  based on edges and conditions           │          │
│     └─────────────────┬────────────────────────┘          │
│                       │                                    │
│  2. Pre-Execution                                          │
│     ┌─────────────────▼────────────────────────┐          │
│     │  • Extract node configuration            │          │
│     │  • Load node-specific settings           │          │
│     │  • Prepare execution context             │          │
│     └─────────────────┬────────────────────────┘          │
│                       │                                    │
│  3. Node Type Dispatch                                     │
│     ┌─────────────────▼────────────────────────┐          │
│     │  Route to appropriate executor:          │          │
│     │  ┌──────────────────────────────────┐   │          │
│     │  │ AGENT → AgentExecutor            │   │          │
│     │  │ TOOL → ToolExecutor               │   │          │
│     │  │ CONDITION → ConditionEvaluator    │   │          │
│     │  │ START/END → PassthroughExecutor   │   │          │
│     │  │ HUMAN → HumanInLoopExecutor       │   │          │
│     │  │ SUBGRAPH → SubgraphExecutor       │   │          │
│     │  └──────────────────────────────────┘   │          │
│     └─────────────────┬────────────────────────┘          │
│                       │                                    │
│  4. Executor Logic                                         │
│     ┌─────────────────▼────────────────────────┐          │
│     │  • Execute node-specific logic           │          │
│     │  • Call external APIs/LLMs               │          │
│     │  • Process inputs and generate outputs   │          │
│     │  • Handle errors and retries             │          │
│     └─────────────────┬────────────────────────┘          │
│                       │                                    │
│  5. State Update                                           │
│     ┌─────────────────▼────────────────────────┐          │
│     │  • Merge execution results into state    │          │
│     │  • Update node execution history         │          │
│     │  • Emit execution events                 │          │
│     └─────────────────┬────────────────────────┘          │
│                       │                                    │
│  6. Checkpoint (Optional)                                  │
│     ┌─────────────────▼────────────────────────┐          │
│     │  • Persist state snapshot to database    │          │
│     │  • Enable pause/resume capability        │          │
│     │  • Support time-travel debugging         │          │
│     └─────────────────┬────────────────────────┘          │
│                       │                                    │
│  7. Next Node Selection                                    │
│     ┌─────────────────▼────────────────────────┐          │
│     │  • Evaluate edge conditions              │          │
│     │  • Determine routing based on state      │          │
│     │  • Continue or terminate execution       │          │
│     └──────────────────────────────────────────┘          │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

## Data Storage Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     PostgreSQL Database                         │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │              Graph Management Schema                      │ │
│  │                                                           │ │
│  │  workflows                                                │ │
│  │  ├─ id (PK)                                               │ │
│  │  ├─ name                                                  │ │
│  │  ├─ description                                           │ │
│  │  ├─ user_id                                               │ │
│  │  ├─ created_at / updated_at                              │ │
│  │  └─ is_public                                            │ │
│  │                                                           │ │
│  │  graph_versions                                           │ │
│  │  ├─ id (PK)                                               │ │
│  │  ├─ workflow_id (FK)                                      │ │
│  │  ├─ version_number                                        │ │
│  │  ├─ graph_data (JSONB) - Full graph definition           │ │
│  │  ├─ created_at                                           │ │
│  │  └─ created_by                                           │ │
│  │                                                           │ │
│  │  shared_graphs                                            │ │
│  │  ├─ id (PK)                                               │ │
│  │  ├─ workflow_id (FK)                                      │ │
│  │  ├─ shared_with_user_id                                   │ │
│  │  └─ permission_level                                      │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │           Execution History Schema                        │ │
│  │                                                           │ │
│  │  execution_records                                        │ │
│  │  ├─ id (PK)                                               │ │
│  │  ├─ workflow_id (FK)                                      │ │
│  │  ├─ graph_version_id (FK)                                 │ │
│  │  ├─ thread_id - LangGraph thread                          │ │
│  │  ├─ status (running/completed/failed/paused)             │ │
│  │  ├─ started_at / completed_at                            │ │
│  │  ├─ input_data (JSONB)                                    │ │
│  │  ├─ output_data (JSONB)                                   │ │
│  │  ├─ error_message                                         │ │
│  │  └─ metrics (JSONB) - tokens, duration, etc.             │ │
│  │                                                           │ │
│  │  execution_events                                         │ │
│  │  ├─ id (PK)                                               │ │
│  │  ├─ execution_id (FK)                                     │ │
│  │  ├─ node_id                                               │ │
│  │  ├─ event_type (node_start/node_end/error)               │ │
│  │  ├─ event_data (JSONB)                                    │ │
│  │  └─ timestamp                                             │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │         LangGraph Checkpoint Schema                       │ │
│  │         (Managed by langgraph-checkpoint-postgres)        │ │
│  │                                                           │ │
│  │  checkpoints                                              │ │
│  │  ├─ thread_id                                             │ │
│  │  ├─ checkpoint_ns                                         │ │
│  │  ├─ checkpoint_id                                         │ │
│  │  ├─ parent_checkpoint_id                                  │ │
│  │  ├─ type (checkpoint/checkpoint_v2)                       │ │
│  │  ├─ checkpoint (BYTEA) - Serialised state                │ │
│  │  └─ metadata (JSONB)                                      │ │
│  │                                                           │ │
│  │  checkpoint_writes                                        │ │
│  │  ├─ thread_id                                             │ │
│  │  ├─ checkpoint_ns                                         │ │
│  │  ├─ checkpoint_id                                         │ │
│  │  ├─ task_id                                               │ │
│  │  ├─ idx                                                   │ │
│  │  ├─ channel                                               │ │
│  │  ├─ type                                                  │ │
│  │  └─ value (BYTEA)                                         │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │              Memory & State Schema                        │ │
│  │                                                           │ │
│  │  conversation_memory                                      │ │
│  │  ├─ id (PK)                                               │ │
│  │  ├─ thread_id                                             │ │
│  │  ├─ node_id                                               │ │
│  │  ├─ memory_data (JSONB) - Conversation history           │ │
│  │  ├─ token_count                                           │ │
│  │  ├─ created_at / updated_at                              │ │
│  │  └─ pruned_at                                            │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │           Model Deployment Schema                         │ │
│  │                                                           │ │
│  │  model_deployments                                        │ │
│  │  ├─ id (PK)                                               │ │
│  │  ├─ name                                                  │ │
│  │  ├─ provider (azure/openai/anthropic)                    │ │
│  │  ├─ model_name                                            │ │
│  │  ├─ encrypted_credentials (TEXT)                          │ │
│  │  ├─ user_id                                               │ │
│  │  └─ created_at / updated_at                              │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Communication Patterns

```
┌──────────┐                                          ┌──────────┐
│  Client  │                                          │  Server  │
└────┬─────┘                                          └────┬─────┘
     │                                                     │
     │  POST /api/graph/graphs                            │
     │  { "name": "My Workflow", ... }                    │
     │────────────────────────────────────────────────────▶│
     │                                                     │
     │                                   [Create Graph]   │
     │                                   [Store in DB]    │
     │                                                     │
     │  201 Created                                        │
     │  { "id": "abc123", "name": "My Workflow" }         │
     │◀────────────────────────────────────────────────────│
     │                                                     │
     │  POST /api/graph/execute                            │
     │  { "graph_id": "abc123", "input": {...} }          │
     │────────────────────────────────────────────────────▶│
     │                                                     │
     │                                   [Execute Sync]   │
     │                                   [Wait Complete]  │
     │                                                     │
     │  200 OK                                             │
     │  { "result": {...}, "duration": 3.4 }              │
     │◀────────────────────────────────────────────────────│
     │                                                     │
```

### WebSocket Streaming Communication

```
┌──────────┐                                          ┌──────────┐
│  Client  │                                          │  Server  │
└────┬─────┘                                          └────┬─────┘
     │                                                     │
     │  WS Connect /api/websocket/execute                  │
     │────────────────────────────────────────────────────▶│
     │                                                     │
     │  Connection Established                             │
     │◀────────────────────────────────────────────────────│
     │                                                     │
     │  { "action": "execute", "graph_id": "abc123" }      │
     │────────────────────────────────────────────────────▶│
     │                                                     │
     │                           [Start Execution]        │
     │                                                     │
     │  { "event": "node_start", "node": "agent_1" }       │
     │◀────────────────────────────────────────────────────│
     │                                                     │
     │  { "event": "token_stream", "token": "Hello" }      │
     │◀────────────────────────────────────────────────────│
     │                                                     │
     │  { "event": "token_stream", "token": " World" }     │
     │◀────────────────────────────────────────────────────│
     │                                                     │
     │  { "event": "node_end", "node": "agent_1" }         │
     │◀────────────────────────────────────────────────────│
     │                                                     │
     │  { "event": "execution_complete", "result": {...} } │
     │◀────────────────────────────────────────────────────│
     │                                                     │
     │  Close Connection                                   │
     │────────────────────────────────────────────────────▶│
     │                                                     │
```

### Server-Sent Events (SSE) Communication

```
┌──────────┐                                          ┌──────────┐
│  Client  │                                          │  Server  │
└────┬─────┘                                          └────┬─────┘
     │                                                     │
     │  GET /api/http-execution/stream/{token}             │
     │  Accept: text/event-stream                          │
     │────────────────────────────────────────────────────▶│
     │                                                     │
     │                           [Start Streaming]        │
     │                                                     │
     │  data: {"event": "node_start", "node": "agent_1"}   │
     │  id: 1                                              │
     │◀────────────────────────────────────────────────────│
     │                                                     │
     │  data: {"event": "token", "token": "Processing..."}│
     │  id: 2                                              │
     │◀────────────────────────────────────────────────────│
     │                                                     │
     │  data: {"event": "node_end", "result": {...}}      │
     │  id: 3                                              │
     │◀────────────────────────────────────────────────────│
     │                                                     │
     │  data: {"event": "complete"}                        │
     │  id: 4                                              │
     │◀────────────────────────────────────────────────────│
     │                                                     │
     │  [Connection closed by server]                      │
     │                                                     │
```

## Dependency Injection Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│           Dependency Injection Container                        │
│         (backend/services/dependency_injection/)                │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                    Container Initialisation                │ │
│  │                                                            │ │
│  │  At Application Startup (app.py lifespan):                │ │
│  │                                                            │ │
│  │  initialize_dependencies()                                 │ │
│  │      │                                                     │ │
│  │      ├──▶ Create GraphManager                              │ │
│  │      │       ├─ Load graph storage config                 │ │
│  │      │       ├─ Initialize filesystem storage             │ │
│  │      │       └─ Register tool factories                    │ │
│  │      │                                                     │ │
│  │      └──▶ Create ExecutionEngine                           │ │
│  │            ├─ Initialize checkpointer (Postgres/Memory)    │ │
│  │            ├─ Set up LangGraph configuration              │ │
│  │            └─ Configure execution context                  │ │
│  │                                                            │ │
│  │  Store in thread-safe singleton container                 │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                  Usage Patterns                            │ │
│  │                                                            │ │
│  │  1. Direct Access (for non-FastAPI code):                 │ │
│  │     ┌──────────────────────────────────────────────┐      │ │
│  │     │ from backend.services.dependency_injection   │      │ │
│  │     │     import get_graph_manager                │      │ │
│  │     │                                              │      │ │
│  │     │ graph_mgr = get_graph_manager()              │      │ │
│  │     │ graphs = graph_mgr.list_graphs()             │      │ │
│  │     └──────────────────────────────────────────────┘      │ │
│  │                                                            │ │
│  │  2. FastAPI Dependency Injection:                          │ │
│  │     ┌──────────────────────────────────────────────┐      │ │
│  │     │ from backend.services.dependency_injection   │      │ │
│  │     │     import GraphManager                      │      │ │
│  │     │                                              │      │ │
│  │     │ @router.get("/graphs")                        │      │ │
│  │     │ async def list_graphs(                        │      │ │
│  │     │     graph_mgr: GraphManager                  │      │ │
│  │     │ ):                                           │      │ │
│  │     │     return graph_mgr.list_graphs()            │      │ │
│  │     └──────────────────────────────────────────────┘      │ │
│  │                                                            │ │
│  │  Benefits:                                                 │ │
│  │  • Single instance across application                     │ │
│  │  • Thread-safe access                                     │ │
│  │  • Easy mocking for tests                                 │ │
│  │  • Type-safe with Protocol definitions                    │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Security Layers                             │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │              Layer 1: Network & Transport                 │ │
│  │                                                           │ │
│  │  • HTTPS/TLS for all HTTP traffic                        │ │
│  │  • WSS (WebSocket Secure) for WebSocket connections      │ │
│  │  • CORS middleware with origin validation                │ │
│  └───────────────────────────────────────────────────────────┘ │
│                             │                                   │
│                             ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │           Layer 2: Authentication (OAuth2-Proxy)          │ │
│  │                                                           │ │
│  │  OAuth2-Proxy (Nginx reverse proxy)                       │ │
│  │  ├─ Azure AD integration                                  │ │
│  │  ├─ JWT token validation                                  │ │
│  │  ├─ Session management                                    │ │
│  │  └─ User header injection (X-Forwarded-User, etc.)        │ │
│  └───────────────────────────────────────────────────────────┘ │
│                             │                                   │
│                             ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │              Layer 3: Authorisation (Backend)             │ │
│  │                                                           │ │
│  │  API Layer (FastAPI)                                       │ │
│  │  ├─ Extract user from auth headers                        │ │
│  │  ├─ Resolve user ID                                       │ │
│  │  ├─ Verify resource ownership                             │ │
│  │  └─ Check permissions (read/write/execute)                │ │
│  │                                                           │ │
│  │  Storage Layer                                            │ │
│  │  ├─ User-scoped queries (WHERE user_id = ?)               │ │
│  │  ├─ Shared resource validation                            │ │
│  │  └─ Access control lists                                  │ │
│  └───────────────────────────────────────────────────────────┘ │
│                             │                                   │
│                             ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │            Layer 4: Data Protection                       │ │
│  │                                                           │ │
│  │  Credential Encryption                                    │ │
│  │  ├─ AES-256 encryption for LLM API keys                   │ │
│  │  ├─ Per-user encryption keys                              │ │
│  │  └─ Secure key derivation (PBKDF2)                        │ │
│  │                                                           │ │
│  │  Database Security                                        │ │
│  │  ├─ PostgreSQL SSL connections                            │ │
│  │  ├─ Parameterised queries (SQL injection prevention)      │ │
│  │  └─ Row-level security (user_id filtering)                │ │
│  │                                                           │ │
│  │  Environment Secrets                                      │ │
│  │  ├─ .env file for local development                       │ │
│  │  └─ Environment variables for production                  │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Production Deployment                        │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                  Nginx / OAuth2-Proxy                     │ │
│  │  • SSL termination                                        │ │
│  │  • Authentication gateway                                 │ │
│  │  • Static file serving (frontend build)                   │ │
│  │  • Reverse proxy to backend                               │ │
│  └─────────────────────┬─────────────────────────────────────┘ │
│                        │                                        │
│         ┌──────────────┴────────────────┐                      │
│         │                               │                      │
│  ┌──────▼──────────┐           ┌───────▼────────────┐         │
│  │   Next.js App   │           │   FastAPI Backend  │         │
│  │   (SSR/SSG)     │           │   (Uvicorn)        │         │
│  │                 │           │                    │         │
│  │  • Port 3000    │           │  • Port 8000       │         │
│  │  • React UI     │           │  • API endpoints   │         │
│  │  • Server       │           │  • WebSocket srv   │         │
│  │    rendering    │           │  • Background      │         │
│  └─────────────────┘           │    tasks           │         │
│                                 └──────┬─────────────┘         │
│                                        │                       │
│  ┌─────────────────────────────────────▼────────────────────┐ │
│  │              PostgreSQL Database                         │ │
│  │  • Primary data store                                    │ │
│  │  • Connection pooling                                    │ │
│  │  • Automated backups                                     │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                  External Services                       │ │
│  │                                                          │ │
│  │  ┌────────────┐  ┌────────────┐  ┌───────────────┐     │ │
│  │  │    LLMs    │  │   Email    │  │   LangSmith   │     │ │
│  │  │  (Azure)   │  │ (Mailgun)  │  │   (Traces)    │     │ │
│  │  └────────────┘  └────────────┘  └───────────────┘     │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Related Documentation

- [00-overview.md](./00-overview.md) - System overview and tech stack
- [02-data-flow.md](./02-data-flow.md) - Detailed data flow scenarios
- [03-design-principles.md](./03-design-principles.md) - Architectural decisions
