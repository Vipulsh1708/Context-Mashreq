# Data Flow Patterns

This document describes how data flows through the Agentic Studio system for common operations, from user interaction through
to data persistence and external API calls.

## Overview

Agentic Studio implements several data flow patterns depending on the operation type:

- **CRUD Operations** - Synchronous request/response for managing workflows
- **Workflow Execution** - Asynchronous, stateful execution with multiple communication patterns
- **Document Processing** - Pipeline-based transformation with caching
- **Real-time Streaming** - WebSocket and SSE for live updates

## Common Data Flow Patterns

### Pattern 1: Standard CRUD Operation

**Use Case:** Creating or updating a workflow definition

```
┌──────────┐                                                ┌──────────┐
│  Client  │                                                │ Backend  │
└────┬─────┘                                                └────┬─────┘
     │                                                           │
     │ 1. HTTP Request                                           │
     │    POST /api/graph/graphs                                 │
     │    Content-Type: application/json                         │
     │    {                                                      │
     │      "name": "Customer Support Workflow",                 │
     │      "description": "Automated support triage"            │
     │    }                                                      │
     │──────────────────────────────────────────────────────────▶│
     │                                                           │
     │                                         2. Route Handler │
     │                            (api/graph/routes.py:create_graph)
     │                                                           │
     │                                      3. Input Validation │
     │                                      (Pydantic models)    │
     │                                                           │
     │                                      4. Get Dependencies │
     │                              (GraphManager via DI)        │
     │                                                           │
     │                                      5. Business Logic   │
     │                              (services/graph/manager.py)  │
     │                                            ├─ Generate UUID
     │                                            ├─ Validate name
     │                                            └─ Create metadata
     │                                                           │
     │                                      6. Database Insert  │
     │                              (GraphStorageService)        │
     │                                            │              │
     │                                            ▼              │
     │                                      [PostgreSQL]         │
     │                                      INSERT INTO          │
     │                                      workflows...         │
     │                                            │              │
     │                                      7. Return Record    │
     │                                            │              │
     │                                      8. Serialise         │
     │                                      (Pydantic model)     │
     │                                                           │
     │ 9. HTTP Response                                          │
     │    201 Created                                            │
     │    {                                                      │
     │      "id": "abc-123",                                     │
     │      "name": "Customer Support Workflow",                 │
     │      "created_at": "2025-10-20T10:30:00Z"                 │
     │    }                                                      │
     │◀──────────────────────────────────────────────────────────│
     │                                                           │
```

**Key Components:**

1. **API Route Handler**
2. **GraphManager**
3. **GraphStorageService**
4. **Database** - PostgreSQL workflows table

**Data Transformations:**

- Client JSON → Pydantic Request Model
- Request Model → Domain Object (GraphData)
- Domain Object → Database Record (SQLAlchemy)
- Database Record → Pydantic Response Model
- Response Model → Client JSON

### Pattern 2: Synchronous Workflow Execution

**Use Case:** Execute a simple workflow and wait for completion

