import os
import json
import requests
import pandas as pd
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_recall, context_precision
from datasets import Dataset

# --- Configuration ---
CHATBOT_API_URL = "http://localhost:8000/chat"
EVALUATION_DATASET_PATH = "evaluation_dataset.jsonl"

def load_evaluation_data(path: str) -> list:
    """Loads the evaluation dataset from a .jsonl file."""
    with open(path, 'r') as f:
        return [json.loads(line) for line in f]

def query_chatbot(question: str) -> dict:
    """
    Queries the chatbot API and returns the answer and retrieved contexts.
    Returns a dictionary with 'answer' and 'contexts' keys.
    """
    try:
        response = requests.post(
            CHATBOT_API_URL,
            json={"query": question},
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        data = response.json()

        # Extract the content from the retrieved documents to form the contexts
        contexts = [doc['content'] for doc in data.get('retrieved_documents', [])]

        return {
            "answer": data.get("answer", ""),
            "contexts": contexts
        }
    except requests.exceptions.RequestException as e:
        print(f"Error querying chatbot API: {e}")
        return {"answer": "", "contexts": []}

def run_evaluation():
    """
    Runs the full evaluation pipeline using Ragas.
    """
    print("--- Starting Evaluation Pipeline ---")

    # 1. Load the dataset
    print(f"Loading evaluation dataset from: {EVALUATION_DATASET_PATH}")
    eval_data = load_evaluation_data(EVALUATION_DATASET_PATH)
    if not eval_data:
        print("Evaluation dataset is empty. Exiting.")
        return

    questions = [item['question'] for item in eval_data]
    ground_truths = [item['ground_truth'] for item in eval_data]

    # 2. Query the chatbot for each question to get answers and contexts
    print("Querying chatbot to get generated answers and contexts...")
    results = [query_chatbot(q) for q in questions]
    answers = [r['answer'] for r in results]
    contexts = [r['contexts'] for r in results]

    # 3. Create a Hugging Face Dataset object, which is what Ragas expects
    dataset_dict = {
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths,
    }
    dataset = Dataset.from_dict(dataset_dict)

    # 4. Define the metrics and run the evaluation
    print("Running Ragas evaluation...")
    metrics = [
        faithfulness,      # How much the answer is grounded in the context
        answer_relevancy,  # How relevant the answer is to the question
        context_recall,    # How well the context captures the ground truth
        context_precision, # How signal-to-noise the context is
    ]

    result = evaluate(dataset, metrics=metrics)
    print("--- Evaluation Finished ---")

    # 5. Print the results
    print("Evaluation Metrics:")
    print(result)

    # Convert to a pandas DataFrame for better display
    df = result.to_pandas()
    print("\nEvaluation Results DataFrame:")
    print(df.head())

if __name__ == "__main__":
    # Ensure the chatbot service is running before starting the evaluation
    print("Please ensure the chatbot service is running via 'docker-compose up'.")
    run_evaluation()
