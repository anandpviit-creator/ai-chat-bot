import argparse
import time
from src.indexing_logic import ConfluenceIndexer

def main():
    """
    Main entry point for the command-line indexing script.
    Provides an argument to clear existing data before indexing.
    """
    parser = argparse.ArgumentParser(description="Confluence Indexing Script")
    parser.add_argument(
        "--reindex",
        action="store_true",
        help="If set, all existing data will be cleared from the databases before starting the indexing process."
    )
    args = parser.parse_args()

    print("--- Confluence Indexing Initialized ---")
    if args.reindex:
        print("Re-indexing flag set. All existing data will be cleared.")

    # A small delay to ensure other services like Postgres and OpenSearch are fully ready.
    time.sleep(10)

    indexer = ConfluenceIndexer()
    indexer.run_indexing(clear_first=args.reindex)

    print("--- Confluence Indexing Finished ---")

if __name__ == "__main__":
    main()
