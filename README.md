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

**Option A: Use the Development Startup Script (Recommended)**
```bash
./start_dev.sh
```
This script automatically:
- Activates the virtual environment
- Validates API key setup
- Starts both API server and web interface
- Provides helpful startup diagnostics

**Option B: Manual Startup**
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
├── start_dev.sh              # Development startup script
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
- **Enhanced decision interface with natural language feedback**
- **Smart plan modification and replacement capabilities**
- Maintains control over the diagnostic process

## 🤝 Enhanced Human Decision Interface

The system features an intelligent human-in-the-loop interface that gives you full control over the diagnostic process:

### 🎯 **BUTTON BEHAVIOR SUMMARY**

> **📊 Quick Reference Table**

| Action | Feedback | Result |
|--------|----------|--------|
| **Continue** | `"check temperature correlations"` | ✏️ Modifies existing step: `"SCADA: Check pressure and temperature correlations"` |
| **✏️ Edit** | `"check temperature correlations"` | 🔄 Replaces plan: `"SCADA: Get temperature correlation data"` |
| **Continue** | None | ➡️ Proceeds with existing plan unchanged |

### 📋 Decision Button Requirements

| Button | Feedback Required | Action |
|--------|-------------------|--------|
| **Continue** | Optional | Add feedback to current plan (modifies existing steps) |
| **✏️ Edit** | **Required** | Replace plan with new AI-generated plan based on feedback |
| **Synthesize** | Optional | Force final answer (incorporates feedback if provided) |
| **Quit** | Optional | End workflow (logs feedback for context) |

### 💬 **FEEDBACK EXAMPLES**

#### 🔄 **Continue Button** (Modifies Existing Plan)
| Original Step | Your Feedback | Modified Result |
|---------------|---------------|-----------------|
| `"SCADA: Check pressure readings"` | `"check temperature correlations"` | `"SCADA: Check pressure and temperature correlations"` |
| `"MANUAL: Search for pump procedures"` | `"focus on last 24 hours"` | `"MANUAL: Search for pump procedures from last 24 hours"` |
| `"SCADA: Get error codes"` | `"also include vibration data"` | `"SCADA: Get error codes and vibration data"` |

#### ✏️ **Edit Button** (Replaces Entire Plan)
| Your Feedback | New AI-Generated Plan |
|---------------|----------------------|
| `"search for high pressure troubleshooting methods"` | `"MANUAL: Search for high pressure troubleshooting procedures"` |
| `"get historical temperature data for last month"` | `"SCADA: Get historical temperature data for last month"` |
| `"find pump noise diagnostic procedures"` | `"MANUAL: Find pump noise diagnostic procedures"` |

#### 📚 **Conversation History** (Follow-up Queries)
| Example Query | System Understanding |
|---------------|---------------------|
| `"What about the pressure data from my last query?"` | References previous analysis and gets current pressure |
| `"Check the temperature trends we discussed earlier"` | Uses context from previous temperature conversation |
| `"Compare this with the vibration data we analyzed"` | Correlates current data with previous vibration analysis |

### 🎯 Intelligent Plan Management

- **Continue**: Modifies existing plan steps to incorporate your feedback
- **Edit**: Uses AI to generate completely new plan based on your specific instructions
- **Smart Step Limits**: System prevents excessive steps while allowing consolidated feedback-enhanced operations
- **Context Awareness**: AI considers already completed work to avoid duplication

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
- ✅ **Natural Language Feedback** - Guide the system with plain English instructions
- ✅ **Intelligent Plan Modification** - Continue modifies existing steps, Edit creates new plans
- ✅ **Smart Step Management** - Prevents excessive steps while allowing feedback-enhanced operations

## 💡 **COMPLETE WORKFLOW EXAMPLES**

### 🎯 **Real-World Scenario: Pump Troubleshooting with Human Feedback**

```
🔧 INITIAL QUERY: "The pump is making unusual noise, what should I check?"

📋 SYSTEM PLAN:
1. SCADA: Check current vibration readings  
2. MANUAL: Search for unusual noise procedures

⚙️ STEP 1 EXECUTED: "SCADA: Check current vibration readings"
Result: "Vibration detected at 15Hz, above normal range of 5-10Hz"

🤝 HUMAN DECISION POINT:
Current Plan: ["MANUAL: Search for unusual noise procedures"]

👤 HUMAN CHOICE: Continue with feedback: "also check temperature correlations"
🔄 MODIFIED PLAN: ["MANUAL: Search for unusual noise and temperature correlation procedures"]

⚙️ STEP 2 EXECUTED: Modified step completed
Result: "Found troubleshooting guide linking high vibration to temperature fluctuations"

🤝 HUMAN DECISION POINT:
No remaining steps

👤 HUMAN CHOICE: Edit with feedback: "get historical temperature data for last week"
✏️ NEW PLAN: ["SCADA: Get historical temperature data for last week"]

⚙️ STEP 3 EXECUTED: New plan step
Result: "Temperature fluctuated between 65-85°F last week, correlating with vibration spikes"

🧬 FINAL SYNTHESIS: "Pump noise is caused by thermal expansion from temperature fluctuations 
(65-85°F) causing misalignment and high vibration (15Hz vs normal 5-10Hz). 
Recommend: Install temperature stabilization and realign pump housing."
```

### 📚 **Multi-Turn Conversation Example**

```
TURN 1: "What's the current pressure reading?"
→ Result: "Current pressure: 75 PSI (normal range: 60-80 PSI)"

TURN 2: "What about the temperature data from my last query?"
→ System Context: References previous pressure analysis
→ Plan: ["SCADA: Get current temperature readings for pressure system"]
→ Result: "Temperature: 68°F, within normal operating range"

TURN 3: "Compare this with the readings we discussed yesterday"
→ System Context: References yesterday's pressure/temperature discussion  
→ Plan: ["SCADA: Get comparative readings from yesterday for analysis"]
→ Result: "Yesterday: 78 PSI, 71°F. Today: 75 PSI, 68°F. Slight decrease in both values."
```

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

**Docker (Production):**
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

**Development:**
```bash
# Start with automated setup
./start_dev.sh

# Manual start (alternative)
source venv/bin/activate
python api_server.py & streamlit run streamlit_app.py
```
