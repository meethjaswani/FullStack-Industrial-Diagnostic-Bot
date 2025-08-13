import os
import json
import requests
from typing import Literal
from pydantic import BaseModel, Field
from typing import Union
from dotenv import load_dotenv

from langgraph.graph import StateGraph, START, END
from langchain_core.runnables import RunnableLambda

from .plan_execute_state import PlanExecuteState
from scada.scada_query_tool import query_scada
from manual.manual_search_tool import ManualSearchTool

# Load environment
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Initialize tools
manual_tool = ManualSearchTool()

# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class Plan(BaseModel):
    """Plan to follow in future"""
    steps: list[str] = Field(
        description="different steps to follow, should be in sorted order"
    )

class Response(BaseModel):
    """Response to user."""
    response: str

class Act(BaseModel):
    """Action to perform."""
    action: Union[Response, Plan] = Field(
        description="Action to perform. If you want to respond to user, use Response. "
        "If you need to further use tools to get the answer, use Plan."
    )

# =============================================================================
# GROQ API HELPER
# =============================================================================

def call_groq_structured(prompt: str, model_class: BaseModel):
    """Call Groq API and return structured output"""
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama3-8b-8192",
                "messages": [
                    {"role": "system", "content": f"You are a helpful assistant. Respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0,
                "max_tokens": 500
            }
        )
        
        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"]
            data = json.loads(content)
            return model_class.model_validate(data)
        else:
            raise Exception(f"API error: {response.status_code}")
    except Exception as e:
        print(f"❌ Groq error: {e}")
        if model_class == Plan:
            return Plan(steps=["SCADA: Get system information"])
        else:
            return Act(action=Response(response="I encountered an error processing your request."))

# =============================================================================
# NODE FUNCTIONS
# =============================================================================

async def execute_step(state: PlanExecuteState):
    """Execute step with tool prefix recognition"""
    plan = state["plan"]
    plan_str = "\n".join(f"{i+1}. {step}" for i, step in enumerate(plan))
    task = plan[0]
    
    print(f"🔧 Executing: {task}")
    
    # Extract tool from prefix
    if task.startswith("SCADA:"):
        tool_name = "SCADA"
        step_description = task.replace("SCADA:", "").strip()
        try:
            print("📊 Using SCADA tool...")
            result = query_scada(state["input"])
        except Exception as e:
            result = f"SCADA error: {str(e)}"
            
    elif task.startswith("MANUAL:"):
        tool_name = "MANUAL"
        step_description = task.replace("MANUAL:", "").strip()
        try:
            print("📖 Using Manual tool...")
            search_results = manual_tool.search(state["input"], top_k=3)
            formatted_results = []
            for i, res in enumerate(search_results, 1):
                content_preview = res['content'][:200] + "..." if len(res['content']) > 200 else res['content']
                source = res['metadata'].get('source', 'Unknown')
                formatted_results.append(f"{i}. {content_preview} (Source: {source})")
            result = "\n".join(formatted_results) if formatted_results else "No relevant information found"
        except Exception as e:
            result = f"Manual search error: {str(e)}"
    else:
        # Fallback tool selection
        if any(word in task.lower() for word in ["sensor", "pressure", "temperature", "data", "reading", "current"]):
            print("📊 Using SCADA tool (auto-detected)...")
            result = query_scada(state["input"])
        else:
            print("📖 Using Manual tool (auto-detected)...")
            search_results = manual_tool.search(state["input"], top_k=3)
            result = "\n".join([f"- {r['content'][:200]}..." for r in search_results])
    
    return {"past_steps": [(task, result)]}

