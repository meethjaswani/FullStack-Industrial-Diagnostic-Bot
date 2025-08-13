# agents/planner_agent.py
import os
import json
import requests
from typing import List
# from dotenv import load_dotenv # Already loaded in utils.py

from .diagnostic_state import DiagnosticState
from .utils import call_groq_structured, Plan # Import Plan model and the Groq helper
class PlannerAgent:
    """
    Planner Agent: Creates step-by-step diagnostic plans with tool prefixes
    Constrained to only create steps that our tools can execute (SCADA: or MANUAL:)
    """

    def __init__(self):
        self.name = "PlannerAgent"
        # self.google_api_key = os.getenv("GOOGLE_API_KEY") # Handled by utils.py now

    def create_plan(self, state: DiagnosticState) -> dict:
        """Create diagnostic execution plan with SCADA: or MANUAL: prefixes"""
        user_query = state["input"]
        print(f"🧠 {self.name}: Analyzing query '{user_query}'")

        planning_prompt = f"""You are an industrial diagnostics planning agent for a SentientGrid system.

For the given diagnostic query, create a step-by-step execution plan using ONLY the available tools.

Available Tools (ONLY THESE):
- SCADA: Access real-time sensor data (pressure, temperature, vibration, RPM, load, error codes)
- MANUAL: Search technical manuals and troubleshooting procedures

CRITICAL CONSTRAINTS:
1. Each step MUST start with either "SCADA:" or "MANUAL:"
2. ONLY create steps that these tools can execute
3. DO NOT create analysis, synthesis, or comparison steps (another agent handles that separately)
4. Maximum 3 steps total

Query: "{user_query}"

Good Examples:
- "What is the pressure in March?" → ["SCADA: Get March pressure readings"]
- "How do I fix a pump leak?" → ["MANUAL: Search for pump leak repair procedures"]
- "Pressure is high, what should I do?" → ["SCADA: Check current pressure readings", "MANUAL: Find high pressure troubleshooting procedures"]

Bad Examples (DON'T DO THIS):
- "Analyze the pressure data" ❌ (Analysis is not a tool)
- "Compare SCADA vs Manual results" ❌ (Comparison is not a tool)
- "Determine root cause" ❌ (Analysis is not a tool)

SCADA Tool Can Do:
- Get current sensor readings
- Query historical data
- Check error codes
- Retrieve measurements

MANUAL Tool Can Do:
- Search for procedures
- Find troubleshooting steps
- Look up safety protocols
- Find maintenance instructions

Create a logical plan with 1-3 steps that ONLY use these tools for data gathering.

Respond with ONLY a JSON object like this example:
{{"steps": ["SCADA: get specific data", "MANUAL: search for specific procedures"]}}"""

        try:
            # Use the generalized Gemini structured call
            plan_obj = call_groq_structured(planning_prompt, Plan)
            steps = plan_obj.steps

            # Validate steps (logic remains the same from original file)
            validated_steps = self._validate_steps(steps)

            print(f"📋 Plan created with {len(validated_steps)} steps:")
            for i, step in enumerate(validated_steps, 1):
                if ":" in step:
                    tool_name = step.split(":")[0]
                    step_desc = step.split(":", 1)[1].strip()
                    print(f"  {i}. [{tool_name}] {step_desc}")
                else:
                    print(f"  {i}. {step}")

            return {"plan": validated_steps}

        except Exception as e:
            print(f"❌ Planning error: {e}")
            return {"plan": []}

    def _validate_steps(self, steps: List[str]) -> List[str]:
        """Validate that all steps use available tools and remove invalid ones"""
        validated_steps = []

        # Words that indicate invalid analysis steps (not tool operations)
        analysis_words = [
            "analyze", "analysis", "compare", "comparison", "determine", "conclude",
            "synthesize", "synthesis", "evaluate", "assess", "correlate", "interpret",
            "identify root cause", "make decision", "decide", "recommend"
        ]

        for step in steps:
            step_lower = step.lower()

            # Check if step has valid prefix
            if not (step.startswith("SCADA:") or step.startswith("MANUAL:")):
                print(f"⚠️ Skipping step without valid prefix: {step}")
                continue

            # Check if step is an analysis step (not a tool operation)
            is_analysis = any(word in step_lower for word in analysis_words)
            if is_analysis:
                print(f"⚠️ Skipping analysis step (not a tool operation): {step}")
                continue

            # Step is valid - it's a proper tool operation
            validated_steps.append(step)

        # Ensure we have at least one valid step, or provide a default
        if not validated_steps:
            print("⚠️ No valid steps found or planning failed, creating default data gathering step")
            validated_steps = ["SCADA: Get current system readings"]

        return validated_steps