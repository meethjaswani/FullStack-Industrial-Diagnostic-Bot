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
        """Create diagnostic execution plan with SCADA: or MANUAL: prefixes and conversation context"""
        user_query = state["input"]
        conversation_context = state.get("current_turn_context", "")
        turn_number = state.get("turn_number", 1)
        
        print(f"🧠 {self.name}: Analyzing query '{user_query}' (Turn {turn_number})")
        
        if conversation_context and turn_number > 1:
            print(f"📚 {self.name}: Using conversation context for follow-up question")

        # Enhanced planning prompt with conversation context
        planning_prompt = f"""You are an industrial diagnostics planning agent for a SentientGrid system.

For the given diagnostic query, create a step-by-step execution plan using ONLY the available tools.

{'CONVERSATION CONTEXT (Previous Analysis):' if conversation_context else 'NEW CONVERSATION:'}
{conversation_context if conversation_context else 'This is the first query in the session.'}

CURRENT QUERY: "{user_query}"

Available Tools (ONLY THESE):
- SCADA: Access real-time sensor data (pressure, temperature, vibration, RPM, load, error codes)
- MANUAL: Search technical manuals and troubleshooting procedures

CRITICAL CONSTRAINTS:
1. Each step MUST start with either "SCADA:" or "MANUAL:"
2. ONLY create steps that these tools can execute
3. DO NOT create analysis, synthesis, or comparison steps (another agent handles that separately)
4. Maximum 3 steps total
5. For follow-up questions, consider what was already analyzed in previous turns

FOLLOW-UP QUESTION GUIDANCE:
- If user asks "what about X from my last query" → Focus on the specific aspect X
- If user asks "check the trends we discussed" → Query relevant historical data
- If user asks "compare with previous results" → Get current data for comparison
- If user asks "what else should I check" → Suggest additional diagnostic steps

Query: "{user_query}"

Good Examples:
- "What is the pressure in March?" → ["SCADA: Get March pressure readings"]
- "How do I fix a pump leak?" → ["MANUAL: Search for pump leak repair procedures"]
- "Pressure is high, what should I do?" → ["SCADA: Check current pressure readings", "MANUAL: Find high pressure troubleshooting procedures"]
- "What about the temperature data from my last query?" → ["SCADA: Get current temperature readings for comparison"]
- "Check the pressure trends we discussed earlier" → ["SCADA: Get historical pressure data for trend analysis"]

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
Consider the conversation context when planning follow-up questions.

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
                    print(f"  {i}. {tool_name}: {step_desc}")
                else:
                    print(f"  {i}. {step}")

            return {"plan": validated_steps}

        except Exception as e:
            print(f"❌ Planning error: {e}")
            return {"plan": []}

    def _validate_steps(self, steps: List[str]) -> List[str]:
        """Validate that all steps use available tools and remove invalid ones"""
        validated_steps = []

        # Words that indicate invalid pure analysis steps (not data gathering)
        # Be more specific - only reject pure analysis, not data gathering that includes analysis
        pure_analysis_phrases = [
            "determine root cause", "make decision", "decide on", "recommend action",
            "conclude that", "synthesize results", "provide recommendation",
            "identify the problem", "diagnose the issue"
        ]

        for step in steps:
            step_lower = step.lower()

            # Check if step has valid prefix
            if not (step.startswith("SCADA:") or step.startswith("MANUAL:")):
                print(f"⚠️ Skipping step without valid prefix: {step}")
                continue

            # Check if this is a pure analysis step (not data gathering that includes analysis)
            is_pure_analysis = any(phrase in step_lower for phrase in pure_analysis_phrases)
            
            # Allow SCADA and MANUAL steps that include analysis as part of data gathering
            # e.g., "SCADA: Get pressure data and analyze correlations" is valid
            # but "ANALYSIS: Determine root cause" would be invalid
            if is_pure_analysis and not (
                ("get" in step_lower or "check" in step_lower or "search" in step_lower or 
                 "find" in step_lower or "query" in step_lower or "retrieve" in step_lower)
            ):
                print(f"⚠️ Skipping pure analysis step (not a data gathering operation): {step}")
                continue

            # Step is valid - it's a proper tool operation
            validated_steps.append(step)

        # Ensure we have at least one valid step, or provide a default
        if not validated_steps:
            print("⚠️ No valid steps found or planning failed, creating default data gathering step")
            validated_steps = ["SCADA: Get current system readings"]

        return validated_steps

    def create_plan_from_feedback(self, state: DiagnosticState, feedback: str) -> dict:
        """Create a new diagnostic plan based on human feedback, replacing the current plan"""
        user_query = state["input"]
        past_steps = state.get("past_steps", [])
        turn_number = state.get("turn_number", 1)
        
        print(f"✏️ {self.name}: Generating new plan based on feedback: '{feedback}'")
        
        # Build context of what has already been done
        completed_context = ""
        if past_steps:
            completed_context = "ALREADY COMPLETED STEPS:\n"
            for i, (step, result) in enumerate(past_steps, 1):
                completed_context += f"{i}. {step}\n   Result: {result[:100]}...\n"
            completed_context += "\n"

        # Enhanced planning prompt specifically for feedback-driven planning
        feedback_planning_prompt = f"""You are an industrial diagnostics planning agent creating a NEW plan based on human feedback.

