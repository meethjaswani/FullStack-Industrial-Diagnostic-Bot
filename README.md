# SentientGrid: AI Diagnostic Assistant

An advanced multi-agent AI diagnostic system that intelligently combines SCADA sensor data with technical manuals to provide comprehensive industrial equipment troubleshooting and analysis.

## 🚀 Quick Setup

### 🐳 Docker Deployment (Recommended)
This project uses Docker to create a self-contained, multi-service application.

**Prerequisites:** Docker Desktop installed on your machine.

1. **Clone the repository:**
```bash
git clone <your-repo-url>
cd SentientAI-main
```

2. **Create .env file with your Groq API key:**
```bash
echo "GROQ_API_KEY=your_actual_api_key_here" > .env
```
**Important:** Replace `your_actual_api_key_here` with your actual Groq API key from [Groq Console](https://console.groq.com/)

3. **Start the application:**
```bash
docker-compose up -d --build
```

4. **Access the system:**
- 🌐 **Web Interface**: http://localhost:8501
- 📊 **API Server**: http://localhost:8000
- 📚 **API Docs**: http://localhost:8000/docs

5. **Stop the application:**
```bash
docker-compose down
```

### 📋 Manual Setup (Development)

<details>
<summary>Click to expand manual setup instructions</summary>

#### 1. Install Dependencies
```bash
git clone <your-repo-url>
cd SentientAI-main
python3 -m venv .venv
source .venv/bin/activate 
pip install -r requirements.txt
```

#### 2. Get Your API Key
- Go to [Groq Console](https://console.groq.com/)
- Create an account and get your API key

**Option A: Enter API Key in Web Interface (Easiest)**
- Your API key will be entered directly in the web interface
- No need to create any files
- Stored securely in your browser session

**Option B: Use .env File (Traditional)**
- Create a `.env` file in the project root:
```bash
echo "GROQ_API_KEY=your_actual_api_key_here" > .env
```

#### 3. Add Your Manuals (Optional)
Place any PDF technical manuals in `data/pdf_manuals/` folder. Supported brands include:
- Kawasaki robotics manuals
- Mitsubishi equipment manuals  
- Rockwell automation manuals
- KUKA quantec manuals
- And more...

#### 4. Start the Services
```bash
# Terminal 1: Start API server
python api_server.py

# Terminal 2: Start web interface
streamlit run streamlit_app.py
```
Then open http://localhost:8501 in your browser

</details>

## 🛠️ What It Does

**Ask questions in plain English:**
- "Pressure is very high, help please"
- "What's the temperature in June?"
- "How do I fix a pressure leak?"
- "Compressor is vibrating, what's wrong?"
- "Check current SCADA readings"
- "Find troubleshooting procedures for high temperature"

**The Multi-Agent System:**
1. **🧠 Planner Agent** - Creates diagnostic plan with specific steps
2. **⚙️ Executor Agent** - Runs SCADA queries and manual searches  
3. **🤔 Replan Agent** - Decides next actions and prevents loops
4. **🧬 Synthesizer Agent** - Creates comprehensive final answers
5. **🤝 Human-in-the-Loop** - You review and approve at key decision points

**Intelligent Features:**
- ✅ **Human Review After 1 Iteration** - System asks for your input early
- ✅ **Clean, Professional Output** - No redundant or verbose messages
- ✅ **Duplicate Detection** - Prevents infinite loops automatically
- ✅ **Auto-tool Detection** - Intelligently chooses SCADA vs Manual search
- ✅ **Real-time Human Decision Interface** - Always available when needed
- ✅ **Multi-turn Conversations** - Builds context from previous queries

## 🌐 Web Interface Features

**Modern Streamlit Dashboard:**
- 🔑 **Built-in API Key Setup** - Enter your Groq API key directly in the interface
- 📊 Real-time diagnostic workflow visualization
- 🎯 Quick example queries for testing
- 🔄 Live output with organized sections:
  - System Initialization & Planning
  - Execution Loop Iterations  
  - Human Decision Interface
- 📋 Decision buttons (Continue, Synthesize, Quit) appear when needed
- 🧹 Clean message filtering (hides debug info, shows important results)
- 🔐 Secure session-based API key storage (no files needed)

## 📁 Project Structure
```
SentientAI-main/
├── agents/                    # Multi-agent system
│   ├── orchestrator.py       # Main workflow coordinator
│   ├── planner_agent.py      # Creates diagnostic plans
│   ├── executor_agent.py     # Executes SCADA/manual searches
│   ├── replan_agent.py       # Decides next actions
│   ├── synthesizer_agent.py  # Creates final answers
│   ├── scada_agent.py        # SCADA data interface
│   ├── manual_agent.py       # Manual search interface
│   ├── diagnostic_state.py   # Shared state management
│   └── utils.py              # Utility functions
├── manual/                    # Manual search system
│   ├── create_vector_store.py # PDF processing & vectorization
│   └── manual_search_tool.py  # Semantic manual search
├── scada/                     # SCADA data system  
│   ├── generate_scada_db.py   # Sample SCADA data generation
│   └── scada_query_tool.py    # SCADA query interface
├── data/
│   ├── pdf_manuals/          # Your technical manuals (PDF)
│   ├── scada_data.db         # SCADA database
│   └── vector_store/         # Processed manual database
├── api_server.py             # REST API backend
├── streamlit_app.py          # Web interface frontend
├── shared_decision.py        # Human decision coordination
├── docker-compose.yml        # Docker orchestration
├── Dockerfile.api            # API service container
├── Dockerfile.web            # Web service container
├── requirements.txt           # Python dependencies
└── .env                      # Your API key (optional)
```

## 🔧 Development Tools

**Rebuild the manual database:**
```bash
python -c "from manual.create_vector_store import VectorStoreManager; VectorStoreManager().run_full_pipeline()"
```

**Regenerate SCADA data:**
```bash
python -m scada.generate_scada_db
```

**Test the API endpoints:**
```bash
# Check system status
curl http://localhost:8000/api/status

# Submit a query
curl -X POST http://localhost:8000/api/query -H "Content-Type: application/json" -d '{"query": "Check pressure readings"}'

# Send human decision
curl -X POST http://localhost:8000/api/human-decision -H "Content-Type: application/json" -d '{"choice": "c"}'
```

## 🤖 How the Multi-Agent System Works

### Workflow Overview:
```
1. 📝 User Query → 🧠 Planner Agent
   ↓
2. 📋 Diagnostic Plan → ⚙️ Executor Agent  
   ↓
3. 🔍 Execute Steps → 🤝 Human Review (after 1 iteration)
   ↓
4. 🤔 Replan Agent → Decision (Continue/Synthesize/Quit)
   ↓
5. 🧬 Synthesizer Agent → 📊 Final Answer
```

### Agent Responsibilities:

**🧠 Planner Agent:**
- Analyzes user queries
- Creates structured diagnostic plans
- Determines whether SCADA data or manual procedures are needed
- **Uses conversation context for follow-up questions**

**⚙️ Executor Agent:**
- Executes individual plan steps
- Auto-detects tool requirements (SCADA vs Manual)
- Interfaces with SCADA and manual search systems

**🤔 Replan Agent:**
- Evaluates workflow progress
- Detects duplicate work to prevent loops
- Decides if more steps are needed or if synthesis should begin

**🧬 Synthesizer Agent:**  
- Combines all gathered information
- Creates comprehensive diagnostic reports
- Provides actionable recommendations

**🤝 Human-in-the-Loop:**
- **Automatically triggered after 1 iteration**
- Reviews system decisions at critical points
- Can continue, force synthesis, or quit
- Maintains control over the diagnostic process

## 🎯 Key Features & Improvements

- ✅ **Early Human Review** - System asks for your input after just 1 iteration
- ✅ **Clean Output** - Removed all redundant and verbose messages
- ✅ **Professional Formatting** - Consistent, organized output structure
- ✅ **Smart Step Numbering** - Clean sequential numbering (1, 2, 3)
- ✅ **Duplicate Prevention** - Automatically detects and prevents repetitive work
- ✅ **Real-time Web Interface** - Modern dashboard with live updates
- ✅ **Human Control** - Decision buttons appear exactly when needed
- ✅ **Auto-tool Detection** - Intelligently chooses SCADA vs Manual search
- ✅ **Comprehensive Reporting** - Structured final answers with actionable recommendations
- ✅ **Multi-turn Conversations** - Builds intelligent context from previous queries

## 💡 Example Diagnostic Workflows

**Scenario 1: High Pressure Alert**
```
Query: "Pressure is very high, help please"
→ Plan: 1. Check SCADA pressure readings, 2. Find pressure troubleshooting procedures  
→ Execute: Gets current pressure data + manual procedures
→ Human Review: After 1 iteration, you decide to continue or synthesize
→ Result: "Current pressure is 95 PSI (normal: 60-80). Recommended actions: Check relief valve, inspect seals..."
```

**Scenario 2: Historical Data Query**
```
Query: "What was the temperature in March?"
→ Plan: 1. Query SCADA historical data
→ Execute: Retrieves March temperature logs
→ Human Review: After 1 iteration, you decide to continue or synthesize
→ Result: "March average temperature: 72°F, Range: 68-76°F, Peak occurred on March 15th..."
```

**Scenario 3: Equipment Maintenance**
```
Query: "How do I calibrate the pressure sensor?"
→ Plan: 1. Search manual for calibration procedures
→ Execute: Finds relevant manual sections
→ Human Review: After 1 iteration, you decide to continue or synthesize
→ Result: "Calibration procedure from Rockwell manual: 1. Power down system, 2. Remove sensor housing..."
```

**Scenario 4: Multi-turn Conversation with Context**
```
Turn 1: "The pump is making unusual noise, what should I check?"
→ System analyzes pump noise, checks SCADA data, searches manuals
→ Result: "Pump noise likely due to bearing wear or misalignment. Check vibration levels and inspect bearings."

Turn 2: "What about the pressure readings from my last query?"
→ System recognizes this is a follow-up about the same pump
→ Uses context: "Based on your previous query about pump noise, let me check the current pressure readings..."
→ Plan: ["SCADA: Get current pressure readings for the noisy pump"]
→ Result: "Current pressure: 85 PSI (normal: 60-80). Elevated pressure may be contributing to the noise issue you reported earlier."

Turn 3: "Compare this with the vibration data we discussed"
→ System understands you want to correlate pressure and vibration
→ Uses context: "Comparing pressure (85 PSI) with vibration data from your pump noise analysis..."
→ Plan: ["SCADA: Get current vibration readings for correlation with pressure"]
→ Result: "Pressure: 85 PSI, Vibration: 0.8 g (normal: 0.2-0.5 g). Both elevated - suggests pump strain contributing to noise."
```

## 🐛 Common Issues

| Problem | Solution |
|---------|----------|
| "Module not found" | `pip install -r requirements.txt` |
| "API key error" | Check your `.env` file or enter in web interface |
| "No PDFs found" | Add PDFs to `data/pdf_manuals/` folder |
| "Vector store not found" | Run manual rebuild command |
| "Port already in use" | Stop conflicting services or change ports |
| "Streamlit not loading" | Check both services running |
| "Human decisions not working" | Ensure `shared_decision.py` file is accessible |
| "Docker build fails" | Ensure Docker Desktop is running and has sufficient resources |

## 🚀 Quick Start Commands

```bash
# Start the system
docker-compose up -d --build

# Check status
curl http://localhost:8000/api/status

# Stop the system
docker-compose down

# View logs
docker-compose logs -f
```

---

**Need help?** Check the troubleshooting section above, review the example workflows, or open an issue on GitHub.
