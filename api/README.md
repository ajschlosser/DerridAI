# DerridAI API

This project contains the backend services for DerridAI, providing endpoints for corpus building, record management, and RAG interactions.

## Overview

- **Framework**: FastAPI
- **Language**: Python 3.12
- **Key Features**:
  - Corpus builder (PDF to JSONL)
  - Record review and editing
  - RAG-based retrieval and generation
  - User authentication and authorization

## Getting Started

### Local Development

To get started with the API locally, follow these steps:

1. **Environment Setup**:
   Ensure you have Docker and Docker Compose installed. Create a `.env` file in the root directory (or copy `.env.example`) and configure your API keys and local settings.

2. **Start the Services**:
   Run the following command to build and start the backend and frontend:

   ```bash
   docker compose up -d --build
   ```

3. **Access the API**:
   - **Swagger UI**: `http://localhost:8000/docs`
   - **Redoc**: `http://localhost:8000/redoc`

### Codebase Navigation

The `api/` directory contains the core backend logic. Here is a breakdown of the primary components:

- `app/`: The main FastAPI application.
  - `main.py`: Entry point for the FastAPI application, defining routes and middleware.
  - `config.py`: Configuration management using environment variables.
  - `auth.py`: Authentication and authorization logic.
  - `models/`: Pydantic models for request/response validation and SQLAlchemy models for database interaction.
  - `routes/`: (If applicable) Organized API endpoints.
- `corpus_builder.py`: The core logic for the ingestion pipeline (PDF $\rightarrow$ JSONL).
- `chroma_store.py`: Logic for interacting with the ChromaDB vector store.
- `rag.py`: The RAG engine implementation, including retrieval and reranking.
- `llm.py` / `llm_tools.py`: Integration with various LLM providers (Ollama, OpenAI, etc.).
- `jobs.py`: Background task processing using Celery or similar.
- `persistence.py` / `system_store.py`: Database interaction layer for SQLite.
- `locales/`: Translation files for multi-language support.

## Documentation

The API documentation can be accessed at:
`http://localhost:8000/docs`

## Architecture & Capabilities

The API serves as the central hub for the DerridAI ecosystem, managing the lifecycle of scholarly data from ingestion to retrieval. It is built with FastAPI and follows a modular architecture:

- **Ingestion Pipeline**: Handles the conversion of raw PDFs into structured JSONL records. This pipeline is specifically engineered for scholarly texts, ensuring that complex academic structures are preserved during conversion. This includes:
  - **Extraction**: Extracting text from PDF files while preserving layout, footnotes, and citations.
  - **Segmentation**: Breaking down long texts into manageable chunks while maintaining context and ensuring that citations remain linked to their respective claims.
  - **Enrichment**: Automatically identifying and assigning metadata (e.g., speaker, stance, evidence) to each segment. A critical component of this phase is the preservation of scholarly provenance: the system distinguishes between the primary author's voice and the voices of cited scholars, ensuring that the distinction between the author's voice and the voices of cited scholars is maintained in the final data structure.
- **Storage Layer**: Manages a hybrid storage system designed for both structured metadata management and high-dimensional vector search:
  - **Relational Database (SQLite)**: Serves as the source of truth for structured data, including user accounts, session state, and the primary metadata for every record. It ensures ACID compliance for critical system operations.
  - **Vector Store (ChromaDB)**: Powers the semantic retrieval engine by storing high-dimensional embeddings. It is optimized for rapid similarity searches, allowing the system to retrieve the most relevant scholarly segments in milliseconds.
- **RAG Engine**: Orchestrates the retrieval-augmented generation process to ensure evidence-grounded outputs:
  - **Retrieval**: Executes multi-vector searches to fetch relevant segments. It utilizes hybrid search techniques to combine semantic similarity with keyword matching.
  - **Reranking**: Processes the retrieved candidates through a reranking model to prioritize the most contextually relevant segments, ensuring the most critical information is prioritized within the LLM's context window.
  - **Generation**: Interfaces with a variety of LLM providers (including local models via Ollama and remote models via OpenAI-compatible APIs). It enforces strict grounding, ensuring that the model's output is directly supported by the retrieved evidence.
- **Auth & Security**: Implements a robust security layer to protect the integrity of the scholarly corpus:
  - **Authentication**: Secure login and session management for different user roles.
  - **Authorization**: Role-Based Access Control (RBAC) ensures that only authorized users can perform specific actions, such as modifying the core corpus or performing advanced research queries.
  - **Data Integrity**: Ensures that the transition from raw data to structured records maintains a strict chain of provenance.

## Gotchas & Known Issues

While the system is designed for robustness, there are several critical areas that require attention during setup and development:

- **Environment Configuration**: A properly populated `.env` file is mandatory. Ensure you have specific keys for your LLM provider (e.g., `OPENAI_API_KEY`) and local services.
- **Ollama Dependency**: If using local models, the Ollama service must be running and the specific models must be pre-pulled (e.g., `ollama pull llama3`).
- **Docker Build Logic**: The build process uses a `gitmeta` mount to capture repository metadata. This requires a valid git history to be present during the build phase.
- **Port Conflicts**: The API typically runs on port `8000` and Ollama on `11434`. Ensure these are not occupied by other services on your host machine.
- **ChromaDB Persistence**: Ensure that the Docker volumes for ChromaDB are correctly mapped; otherwise, the vector index will be lost upon container restart.
