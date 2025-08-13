# SentientGrid: AI Diagnostic Assistant

An advanced multi-agent AI diagnostic system that intelligently combines SCADA sensor data with technical manuals to provide comprehensive industrial equipment troubleshooting and analysis.

## 🚀 Quick Setup

### 🐳 Docker Deployment
This project uses Docker to create a self-contained, multi-service application. This is the recommended method for easy setup and consistency across different environments.

Prerequisites: You need Docker Desktop installed on your machine.

1. Clone the repository:

git clone <your-repo-url>
cd SentientAI-main

2. Start the application:
This command will build the Docker images for both the api and web services and then start the containers in the background.

docker-compose up -d --build

3. Access the system:
Once the containers are running, you can access the application at the following addresses:

🌐 Web Interface: http://localhost:8501

📊 API Server: http://localhost:8000

📚 API Docs: http://localhost:8000/docs

4. Stop the application:
When you are finished, you can stop all the running containers with a single command from the same directory:

 docker-compose down

**Prerequisites:** Docker and Docker Compose installed

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd SentientAI-main

# 2. Deploy with one command
./deploy.sh deploy

# That's it! 🎉
```

**Access the system:**
- 🌐 **Web Interface**: http://localhost:8501
- 📊 **API Server**: http://localhost:8000
- 📚 **API Docs**: http://localhost:8000/docs

### 📋 Manual Setup (Development)

<details>
<summary>Click to expand manual setup instructions</summary>

#### 1. Install Dependencies
```bash
git clone <your-repo-url>
cd SentientAI-main
python3 -m venv venv
source venv/bin/activate 
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

#### 4. Choose Your Interface

**Option A: Web Interface (Recommended)**
```bash
# Terminal 1: Start API server
python api_server.py

# Terminal 2: Start web interface
streamlit run streamlit_app.py
```
Then open http://localhost:8501 in your browser

**Option B: Command Line**
```bash
python main.py
```

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
- ✅ Sequential step numbering (1, 2, 3...)
- ✅ Duplicate detection to prevent infinite loops
- ✅ Auto-tool detection (SCADA vs Manual search)
- ✅ Real-time human decision interface
- ✅ Clean, organized output with clear sections

## 🌐 Web Interface Features

**Modern Streamlit Dashboard:**
- 🔑 **Built-in API Key Setup** - Enter your Groq API key directly in the interface
- 📊 Real-time diagnostic workflow visualization
- 🎯 Quick example queries for testing
- 🔄 Live output with organized sections:
  - System Initialization & Planning
  - Execution Loop Iterations  
  - Human Decision Interface
- 📋 Always-available decision buttons (Continue, Synthesize, Edit, Quit)
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
│   └── diagnostic_state.py   # Shared state management
├── manual/                    # Manual search system
│   ├── create_vector_store.py # PDF processing & vectorization
│   └── manual_search_tool.py  # Semantic manual search
├── scada/                     # SCADA data system  
│   ├── generate_scada_db.py   # Sample SCADA data generation
│   └── scada_query_tool.py    # SCADA query interface
├── data/
│   ├── pdf_manuals/          # Your technical manuals (PDF)
│   └── vector_store/         # Processed manual database
├── api_server.py             # REST API backend
├── streamlit_app.py          # Web interface frontend
├── main.py                   # Command-line interface
├── shared_decision.py        # Human decision coordination
└── .env                      # Your API key
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
3. 🔍 Execute Steps → 🤔 Replan Agent
   ↓
4. 🤝 Human Review → Decision (Continue/Synthesize/Quit)
   ↓
5. 🧬 Synthesizer Agent → 📊 Final Answer
```

### Agent Responsibilities:

**🧠 Planner Agent:**
- Analyzes user queries
- Creates structured diagnostic plans
- Determines whether SCADA data or manual procedures are needed

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
- Reviews system decisions at critical points
- Can continue, force synthesis, edit plans, or quit
- Maintains control over the diagnostic process

## 🐛 Common Issues

| Problem | Solution |
|---------|----------|
| "Module not found" | `pip install -r requirements.txt` |
| "API key error" | Check your `.env` file |
| "No PDFs found" | Add PDFs to `data/pdf_manuals/` folder |
| "Vector store not found" | Run manual rebuild command |
| "Port already in use" | Stop conflicting services or change ports |
| "Streamlit not loading" | Check both services running |
| "Human decisions not working" | Ensure `shared_decision.py` file is accessible |
| "Duplicate steps appearing" | System now auto-detects and prevents this |

## 💡 Example Diagnostic Workflows

**Scenario 1: High Pressure Alert**
```
Query: "Pressure is very high, help please"
→ Plan: 1. Check SCADA pressure readings, 2. Find pressure troubleshooting procedures  
→ Execute: Gets current pressure data + manual procedures
→ Result: "Current pressure is 95 PSI (normal: 60-80). Recommended actions: Check relief valve, inspect seals..."
```

**Scenario 2: Historical Data Query**
```
Query: "What was the temperature in March?"
→ Plan: 1. Query SCADA historical data
→ Execute: Retrieves March temperature logs
→ Result: "March average temperature: 72°F, Range: 68-76°F, Peak occurred on March 15th..."
```

**Scenario 3: Equipment Maintenance**
```
Query: "How do I calibrate the pressure sensor?"
→ Plan: 1. Search manual for calibration procedures
→ Execute: Finds relevant manual sections
→ Result: "Calibration procedure from Rockwell manual: 1. Power down system, 2. Remove sensor housing..."
```

## 🎯 Key Features & Improvements

- ✅ **Smart Step Numbering**: Clean sequential numbering (1, 2, 3) instead of confusing duplicates
- ✅ **Duplicate Prevention**: Automatically detects and prevents repetitive work
- ✅ **Clean Output**: Streamlined messages, removed verbose debugging
- ✅ **Real-time Web Interface**: Modern dashboard with live updates
- ✅ **Human Control**: Always-available decision buttons for workflow control
- ✅ **Auto-tool Detection**: Intelligently chooses SCADA vs Manual search
- ✅ **Comprehensive Reporting**: Structured final answers with actionable recommendations

---

**Need help?** Check the troubleshooting section above, review the example workflows, or open an issue on GitHub.
