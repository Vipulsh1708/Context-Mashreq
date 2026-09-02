# Design Principles & Architectural Decisions

This document explains the key design principles and architectural decisions that shaped Agentic Studio's architecture,
particularly focusing on the recent refactoring that separated components into structured modules.

## Core Design Principles

1. **Separation of Concerns**
    - Clear boundary between API layer (HTTP handling) and Services layer (business logic)
    - Services are framework-agnostic and reusable
    - API endpoints are thin wrappers around service functions

2. **Dependency Injection**
    - Centralised dependency management via `services.dependency_injection`
    - Thread-safe singleton container for shared resources
    - Easy testing and mocking through protocol-based typing

3. **Async-First Design**
    - All I/O operations are async where possible
    - Background task execution for long-running workflows
    - Non-blocking WebSocket and SSE streams

4. **Type Safety**
    - Pydantic models for all API contracts
    - Protocol-based dependency injection
    - Comprehensive type hints throughout codebase

5. **Modularity**
    - Feature-based module organisation
    - Each API module is self-contained with its own routes, models, handlers
    - Services organised by domain (execution, document, email, etc.)

### 1. Separation of Concerns (SoC)

**Principle:** Each component should have a single, well-defined responsibility.

**Implementation:**

**API Layer**

- **Responsibility:** HTTP protocol concerns only
  - Request/response handling
  - Input validation (via Pydantic)
  - HTTP status codes and headers
  - WebSocket connection management
  - Error serialisation
- **Does NOT:** Contain business logic, database queries, or complex algorithms

**Services Layer**

- **Responsibility:** Business logic and domain operations
  - Data processing and transformation
  - External API integration
  - Database operations
  - Workflow orchestration
  - Business rules enforcement
- **Does NOT:** Know about HTTP, FastAPI, or web protocols

**Benefits:**

- Services can be tested without starting a web server
- Business logic is reusable across different entry points (HTTP, CLI, scheduled jobs)
- Changes to API protocols don't affect business logic
- Clear boundaries make code easier to understand and maintain

**Example:**

```python
# ❌ BAD: Business logic mixed with HTTP handling
@router.post("/graphs")
async def create_graph(request: Request):
    data = await request.json()
    # Validation logic here...
    # Database logic here...
    # File system logic here...
    return {"id": new_id}


# ✅ GOOD: Separation of concerns
@router.post("/graphs")
async def create_graph(
        request: GraphCreateRequest,
        graph_mgr: GraphManager  # Injected service
):
    # API layer: Just handle HTTP and delegate to service
    graph = graph_mgr.create_graph(
        name=request.name,
        description=request.description
    )
    return GraphResponse.from_domain(graph)
```

### 2. Dependency Injection (DI)

**Principle:** Dependencies should be provided to components rather than created by them.

**Implementation:**

**Centralised Container**

- Thread-safe singleton container
- Initialised once at application startup
- Provides consistent instances throughout app lifecycle

**Usage Patterns:**

```python
# For non-FastAPI code (services layer)
from backend.services.dependency_injection import get_graph_manager

graph_mgr = get_graph_manager()

# For FastAPI routes (API layer)
from backend.services.dependency_injection import GraphManager


@router.get("/graphs")
async def list_graphs(graph_mgr: GraphManager):
    return graph_mgr.list_graphs()
```

**Benefits:**

- Easy testing via mocking
- Single source of truth for shared resources
- Automatic lifecycle management
- Type-safe dependency resolution
- No global variables or singletons scattered through code

**Decision Rationale:**

