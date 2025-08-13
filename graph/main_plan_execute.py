import os
import asyncio
from .plan_execute_graph import build_plan_execute_graph
from .plan_execute_state import PlanExecuteState
from scada.generate_scada_db import generate_database
from manual.create_vector_store import VectorStoreManager

def ensure_data_ready():
    """Initialize SCADA database and vector store if needed"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Check and create SCADA database
    db_path = os.path.join(base_dir, "data", "scada_data.db")
    if not os.path.exists(db_path):
        print("🛠 Generating SCADA database...")
        generate_database()
        print("✅ SCADA database ready")
    
    # Check and create vector store
    vector_store_path = os.path.join(base_dir, "data", "vector_store")
    if not os.path.exists(vector_store_path) or not os.listdir(vector_store_path):
        print("📚 Creating vector store from PDF manuals...")
        manager = VectorStoreManager()
        manager.run_full_pipeline()
        print("✅ Vector store ready")

async def main():
    """Main function with synthesizer flow"""
    ensure_data_ready()
    app = build_plan_execute_graph()
    
    print("🧠 SentientGrid Plan-and-Execute Agent Started!")
    print("🧬 Features: Tool prefixes + Comprehensive Synthesizer")
    print("Type 'exit' to stop.\n")
    
    while True:
        query = input("🔍 Enter diagnostic query: ").strip()
        
        if query.lower() in ["exit", "quit", "stop"]:
            print("👋 Goodbye!")
            break
            
        if not query:
            continue
        
        try:
            print(f"\n🎯 Processing: '{query}'")
            print("=" * 60)
            
            # Run the graph
            config = {"recursion_limit": 50}
            inputs = {"input": query}
            
            async for event in app.astream(inputs, config=config):
                for k, v in event.items():
                    if k != "__end__":
                        # Only show final synthesized response
                        if "response" in v and v["response"]:
                            print(f"\n🎯 Final Diagnostic Analysis:")
                            print("=" * 60)
                            print(v["response"])
                            print("=" * 60)
                        
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
        
        print()

if __name__ == "__main__":
    asyncio.run(main())