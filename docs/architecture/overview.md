# Architecture Overview

## System Summary

**Agentic Studio** is a no-code/low-code AI workflow builder platform that enables users to create and execute sophisticated
AI agent workflows through a visual drag-and-drop interface.

The system combines LangGraph's state management
capabilities with LangChain's AI tooling to provide a comprehensive workflow automation solution.

## High-Level Architecture Layers

```text
┌─────────────────────────────────────────────────────────────┐
│                    Frontend Layer                           │
│  Next.js + React + ReactFlow + Tailwind CSS                 │
│  - Visual workflow builder                                  │
│  - Real-time execution monitoring                           │
│  - Authentication and authorisation                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ HTTP/REST + WebSocket
                         │
┌────────────────────────▼────────────────────────────────────┐
│                     API Layer                               │
│  FastAPI Routers (20+ feature modules)                      │
│  - graph, execution, http_execution                         │
│  - auth, monitoring, trace                                  │
│  - email, documents, datasources                            │
│  - memory, checkpoints, workflow                            │
│  [Handles HTTP, validation, serialisation]                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Function Calls
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   Services Layer                            │
│  Business Logic (30+ service domains)                       │
│  - execution, graph, nodes                                  │
│  - document, email, datasource                              │
│  - conditions, delegation, workflow                         │
│  - memory, metrics, tracing                                 │
│  [Framework-agnostic, reusable, testable]                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ SQL + LangGraph APIs
                         │
┌────────────────────────▼────────────────────────────────────┐
│                 Data & Integration Layer                    │
│  - PostgreSQL (via SQLAlchemy)                              │
│  - LangGraph StateGraph execution                           │
│  - External APIs (email providers, search, etc.)            │
│  - File system storage                                      │
└─────────────────────────────────────────────────────────────┘
```

## Technology Stack

### Backend Stack

#### Core Framework

- **FastAPI** - High-performance async web framework for Python
- **Python 3.11+** - Primary backend language
- **Uvicorn** - ASGI server for production deployment

#### AI & Workflow Engine

- **LangGraph** - State machine and workflow orchestration
- **LangChain** - AI agent framework and tool integration

#### Database & Persistence

- **PostgreSQL** - Primary relational database
  - Graph storage and versioning
  - Embedding storage for document search
  - Execution history and checkpoints
  - User management and access control
  - Workflow state persistence
- **SQLAlchemy** - ORM and database toolkit
- **Psycopg** - PostgreSQL adapter with connection pooling

#### LLM Providers

Multiple providers are supported:

- Azure OpenAI
- OpenAI
- Anthropic Claude
- Configurable model deployments

#### Communication Protocols

- **REST API** - Primary API interface
- **WebSocket** - Real-time execution streaming and event notifications
- **Server-Sent Events (SSE)** - HTTP-based streaming for long-running operations

### Frontend Stack

#### Core Framework

- **Next.js 15** - React framework with server-side rendering
- **React 19** - UI component library
- **TypeScript 5** - Type-safe JavaScript

#### UI Libraries

- **ReactFlow** - Visual workflow builder and graph editor
- **Tailwind CSS 4** - Utility-first CSS framework
- **Framer Motion** - Animation library
- **Lucide React** - Icon library

#### State Management & Data

- **React Hooks** - Built-in state management
- **Server-Sent Events** - Real-time updates from backend
- **WebSocket clients** - Bidirectional communication

#### Authentication

- **OAuth2-Proxy** - Authentication proxy layer