```
┌──────────┐                                                ┌──────────┐
│  Client  │                                                │ Backend  │
└────┬─────┘                                                └────┬─────┘
     │                                                           │
     │ 1. HTTP Request                                           │
     │    POST /api/graph/execute                                │
     │    {                                                      │
     │      "graph_id": "abc-123",                               │
     │      "input": {"query": "What's the weather?"}            │
     │    }                                                      │
     │──────────────────────────────────────────────────────────▶│
     │                                                           │
     │                                2. Route Handler          │
     │                            (api/graph/handlers/execution.py)
     │                                                           │
     │                                3. Load Graph Definition  │
     │                            (GraphManager.get_graph)       │
     │                                     │                     │
     │                                     ▼                     │
     │                              [PostgreSQL]                 │
     │                              SELECT graph_data            │
     │                                     │                     │
     │                                4. Build LangGraph        │
     │                            (ExecutionEngine)              │
     │                              ├─ Create StateGraph        │
     │                              ├─ Add nodes                 │
     │                              ├─ Add edges                 │
     │                              └─ Compile                   │
     │                                     │                     │
     │                                5. Execute Workflow        │
     │                            [LangGraph Engine]             │
     │                                     │                     │
     │                              ┌──────▼──────┐             │
     │                              │  START Node │             │
     │                              └──────┬──────┘             │
     │                                     │                     │
     │                              ┌──────▼──────┐             │
     │                              │ AGENT Node  │             │
     │                              │             │             │
     │                    6. Call LLM Provider    │             │
     │                              │             │             │
     │                              │   [Azure    │             │
     │                              │   OpenAI]   │             │
     │                              │      │      │             │
     │                              │      ▼      │             │
     │                              │  Response   │             │
     │                              └──────┬──────┘             │
     │                                     │                     │
     │                              ┌──────▼──────┐             │
     │                              │   END Node  │             │
     │                              └──────┬──────┘             │
     │                                     │                     │
     │                                7. Collect Results        │
     │                                     │                     │
     │                                8. Save Execution History │
     │                                     │                     │
     │                                     ▼                     │
     │                              [PostgreSQL]                 │
     │                              INSERT INTO                  │
     │                              execution_records...         │
     │                                     │                     │
     │                                9. Checkpoint State        │
     │                              (Optional)                   │
     │                                     │                     │
     │                                     ▼                     │
     │                              [PostgreSQL]                 │
     │                              INSERT INTO checkpoints...   │
     │                                                           │
     │ 10. HTTP Response                                         │
     │     200 OK                                                │
     │     {                                                     │
     │       "result": "The weather is sunny, 22°C",             │
     │       "execution_id": "exec-456",                         │
     │       "duration": 3.4,                                    │
     │       "node_results": {...}                               │
     │     }                                                     │
     │◀──────────────────────────────────────────────────────────│
     │                                                           │
```

**Key Components:**

1. **Execution Handler**
2. **ExecutionEngine**
3. **LangGraph StateGraph**
4. **Node Executors**
5. **Checkpointer**

**Data Transformations:**

- Client Input → Execution Request Model
- Request Model → LangGraph Initial State
- State → Node Inputs
- Node Outputs → Updated State
- Final State → Execution Result Model
- Result Model → Client Response

### Pattern 3: WebSocket Streaming Execution

**Use Case:** Execute workflow with real-time updates

```
┌──────────┐                                                ┌──────────┐
│  Client  │                                                │ Backend  │
└────┬─────┘                                                └────┬─────┘
     │                                                           │
     │ 1. WebSocket Connection                                   │
     │    ws://api/websocket/execute                             │
     │──────────────────────────────────────────────────────────▶│
     │                                                           │
     │                                2. Connection Accepted     │
     │                            (api/websocket/execution.py)   │
     │◀──────────────────────────────────────────────────────────│
     │                                                           │
     │ 3. Send Execute Message                                   │
     │    {                                                      │
     │      "action": "execute",                                 │
     │      "graph_id": "abc-123",                               │
     │      "input": {"query": "Analyse this document"}          │
     │    }                                                      │
     │──────────────────────────────────────────────────────────▶│
     │                                                           │
     │                                4. Start Async Execution   │
     │                            (ExecutionEngine.astream)      │
     │                                                           │
     │ 5. Stream Event: execution_started                        │
     │    {                                                      │
     │      "event": "execution_started",                        │
     │      "execution_id": "exec-789",                          │
     │      "timestamp": "2025-10-20T10:35:00Z"                  │
     │    }                                                      │
     │◀──────────────────────────────────────────────────────────│
     │                                                           │
     │                           [LangGraph Execution Starts]    │
     │                                                           │
     │ 6. Stream Event: node_start                               │
     │    {                                                      │
     │      "event": "node_start",                               │
     │      "node_id": "agent_1",                                │
     │      "node_name": "Document Analyser"                     │
     │    }                                                      │
     │◀──────────────────────────────────────────────────────────│
     │                                                           │
     │                           [Agent processes document]      │
     │                           [Calls LLM with streaming]      │
     │                                                           │
     │ 7. Stream Event: token (multiple)                         │
     │    { "event": "token", "content": "The" }                 │
     │◀──────────────────────────────────────────────────────────│
     │    { "event": "token", "content": " document" }           │
     │◀──────────────────────────────────────────────────────────│
     │    { "event": "token", "content": " contains" }           │
     │◀──────────────────────────────────────────────────────────│
     │    { "event": "token", "content": "..." }                 │
     │◀──────────────────────────────────────────────────────────│
     │                                                           │
     │ 8. Stream Event: node_end                                 │
     │    {                                                      │
     │      "event": "node_end",                                 │
     │      "node_id": "agent_1",                                │
     │      "result": "Analysis complete",                       │
     │      "duration": 2.3                                      │
     │    }                                                      │
     │◀──────────────────────────────────────────────────────────│
     │                                                           │
     │                           [Next node executes]            │
     │                                                           │
     │ 9. Stream Event: execution_complete                       │
     │    {                                                      │
     │      "event": "execution_complete",                       │
     │      "execution_id": "exec-789",                          │
     │      "final_result": {...},                               │
     │      "total_duration": 4.7                                │
     │    }                                                      │
     │◀──────────────────────────────────────────────────────────│
     │                                                           │
     │ 10. Close Connection                                      │
     │──────────────────────────────────────────────────────────▶│
     │                                                           │
```

