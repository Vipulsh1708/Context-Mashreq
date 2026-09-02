# Architecture Reference

## Application Lifecycle

### Startup Sequence

1. **Environment Loading**
    - Load `.env` file
    - Configure logging filters

2. **Dependency Initialisation**
    - Initialise `GraphManager` singleton
    - Initialise `ExecutionEngine` singleton
    - Set up dependency injection container

3. **LangGraph Engine Setup**
    - Initialise checkpointer (PostgreSQL or in-memory)
    - Configure state management
    - Set up execution context

4. **Database Initialisation**
    - Create tables if not exists
    - Run migrations
    - Validate database connectivity

5. **API Registration**
    - Mount all API routers
    - Configure middleware (CORS, logging)
    - Set up static file serving

### Request Lifecycle

1. **HTTP Request** arrives at FastAPI
2. **Middleware Processing** (CORS, auth, logging)
3. **Route Matching** to appropriate router
4. **Dependency Injection** resolves dependencies
5. **Handler Execution** in API layer
6. **Service Invocation** for business logic
7. **Database/External API Calls** as needed
8. **Response Serialisation** via Pydantic
9. **HTTP Response** sent to client

### WebSocket Lifecycle

1. **Connection Establishment**
2. **Authentication/Authorisation** check
3. **Event Loop** for bidirectional messages
4. **Execution Updates** streamed to client
5. **Error Handling** with reconnection support
6. **Connection Closure** and cleanup

## Execution Flow

### Six-Phase Workflow Execution

Implemented in `backend/services/execution/workflow_executor.py`:

1. **Initialize Context** — Create DB execution record, set up `active_executions` tracking
2. **Process START Node** — Handle initial user input, create execution history record
3. **Build & Compile Graph** — Construct `StateGraph` from the workflow definition, compile with PostgreSQL checkpointer
4. **Execute Streaming** — Main loop via LangGraph's `astream()`, emit WebSocket events per node
5. **Handle Control** — Process pause/stop requests, handle human-in-the-loop interrupts
6. **Finalize Execution** — Process END node output, mark execution complete, clean up state

### WorkflowState

The shared state object threaded through every node (`backend/services/workflow/state/schemas.py`):

```python
class WorkflowState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]  # Chat history with reducer
    node_outputs: Annotated[Dict[str, NodeOutput], merge_node_outputs]  # Per-node results
    results: Annotated[List[NodeResult], merge_results]  # Accumulated results
    current_node: Annotated[Optional[str], last_value_reducer]
    execution_id: str
    execution_order: Annotated[int, max_execution_order]
    metadata: Annotated[WorkflowMetadata, merge_metadata]
    memory_context: Optional[MemoryContext]
    orchestration_context: Optional[OrchestrationContext]
```

Each node reads from and writes to this state. LangGraph applies the annotated reducers to merge concurrent updates safely.

## Key Subsystems

### Workflow Execution Engine

**Components:**

- **Graph Manager** (`services/graph/manager.py`) — CRUD operations for workflow definitions
- **Execution Engine** (`services/execution/engine.py`) — Coordinates the 6-phase execution lifecycle
- **WorkflowExecutor** (`services/execution/workflow_executor.py`) — Implements each execution phase
- **Checkpointer** — PostgreSQL-backed LangGraph checkpointer for pause/resume and state snapshots
- **Node Executor Registry** (`services/nodes/registry.py`) — Strategy pattern; maps node types to executor implementations

**Execution Modes:**

- **Synchronous HTTP** — Block until complete, return final result
- **Asynchronous HTTP** — Return immediately, poll for status
- **WebSocket Streaming** — Real-time events: `node_start`, `token`, `node_end`, `execution_complete`
- **SSE Streaming** — Server-sent events, used by the HTTP execution API

### Document Processing Pipeline

**Components:**

- **Processors** - Extract content from various formats (PDF, DOCX, Excel, images)
- **OCR Service** - Text extraction from images
- **Formatters** - Convert to standardised formats (Markdown, JSON)
- **Cache Manager** - LRU cache for processed documents
- **Metadata Extraction** - Automatic metadata extraction

**Supported Formats:**

- PDF (text and image-based)
- Microsoft Office (DOCX, XLSX)
- Plain text
- Images (via OCR)
- Unstructured documents

### Email Integration System

**Components:**

- **Email Manager** - High-level email operations
- **Provider Abstraction** - Multi-provider support (Outlook, Mailgun, MailSlurp)
- **Polling Service** - Background email checking (if supported for the given provider)
- **Checkpoint Integration** - Workflow pause/resume on email triggers

**Use Cases:**

- Human-in-the-loop workflows
- Email-triggered automation
- Approval workflows
- Notification delivery

### Memory Management

**Components:**

- **Memory Manager** - Conversation memory for agents
- **Pruning Service** - Automatic memory cleanup based on policies
- **Statistics Tracker** - Memory usage metrics
- **Formatter** - Memory serialisation for storage

**Features:**

- Short-term conversation memory
- Long-term memory persistence
- Token-based pruning
- Time-based expiration

### Monitoring & Observability

**Components:**

- **Health Checks** - Service availability monitoring
- **Diagnostics Service** - System health metrics
- **Trace Viewer** - LangSmith trace integration
- **Metrics Collector** - Custom metrics (execution time, token usage)
- **Feature Flags** - Runtime feature toggles

**Integrations:**

- StatsD exporters
- JSON log exporters

## Security Architecture

### Authentication

- **OAuth2-Proxy** - Central authentication gateway
- **Azure AD Integration** - Enterprise SSO
- **JWT Token Validation** - Stateless auth
- **User Resolution** - Extract user info from headers

### Authorisation

- **User-scoped Resources** - Graphs, workflows owned by users
- **Access Control Lists** - Graph sharing and permissions
- **API Key Management** - Encrypted storage for LLM API keys

### Data Protection

- **Credential Encryption** - AES encryption for sensitive data
- **Environment Variables** - Secrets management
- **PostgreSQL SSL** - Encrypted database connections
- **HTTPS/WSS** - Encrypted transport

## Scalability Considerations

### Current Architecture

- **Single-server deployment** - Monolithic FastAPI application
- **PostgreSQL** - Single database instance
- **In-memory caching** - Process-local caches
- **Background tasks** - FastAPI BackgroundTasks

### Scaling Options

- **Horizontal Scaling** - Multiple API server instances
- **Load Balancing** - Nginx/ALB for traffic distribution
- **Redis** - Distributed caching and pub/sub
- **Celery** - Distributed task queue for executions
- **Database Replication** - Read replicas for scaling reads
- **Object Storage** - S3 for document storage

## Related Documentation

- [01-architecture-diagram.md](./01-architecture-diagram.md) - Visual architecture diagrams
- [02-data-flow.md](./02-data-flow.md) - Data flow through the system
- [03-design-principles.md](./03-design-principles.md) - Architectural decisions and rationale
