# agents/replan_agent.py
from typing import Literal
from .diagnostic_state import DiagnosticState
from .utils import call_groq_structured, Act, Response, Plan # Import relevant models and Groq helper

class ReplanAgent:
    """
    Replan Agent: Decides the next action in the diagnostic workflow:
    continue with the plan, signal for synthesis, or end the process.
    """
    def __init__(self):
        self.name = "ReplanAgent"

    def process_human_feedback(self, feedback: str, state: DiagnosticState) -> dict:
        """
        Process human feedback and convert it into actionable workflow modifications.
        This method uses Groq API to analyze natural language feedback and suggest specific actions.
        """

        
        try:
            # Use Groq API for intelligent feedback processing
            import os
            import requests

            groq_api_key = os.getenv("GROQ_API_KEY")
            if not groq_api_key:
                print(f"⚠️ {self.name}: No Groq API key available, using fallback pattern matching")
                return self._fallback_feedback_processing(feedback, state)

            # Build context from current state
            current_state_context = f"""
Current diagnostic state:
- User query: {state.get('input', 'Unknown')}
- Completed steps: {len(state.get('past_steps', []))}
- Current plan: {state.get('plan', [])}

Previous steps completed:
"""
            for i, (step, result) in enumerate(state.get('past_steps', [])):
                current_state_context += f"{i+1}. {step}: {str(result)[:100]}...\n"

            # Get current plan to avoid duplicates
            current_plan = state.get('plan', [])
            current_plan_text = ""
            if current_plan:
                current_plan_text = f"\n\nCURRENT PLANNED STEPS (DO NOT SUGGEST THESE AGAIN):\n" + "\n".join([f"- {step}" for step in current_plan])

            feedback_prompt = f"""You are an expert industrial diagnostic assistant. Analyze this human feedback and convert it into specific diagnostic actions.

HUMAN FEEDBACK: "{feedback}"

CONTEXT:
{current_state_context}{current_plan_text}

IMPORTANT: Respond ONLY with a valid JSON object. Do not include any other text, explanations, or markdown formatting.

JSON FORMAT:
{{
    "primary_action": "Main action to take (e.g., analyze_pressure_data, check_temperature_correlations, search_error_codes)",
    "suggested_steps": ["Step 1", "Step 2", "Step 3"],
    "focus_areas": ["area1", "area2"],
    "time_scope": "time period mentioned (e.g., last_24_hours, weekly, monthly, or empty string)",
    "tool_preference": "preferred tools (e.g., SCADA, MANUAL, or empty string)",
    "analysis_depth": "basic|detailed|comprehensive",
    "feedback_summary": "brief summary of the feedback"
}}

EXAMPLE RESPONSE:
{{
    "primary_action": "analyze_pressure_data",
    "suggested_steps": ["SCADA: Check pressure sensor readings", "SCADA: Analyze pressure trends"],
    "focus_areas": ["pressure", "sensors"],
    "time_scope": "last_24_hours",
    "tool_preference": "SCADA",
    "analysis_depth": "detailed",
    "feedback_summary": "Analyze pressure data more carefully"
}}

JSON ONLY:"""

            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {groq_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama3-8b-8192",
                    "messages": [
                        {"role": "system", "content": "You are an expert industrial diagnostic assistant. Analyze human feedback and convert it into specific diagnostic actions. Always respond with valid JSON."},
                        {"role": "user", "content": feedback_prompt}
                    ],
                    "temperature": 0.2,
                    "max_tokens": 300
                }
            )

            if response.status_code == 200:
                result = response.json()["choices"][0]["message"]["content"]

                # Parse JSON response
                try:
                    import json
                    feedback_analysis = json.loads(result)

                    return {
                        "feedback_processed": True,
                        "suggested_actions": feedback_analysis.get("suggested_steps", []),
                        "primary_action": feedback_analysis.get("primary_action", ""),
                        "focus_areas": feedback_analysis.get("focus_areas", []),
                        "time_scope": feedback_analysis.get("time_scope", ""),
                        "tool_preference": feedback_analysis.get("tool_preference", ""),
                        "analysis_depth": feedback_analysis.get("analysis_depth", "basic"),
                        "feedback_summary": f"Human feedback: {feedback}"
                    }
                except json.JSONDecodeError:
                    return self._fallback_feedback_processing(feedback, state)
            else:
                return self._fallback_feedback_processing(feedback, state)

        except Exception:
            return self._fallback_feedback_processing(feedback, state)

    def _fallback_feedback_processing(self, feedback: str, state: DiagnosticState) -> dict:
        """
        Fallback method for processing feedback when AI analysis is unavailable
        """


        # Enhanced feedback patterns and their interpretations
        feedback_patterns = {
            # Original patterns
            "pressure": "SCADA pressure data analysis",
            "temperature": "SCADA temperature data analysis", 
            "correlation": "Data correlation analysis",
            "trend": "Historical trend analysis",
            "error": "Error code investigation",
            "manual": "Technical manual procedures",
            "procedure": "Troubleshooting procedures",
            "carefully": "Detailed analysis",
            "different": "Alternative approach",
            "compare": "Comparative analysis",
            "historical": "Historical data review",
            "24 hour": "Recent 24-hour data focus",
            "last week": "Weekly data analysis",
            "month": "Monthly data analysis",

            # Additional patterns for better coverage
            "weight": "SCADA weight data analysis",
            "speed": "SCADA speed data analysis",
            "flow": "SCADA flow rate data analysis",
            "level": "SCADA level data analysis",
            "current": "SCADA current data analysis",
            "voltage": "SCADA voltage data analysis",
            "power": "SCADA power data analysis",
            "vibration": "SCADA vibration data analysis",
            "noise": "SCADA noise data analysis",
            "analyze": "Detailed data analysis",
            "check": "Data verification",
            "verify": "Data verification",
            "instead": "Alternative approach",
            "more": "Detailed analysis",
            "deeper": "Comprehensive analysis",
            "deep": "Comprehensive analysis",
            "thorough": "Comprehensive analysis",
            "comprehensive": "Comprehensive analysis",
            "compare": "Comparative analysis",
            "comparison": "Comparative analysis",
            "versus": "Comparative analysis",
            "vs": "Comparative analysis",
            "recent": "Recent data analysis",
            "latest": "Recent data analysis",
            "yesterday": "Previous day data analysis",
            "today": "Current data analysis",
            "now": "Real-time data analysis"
        }

        # Analyze feedback for specific keywords with smarter matching
        suggested_actions = []
        feedback_lower = feedback.lower()
        
        # First pass: find exact matches
        for keyword, action in feedback_patterns.items():
            if keyword in feedback_lower:
                if action not in suggested_actions:  # Avoid duplicates
                    suggested_actions.append(action)
        
        # Second pass: look for partial matches and compound terms
        if not suggested_actions:
            # Check for compound terms like "analyse weight"
            if "analyse" in feedback_lower or "analyze" in feedback_lower:
                if "weight" in feedback_lower:
                    suggested_actions.append("SCADA weight data analysis")
                elif "pressure" in feedback_lower:
                    suggested_actions.append("SCADA pressure data analysis")
                elif "temperature" in feedback_lower:
                    suggested_actions.append("SCADA temperature data analysis")
                elif "speed" in feedback_lower:
                    suggested_actions.append("SCADA speed data analysis")
                elif "flow" in feedback_lower:
                    suggested_actions.append("SCADA flow rate data analysis")
                else:
                    suggested_actions.append("Detailed data analysis")

            # Check for verification requests
            elif "check" in feedback_lower or "verify" in feedback_lower:
                suggested_actions.append("Data verification")

            # Check for comparison requests
            elif "compare" in feedback_lower or "versus" in feedback_lower or "vs" in feedback_lower:
                suggested_actions.append("Comparative analysis")

        # If still no specific patterns found, provide general guidance
        if not suggested_actions:
            # Try to extract any sensor/measurement names from the feedback
            words = feedback_lower.split()
            for word in words:
                if len(word) > 3:  # Skip short words
                    for keyword, action in feedback_patterns.items():
                        if keyword in word or word in keyword:
                            if action not in suggested_actions:
                                suggested_actions.append(action)
                                break

        # Final fallback
        if not suggested_actions:
            suggested_actions = ["Detailed analysis based on feedback"]
        

        
        return {
            "feedback_processed": True,
            "suggested_actions": suggested_actions,
            "feedback_summary": f"Human feedback: {feedback}"
        }

    def decide_next_action(self, state: DiagnosticState) -> dict:
        """
        Determines whether to continue executing the plan, synthesize a final answer,
        or end the process, based on the current state and past steps.
        """
        print(f"🤔 {self.name}: Evaluating current state for next action...")

        # Note: Human feedback is now handled by the orchestrator before reaching this point
        # The orchestrator uses the planner to modify or replace plans based on feedback
        # This ensures better control over step limits and plan coherence


        # Check for duplicate results (logic from original replan_step)
        duplicate_warning = ""
        force_synthesis = False
        if len(state["past_steps"]) >= 2:
            last_result = state["past_steps"][-1][1][:200]
            previous_result = state["past_steps"][-2][1][:200]

            # Simple duplicate detection
            if last_result.lower().strip() == previous_result.lower().strip():
                duplicate_warning = """
🚨 CRITICAL: The last step returned IDENTICAL results to the previous step.
This means you're asking the same tool for the same information repeatedly.
YOU MUST CHOOSE "SYNTHESIZE" NOW - DO NOT CONTINUE WITH MORE STEPS.
This is a hard requirement to prevent infinite loops."""
                print(f"⚠️ Duplicate detected - recommending synthesis.")
                force_synthesis = True

        # Build complete context showing what we've actually accomplished (logic from original replan_step)
        completed_steps_str = ""
        for i, (step, result) in enumerate(state["past_steps"]):
            completed_steps_str += f"{i+1}. {step}\nResult: {result[:200]}...\n\n"

        # Show remaining steps from current plan (if any) (logic from original replan_step)
        remaining_steps_str = ""
        if state["plan"]: # state["plan"] here should reflect steps *remaining*
            # For accurate depiction in the prompt, let's only show the next step if it's not empty
            if len(state["plan"]) > 0:
                remaining_steps_str = f"\nRemaining steps in current plan (next is '{state['plan'][0]}'): {state['plan']}"
            else:
                remaining_steps_str = "\nNo new steps proposed by Replan Agent."

        # Feedback handling is now done by orchestrator before reaching this point
        feedback_context = ""

        # All human feedback is now processed by the orchestrator using the planner
        # This ensures better plan coherence and step limit management

        # Build the replanner prompt (always defined outside conditional blocks)
        replanner_prompt = f"""For the given objective, decide if you need more steps or can provide final answer.

USER QUESTION: {state["input"]}

COMPLETED STEPS:
{completed_steps_str}
{remaining_steps_str}

{duplicate_warning}
{feedback_context}

DECISION ANALYSIS:
- You have completed {len(state["past_steps"])} steps.
- For simple "What is X?" questions, 1-2 steps are usually sufficient.
- For diagnostic "X is wrong, what do I do?" questions, you need both SCADA data and MANUAL procedures.

Decision options:
1. If you have sufficient information to answer the user's question comprehensively:
   Respond with: {{"action": {{"response": "SYNTHESIZE"}}}}

2. If you still need critical missing information (maximum 1-2 more steps):
   Respond with: {{"action": {{"steps": ["TOOL: specific missing info"]}}}}

CRITICAL RULES:
- For "What is pressure in March?" → SCADA data alone is sufficient → SYNTHESIZE
- Don't ask for "more specific" data if you already have comprehensive data.
- If you have SCADA readings, you have ALL available sensor data from SCADA.
- If results are repeating, choose "SYNTHESIZE".
- Maximum 3 total execution steps (including past and planned future) recommended.

Respond with JSON only."""

        try:
            # If duplicates detected, warn but let human decide
            if force_synthesis:
                # Don't force synthesis - let human decide in the review
                return {"duplicate_warning": True}

            output = call_groq_structured(replanner_prompt, Act)

            if isinstance(output, Response):
                if output.response == "SYNTHESIZE":
                    print(f"✅ Decision - Recommending synthesis for human review.")
                    return {"synthesis_recommended": True}
                else:
                    # This case implies a direct response, but the graph usually routes to __end__
                    # if a direct response is generated here. Let's align with the graph's original intent.
                    print(f"✅ Decision - Direct response generated: {output.response}")
                    return {"response": output.response}
            else: # isinstance(output, Plan)
                remaining_steps = output.steps

                # Check if remaining_steps is valid
                if not remaining_steps:
                    print(f"📋 Decision - No additional steps needed.")
                    return {"ready_for_synthesis": True}

                # Smart step counting - be more flexible with feedback-modified plans
                total_steps = len(state["past_steps"]) + len(remaining_steps)
                
                # More flexible logic for step counting
                if total_steps > 5:
                    # Hard limit - definitely too many steps
                    print(f"⚠️ Too many total steps planned ({total_steps} > 5). Recommending synthesis to avoid complexity.")
                    return {"too_many_steps_warning": True}
                elif total_steps > 3:
                    # Soft limit - warn but allow if steps seem consolidated/feedback-driven
                    print(f"📊 Notice: {total_steps} total steps planned (> 3). This may be due to feedback incorporation.")
                    
                    # Check if we have very long steps that might be consolidated
                    long_steps = [step for step in remaining_steps if len(step) > 80]
                    if long_steps or "correlations" in " ".join(remaining_steps).lower() or "and" in " ".join(remaining_steps).lower():
                        print(f"📋 Allowing {total_steps} steps as they appear to be consolidated or feedback-enhanced.")
                    else:
                        print(f"⚠️ Too many discrete steps ({total_steps} > 3). Recommending synthesis.")
                        return {"too_many_steps_warning": True}

                print(f"📋 Decision - Continuing with {len(remaining_steps)} more steps.")
                return {"plan": remaining_steps}

        except Exception as e:
            print(f"❌ Replanning failed. Error: {str(e)}")
            print(f"❌ Exception type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            print("Consider using 'Synthesize' for final answer.")
            # Don't force synthesis - let human decide
            return {"replan_failed_warning": True}