**Key Components:**

1. **WebSocket Handler**
2. **ExecutionEngine.astream** - Async streaming execution
3. **WebSocket Notifier**
4. **Event Emitters** - In node executors

**Event Types:**

- `execution_started` - Workflow begins
- `node_start` - Node begins execution
- `token` - Streaming LLM tokens
- `node_end` - Node completes
- `error` - Error occurred
- `execution_complete` - Workflow finished

### Pattern 4: Document Processing Pipeline

**Use Case:** Upload and process a document

```
┌──────────┐                                                ┌──────────┐
│  Client  │                                                │ Backend  │
└────┬─────┘                                                └────┬─────┘
     │                                                           │
     │ 1. HTTP Request (Multipart)                               │
     │    POST /api/documents/upload                             │
     │    Content-Type: multipart/form-data                      │
     │    file=@document.pdf                                     │
     │──────────────────────────────────────────────────────────▶│
     │                                                           │
     │                                2. Route Handler          │
     │                            (api/documents/routes.py)      │
     │                                                           │
     │                                3. Save Temporary File     │
     │                            (workspace/uploads/)           │
     │                                     │                     │
     │                                     ▼                     │
     │                              [File System]                │
     │                                     │                     │
     │                                4. Check Cache             │
     │                            (DocumentCache)                │
     │                                     │                     │
     │                                     ▼                     │
     │                              Cache Miss                   │
     │                                     │                     │
     │                                5. Detect File Type        │
     │                            (by extension/MIME)            │
     │                                     │                     │
     │                                6. Select Processor        │
     │                            (ProcessorFactory)             │
     │                                     │                     │
     │                         ┌───────────┴───────────┐        │
     │                         │                       │        │
     │                    PDF Processor          DOCX Processor │
     │                         │                       │        │
     │                    7. Extract Text              │        │
     │                    ├─ Try text extraction       │        │
     │                    ├─ Fall back to OCR          │        │
     │                    └─ Extract metadata          │        │
     │                         │                       │        │
     │                    8. Process Content           │        │
     │                    ├─ Clean text                │        │
     │                    ├─ Extract structure         │        │
     │                    └─ Build elements            │        │
     │                         │                       │        │
     │                         └───────────┬───────────┘        │
     │                                     │                     │
     │                                9. Format Output          │
     │                            (FormatterFactory)             │
     │                                     │                     │
     │                         ┌───────────┴───────────┐        │
     │                         │                       │        │
     │                  Markdown Format          JSON Format    │
     │                         │                       │        │
     │                         └───────────┬───────────┘        │
     │                                     │                     │
     │                                10. Cache Result           │
     │                            (LRU Cache)                    │
     │                                     │                     │
     │                                11. Store Metadata         │
     │                                     │                     │
     │                                     ▼                     │
     │                              [PostgreSQL]                 │
     │                              INSERT INTO documents...     │
     │                                                           │
     │ 12. HTTP Response                                         │
     │     200 OK                                                │
     │     {                                                     │
     │       "document_id": "doc-321",                           │
     │       "filename": "document.pdf",                         │
     │       "format": "markdown",                               │
     │       "content": "# Document Title\n...",                 │
     │       "metadata": {                                       │
     │         "pages": 5,                                       │
     │         "author": "John Smith"                            │
     │       }                                                   │
     │     }                                                     │
     │◀──────────────────────────────────────────────────────────│
     │                                                           │
```

**Key Components:**

1. **Document Routes**
2. **Document Service**
3. **Processors**
    - PDFProcessor
    - DOCXProcessor
    - ExcelProcessor
    - OCRProcessor