ORIGINAL QUERY: "{user_query}"

{completed_context}HUMAN FEEDBACK: "{feedback}"

Your task: Create a COMPLETELY NEW diagnostic plan that addresses the human feedback while avoiding duplicate work.

Available Tools (ONLY THESE):
- SCADA: Access real-time sensor data (pressure, temperature, vibration, RPM, load, error codes, historical data)
- MANUAL: Search technical manuals and troubleshooting procedures

CRITICAL REQUIREMENTS:
1. Each step MUST start with either "SCADA:" or "MANUAL:"
2. CREATE NEW STEPS that specifically address the feedback
3. DO NOT repeat steps that were already completed
4. Maximum 3 steps total
5. Focus on what the human is asking for in the feedback

FEEDBACK INTERPRETATION EXAMPLES:
- "analyze pressure data more carefully" → ["SCADA: Get detailed pressure readings with timestamps", "SCADA: Check pressure alarm history"]
- "search for high pressure troubleshooting" → ["MANUAL: Search for high pressure troubleshooting procedures", "MANUAL: Find pressure relief valve maintenance guides"]
- "check temperature correlations" → ["SCADA: Get temperature data for correlation analysis", "SCADA: Check temperature sensor calibration history"]
- "look at historical trends" → ["SCADA: Get historical trend data for the last 30 days", "SCADA: Check for recurring patterns in historical data"]
- "compare with last week's data" → ["SCADA: Get last week's comparative readings", "SCADA: Check for recent configuration changes"]

SCADA Tool Capabilities:
- Get current sensor readings
- Query historical data with time ranges
- Check error codes and alarms
- Retrieve specific measurements
- Get trend data
- Check calibration records

MANUAL Tool Capabilities:
- Search for specific procedures
- Find troubleshooting steps
- Look up safety protocols
- Find maintenance instructions
- Search by equipment type or problem

Create a targeted plan that directly addresses the feedback: "{feedback}"

Respond with ONLY a JSON object:
{{"steps": ["SCADA: specific action based on feedback", "MANUAL: specific search based on feedback"]}}"""

        try:
            # Use the Groq structured call to generate new plan
            plan_obj = call_groq_structured(feedback_planning_prompt, Plan)
            steps = plan_obj.steps

            # Validate steps
            validated_steps = self._validate_steps(steps)

            print(f"📋 New plan created from feedback with {len(validated_steps)} steps:")
            for i, step in enumerate(validated_steps, 1):
                if ":" in step:
                    tool_name = step.split(":")[0]
                    step_desc = step.split(":", 1)[1].strip()
                    print(f"  {i}. {tool_name}: {step_desc}")
                else:
                    print(f"  {i}. {step}")

            return {"plan": validated_steps}

        except Exception as e:
            print(f"❌ Feedback planning error: {e}")
            # Fallback: create a basic plan that acknowledges the feedback
            fallback_steps = [f"SCADA: Address feedback - {feedback[:50]}..."]
            return {"plan": fallback_steps}

    def modify_plan_with_feedback(self, state: DiagnosticState, feedback: str) -> dict:
        """Intelligently modify existing plan steps to incorporate feedback without exceeding limits"""
        user_query = state["input"]
        current_plan = state.get("plan", [])
        past_steps = state.get("past_steps", [])
        
        print(f"🔄 {self.name}: Modifying existing plan based on feedback: '{feedback}'")
        
        if not current_plan:
            print("⚠️ No existing plan to modify, creating new plan from feedback")
            return self.create_plan_from_feedback(state, feedback)
        
        # Build context of what has already been done
        completed_context = ""
        if past_steps:
            completed_context = "ALREADY COMPLETED STEPS:\n"
            for i, (step, result) in enumerate(past_steps, 1):
                completed_context += f"{i}. {step}\n   Result: {result[:100]}...\n"
            completed_context += "\n"

        # Create modification prompt for existing plan
        modify_prompt = f"""You are modifying an existing diagnostic plan based on human feedback.