async def plan_step(state: PlanExecuteState):
    """Create plan with tool prefixes"""
    print("🧠 Creating plan with tool specifications...")
    
    planner_prompt = f"""For the given objective, come up with a simple step by step plan for industrial diagnostics.
Each step MUST start with either "SCADA:" or "MANUAL:" to specify which tool to use.

Available tools:
- SCADA: Access sensor data (pressure, temperature, vibration, RPM, load, error codes)  
- MANUAL: Search technical manuals and troubleshooting procedures

Objective: {state["input"]}

Examples:
- "What is the pressure in March?" → ["SCADA: Get March pressure readings"]
- "How do I fix a leak?" → ["MANUAL: Search for leak repair procedures"]  
- "Pressure is high, what should I do?" → ["SCADA: Check current pressure readings", "MANUAL: Find pressure troubleshooting procedures"]

IMPORTANT: Each step MUST start with "SCADA:" or "MANUAL:"

Respond with JSON: {{"steps": ["SCADA: step 1", "MANUAL: step 2"]}}"""

    try:
        plan = call_groq_structured(planner_prompt, Plan)
        
        # Validate steps have prefixes
        validated_steps = []
        for step in plan.steps:
            if step.startswith("SCADA:") or step.startswith("MANUAL:"):
                validated_steps.append(step)
            else:
                # Auto-add prefix based on content
                if any(word in step.lower() for word in ["pressure", "temperature", "sensor", "data", "reading"]):
                    validated_steps.append(f"SCADA: {step}")
                else:
                    validated_steps.append(f"MANUAL: {step}")
        
        print(f"📋 Plan created with {len(validated_steps)} steps:")
        for i, step in enumerate(validated_steps, 1):
            tool = step.split(":")[0] if ":" in step else "AUTO"
            desc = step.split(":", 1)[1].strip() if ":" in step else step
            print(f"  {i}. [{tool}] {desc}")
            
        return {"plan": validated_steps}
    except Exception as e:
        print(f"❌ Planning failed: {e}")
        return {"plan": ["SCADA: Get system information"]}

async def replan_step(state: PlanExecuteState):
    """Replan step - decides continue or synthesize"""
    print("🤔 Replanning...")
    
    # 🆕 Check for duplicate results
    duplicate_warning = ""
    if len(state["past_steps"]) >= 2:
        last_result = state["past_steps"][-1][1][:200]
        previous_result = state["past_steps"][-2][1][:200]
        
        # Simple duplicate detection
        if last_result.lower().strip() == previous_result.lower().strip():
            duplicate_warning = """
⚠️ CRITICAL: The last step returned IDENTICAL results to the previous step. 
This means you're asking the same tool for the same information repeatedly.
You MUST either:
1. Use a DIFFERENT tool type (SCADA vs MANUAL), OR  
2. Choose "SYNTHESIZE" to provide final answer
DO NOT ask for more of the same data type."""
            print("⚠️ Duplicate result detected - warning LLM")
    
    # 🛠️ FIXED: Build complete context showing what we've actually accomplished
    completed_steps_str = ""
    for i, (step, result) in enumerate(state["past_steps"]):
        completed_steps_str += f"{i+1}. {step}\nResult: {result[:200]}...\n\n"
    
    # 🛠️ FIXED: Show remaining steps from current plan (if any)
    remaining_steps_str = ""
    if state["plan"]:
        remaining_steps_str = f"\nRemaining steps in current plan: {state['plan']}"
    
    # 🛠️ FIXED: Better context for decision making
    replanner_prompt = f"""For the given objective, decide if you need more steps or can provide final answer.

USER QUESTION: {state["input"]}

COMPLETED STEPS:
{completed_steps_str}
{remaining_steps_str}

{duplicate_warning}

DECISION ANALYSIS:
- You have completed {len(state["past_steps"])} steps
- For simple "What is X?" questions, 1-2 steps are usually sufficient
- For diagnostic "X is wrong, what do I do?" questions, you need both SCADA data and MANUAL procedures

Decision options:
1. If you have sufficient information to answer the user's question comprehensively:
   Respond with: {{"action": {{"response": "SYNTHESIZE"}}}}

2. If you still need critical missing information (maximum 1-2 more steps):  
   Respond with: {{"action": {{"steps": ["TOOL: specific missing info"]}}}}

CRITICAL RULES:
- For "What is pressure in March?" → SCADA data alone is sufficient → SYNTHESIZE
- Don't ask for "more specific" data if you already have comprehensive data
- If you have SCADA readings, you have ALL available sensor data
- If results are repeating, choose "SYNTHESIZE"
- Maximum 3 total steps allowed

Respond with JSON only."""

    try:
        output = call_groq_structured(replanner_prompt, Act)
        
        if isinstance(output.action, Response):
            if output.action.response == "SYNTHESIZE":
                print("✅ Ready for synthesis")
                return {"ready_for_synthesis": True}
            else:
                return {"response": output.action.response}
        else:
            remaining_steps = output.action.steps
            
            # 🛠️ FIXED: Safety check - don't allow too many steps
            total_steps = len(state["past_steps"]) + len(remaining_steps)
            if total_steps > 3:
                print("⚠️ Too many steps planned - going to synthesis instead")
                return {"ready_for_synthesis": True}
            
            print(f"📋 Continuing with {len(remaining_steps)} more steps")
            return {"plan": remaining_steps}
            
    except Exception as e:
        print(f"❌ Replanning failed: {e}")
        return {"ready_for_synthesis": True}
    

