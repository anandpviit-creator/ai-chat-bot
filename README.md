# Confluence Q&A Backend with Hybrid Search

This project implements a backend for a question-answering chatbot that uses documents from a Confluence space as its knowledge base. It leverages a hybrid search approach, combining keyword-based search with semantic search to retrieve the most relevant information, and uses a local Mistral model to generate natural language responses.

## Features

- **Hybrid Search**: Combines keyword search (OpenSearch) and semantic search (PGVector) for improved retrieval accuracy.
- **LangGraph Orchestration**: Uses LangGraph to manage the flow of running searches in parallel, fusing results, and generating a response.
- **Local LLM**: Utilizes a local Mistral model for generation, ensuring data privacy and reducing reliance on external APIs.
- **Confluence Integration**: Fetches and indexes documents directly from Confluence.
- **Dockerized**: All services (FastAPI app, OpenSearch, PostgreSQL/PGVector) are containerized with Docker for easy setup and deployment.

## Architecture

The system is designed around a multi-stage process:

1.  **Indexing**: A script (`index_confluence.py`) fetches documents from Confluence, splits them into chunks, and indexes them into both OpenSearch (for keyword matching) and a PostgreSQL database with the PGVector extension (for semantic similarity).
2.  **Query Processing**: A user query is received via a FastAPI endpoint.
3.  **Parallel Search**: The query is sent to two parallel search pipelines orchestrated by LangGraph:
    - **Keyword Search**: The query is sent to OpenSearch.
    - **Semantic Search**: The query is converted into a vector embedding and used to search for similar vectors in PGVector.
4.  **Result Fusion**: The results from both searches are combined and re-ranked using a weighted scoring algorithm (Reciprocal Rank Fusion) to produce a final, hybrid-ranked list of document chunks.
5.  **Response Generation**: The top-ranked document chunks are passed as context to the local Mistral LLM, which generates a coherent, human-readable answer.

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.9+
- A Confluence account with an API token.

### Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-name>
    ```

2.  **Set up environment variables:**
    - Copy the example environment file:
      ```bash
      cp .env.example .env
      ```
    - Edit the `.env` file with your specific configurations:
      - `CONFLUENCE_URL`: Your Confluence instance URL (e.g., `https://your-domain.atlassian.net`).
      - `CONFLUENCE_USERNAME`: Your Confluence username (usually your email).
      - `CONFLUENCE_API_TOKEN`: Your Confluence API token.
      - `CONFLUENCE_SPACE_KEY`: The key of the Confluence space you want to index.

3.  **Build and run the services:**
    ```bash
    docker-compose up --build
    ```
    This command will build the Docker images and start the FastAPI application, OpenSearch, and PostgreSQL containers.

4.  **Run the indexing script:**
    - Open a new terminal and execute the following command to run the indexing process inside the running container:
    ```bash
    docker-compose exec app python index_confluence.py
    ```

### Usage

Once the services are running and the data is indexed, you can send queries to the chatbot via the FastAPI endpoint.

- **Endpoint**: `http://localhost:8000/chat`
- **Method**: `POST`
- **Body** (JSON):
  ```json
  {
    "query": "Your question about the Confluence documents"
  }
  ```

You can use a tool like `curl` or Postman to interact with the API:

```bash
curl -X POST "http://localhost:8000/chat" \
-H "Content-Type: application/json" \
-d '{"query": "How do I set up a development environment?"}'
```

## VS Code Debugging

This project includes a VS Code launch configuration for debugging the FastAPI application.

1.  Open the project in VS Code.
2.  Make sure the Docker containers are running (`docker-compose up`).
3.  Go to the "Run and Debug" panel (Ctrl+Shift+D).
4.  Select the "Python: Attach to Docker" configuration from the dropdown and press F5.

The debugger will attach to the running FastAPI process inside the `app` container. You can now set breakpoints and inspect variables.