4. **Formatters**
    - MarkdownFormatter
    - JSONFormatter
5. **Cache Manager**

**Processing Pipeline:**

1. Upload → Temporary Storage
2. Cache Check → Hit/Miss
3. Type Detection → Select Processor
4. Content Extraction → Text/Tables/Images
5. Format Conversion → Markdown/JSON/Elements
6. Cache Storage → Future Requests
7. Metadata Storage → Database

### Pattern 5: Email-Triggered Workflow

**Use Case:** Workflow pauses until email received

```
┌──────────┐  ┌──────────┐                            ┌──────────┐
│  Client  │  │  Email   │                            │ Backend  │
│          │  │ Provider │                            │          │
└────┬─────┘  └────┬─────┘                            └────┬─────┘
     │             │                                        │
     │ 1. Start Execution                                   │
     │    (with EMAIL_WAIT node)                            │
     │─────────────────────────────────────────────────────▶│
     │             │                                        │
     │             │                            2. Execute Nodes
     │             │                            Until EMAIL_WAIT
     │             │                                        │
     │             │                            3. Create   │
     │             │                            Email Inbox │
     │             │◀───────────────────────────────────────│
     │             │  Create inbox via API                  │
     │             │                                        │
     │             │  Inbox created                         │
     │             │────────────────────────────────────────▶│
     │             │                                        │
     │             │                            4. Pause    │
     │             │                            Execution   │
     │             │                            (Checkpoint)│
     │             │                                   │    │
     │             │                                   ▼    │
     │             │                            [PostgreSQL]│
     │             │                            Save state  │
     │             │                                        │
     │ 5. Return Paused Status                              │
     │    {                                                 │
     │      "status": "paused",                             │
     │      "email_address": "wait-abc@..."                 │
     │    }                                                 │
     │◀─────────────────────────────────────────────────────│
     │             │                                        │
     │             │                            6. Start    │
     │             │                            Background  │
     │             │                            Polling     │
     │             │                            (every 30s) │
     │             │                                        │
     │             │  Poll for new emails                   │
     │             │◀───────────────────────────────────────│
     │             │                                        │
     │             │  No new emails                         │
     │             │────────────────────────────────────────▶│
     │             │                                        │
     │ [Time passes - user sends email]                     │
     │             │                                        │
     │             │  New email sent to wait-abc@...        │
     │      ───────┼──────────────────▶                     │
     │             │  Email received                        │
     │             │                                        │
     │             │  Poll for new emails                   │
     │             │◀───────────────────────────────────────│
     │             │                                        │
     │             │  Email found!                          │
     │             │────────────────────────────────────────▶│
     │             │                                        │
     │             │                            7. Parse    │
     │             │                            Email       │
     │             │                            Content     │
     │             │                                        │
     │             │                            8. Resume   │
     │             │                            Execution   │
     │             │                            (from       │
     │             │                            checkpoint) │
     │             │                                   │    │
     │             │                                   ▼    │
     │             │                            [PostgreSQL]│
     │             │                            Load state  │
     │             │                                        │
     │             │                            9. Continue │
     │             │                            Workflow    │
     │             │                            (with email │
     │             │                            content)    │
     │             │                                        │
     │ 10. WebSocket Notification                           │
     │     { "event": "execution_resumed" }                 │
     │◀─────────────────────────────────────────────────────│
     │             │                                        │
     │ 11. Fetch Updated Status                             │
     │─────────────────────────────────────────────────────▶│
     │             │                                        │
     │     { "status": "completed" }                        │
     │◀─────────────────────────────────────────────────────│
     │             │                                        │
```

**Key Components:**

1. **Email Service**
2. **Email Providers**
3. **Polling Service**
4. **Paused Execution Service**
5. **Checkpoint Handler**

**Lifecycle:**

1. Execution reaches EMAIL_WAIT node
2. Create temporary inbox (via Mailgun/MailSlurp)
3. Save checkpoint to PostgreSQL
4. Return paused status to client
5. Background poller checks inbox periodically
6. Email arrives and is detected
7. Parse email content
8. Load checkpoint from database
9. Resume execution with email data
10. Complete workflow

## Cross-Cutting Data Flows

### Authentication & Authorisation Flow