ORIGINAL QUERY: "{user_query}"

{completed_context}CURRENT REMAINING PLAN:
{chr(10).join([f"{i}. {step}" for i, step in enumerate(current_plan, len(past_steps) + 1)])}

HUMAN FEEDBACK: "{feedback}"

Your task: Modify the EXISTING remaining plan to incorporate the feedback. DO NOT add new steps - modify or replace existing ones.

MODIFICATION STRATEGIES:
1. If feedback suggests additional data: Enhance existing SCADA steps to include that data
2. If feedback suggests new searches: Modify existing MANUAL steps to include those searches  
3. If feedback is completely different: Replace existing steps with new ones that address feedback
4. Keep the total number of remaining steps ≤ 3

EXAMPLES:
Original: ["SCADA: Check pressure readings"]
Feedback: "also check temperature correlations"
Modified: ["SCADA: Check pressure readings and temperature correlations"]

Original: ["MANUAL: Search for pump procedures", "SCADA: Get current data"]
Feedback: "focus on high vibration troubleshooting"
Modified: ["MANUAL: Search for high vibration troubleshooting procedures", "SCADA: Get vibration and related sensor data"]

Original: ["SCADA: Check error codes"]
Feedback: "check temperature correlations with vibration data"
Modified: ["SCADA: Check error codes and analyze temperature-vibration correlations"]

Available Tools:
- SCADA: Access sensor data, historical data, error codes, correlations
- MANUAL: Search technical manuals and procedures

CRITICAL REQUIREMENTS:
1. Each step MUST start with "SCADA:" or "MANUAL:"
2. MODIFY existing steps to incorporate feedback
3. Keep total remaining steps ≤ 3 (currently {len(current_plan)} steps)
4. Make steps comprehensive to address both original plan and feedback

Respond with ONLY a JSON object:
{{"steps": ["Modified step 1", "Modified step 2", ...]}}"""

        try:
            # Use Groq to generate modified plan
            plan_obj = call_groq_structured(modify_prompt, Plan)
            steps = plan_obj.steps

            # Validate steps
            validated_steps = self._validate_steps(steps)
            
            # Ensure we don't exceed reasonable limits
            if len(validated_steps) > 3:
                print(f"⚠️ Modified plan has {len(validated_steps)} steps, trimming to 3")
                validated_steps = validated_steps[:3]

            print(f"📋 Plan modified based on feedback with {len(validated_steps)} steps:")
            for i, step in enumerate(validated_steps, 1):
                if ":" in step:
                    tool_name = step.split(":")[0]
                    step_desc = step.split(":", 1)[1].strip()
                    print(f"  {i}. {tool_name}: {step_desc}")
                else:
                    print(f"  {i}. {step}")

            return {"plan": validated_steps}

        except Exception as e:
            print(f"❌ Plan modification error: {e}")
            # Fallback: keep original plan but modify first step to include feedback
            if current_plan:
                modified_first_step = f"{current_plan[0]} (incorporating: {feedback[:50]}...)"
                fallback_plan = [modified_first_step] + current_plan[1:]
                return {"plan": fallback_plan[:3]}  # Ensure limit
            else:
                return {"plan": [f"SCADA: Address feedback - {feedback[:50]}..."]}