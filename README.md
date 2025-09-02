# Confluence Q&A Backend with Agentic Hybrid Search

This project implements a sophisticated backend for a question-answering chatbot that uses documents from Confluence as its knowledge base. It leverages an advanced agentic architecture to provide accurate answers from multiple data sources, including a traditional vector search and a knowledge graph.

## Features

-   **Agentic Architecture**: Uses LangGraph to create a smart agent that can reason and choose the best tool for a given question.
-   **Hybrid Document Search**: Combines keyword search (OpenSearch) and semantic search (PGVector) for high-quality document retrieval.
-   **Knowledge Graph Search**: Includes a Neo4j knowledge graph, automatically built from your Confluence data. The agent can query this graph to answer complex, relational questions.
-   **Dynamic Tool Use**: The agent intelligently decides whether to use the document search or the knowledge graph search based on the user's query.
-   **Conversation Memory**: The chatbot remembers the context of the conversation to answer follow-up questions.
-   **Local LLM**: Utilizes a local Mistral model (via Ollama) for all reasoning and generation, ensuring data privacy and reducing costs.
-   **Granular Data Indexing**: Configure the system to index entire Confluence spaces or just specific "folders" (parent pages).
-   **Automated Re-indexing**: Includes scripts and documentation for setting up periodic re-indexing to keep the knowledge base fresh.
-   **Performance Evaluation**: Comes with a built-in evaluation framework using the Ragas library to quantitatively measure the chatbot's performance.
-   **Dockerized**: All services (FastAPI app, OpenSearch, PostgreSQL/PGVector, Neo4j) are containerized with Docker for easy setup and deployment.

## Architecture

The system is designed around a multi-stage agentic workflow orchestrated by LangGraph:

1.  **Indexing (Offline Process)**: The `index_confluence.py` script fetches content from your specified Confluence spaces or folders. It indexes the text in two ways:
    -   **Vector/Keyword Search**: Chunks of text are indexed into OpenSearch (for keywords) and PGVector (for semantic meaning).
    -   **Knowledge Graph**: An LLM extracts entities (like people, projects, pages) and their relationships from the text, which are then loaded into a Neo4j graph database.

2.  **Query Processing (Live Query)**:
    -   A user query is received via a FastAPI endpoint.
    -   **Space Classification:** The agent first determines which Confluence space is most relevant to the query.
    -   **Router:** The agent then analyzes the query to decide on the best tool: `document_search` for general questions or `graph_search` for relational questions.
    -   **Tool Execution:**
        -   If `document_search` is chosen, a hybrid search is performed in parallel across OpenSearch and PGVector, and the results are fused.
        -   If `graph_search` is chosen, an LLM converts the query into a Cypher query, which is then executed against the Neo4j database.
    -   **Response Generation:** The retrieved context (either documents or graph data) and the conversation history are passed to the local Mistral LLM to generate a coherent, human-readable answer.

## Getting Started

### Prerequisites

-   Docker and Docker Compose
-   Python 3.9+
-   A Confluence account with an API token.
-   Ollama running locally with the `mistral` model pulled (`ollama pull mistral`).

### Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-name>
    ```

2.  **Set up environment variables:**
    -   Copy the example environment file: `cp .env.example .env`
    -   Edit the `.env` file with your specific configurations for Confluence and Neo4j. Pay special attention to `CONFLUENCE_SOURCES`.

3.  **Build and run the services:**
    ```bash
    docker-compose up --build -d
    ```
    This command will build the Docker images and start all services (FastAPI app, OpenSearch, PostgreSQL, Neo4j) in the background.

4.  **Run the indexing script:**
    -   Open a new terminal and execute the following command to run the indexing process. This will populate your databases and the knowledge graph.
    ```bash
    docker-compose exec app python index_confluence.py
    ```
    -   For subsequent updates, you can run `docker-compose exec app python index_confluence.py --reindex` to clear old data first. See `SCHEDULING.md` for automating this.

### Usage

Once the services are running and the data is indexed, you can send queries to the chatbot via the FastAPI endpoint. The API supports conversation history.

-   **Endpoint**: `http://localhost:8000/chat`
-   **Method**: `POST`
-   **Body** (JSON):
    ```json
    {
      "query": "Your question about the Confluence documents",
      "chat_history": [
        {"role": "human", "content": "An earlier question..."},
        {"role": "ai", "content": "An earlier answer..."}
      ]
    }
    ```

You can use a tool like `curl` or Postman to interact with the API. See `EVALUATION.md` for details on how to measure the performance of your chatbot.