```
┌──────────┐                                                ┌──────────┐
│  Client  │                                                │  System  │
└────┬─────┘                                                └────┬─────┘
     │                                                           │
     │ 1. HTTP Request                                           │
     │    GET /api/graph/graphs                                  │
     │    Authorization: Bearer eyJhbG...                        │
     │──────────────────────────────────────────────────────────▶│
     │                                                           │
     │                                2. OAuth2-Proxy            │
     │                                Validates JWT              │
     │                                     │                     │
     │                                     ├─ Verify signature   │
     │                                     ├─ Check expiry       │
     │                                     └─ Extract user info  │
     │                                                           │
     │                                3. Inject Headers          │
     │                                X-Forwarded-User: user@... │
     │                                X-Forwarded-Email: user@...│
     │                                     │                     │
     │                                     ▼                     │
     │                                [FastAPI Middleware]       │
     │                                                           │
     │                                4. Extract User Context    │
     │                                (auth/dependencies.py)     │
     │                                     │                     │
     │                                5. Resolve User ID         │
     │                                (user_resolver.py)         │
     │                                     │                     │
     │                                     ▼                     │
     │                                [PostgreSQL]               │
     │                                SELECT user_id             │
     │                                WHERE email = ...          │
     │                                     │                     │
     │                                6. Add to Request Context  │
     │                                current_user = User(...)   │
     │                                                           │
     │                                7. Route Handler           │
     │                                (with user context)        │
     │                                     │                     │
     │                                8. Authorisation Check     │
     │                                (GraphStorageService)      │
     │                                     │                     │
     │                                     ▼                     │
     │                                [PostgreSQL]               │
     │                                SELECT * FROM workflows    │
     │                                WHERE user_id = ?          │
     │                                OR id IN (                 │
     │                                  SELECT workflow_id       │
     │                                  FROM shared_graphs       │
     │                                  WHERE user_id = ?        │
     │                                )                          │
     │                                     │                     │
     │                                9. Filter Results          │
     │                                (user-scoped data)         │
     │                                                           │
     │ 10. HTTP Response                                         │
     │     [Only user's workflows + shared workflows]            │
     │◀──────────────────────────────────────────────────────────│
     │                                                           │
```

### Error Handling Flow

```
┌──────────┐                                                ┌──────────┐
│  Client  │                                                │ Backend  │
└────┬─────┘                                                └────┬─────┘
     │                                                           │
     │ 1. Request                                                │
     │──────────────────────────────────────────────────────────▶│
     │                                                           │
     │                                2. Exception Raised        │
     │                                (during execution)         │
     │                                     │                     │
     │                              ┌──────▼──────┐             │
     │                              │  Exception  │             │
     │                              │   Handler   │             │
     │                              │  Middleware │             │
     │                              └──────┬──────┘             │
     │                                     │                     │
     │                                3. Log Error               │
     │                                (with context)             │
     │                                     │                     │
     │                                4. Determine Error Type    │
     │                                     │                     │
     │                         ┌───────────┼───────────┐        │
     │                         │           │           │        │
     │                   Validation   Business   System         │
     │                    Error        Error     Error          │
     │                         │           │           │        │
     │                         └───────────┼───────────┘        │
     │                                     │                     │
     │                                5. Format Error Response   │
     │                                     │                     │
     │                                6. Record in Database      │
     │                                (if execution error)       │
     │                                     │                     │
     │                                     ▼                     │
     │                                [PostgreSQL]               │
     │                                UPDATE execution_records   │
     │                                SET status = 'failed'      │
     │                                                           │
     │ 7. HTTP Error Response                                    │
     │    400/500 Error                                          │
     │    {                                                      │
     │      "error": {                                           │
     │        "code": "VALIDATION_ERROR",                        │
     │        "message": "Invalid node configuration",           │
     │        "details": {...}                                   │
     │      }                                                    │
     │    }                                                      │
     │◀──────────────────────────────────────────────────────────│
     │                                                           │
```

## Monitoring & Observability Data Flow

### LangSmith Tracing

