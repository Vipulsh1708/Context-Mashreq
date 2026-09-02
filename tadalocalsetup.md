# TADA (Agentic AI Platform) – Local Setup Guide

Classification: Internal Use

## 1. Architecture Overview

The platform consists of three core microservices that work together to provide agentic AI functionality:

```
User Request
      |
      v
RunnerAI (Orchestrator)
  - LLM Interactions (OpenAI, Azure OpenAI)
  - Workflow Orchestration
  - API Gateway (REST endpoints)
  - Business Logic (investment research, workflows)
      |             |
      v             v
Ingester Service     Data Agent MCP Server
  - OCR Processing      - Database Schema Access
  - PDF Parsing          - Read-only SQL Queries
  - Document Chunking    - Text-to-SQL Mapping
  - Data Vectorization   - Multi-DB Support
```

**Data Flow:**
1. **RunnerAI** receives user requests and handles LLM reasoning
2. For data ingestion tasks → delegates to **Ingester Service**
3. For database queries → calls tools exposed by **Data Agent MCP**

## 2. Repository Structure

| Repository | Role | URL |
|---|---|---|
| **ds-agenticai-runnerAI** | Main Orchestrator | `https://dev.azure.com/MashreqCorpTech/Data/_git/ds-agenticai-runnerAI` |
| **ds-agenticai-ingester** | Data Ingestion & Processing | `https://dev.azure.com/MashreqCorpTech/Data/_git/ds-agenticai-ingester` |
| **ds-agenticai-dataagentmcp** | Database Access (MCP Server) | `https://dev.azure.com/MashreqCorpTech/Data/_git/ds-agenticai-dataagentmcp` |
| **ds-agenticai-frontend** | React JS (TypeScript) Frontend | (clone URL used in your workflow) |
| **ds-agenticai-authz** | Authentication & Authorization (Spring Boot) | (clone URL used in your workflow) |
| **ds-agenticai-backend** | Backend Service (Spring Boot) | (clone URL used in your workflow) |

## 3. Prerequisites (Python Services)

### 3.1 Required Software

| Software | Version | Purpose |
|---|---|---|
| Python | 3.12.4 | Runtime environment |
| Git | Latest | Version control |
| Docker | Latest | Containerization (optional) |

**Python Version Management:** Use `pyenv` or `conda` for managing Python versions.

### 3.2 System Dependencies

**macOS (Homebrew):**
```bash
brew install libreoffice tesseract poppler ffmpeg cmake postgresql
```

| Dependency | Purpose |
|---|---|
| `libreoffice` | Document conversion (DOCX → PDF) |
| `tesseract` | OCR (Optical Character Recognition) |
| `poppler` | PDF processing |
| `ffmpeg` | Multimedia processing |
| `cmake` | Building Python extensions |
| `postgresql` | PostgreSQL client libraries (`libpq`) |

**Alternative (Conda):**
```bash
conda install -c conda-forge poppler ffmpeg tesseract
```
> Note: `libreoffice` still requires Homebrew or manual installation.

**Linux/Debian/Ubuntu:**
```bash
sudo apt-get update
sudo apt-get install -y \
    libreoffice \
    tesseract-ocr \
    poppler-utils \
    ffmpeg \
    cmake \
    libpq-dev \
    gcc
```

### 3.3 SQL Server Driver (if using SQL Server)

Install ODBC Driver 17 or 18 for SQL Server (required for `pyodbc`).

### 3.4 Frontend Prerequisites

Ensure the following are installed on your system:
- Node.js: 22.14.0
- NPM: 10.9.0
- IDE: Visual Studio Code
- Git

Verify versions:
```bash
node -v
npm -v
```

---

## 4. Setup: RunnerAI (Main Orchestrator)

### Step 1: Clone the Repository
```bash
git clone https://dev.azure.com/MashreqCorpTech/Data/_git/ds-agenticai-runnerAI
cd ds-agenticai-runnerAI
```

### Step 2: Create Virtual Environment

**Option A: Using venv (Standard)**
```bash
python3.12 -m venv venv
source venv/bin/activate
```

**Option B: Using Conda (Recommended)**
```bash
conda create -n runner-gpt python=3.12.4
conda activate runner-gpt
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```
Or use the Makefile:
```bash
make build
```

