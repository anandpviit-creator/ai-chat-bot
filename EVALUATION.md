# Evaluating Chatbot Performance with Ragas

This project includes a framework for evaluating the performance of the Retrieval-Augmented Generation (RAG) system using the **Ragas** library. This allows you to quantitatively measure the quality of the chatbot's responses.

## How It Works

The `run_evaluation.py` script automates the following process:
1.  **Loads Questions:** It reads a predefined list of questions and their "ground truth" (ideal) answers from `evaluation_dataset.jsonl`.
2.  **Queries the Chatbot:** For each question, it calls the live chatbot API to get its generated answer and the context it retrieved to produce that answer.
3.  **Calculates Metrics:** It uses Ragas to compare the chatbot's output against the ground truth and calculates several key metrics.
4.  **Reports Results:** It prints a summary of the scores for each metric.

## Key Metrics

The evaluation script measures the following:
-   **Faithfulness:** How much the generated answer is grounded in the provided context. A low faithfulness score means the chatbot is "hallucinating" or making things up.
-   **Answer Relevancy:** How relevant the answer is to the user's question.
-   **Context Precision:** Measures the signal-to-noise ratio of the retrieved context. A low score means the retrieved documents were not relevant to the question.
-   **Context Recall:** Measures how well the retrieved context covers the information needed to answer the question based on the ground truth.

## How to Run the Evaluation

1.  **Ensure Services are Running:** The main application stack must be running. You can start it with:
    ```bash
    docker-compose up -d
    ```

2.  **Customize the Evaluation Dataset:**
    -   Open the `evaluation_dataset.jsonl` file.
    -   Add your own questions and ideal "ground truth" answers. A good evaluation set should have at least 10-20 diverse questions.

3.  **Run the Evaluation Script:**
    -   Execute the script from your terminal. This script runs on your **local machine**, not inside a Docker container, as it needs to make API calls to the service.
    -   Make sure you have installed the dependencies first (`pip install -r requirements.txt`).
    ```bash
    python run_evaluation.py
    ```

4.  **Analyze the Results:**
    -   The script will print a summary of the Ragas scores to the console. The scores range from 0 to 1, with higher scores being better.
    -   This allows you to track the impact of changes. For example, you can run the evaluation, change an LLM prompt, and then run it again to see if your scores improved.
