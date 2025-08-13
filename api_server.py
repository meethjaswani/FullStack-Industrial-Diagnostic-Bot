# api_server.py (COMPLETE FIXED VERSION)
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio
import os
import sys
from datetime import datetime
import traceback

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

app = FastAPI(title="SentientGrid API", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state management
class SystemState:
    def __init__(self):
        self.initialization_complete = False
        self.orchestrator = None
        self.is_processing = False
        self.current_query = None
        self.terminal_output = []
        self.current_iteration = 0
        self.awaiting_human_input = False
        self.human_decision_response = None
        self.human_input_event = None
        self.workflow_history = []
        
system_state = SystemState()

# Pydantic models for API
class QueryRequest(BaseModel):
    query: str

class HumanDecision(BaseModel):
    choice: str  # 'c', 's', 'e', 'q'
    plan_steps: Optional[List[str]] = None

# Custom print capture for terminal output
class TerminalCapture:
    def __init__(self):
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
    
    def write(self, text):
        if text.strip():
            # Extract iteration number if present
            iteration = system_state.current_iteration
            if "Execution Loop Iteration" in text:
                try:
                    iteration = int(text.split("Execution Loop Iteration")[1].strip().split()[0])
                    system_state.current_iteration = iteration
                except:
                    pass
            
            # Add to terminal output
            system_state.terminal_output.append({
                "timestamp": datetime.now().isoformat(),
                "type": self._get_message_type(text),
                "message": text.strip(),
                "iteration": iteration
            })
        
        # Still write to original stdout
        self.original_stdout.write(text)
        return len(text)
    
    def flush(self):
        self.original_stdout.flush()
    
    def _get_message_type(self, text):
        if "❌" in text or "ERROR" in text.upper():
            return "error"
        elif "✅" in text or "SUCCESS" in text.upper():
            return "success"
        elif "⚠️" in text or "WARNING" in text.upper():
            return "warning"
        elif "HUMAN IN THE LOOP" in text:
            return "human_input"
        elif "🧠" in text or "🔧" in text or "📊" in text or "🤔" in text:
            return "agent"
        else:
            return "info"

# Initialize system on startup
@app.on_event("startup")
async def startup_event():
    """Initialize the system components in background"""
    print("🚀 Starting background initialization...")
    
    # Redirect stdout to capture print statements
    sys.stdout = TerminalCapture()
    
    # Start initialization in background task
    asyncio.create_task(initialize_system_components())

async def initialize_system_components():
    """Initialize system components in background"""
    try:
        print("🚀 Initializing SentientGrid API components...")
        
        # Import here to avoid circular imports
        from agents.orchestrator import Orchestrator
        from scada.generate_scada_db import generate_database
        from manual.create_vector_store import VectorStoreManager
        
        # Ensure data is ready
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Check SCADA database
        db_path = os.path.join(base_dir, "data", "scada_data.db")
        if not os.path.exists(db_path):
            print("Generating SCADA database...")
            generate_database()
            print("✅ SCADA database ready")
        else:
            print("✅ SCADA database already exists")
        
        # Check vector store
        vector_store_path = os.path.join(base_dir, "data", "vector_store")
        if not os.path.exists(vector_store_path) or not os.listdir(vector_store_path):
            print("Creating vector store from PDF manuals...")
            manager = VectorStoreManager()
            manager.run_full_pipeline()
            print("✅ Vector store ready")
        else:
            print("✅ Vector store already exists")
        
        # Initialize orchestrator
        system_state.orchestrator = Orchestrator()
        system_state.initialization_complete = True
        print("✅ API Server components ready!")
        
    except Exception as e:
        print(f"❌ Error during background initialization: {e}")
        traceback.print_exc()

# Main endpoints
@app.get("/")
async def root():
    return {
        "name": "SentientGrid API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "server": "SentientGrid API",
        "initialization": "complete" if system_state.initialization_complete else "in_progress"
    }

@app.get("/api/status")
async def get_status():
    """Get current system status"""
    return {
        "is_processing": system_state.is_processing,
        "current_query": system_state.current_query,
        "awaiting_human_input": system_state.awaiting_human_input,
        "current_iteration": system_state.current_iteration,
        "timestamp": datetime.now().isoformat()
    }

def set_groq_api_key(api_key: str):
    """Set the GROQ API key for the session"""
    if api_key:
        os.environ["GROQ_API_KEY"] = api_key
        return True
    return False

@app.post("/api/query")
async def submit_query(request: QueryRequest, x_groq_api_key: Optional[str] = Header(None)):
    """Submit a new diagnostic query"""
    # Set API key if provided in headers
    if x_groq_api_key:
        set_groq_api_key(x_groq_api_key)
    
    if system_state.is_processing:
        raise HTTPException(status_code=400, detail="System is already processing a query")
    
    if not system_state.orchestrator:
        raise HTTPException(status_code=500, detail="System not initialized. Please restart the server.")
    
    # Clear previous state
    system_state.terminal_output = []
    system_state.current_iteration = 0
    system_state.awaiting_human_input = False
    system_state.human_decision_response = None
    
    # Clear shared decision
    import shared_decision
    shared_decision.clear_decision()
    
    # Start processing in background
    asyncio.create_task(process_query(request.query))
    
    return {
        "status": "processing",
        "query": request.query,
        "message": "Query submitted successfully"
    }

async def process_query(query: str):
    """Process the diagnostic query"""
    system_state.is_processing = True
    system_state.current_query = query
    
    try:
        print(f"\n--- Processing query: '{query}' ---")
        print("🔍 Starting diagnostic workflow...")
        
        result = await system_state.orchestrator.run_diagnostic_workflow(query)
        
        print("\n" + "="*60)
        print("🔧 FINAL DIAGNOSTIC ANSWER:")
        print(result)
        print("="*60)
        
        system_state.workflow_history.append({
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "result": result
        })
        
    except Exception as e:
        print(f"❌ Error during workflow execution: {e}")
        traceback.print_exc()
    
    finally:
        system_state.is_processing = False
        system_state.current_query = None
        system_state.awaiting_human_input = False

@app.post("/api/human-decision")
async def submit_human_decision(decision: HumanDecision, x_groq_api_key: Optional[str] = Header(None)):
    """Submit human decision for workflow continuation"""
    # Set API key if provided in headers
    if x_groq_api_key:
        set_groq_api_key(x_groq_api_key)
        
    print(f"👤 Human decision received: {decision.choice}")
    
    # Store in shared decision file
    import shared_decision
    shared_decision.set_decision(decision.choice)
    
    # Also store in system state (backup)
    system_state.human_decision_response = decision.choice
    
    return {"status": "decision_received", "decision": decision.choice}

@app.get("/api/human-decision-response")
async def get_human_decision_response():
    """Get the stored human decision response"""
    import shared_decision
    decision = shared_decision.get_decision()
    if decision:
        return {"decision": decision}
    else:
        return {"decision": None}

@app.delete("/api/human-decision-response")
async def clear_human_decision_response():
    """Clear the stored human decision response"""
    import shared_decision
    shared_decision.clear_decision()
    system_state.human_decision_response = None
    return {"status": "cleared"}

@app.get("/api/terminal-output")
async def get_terminal_output():
    """Get current terminal output organized by iterations"""
    # Group by iterations
    iterations = {}
    general_output = []
    
    for entry in system_state.terminal_output:
        iteration = entry.get('iteration', 0)
        if iteration > 0:
            if iteration not in iterations:
                iterations[iteration] = []
            iterations[iteration].append(entry)
        else:
            general_output.append(entry)
    
    return {
        "terminal_output": system_state.terminal_output,
        "general_output": general_output,
        "iterations": iterations,
        "current_iteration": system_state.current_iteration
    }

@app.get("/api/history")
async def get_history():
    """Get workflow history"""
    return {"history": system_state.workflow_history}

@app.delete("/api/history")
async def clear_history():
    """Clear workflow history"""
    system_state.workflow_history = []
    system_state.terminal_output = []
    return {"status": "history_cleared"}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting SentientGrid API Server...")
    print("📍 Server will be available at: http://localhost:8000")
    print("🔧 API endpoints:")
    print("   - GET  /                           - Root endpoint")
    print("   - GET  /health                     - Health check")
    print("   - GET  /api/status                 - System status")
    print("   - POST /api/query                  - Submit diagnostic query")
    print("   - GET  /api/terminal-output        - Get terminal output")
    print("   - POST /api/human-decision         - Submit human decision")
    print("   - GET  /api/human-decision-response - Get human decision")
    print("   - DELETE /api/human-decision-response - Clear human decision")
    print("-" * 50)
    print("💡 Server starts immediately, components initialize in background")
    print("-" * 50)
    
    try:
        uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server error: {e}")
        traceback.print_exc()