### Step 4: Configure Environment Variables
```bash
# Create environment file
touch .env.local

# Edit with your preferred editor
nano .env.local
```

Add the required variables:
```bash
# Core Settings
ENVIRONMENT=local
LOG_LEVEL=DEBUG
CORS_ORIGINS=http://localhost:3000

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER_NAME=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DATABASE_NAME=runner_gpt

# Vector Database
VECTOR_DATABASE_TO_USE=pinecone
```

### Step 5: Start the Service
```bash
source venv/bin/activate  # if not already active
python runner_gpt/runner_gpt_service.py
```

### Step 6: Verify Installation
```bash
pytest tests/test_evals_service.py
```

---

## 5. Setup: Ingester Service

### Step 1: Clone the Repository
```bash
git clone https://dev.azure.com/MashreqCorpTech/Data/_git/ds-agenticai-ingester
cd ds-agenticai-ingester
```

### Step 2: Create Virtual Environment
```bash
python3.12 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Create a `.env` file:
```bash
cp example.env .env
nano .env
```

```bash
# Core Settings
CALLBACK_API_HOSTNAME=
LOG_LEVEL=INFO

# Metadata Database (stores connection configs)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER_NAME=postgres
POSTGRES_PASSWORD=password
NEW_DB_NAME=smart_mcp_meta
DB_TYPE=postgres

# Vector Database
VECTOR_DB=pinecone
INDEX_NAME=sqlquery-samples
PINECONE_API_KEY=your-pinecone-key
```

### Step 5: Start the Service

**Option A: Run Locally**
```bash
python runner_gpt/runner_gpt_service.py
```

**Option B: Run with Docker**
```bash
# Build the image
make build
# or: docker build -t ingester-service .

# Run the container
docker run --env-file .env -p 8081:8081 ingester-service
```

### Step 6: Verify Installation
```bash
python tests/evals_service.py
# or
pytest
```

---

## 6. Setup: Data Agent MCP Server

### Step 1: Clone the Repository
```bash
git clone https://dev.azure.com/MashreqCorpTech/Data/_git/ds-agenticai-dataagentmcp
cd ds-agenticai-dataagentmcp
```

### Step 2: Create Virtual Environment
```bash
python3.10 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
```bash
cp example.env .env
nano .env
```

```bash
# Metadata / Vector Database
VECTOR_DATABASE_TO_USE=pinecone
PINECONE_API_KEY=your-pinecone-key
PINECONE_ENVIRONMENT=us-east-1
PINECONE_INDEX_NAME=sqlquery-samples

# LLM Configuration
LLM_SERVICE=openai
LLM_MODEL_NAME=gpt-4-turbo
LLM_TEMPERATURE=0.1
LLM_TOKEN_LIMIT=30000
```

### Step 5: Start the Server
```bash
python main.py --port 8000
```

### Step 6: Verify Installation

Access the following endpoints:
- **Root Info:** `http://localhost:8000/`
- **API Docs (Swagger):** `http://localhost:8000/api/docs`
- **MCP Endpoint:** `http://localhost:8000/mcp`

---

## 7. Environment Variables Reference

### 7.1 Common Variables (All Services)

| Variable | Description | Example |
|---|---|---|
| `ENVIRONMENT` | Deployment environment | `local`, `uat`, `prod` |
| `LOG_LEVEL` | Logging verbosity | `DEBUG`, `INFO`, `WARNING` |

### 7.2 Database Configuration

| Variable | Description | Example |
|---|---|---|
| `POSTGRES_HOST` | PostgreSQL host | `localhost` |
| `POSTGRES_PORT` | PostgreSQL port | `5432` |
| `POSTGRES_USER_NAME` | Database username | `postgres` |
| `POSTGRES_PASSWORD` | Database password | `your_password` |
| `POSTGRES_DATABASE_NAME` | Database name | `runner_gpt` |

### 7.3 Vector Database Configuration

| Variable | Description | Example |
|---|---|---|
| `VECTOR_DATABASE_TO_USE` | Vector DB provider | `pinecone` or `opensearch` |
| `PINECONE_API_KEY` | Pinecone API key | `your-key` |
| `PINECONE_ENV` | Pinecone environment | `us-east-1` |
| `OPENSEARCH_URL` | OpenSearch URL | `https://...` |
| `OPENSEARCH_USERNAME` | OpenSearch username | `admin` |
| `OPENSEARCH_PASSWORD` | OpenSearch password | `admin` |

