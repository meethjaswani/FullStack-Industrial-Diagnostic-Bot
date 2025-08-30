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
        This method analyzes natural language feedback and suggests specific actions.
        """
        print(f"💬 {self.name}: Processing human feedback: {feedback}")
        
        # Common feedback patterns and their interpretations
        feedback_patterns = {
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
            "month": "Monthly data analysis"
        }
        
        # Analyze feedback for specific keywords
        suggested_actions = []
        feedback_lower = feedback.lower()
        
        for keyword, action in feedback_patterns.items():
            if keyword in feedback_lower:
                suggested_actions.append(action)
        
        # If no specific patterns found, provide general guidance
        if not suggested_actions:
            suggested_actions = ["Detailed analysis based on feedback"]
        
        print(f"💡 {self.name}: Suggested actions from feedback: {suggested_actions}")
        
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

        # Check for human feedback
        human_feedback = state.get("human_feedback")
        if human_feedback:
            print(f"💬 {self.name}: Human feedback received: {human_feedback}")
            print(f"🤔 {self.name}: Incorporating human feedback into decision making...")
            
            # Process the feedback to get actionable insights
            feedback_analysis = self.process_human_feedback(human_feedback, state)
            print(f"💡 {self.name}: Feedback analysis: {feedback_analysis}")

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

        # Incorporate human feedback into the replan prompt
        feedback_context = ""
        if human_feedback:
            feedback_context = f"""

HUMAN FEEDBACK: {human_feedback}

Based on this feedback, you should:
- Consider if the feedback suggests a different approach or focus area
- Modify your decision to address the specific concerns mentioned
- If the feedback suggests looking at different data or using different tools, plan accordingly
- Ensure your next steps align with the human's guidance
- Focus on the specific areas mentioned in the feedback

"""

        # Replan prompt (from original replan_step)
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
- If human feedback suggests a different approach, prioritize that guidance.

Respond with JSON only."""

        try:
            # If duplicates detected, warn but let human decide
            if force_synthesis:
                # Don't force synthesis - let human decide in the review
                return {"duplicate_warning": True}
            
            output = call_groq_structured(replanner_prompt, Act)

            if isinstance(output.action, Response):
                if output.action.response == "SYNTHESIZE":
                    print(f"✅ Decision - Recommending synthesis for human review.")
                    return {"synthesis_recommended": True}
                else:
                    # This case implies a direct response, but the graph usually routes to __end__
                    # if a direct response is generated here. Let's align with the graph's original intent.
                    print(f"✅ Decision - Direct response generated: {output.action.response}")
                    return {"response": output.action.response}
            else: # isinstance(output.action, Plan)
                remaining_steps = output.action.steps

                # Safety check - don't allow too many steps (from original replan_step)
                # Note: This logic might need refinement depending on how many steps are actually in 'state["plan"]' before this call.
                # Assuming state["plan"] here means the *new* steps LLM wants to add.
                # The total_steps check is for the overall diagnostic process.
                total_steps = len(state["past_steps"]) + len(remaining_steps)
                if total_steps > 3:
                    print(f"⚠️ Too many total steps planned ({total_steps} > 3). Recommending synthesis to avoid complexity.")
                    return {"too_many_steps_warning": True}

                print(f"📋 Decision - Continuing with {len(remaining_steps)} more steps.")
                return {"plan": remaining_steps}

        except Exception as e:
            print(f"❌ Replanning failed: {e}. Warning human but allowing choice.")
            # Don't force synthesis - let human decide
            return {"replan_failed_warning": True}