```
┌────────────────┐                                      ┌────────────────┐
│  Execution     │                                      │   LangSmith    │
│  (Backend)     │                                      │     Cloud      │
└───────┬────────┘                                      └───────┬────────┘
        │                                                       │
        │ 1. Start Execution                                    │
        │    (with tracing context)                             │
        │                                                       │
        │ 2. Emit Trace Start Event                             │
        │    { "run_id": "...", "name": "workflow" }            │
        │──────────────────────────────────────────────────────▶│
        │                                                       │
        │ 3. Execute Node                                       │
        │    (agent/tool/condition)                             │
        │                                                       │
        │ 4. Emit Node Trace                                    │
        │    { "parent_run_id": "...", "inputs": {...} }        │
        │──────────────────────────────────────────────────────▶│
        │                                                       │
        │ 5. LLM Call                                           │
        │                                                       │
        │ 6. Emit LLM Trace                                     │
        │    { "model": "gpt-4", "tokens": {...} }              │
        │──────────────────────────────────────────────────────▶│
        │                                                       │
        │ 7. Complete Execution                                 │
        │                                                       │
        │ 8. Emit Trace End Event                               │
        │    { "run_id": "...", "outputs": {...} }              │
        │──────────────────────────────────────────────────────▶│
        │                                                       │
```

### Metrics Collection

```
┌────────────────┐                                      ┌────────────────┐
│  Services      │                                      │   Metrics      │
│  (Backend)     │                                      │   System       │
└───────┬────────┘                                      └───────┬────────┘
        │                                                       │
        │ 1. Execution Event                                    │
        │    (node start/end)                                   │
        │                                                       │
        │ 2. Collect Metrics                                    │
        │    (MetricsCollector)                                 │
        │    ├─ Duration                                        │
        │    ├─ Token count                                     │
        │    ├─ Error count                                     │
        │    └─ Success rate                                    │
        │                                                       │
        │ 3. Export Metrics                                     │
        │    (via configured exporter)                          │
        │                                                       │
        ├────────────┬──────────────┬────────────────┐         │
        │            │              │                │         │
   Prometheus    StatsD         JSON              Database    │
   Exporter      Exporter       Exporter          Storage     │
        │            │              │                │         │
        ▼            ▼              ▼                ▼         │
   [Prometheus] [StatsD]       [Log File]     [PostgreSQL]    │
    Server       Server                                        │
```

## State Management Data Flow

### LangGraph State Transitions

```
┌──────────────────────────────────────────────────────────────┐
│                    Workflow State Lifecycle                  │
│                                                              │
│  Initial State                                               │
│  ┌───────────────────────────────────────────────────┐      │
│  │ {                                                  │      │
│  │   "messages": [],                                  │      │
│  │   "user_input": "Analyse this data",               │      │
│  │   "current_node": "START",                         │      │
│  │   "execution_metadata": {...}                      │      │
│  │ }                                                  │      │
│  └────────────────────────┬──────────────────────────┘      │
│                           │                                  │
│                           ▼                                  │
│  After Agent Node                                            │
│  ┌───────────────────────────────────────────────────┐      │
│  │ {                                                  │      │
│  │   "messages": [                                    │      │
│  │     {"role": "user", "content": "Analyse..."},     │      │
│  │     {"role": "assistant", "content": "Result..."}  │      │
│  │   ],                                               │      │
│  │   "agent_result": "Analysis complete",             │      │
│  │   "current_node": "agent_1",                       │      │
│  │   "execution_metadata": {...}                      │      │
│  │ }                                                  │      │
│  └────────────────────────┬──────────────────────────┘      │
│                           │                                  │
│                           ▼                                  │
│  After Condition Node                                        │
│  ┌───────────────────────────────────────────────────┐      │
│  │ {                                                  │      │
│  │   "messages": [...],                               │      │
│  │   "agent_result": "Analysis complete",             │      │
│  │   "condition_result": true,                        │      │
│  │   "next_node": "tool_1",                           │      │
│  │   "current_node": "condition_1"                    │      │
│  │ }                                                  │      │
│  └────────────────────────┬──────────────────────────┘      │
│                           │                                  │
│                           ▼                                  │
│  Final State                                                 │
│  ┌───────────────────────────────────────────────────┐      │
│  │ {                                                  │      │
│  │   "messages": [...],                               │      │
│  │   "final_result": "Task completed successfully",   │      │
│  │   "current_node": "END",                           │      │
│  │   "execution_metadata": {...}                      │      │
│  │ }                                                  │      │
│  └───────────────────────────────────────────────────┘      │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## Related Documentation

- [00-overview.md](./00-overview.md) - System overview
- [01-architecture-diagram.md](./01-architecture-diagram.md) - Architecture diagrams
- [03-design-principles.md](./03-design-principles.md) - Design decisions