### 7.4 LLM Configuration

| Variable | Description | Example |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |
| `AZURE_ENDPOINT_*` | Azure OpenAI endpoint | `https://...` |
| `AZURE_API_KEY_*` | Azure OpenAI key | `your-key` |
| `AZURE_DEPLOYMENT_*` | Azure deployment name | `gpt-4` |
| `LANGCHAIN_TRACING_V2` | Enable LangChain tracing | `true` or `false` |
| `LANGCHAIN_API_KEY` | LangChain API key | `your-key` |

### 7.5 AWS Configuration (Optional)

| Variable | Description | Example |
|---|---|---|
| `AWS_ACCESS_KEY_ID` | AWS access key | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | `your-secret` |
| `BUCKET_NAME` | S3 bucket name | `my-bucket` |
| `REGION_NAME` | AWS region | `us-east-1` |

### 7.6 External APIs

| Variable | Description | Example |
|---|---|---|
| `SERP_API_KEY` | SerpAPI key for search | `your-key` |
| `GOOGLE_API_KEY` | Google API key | `your-key` |
| `GOOGLE_CSE_ID` | Google Custom Search Engine ID | `your-cse-id` |

---

## 8. API Endpoints Quick Reference

### 8.1 RunnerAI Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/runner-gpt/multi-agent/workflow/stream-sse` | Multi-agent interactions (SSE) |
| WS | `/runner-gpt/multi-agent/workflow/stream` | Multi-agent WebSocket stream |
| POST | `/runner-gpt/workflow/stream-sse` | Workflow execution (SSE) |
| WS | `/runner-gpt/workflow/stream` | Workflow WebSocket stream |

### 8.2 Ingester Service Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/ingester-service/injest-doc` | Batch document ingestion |
| POST | `/ingester-service/tags/classify-document` | Document classification |

**Batch Ingestion Request Example:**
```json
{
  "skill_id": 123,
  "namespace": "your-namespace",
  "files": [
    {
      "request_id": 1001,
      "response_data_api_path": "/api/callback/status",
      "pre_signed_url": "https://s3.amazonaws.com/bucket/file.pdf",
      "file_name": "document.pdf",
      "original_file_name": "My Document.pdf",
      "process_type": "text",
      "file_type": "pdf",
      "metadata": []
    }
  ]
}
```

### 8.3 Data Agent MCP Server Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Root info |
| - | `/mcp` | MCP endpoint (Streamable HTTP) |
| GET | `/api/docs` | Swagger documentation |
| GET | `/api/databases` | List all databases |
| GET | `/api/databases/enabled` | List enabled databases |
| POST | `/api/databases` | Add new database |
| PUT | `/api/databases/{id}` | Update database config |
| DELETE | `/api/databases/{id}` | Remove database |
| GET | `/api/databases/{id}/test` | Test connection |
| PATCH | `/api/databases/{id}/tables` | Enable/disable tables |
| POST | `/api/databases/{id}/tables/reingest` | Regenerate summaries |
| GET | `/api/databases/{id}/summary` | Get database summary |
| GET | `/api/databases/{id}/summaries/tables` | Get table summaries |
| GET | `/api/databases/{id}/summaries/columns` | Get column summaries |
| POST | `/api/databases/{id}/summaries/regenerate` | Regenerate all summaries |

**MCP Tools Available:**
- `data_agent_schema_tool` – Retrieve database schema
- `data_agent_query_tool` – Execute read-only SQL queries
- `get_table_and_view_names_tool` – List all tables and views

Example search query body:
```json
{
  "params": {},
  "search_type": "HYBRID"
}
```

---

## 9. Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|---|---|---|
| `libcairo` / `poppler` errors | Missing system libraries | Run `brew install poppler` (macOS) or `apt-get install poppler-utils` (Linux) |
| `tesseract` not found | Missing OCR library | Run `brew install tesseract` (macOS) |
| Python version mismatch | Wrong Python version | Use `pyenv` or `conda` to install Python 3.12 |
| `pg_config` not found | Missing PostgreSQL dev libs | Run `brew install postgresql` or `apt-get install libpq-dev` |
| Module not found | PYTHONPATH not set | Run `export PYTHONPATH=$PYTHONPATH:.` or use `python -m module_name` |
| Database connection failed | Wrong credentials or host | Verify `.env` variables match your database setup |