async def synthesizer_step(state: PlanExecuteState):
    """🧬 SYNTHESIZER: Analyze all steps and create comprehensive answer"""
    print("🧬 Synthesizer: Analyzing all steps and creating final answer...")
    
    user_question = state["input"]
    
    # Collect all step results
    step_analysis = []
    for step, result in state["past_steps"]:
        tool = step.split(":")[0] if ":" in step else "UNKNOWN"
        description = step.split(":", 1)[1].strip() if ":" in step else step
        step_analysis.append(f"[{tool}] {description}\nResult: {result}")
    
    analysis_context = "\n\n".join(step_analysis)
    
    synthesis_prompt = f"""You are an expert industrial diagnostics analyst. Analyze all the gathered information and provide a comprehensive diagnostic answer.

User Question: {user_question}

All Executed Steps and Results:
{analysis_context}

Create a comprehensive diagnostic response that:
1. Directly answers the user's question
2. Synthesizes insights from all gathered data
3. Provides actionable recommendations
4. Uses clear, professional language

Format:
🔧 COMPREHENSIVE DIAGNOSTIC ANALYSIS
Question: {user_question}

📊 Data Analysis: [Key findings from SCADA data]
📘 Procedural Guidance: [Relevant steps from manuals]  
💡 Recommendations: [Specific actions to take]
⚠️ Priority: [Most critical actions first]

Keep it thorough but concise (300-400 words)."""

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama3-8b-8192",
                "messages": [
                    {"role": "system", "content": "You are an expert industrial diagnostics analyst. Create comprehensive, actionable diagnostic responses."},
                    {"role": "user", "content": synthesis_prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 600
            }
        )
        
        if response.status_code == 200:
            final_response = response.json()["choices"][0]["message"]["content"]
            print("✅ Synthesizer: Created comprehensive diagnostic analysis")
        else:
            final_response = f"🔧 DIAGNOSTIC SUMMARY\nQuestion: {user_question}\n\nBased on {len(state['past_steps'])} completed diagnostic steps, the system has gathered relevant information. Please review the detailed results above for specific findings and recommendations."
            
    except Exception as e:
        print(f"❌ Synthesizer error: {e}")
        final_response = f"🔧 DIAGNOSTIC SUMMARY\nQuestion: {user_question}\n\nCompleted {len(state['past_steps'])} diagnostic steps successfully."
    
    return {"response": final_response}

def should_continue_or_synthesize(state: PlanExecuteState) -> str:
    """Route to continue, synthesize, or end"""
    if "ready_for_synthesis" in state and state["ready_for_synthesis"]:
        return "synthesizer"
    elif "response" in state and state["response"]:
        return "__end__"
    else:
        return "agent"

def should_end_after_synthesis(state: PlanExecuteState) -> Literal["__end__"]:
    """Always end after synthesis"""
    return "__end__"

# =============================================================================
# BUILD GRAPH
# =============================================================================

def build_plan_execute_graph():
    """Build the plan-and-execute graph with synthesizer"""
    
    workflow = StateGraph(PlanExecuteState)

    # Add nodes
    workflow.add_node("planner", RunnableLambda(plan_step))
    workflow.add_node("agent", RunnableLambda(execute_step))
    workflow.add_node("replan", RunnableLambda(replan_step))
    workflow.add_node("synthesizer", RunnableLambda(synthesizer_step))  # 🆕 NEW

    # Define flow
    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "agent")
    workflow.add_edge("agent", "replan")

    # Conditional routing from replanner
    workflow.add_conditional_edges(
        "replan",
        should_continue_or_synthesize,
        {
            "agent": "agent",           # Continue execution
            "synthesizer": "synthesizer", # Go to synthesizer
            "__end__": END              # Direct end (rare)
        }
    )

    # Synthesizer always ends
    workflow.add_edge("synthesizer", END)

    return workflow.compile()