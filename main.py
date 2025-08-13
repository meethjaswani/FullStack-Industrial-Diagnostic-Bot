import asyncio
import os
import sys

from scada.generate_scada_db import generate_database

# Add the parent directory of 'agents' to the Python path
# This allows imports like 'from agents.orchestrator import Orchestrator' to work
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir) # Add newSentient directory to path

# Import the Orchestrator
from agents.orchestrator import Orchestrator

# Import the data initialization functions from your existing manual and scada directories
# Assuming these are structured like:
# newSentient/manual/manual_vector_store.py (for VectorStoreManager)
# newSentient/scada/scada_database.py (for generate_scada_db)
from manual.create_vector_store import VectorStoreManager
from scada.generate_scada_db import generate_database # Changed name here

async def ensure_data_ready():
    """
    Initializes SCADA database and vector store if needed.
    This function is copied/adapted from your original main_plan_execute.py.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Check and create SCADA database
    db_path = os.path.join(base_dir, "data", "scada_data.db")
    if not os.path.exists(db_path):
        print("Generating SCADA database...")
        generate_database()
        print("✅ SCADA database ready")

    # Check and create vector store
    vector_store_path = os.path.join(base_dir, "data", "vector_store")
    if not os.path.exists(vector_store_path) or not os.listdir(vector_store_path):
        print("Creating vector store from PDF manuals...")
        # Assuming VectorStoreManager can be initialized without arguments for creation
        # or needs a path to source manuals. Adjust if your VectorStoreManager needs more.
        manager = VectorStoreManager() # Assuming it handles path internally or via config
        manager.run_full_pipeline() # Assuming this method builds the store
        print("✅ Vector store ready")
    else:
        print("✅ Vector store already exists.")


async def main():
    """
    Main entry point for the SentientGrid Multi-Agent Diagnostic System.
    """
    print("--- SentientGrid Multi-Agent Diagnostic System Started! ---")
    print("Featuring: Comprehensive Synthesis")
    print("Type 'exit' to stop.")

    # Ensure necessary data (SCADA DB, Vector Store) is initialized
    await ensure_data_ready()

    # Initialize the Orchestrator, which in turn initializes all agents
    orchestrator = Orchestrator()

    while True:
        query = input("\nEnter diagnostic query: ").strip()
        if query.lower() in ["exit", "quit", "stop"]:
            print("Goodbye!")
            break

        if not query:
            continue

        print(f"\n--- Processing query: '{query}' ---")
        try:
            final_answer = await orchestrator.run_diagnostic_workflow(query)
            print("\n" + "="*60)
            print("🔧 FINAL DIAGNOSTIC ANSWER:")
            print(final_answer)
            print("="*60 + "\n")
        except Exception as e:
            print(f"\n❌ An unexpected error occurred during workflow execution: {e}")
            import traceback
            traceback.print_exc() # Print full traceback for debugging

if __name__ == "__main__":
    asyncio.run(main())