### Verifying System Dependencies
```bash
# Check Python version
python --version   # Should show 3.12.x

# Check Tesseract
tesseract --version

# Check Poppler
pdftoppm -v

# Check FFmpeg
ffmpeg -version

# Check PostgreSQL client
pg_config --version
```

### Logs Location
- **RunnerAI:** Check console output or configure logging in `core/settings.py`
- **Ingester:** Check console output or Docker logs (`docker logs <container>`)
- **Data Agent MCP:** Check console output, controlled by `LOG_LEVEL` env var

---

## 10. Quick Start Checklist (Python Services)

- [ ] Python 3.12 installed and accessible
- [ ] System dependencies installed (tesseract, poppler, ffmpeg, etc.)
- [ ] All three repositories cloned
- [ ] Virtual environments created for each service
- [ ] Dependencies installed in each environment
- [ ] `.env` / `.env.local` files configured with required variables
- [ ] PostgreSQL database accessible
- [ ] Vector database (Pinecone/OpenSearch) configured
- [ ] LLM API keys set (OpenAI or Azure)
- [ ] All three services start without errors
- [ ] API endpoints accessible and responding

---

## 11. Run ds-agenticai-frontend Locally

This document describes how to run the **ds-agenticai-frontend** React JS with TypeScript application on a local machine for development and testing purposes.

### Repository Overview
- **Repository Name:** ds-agenticai-frontend
- **Project Type:** React JS (with TypeScript)
- **Default Local URL:** `http://localhost:5173/`

### Branch to Environment Mapping

| Branch Name | Environment URL |
|---|---|
| `qa` | tada.dev.mashreqdev.com |
| `tada-agent` | tada2.dev.mashreqdev.com |
| `prod` | tada.prod.mashreq.com |

### Configuration File

The project uses a custom config file: `config.ts`

### Steps to Run the Application Locally

**1. Clone the Repository**
```bash
git clone <repository-url>
cd ds-agenticai-frontend
```

**2. Checkout the Relevant Branch**
```bash
git checkout qa
# OR
git checkout tada-agent
# OR
git checkout prod
```

**3. Open the Project directory in VS Code**

**4. Open terminal in the root level of project directory**
```bash
npm run dev
```

The application will start on:
`http://localhost:5173/`

---

## 12. Run ds-agenticai-authz Locally

This document explains how to run the **ds-agenticai-authz** Spring Boot (Maven) application locally using IntelliJ IDEA.

### Repository Overview
- **Repository Name:** ds-agenticai-authz
- **Framework:** Spring Boot
- **Build Tool:** Maven
- **Purpose:** Authentication & Authorization service (Microsoft SSO, ID Token validation, JWT generation)

### Branch to Environment Mapping

| Branch | Environment | Domain |
|---|---|---|
| `qa` | QA | tada.dev.mashreqdev.com |
| `tada-agent` | Agent QA | tada2.dev.mashreqdev.com |
| `prod` | Production | tada.prod.mashreq.com |

> For local development, you will still use the `dev` Spring profile, regardless of branch.

### Configuration Files Used

The project uses `application.properties`-based configuration:
```
src/main/resources/
├── application.properties
├── application-dev.properties   ← Used for LOCAL
└── application-qa.properties
```

**Profile Resolution Order:**
`application.properties` → `application-dev.properties` (when dev profile is active)

### Local Runtime Requirements

Ensure the following versions are installed:
- Java: 21
- Maven: 3.9.9
- IDE: IntelliJ IDEA (recommended)
- Git

Verify versions:
```bash
java -version
mvn -version
git --version
```

### Local Port Configuration

- **Local Port:** 3000

Ensure the following exists in `application-dev.properties`:
```
server.port=3000
```

### Clone the Repository
```bash
git clone <repo-url>/ds-agenticai-authz.git
cd ds-agenticai-authz
```

### Checkout the Relevant Branch
```bash
# QA branch
git checkout qa

# OR Agent QA
git checkout tada-agent

# OR Production (read-only usage)
git checkout prod
```

