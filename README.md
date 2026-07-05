# ForgeKB AI - Agentic RAG System (GenAI Engineer Project)

ForgeKB AI is an end-to-end Agentic AI + RAG platform I built using Python and FastAPI, with LangChain and LangGraph as the core orchestration layer and LangSmith-ready tracing hooks.

This project demonstrates practical GenAI engineering patterns: role-based knowledge isolation, asynchronous ingestion, hybrid retrieval, grounded generation, and streaming UX.

## Product Screenshots

### Login

![Login Page](docs/LOGIN_Page.png)

### Signup

![Signup Page](docs/SIGNUP_Page.png)

### User Dashboard

![User Dashboard](docs/USER_Page.png)

### Admin User Management

![Admin User Management](docs/ADMIN_User_Management_Page.png)

### Admin Knowledge Base Management

![Admin Knowledge Base Management](docs/ADMIN_Knowledge_Base_Management_Dashboard.png)

## What This Project Demonstrates

- Building production-style RAG APIs with FastAPI and Python
- Designing an agentic retrieval workflow with LangGraph
- Implementing retrieval and generation chains with LangChain
- Integrating observability hooks for LangSmith tracing
- Running a complete local stack with Docker Compose

## Core Tech Stack

- Language: Python
- API Layer: FastAPI
- Agentic Orchestration: LangGraph
- LLM and Retrieval Framework: LangChain
- Tracing/Observability: LangSmith hooks + structured logs
- Vector Store: FAISS (local)
- Hybrid Search: FAISS semantic + BM25 keyword fusion
- Async Task Queue: Celery + Redis
- Data Layer: MySQL (users, sessions, feedback, datasource registry, audit)
- Frontend: React + Vite + Ant Design

## Agentic AI Architecture

LangGraph state flow drives retrieval before generation:

1. Analyze query intent (factual / analytical / balanced)
2. Refine query and route retrieval strategy
3. Retrieve contexts using hybrid search
4. Score/rerank contexts and compute confidence
5. Generate grounded answer with citations
6. Stream structured events to UI

## RAG Capabilities Implemented

1. Multi-format ingestion: txt, md, pdf, docx
2. Async ingestion pipeline with progress telemetry
3. Recursive chunking for context windows
4. Local embedding generation with sentence-transformers
5. FAISS vector indexing and persistence
6. BM25 keyword search
7. Hybrid retrieval with weighted fusion scoring
8. Query expansion (multi-query rewrite)
9. Parent-context enrichment for better grounding
10. Optional cross-encoder reranking
11. Confidence scoring and abstention logic
12. Citation generation for answer traceability
13. SSE streaming endpoint with token/citation/confidence events
14. History-aware prompting for multi-turn chat
15. Same-file-name latest-version preference in retrieval

## Role-Based Product Features

### Admin

- Admin console for validation chat
- Dedicated knowledge base dashboard
- Single upload + bulk upload
- Single delete + multi-select delete
- User management: promote/demote/offboard

### User

- Personal workspace and chat history
- Upload and manage own files
- Thread-by-thread chat deletion
- Feedback submission on responses

### Access Boundaries

- Admin knowledge is global
- User uploads are user-scoped
- Metadata-aware retrieval and file operations

## Project Structure

- [backend](backend): FastAPI app, LangGraph/LangChain services, Celery tasks
- [frontend](frontend): React dashboards for User/Admin workflows
- [data/uploads](data/uploads): Uploaded documents
- [data/faiss](data/faiss): Vector index and chunk manifest
- [docker-compose.yml](docker-compose.yml): Local orchestration
- [requirements.txt](requirements.txt): root Python requirements entrypoint

## Setup and Run

### 1. Configure Environment

Set API key in [backend/.env](backend/.env):

- OPENAI_API_KEY=your_key_here

Optional for tracing:

- LANGCHAIN_API_KEY=your_langsmith_key

### 2. Start Full Stack

```bash
docker compose up -d --build
```

### 3. Access

- Frontend: http://localhost:3001
- Backend Health: http://localhost:8001/api/health

## API Surface (Highlights)

- Auth: /api/auth/register, /api/auth/login, /api/auth/me, /api/auth/logout
- Chat: /api/chat, /api/chat/stream
- History: /api/history/sessions, /api/history/sessions/{id}
- Datasources: /api/datasources, /api/datasources/upload, /api/datasources/upload/bulk, /api/datasources/retry
- Admin: /api/admin/users, /api/admin/users/{id}/role
- Evaluation: /api/eval/run

## Why This Is Interview-Relevant

- Shows practical Agentic AI implementation beyond prompt-only apps
- Covers full lifecycle: ingestion, retrieval, orchestration, generation, streaming
- Includes role-based product design and data governance patterns
- Demonstrates production-aware engineering tradeoffs in a local-first setup

## GenAI Engineer Profile Alignment

This project demonstrates the full RAG lifecycle expected from a GenAI Engineer role:

- Ingestion and indexing: document parsing, chunking, embedding generation, FAISS indexing, lifecycle tracking.
- Retrieval engineering: hybrid semantic + keyword search, query routing, query expansion, reranking, confidence scoring.
- Agentic orchestration: LangGraph state flow for query analysis and retrieval strategy before generation.
- LLM integration: LangChain-powered retrieval/generation with grounded prompting and citation-first answers.
- API engineering: FastAPI services for auth, chat, history, ingestion, admin controls, and evaluation.
- Asynchronous systems: Celery + Redis pipeline for background indexing and telemetry updates.
- Product and governance: role-based access, admin/global knowledge controls, user-scoped private knowledge.
- Observability and evaluation: structured streaming events, logs, and LangSmith-ready tracing hooks.

Frameworks and tools used:

- Python, FastAPI, SQLAlchemy
- LangChain, LangGraph, LangSmith hooks
- FAISS, rank-bm25, sentence-transformers
- Celery, Redis, MySQL
- React, Vite, Ant Design
- Docker, Docker Compose

## Skills Demonstrated (ATS-Friendly)

Target role: Generative AI Engineer / LLM Engineer / Applied AI Engineer

Keywords covered in this project:

- Agentic AI, Retrieval-Augmented Generation (RAG), Hybrid Search
- LangChain, LangGraph, LangSmith, Prompt Engineering
- FastAPI, Python, SQLAlchemy, REST API Development
- FAISS, BM25, Embeddings, Reranking, Citation Grounding
- Asynchronous Processing, Celery, Redis, Background Jobs
- MySQL, Data Modeling, Role-Based Access Control (RBAC)
- SSE Streaming, Real-Time UX, Observability, Evaluation
- Docker, Docker Compose, Local Production-Style Deployment

Impact summary:

- Designed and implemented an end-to-end Agentic RAG system from ingestion to grounded response streaming.
- Built role-aware knowledge workflows with admin-global and user-private data boundaries.
- Improved retrieval quality through query routing, expansion, score fusion, and optional reranking.