- Initially, components created their own dependencies leading to:
  - Multiple instances of the same resource
  - Difficult testing (couldn't inject mocks)
  - Tight coupling between components
- DI pattern solves all these issues elegantly

### 3. Type Safety

**Principle:** Use static typing extensively to catch errors early and provide better IDE support.

**Implementation:**

**Pydantic Models** for all data contracts:

```python
# API request/response models
class GraphCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None


class GraphResponse(BaseModel):
    id: str
    name: str
    created_at: datetime
```

**Protocol-based Interfaces** for dependency injection:

```python
# Define interface
class GraphManagerProtocol(Protocol):
    def create_graph(self, name: str) -> GraphData: ...

    def get_graph(self, graph_id: str) -> GraphData: ...


# Implementations automatically satisfy protocol
class GraphManager:  # No explicit inheritance needed
    def create_graph(self, name: str) -> GraphData:
# Implementation
```

**Type Hints** throughout codebase:

```python
def execute_node(
        state: WorkflowState,
        node_config: NodeConfig,
        context: ExecutionContext
) -> NodeResult:
# Implementation with full type safety
```

**Benefits:**

- Catch type errors at development time (IDE, mypy)
- Better autocomplete and refactoring support
- Self-documenting code
- Reduced runtime errors

### 4. Async-First Design

**Principle:** Use async/await for all I/O-bound operations to maximise concurrency.

**Implementation:**

**Async Services:**

```python
class ExecutionEngine:
    async def execute(self, graph_id: str, input_data: dict) -> dict:
        # Async execution
        result = await self._run_graph(graph_id, input_data)
        return result

    async def astream(self, graph_id: str) -> AsyncIterator[Event]:
        # Streaming execution
        async for event in self._stream_graph(graph_id):
            yield event
```

**Async Adapters** for sync libraries:

```python
class AsyncCheckpointerAdapter:
    """Wraps synchronous PostgresSaver with async interface."""

    def __init__(self, sync_checkpointer):
        self._checkpointer = sync_checkpointer

    async def aget(self, checkpoint_id: str):
        # Run sync code in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._checkpointer.get, checkpoint_id
        )
```

**Benefits:**

- Handle many concurrent requests with fewer resources
- Non-blocking I/O for database, LLM APIs, file operations
- Better scalability
- Natural fit for streaming and real-time updates

**Trade-offs:**

- More complex than synchronous code
- Need to be careful about blocking operations
- Requires understanding of event loop

### 5. Modularity & Domain Organisation

**Principle:** Organise code by domain/feature, not by technical layer.

**Implementation:**

**Feature-based API Modules:**

```
backend/api/
├── graph/              # Everything related to graph management
│   ├── routes.py
│   ├── models.py
│   ├── handlers/
│   └── dependencies.py
├── execution/          # Execution-related endpoints
├── documents/          # Document processing endpoints
└── email/              # Email integration endpoints
```

**Domain-based Services:**

```
backend/services/
├── execution/          # Execution domain
│   ├── state/          # State management
│   ├── paused/         # Pause/resume functionality
│   ├── history/        # Execution history
│   └── checkpointer.py
├── document/           # Document processing domain
│   ├── processors/     # File type processors
│   ├── formatters/     # Output formatters
│   └── cache/          # Caching layer
└── email/              # Email domain
    ├── providers/      # Email service providers
    ├── polling/        # Background polling
    └── manager.py      # High-level operations
```

**Benefits:**

- Related functionality grouped together
- Easy to find code for a specific feature
- Can evolve domains independently
- Clear boundaries between features
- Easier to split into microservices later if needed

**Contrast with Technical Layering:**

```
# ❌ Technical layering (not used)
backend/
├── controllers/  # All API handlers
├── services/     # All business logic
├── repositories/ # All database code
└── models/       # All data models

# Hard to find all code related to "documents"
# Scattered across multiple directories
```

### 6. Factory Pattern for Polymorphism

**Principle:** Use factories to create objects based on runtime configuration.

**Implementation:**

**Condition Evaluator Factory:**

```python
class ConditionEvaluator:
    """Orchestrates different condition evaluation strategies."""

    def __init__(self):
        self.single_evaluator = SingleConditionEvaluator()
        self.branch_evaluator = BranchConditionEvaluator()
        self.expression_evaluator = ExpressionConditionEvaluator()
        self.llm_evaluator = LLMConditionEvaluator()

    def evaluate(self, condition_type: str, config: dict):
        # Route to appropriate evaluator
        if condition_type == "expression":
            return self.expression_evaluator.evaluate(config)
        elif condition_type == "llm":
            return self.llm_evaluator.evaluate(config)
        # ...
```

**Document Processor Factory:**

```python
class DocumentService:
    def process_document(self, file_path: str):
        # Detect type
        file_type = self._detect_type(file_path)

        # Create appropriate processor
        processor = self._create_processor(file_type)
        # pdf → PDFProcessor
        # docx → DOCXProcessor
        # xlsx → ExcelProcessor

        # Process
        return processor.process(file_path)
```

**Email Provider Factory:**

```python
class EmailProviderFactory:
    @staticmethod
    def create(provider_name: str) -> BaseEmailProvider:
        if provider_name == "mailgun":
            return MailgunProvider()
        elif provider_name == "mailslurp":
            return MailSlurpProvider()
        raise ValueError(f"Unknown provider: {provider_name}")
```

**Benefits:**

- Add new types without modifying existing code (Open/Closed Principle)
- Encapsulate object creation logic
- Type-specific behaviour hidden behind common interface
- Easy to extend system with new node types, file formats, providers

### 7. Repository Pattern for Data Access

**Principle:** Encapsulate database operations behind a service interface.

**Implementation:**

**GraphStorageService:**

```python
class GraphStorageService:
    """Handles all database operations for graphs."""

    def create_workflow(self, name: str, user_id: str) -> Workflow:
        # Database logic encapsulated here
        workflow = Workflow(name=name, user_id=user_id)
        db.add(workflow)
        db.commit()
        return workflow

    def get_user_workflows(self, user_id: str) -> List[Workflow]:
        # User-scoped query
        return db.query(Workflow)
            .filter(Workflow.user_id == user_id)
            .all()
```

**Benefits:**

- Services don't need to know about SQL or SQLAlchemy
- Easy to change database implementation
- Centralised place for query optimisation
- User-scoped queries enforce security
- Easy to mock for testing

**Contrast with Direct DB Access:**

```python
# ❌ BAD: Direct database access scattered everywhere
@router.get("/graphs")
def list_graphs(db: Session):
    graphs = db.query(Workflow).all()  # No user scoping!
    return graphs


# ✅ GOOD: Through repository
@router.get("/graphs")
def list_graphs(storage: GraphStorageService, user: User):
    graphs = storage.get_user_workflows(user.id)  # User scoped!
    return graphs
```

### 8. Configuration via Environment Variables

**Principle:** All configuration should come from the environment, not hardcoded.

**Implementation:**

**Environment-based Config:**

```python
# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")
ENABLE_POSTGRES_CHECKPOINTING = os.getenv("ENABLE_POSTGRES_CHECKPOINTING", "true")

# LLM providers
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Feature flags
ENABLE_LANGGRAPH_ENGINE = os.getenv("ENABLE_LANGGRAPH_ENGINE", "true")
```

**Config Classes** for complex settings:

```python
class DatabaseConfig:
    def __init__(self):
        self.url = os.getenv("DATABASE_URL")
        self.pool_size = int(os.getenv("DB_POOL_SIZE", "5"))
        self.echo = os.getenv("DB_ECHO", "false").lower() == "true"
```

**Benefits:**

- Same code runs in dev/staging/production
- Secrets never committed to repository
- Easy to change config without code changes
- Follows 12-factor app principles

## Key Architectural Decisions

### Decision 1: FastAPI over Flask

**Rationale:**

- Built-in async support (essential for LLM streaming)
- Automatic API documentation (OpenAPI/Swagger)
- Pydantic integration for validation
- Better performance than Flask
- Modern Python features (type hints, async/await)

**Trade-offs:**

- Smaller ecosystem than Flask
- Steeper learning curve for async
- More opinionated framework

### Decision 2: PostgreSQL for Everything

**Rationale:**

- Single database simplifies deployment
- JSONB columns for flexible schema (graph definitions)
- ACID transactions for consistency
- Mature, well-tested, reliable
- Good Python support (psycopg3)

**What we store:**

- **Workflows** - Graph definitions with versioning
- **Execution History** - All execution records
- **Checkpoints** - LangGraph state snapshots (via langgraph-checkpoint-postgres)
- **Users & Access Control** - Authentication data
- **Documents Metadata** - Processed document info

**Trade-offs:**

- Not as fast as Redis for caching (but good enough)
- More setup than SQLite
- Requires PostgreSQL hosting

**Alternative Considered:**

- Redis for caching + PostgreSQL for persistence
  - Rejected: Added complexity for marginal performance gain
  - May revisit for scale

### Decision 3: LangGraph for Workflow Orchestration

**Rationale:**

- Built specifically for AI agent workflows
- State management out of the box
- Checkpointing for pause/resume
- Streaming support for real-time updates
- Human-in-the-loop capabilities
- Active development and good documentation

**Key Features Used:**

- **StateGraph** - Workflow definition
- **Checkpointer** - State persistence
- **Conditional Edges** - Dynamic routing
- **astream** - Streaming execution

**Trade-offs:**

- Relatively new library (less mature than Airflow)
- Tied to LangChain ecosystem
- Learning curve for team

**Alternative Considered:**

- Temporal.io - Robust workflow engine
  - Rejected: Overkill for our use case, requires separate infrastructure
- Custom orchestrator
  - Rejected: Too much work to build equivalent functionality

### Decision 4: Multi-Execution Mode Support

**Decision:** Support three execution modes:

1. **Synchronous HTTP** - Block until complete

   ```python
   POST /api/graph/execute
   # Waits for completion
   # Returns final result
   ```

2. **Asynchronous HTTP** - Background execution

   ```python
   POST /api/graph/execute-async
   # Returns immediately with token
   GET /api/graph/execution-status/{token}
   # Poll for status
   ```

3. **WebSocket Streaming** - Real-time updates

   ```python
   WS /api/websocket/execute
   # Streams events in real-time
   # node_start, token, node_end, complete
   ```

**Rationale:**

- Different use cases need different approaches
- Sync: Simple scripts, testing
- Async: Long-running workflows, batch processing
- WebSocket: Interactive UI, live monitoring

**Implementation:**

- All modes use same `ExecutionEngine`
- Different wrappers for different protocols
- Consistent event model across modes

### Decision 5: Encryption for User Credentials

**Decision:** Encrypt LLM API keys at rest in database.

**Implementation:**

```python
class ModelDeployment:
    encrypted_credentials: str  # AES-256 encrypted

    def get_credentials(self, encryption_key: str) -> dict:
        return decrypt(self.encrypted_credentials, encryption_key)
```

**Rationale:**

- Users provide their own LLM API keys
- Keys are sensitive secrets
- Database compromise shouldn't expose keys
- Per-user encryption keys

**Trade-offs:**

- Slight performance overhead
- Need to manage encryption keys
- More complex than plain text

**Alternative Considered:**

- Store in environment variables
  - Rejected: Can't have per-user keys
- Use secrets management service (AWS Secrets Manager)
  - Rejected: Added infrastructure complexity
  - May revisit for production

### Decision 6: Checkpointing Strategy

**Decision:** Use PostgreSQL for checkpoint storage (not memory).

**Rationale:**

- Workflows can be paused and resumed across server restarts
- Email-triggered workflows need persistent pause state
- Time-travel debugging (view state at any point)
- Multi-server deployment possible

**Implementation:**

```python
# Initialize with PostgreSQL checkpointer
checkpointer = PostgresSaver(connection)
graph = StateGraph(state_schema, checkpointer=checkpointer)
```

**Trade-offs:**

- Database overhead for every state change
- More complex than in-memory
- Need database connectivity

**Benefits:**

- Survives server crashes
- Can resume workflows days later
- Audit trail of state changes

### Decision 7: Service Refactoring Strategy

**Previous Structure** (monolithic):

```
backend/
├── graph_manager.py       # 2000+ lines
├── execution_engine.py    # 1500+ lines
├── enhanced_nodedata.py   # Large data models
└── graph_builder_api.py   # All API endpoints
```

**New Structure** (modular):

```
backend/
├── api/                   # 20+ feature modules
│   ├── graph/
│   ├── execution/
│   └── ...
└── services/              # 30+ service domains
    ├── execution/
    ├── document/
    └── ...
```

**Refactoring Process:**

1. **Extract services** - Move business logic to services/
2. **Create API wrappers** - Thin HTTP handlers in api/
3. **Implement DI** - Centralised dependency management
4. **Add typing** - Comprehensive type hints
5. **Write tests** - Services testable without HTTP

**Benefits Realised:**

- Individual files now < 500 lines
- Clear responsibilities per module
- Easy to find and modify code
- New team members onboard faster
- Bugs easier to isolate and fix

## Design Patterns Used

### 1. Strategy Pattern

**Used in:** Condition evaluation, document processing

**Example:**

```python
class ConditionEvaluator:
    # Different strategies for different condition types
    strategies = {
        "simple": SingleConditionEvaluator(),
        "expression": ExpressionConditionEvaluator(),
        "llm": LLMConditionEvaluator(),
        "branch": BranchConditionEvaluator()
    }

    def evaluate(self, condition_type: str, config: dict):
        strategy = self.strategies[condition_type]
        return strategy.evaluate(config)
```

### 2. Adapter Pattern

**Used in:** Wrapping sync libraries with async interface

**Example:**

```python
class AsyncCheckpointerAdapter:
    """Adapts sync PostgresSaver to async interface."""

    def __init__(self, sync_checkpointer):
        self._sync = sync_checkpointer

    async def aget(self, key):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync.get, key)
```

### 3. Observer Pattern

**Used in:** WebSocket event notifications, execution monitoring

**Example:**

```python
class ExecutionEngine:
    async def astream(self, graph_id: str):
        # Observers (WebSocket clients) subscribe to events
        async for event in self._execute_stream(graph_id):
            # Notify all observers
            await self._notify_websocket_clients(event)
            yield event
```

### 4. Chain of Responsibility

**Used in:** Document processing pipeline

**Example:**

```python
# Each processor in the chain tries to handle the document
processors = [
    PDFProcessor(),
    DOCXProcessor(),
    ExcelProcessor(),
    FallbackProcessor()
]

for processor in processors:
    if processor.can_handle(document):
        return processor.process(document)
```

### 5. Singleton Pattern

**Used in:** Dependency injection container

**Example:**

```python
class DependencyContainer:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
```

## Testing Strategy

### Unit Tests

**Focus:** Individual services in isolation

```python
def test_condition_evaluator():
    evaluator = ConditionEvaluator()

    state = WorkflowState(user_input="test")
    config = {"field": "user_input", "operator": "equals", "value": "test"}

    result = evaluator.evaluate(state, config)
    assert result == True
```

**Benefits:**

- Fast execution
- No external dependencies
- Easy to mock

### Integration Tests

**Focus:** Multiple components working together

```python
async def test_full_execution():
    # Real ExecutionEngine, real LangGraph
    engine = ExecutionEngine()
    result = await engine.execute(graph_id, input_data)

    # Verify end-to-end flow
    assert result.status == "completed"
```

**Benefits:**

- Catches integration issues
- Tests real scenarios
- Validates API contracts

### API Tests

**Focus:** HTTP endpoints and request/response

```python
def test_create_graph_endpoint(client):
    response = client.post("/api/graph/graphs", json={
        "name": "Test Workflow"
    })

    assert response.status_code == 201
    assert response.json()["name"] == "Test Workflow"
```

**Benefits:**

- Tests full HTTP stack
- Validates serialisation
- Checks error handling

## Performance Considerations

### 1. Database Connection Pooling

```python
# SQLAlchemy engine with connection pool
engine = create_engine(
    DATABASE_URL,
    pool_size=10,  # Max 10 connections
    max_overflow=20,  # Allow 20 more when needed
    pool_pre_ping=True  # Check connection before use
)
```

### 2. Document Processing Cache

```python
class DocumentCache:
    # LRU cache for processed documents
    cache = LRU(max_size=100)  # Keep 100 recent documents

    def get(self, file_hash: str):
        return self.cache.get(file_hash)
```

### 3. Async I/O for Concurrency

```python
# Handle multiple requests concurrently
async def handle_multiple_executions(graph_ids: List[str]):
    tasks = [execute_graph(gid) for gid in graph_ids]
    results = await asyncio.gather(*tasks)  # Run in parallel
    return results
```

### 4. Streaming for Large Responses

```python
# Stream tokens instead of waiting for full response
async def stream_llm_response():
    async for token in llm.astream("prompt"):
        yield token  # Send immediately, don't buffer
```

## Security Best Practices

### 1. Input Validation

**Always validate at API boundary:**

```python
class GraphCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
```

### 2. SQL Injection Prevention

**Use parameterised queries:**

```python
# ✅ GOOD: Parameterised
db.query(Workflow).filter(Workflow.id == user_provided_id)

# ❌ BAD: String interpolation
db.execute(f"SELECT * FROM workflows WHERE id = '{user_provided_id}'")
```

### 3. User-Scoped Queries

**Always filter by user:**

```python
def get_user_workflows(user_id: str):
    return db.query(Workflow)
        .filter(Workflow.user_id == user_id)\  # Critical!
    .all()
```

### 4. Credential Encryption

**Never store plaintext secrets:**

```python
encrypted = encrypt(api_key, user_encryption_key)
db.add(ModelDeployment(encrypted_credentials=encrypted))
```

## Future Considerations

### Scalability

**Current:** Single server, single database
**Future Options:**

1. **Horizontal Scaling** - Multiple API servers behind load balancer
2. **Read Replicas** - Database read scaling
3. **Redis Cache** - Reduce database load
4. **Celery Workers** - Distributed task execution
5. **Object Storage** - S3 for documents instead of filesystem

### Monitoring

**Current:** Basic health checks, LangSmith tracing
**Future Options:**

1. **Prometheus Metrics** - Already have exporters
2. **Grafana Dashboards** - Visualise metrics
3. **Error Tracking** - Sentry integration
4. **Performance Profiling** - Identify bottlenecks

### Multi-Tenancy

**Current:** User-scoped data
**Future Options:**

1. **Organisation Support** - Team/company workspaces
2. **Row-Level Security** - PostgreSQL RLS policies
3. **Separate Databases** - Per-tenant isolation

## Conclusion

Agentic Studio's architecture embodies modern software engineering best practices:

- **Separation of Concerns** - Clear boundaries between layers
- **Dependency Injection** - Decoupled, testable components
- **Type Safety** - Comprehensive typing for reliability
- **Modularity** - Feature-based organisation
- **Async-First** - Built for concurrency and streaming
- **Security** - Defence in depth with multiple layers

The recent refactoring has positioned the codebase for:

- **Maintainability** - Easy to understand and modify
- **Extensibility** - Simple to add new features
- **Testability** - Services can be tested in isolation
- **Scalability** - Architecture supports future growth

These principles guide all development decisions and ensure the platform remains robust, performant, and maintainable as
it grows.

## Related Documentation

- [00-overview.md](./00-overview.md) - System overview and tech stack
- [01-architecture-diagram.md](./01-architecture-diagram.md) - Visual architecture diagrams
- [02-data-flow.md](./02-data-flow.md) - Data flow patterns