> ⚠️ Do not modify production configuration values locally.

### Open the Project in IntelliJ IDEA
1. Open IntelliJ IDEA
2. Click **File → Open**
3. Select the cloned ds-agenticai-authz directory
4. Wait for Maven dependencies to download

### Verify Local Configuration (application-dev.properties)

Ensure local-specific values are present:
```
spring.profiles.active=dev
server.port=3000
spring.application.name=ds-agenticai-authz

# Azure AD / Microsoft SSO
azure.ad.tenant-id=<TENANT_ID>
azure.ad.client-id=<CLIENT_ID>
azure.ad.issuer-uri=https://login.microsoftonline.com/<TENANT_ID>/v2.0

# JWT Configuration
jwt.issuer=ds-agenticai
jwt.expiry.minutes=60
```

### Run the Application from IntelliJ

Navigate to: `src/main/java/com/foundation/gcai`

1. Locate the main Spring Boot class: `{AppName}Application.java`
2. Right-click on `{AppName}Application.java`
3. Click **Run '{AppName}Application'**

IntelliJ will start the application using:
- Java 21
- Maven 3.9.9
- Spring Profile: dev
- Port: 3000

### Verify Application is Running

Open browser and hit:
- `http://localhost:3000`
- `http://localhost:3000/swagger-ui/index.html#/`

Check logs in IntelliJ for: `Started {AppName}Application in XX seconds`

### Common Issues & Fixes

**❌ Port Already in Use**
Error: `Port 3000 already in use`
Fix:
- Stop the process using port 3000
- OR change port in `application-dev.properties`

**❌ Wrong Profile Loaded**
Symptom: App tries to connect to QA URLs
Fix:
```
spring.profiles.active=dev
```

**❌ SSO Redirect Error**
Fix: Ensure Azure AD App Registration contains:
`http://localhost:3000/login/oauth2/code/azure`

### Best Practices
- ✅ Always use `application-dev.properties` for local
- ❌ Never commit secrets
- ❌ Never modify `application-qa.properties` or prod values
- ✅ Keep Java & Maven versions aligned

### Summary
- ✅ Java 21 & Maven 3.9.9
- ✅ Port 3000
- ✅ dev profile for local
- ✅ IntelliJ-based run

---

## 13. Run ds-agenticai-backend Locally

This document describes how to run the **ds-agenticai-backend** Spring Boot Maven application on a local machine for development and testing purposes.

### Repository Overview
- **Repository Name:** ds-agenticai-backend
- **Project Type:** Spring Boot (Maven)
- **Default Local Port:** 3000

### Branch to Environment Mapping

| Branch | Environment URL |
|---|---|
| `qa` | tada.dev.mashreqdev.com |
| `tada-agent` | tada2.dev.mashreqdev.com |
| `prod` | tada.prod.mashreq.com |

Each branch is already configured to point to its respective environment. For local runs, the application will still start on localhost.

### Prerequisites

Ensure the following are installed on your system:
- Java: 21
- Maven: 3.9.9
- IDE: IntelliJ IDEA (recommended)
- Git

Verify versions:
```bash
java -version
mvn -version
```

### Configuration Files

The project uses Spring profiles with the following configuration files:
- application.properties
- application-dev.properties
- application-qa.properties

> Note: Local verification of application-dev.properties is **not required** and can be ignored for this setup.

### Steps to Run the Application Locally

**1. Clone the Repository**
```bash
git clone <repository-url>
cd ds-agenticai-backend
```

**2. Checkout the Relevant Branch**
```bash
git checkout qa
# OR
git checkout tada-agent
# OR
git checkout prod
```

**3. Open the Project in IntelliJ IDEA**
- Open IntelliJ IDEA
- Select **Open**
- Choose the ds-agenticai-backend project directory
- Allow Maven dependencies to download

**4. Select and Run the Main Application Class**

Navigate to: `src/main/java/com/foundation/gcai`

1. Locate the main Spring Boot application file: `{AppName}Application.java`
2. Right-click on the file
3. Click **Run '{AppName}Application'**

The application will start on:
- `http://localhost:3000`
- `http://{baseurl}/service-gpt/swagger-ui/index.html#/`
