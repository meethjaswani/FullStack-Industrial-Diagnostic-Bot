# agents/orchestrator.py (COMPLETE FIXED VERSION WITH CONVERSATION SUPPORT)
import copy
import asyncio
import time
from datetime import datetime

from typing import Dict, Any, Optional, List
from .diagnostic_state import DiagnosticState, ConversationTurn
from .planner_agent import PlannerAgent
from .executor_agent import ExecutorAgent
from .scada_agent import ScadaAgent
from .manual_agent import ManualAgent
from .replan_agent import ReplanAgent
from .synthesizer_agent import SynthesizerAgent

class Orchestrator:
    """
    Orchestrator: Manages the flow of the multi-agent diagnostic system with conversation support.
    """
    def __init__(self):
        self.name = "Orchestrator"
        print(f"🚀 {self.name}: Initializing agents...")

        # Instantiate specialized tool agents first
        self.scada_agent = ScadaAgent()
        self.manual_agent = ManualAgent()

        # Instantiate core agents, injecting dependencies where needed
        self.planner_agent = PlannerAgent()
        self.executor_agent = ExecutorAgent(
            scada_agent=self.scada_agent,
            manual_agent=self.manual_agent
        )
        self.replan_agent = ReplanAgent()
        self.synthesizer_agent = SynthesizerAgent()

        # Conversation management
        self.conversation_history: List[ConversationTurn] = []
        
        print(f"✅ {self.name}: All agents initialized.")

    def _add_conversation_turn(self, turn: ConversationTurn):
        """Add a completed conversation turn to history"""
        self.conversation_history.append(turn)

    def _get_conversation_context(self, user_query: str) -> str:
        """Generate conversation context for follow-up questions"""
        if not self.conversation_history:
            return ""
        
        # Get the last few turns for context
        recent_turns = self.conversation_history[-3:]  # Last 3 turns
        
        context_parts = []
        for turn in recent_turns:
            context_parts.append(f"Query: {turn['user_query']}")
            context_parts.append(f"Key Findings: {turn['context_summary']}")
        
        context = "\n".join(context_parts)
        return f"Previous conversation context:\n{context}\n\nCurrent query: {user_query}"

    async def _human_in_the_loop_review(self, state: DiagnosticState, duplicate_warning: bool = False, too_many_steps_warning: bool = False, replan_failed_warning: bool = False) -> Dict[str, Any]:
        """
        Human review using shared decision file
        """
        print("\n--- HUMAN IN THE LOOP: Review Required ---")
        
        # Show warnings if detected
        if duplicate_warning:
            print("🚨 DUPLICATE DETECTED: The last step returned similar results to the previous step.")
            print("Consider choosing 'synthesize' to get a final answer now.\n")
        
        if too_many_steps_warning:
            print("⚠️ TOO MANY STEPS: The system is planning more than 3 total steps.")
            print("Consider choosing 'synthesize' to get a final answer now.\n")
            
        if replan_failed_warning:
            print("❌ REPLAN FAILED: The system encountered an error while planning next steps.")
            print("Consider choosing 'synthesize' to get a final answer now.\n")
        
        print("Current State Overview:")
        print(f"User Query: {state['input']}")
        print(f"Turn: {state.get('turn_number', 'Unknown')}")
        
        print(f"Completed Steps ({len(state['past_steps'])}):")
        if state['past_steps']:
            for i, (step, result) in enumerate(state['past_steps'], 1):
                print(f"{i}. {step}")
                result_preview = str(result)[:100] + "..." if result else "No result"
                print(f"   Result Preview: {result_preview}")
        else:
            print("No steps completed yet.")

        print(f"Next Planned Steps ({len(state['plan'])}):")
        if state['plan']:
            start_num = len(state['past_steps']) + 1
            for i, step in enumerate(state['plan'], start_num):
                print(f"{i}. {step}")
        else:
            print("No new steps proposed by Replan Agent.")

        print("\nOptions:")
        print(" 'Continue': Proceed with current plan (optional feedback modifies existing steps).")
        print(" 'Edit': Replace plan with new AI-generated plan (requires feedback).")
        print(" 'Synthesize': Force synthesis of a final answer now.")
        print(" 'Quit': Abort the workflow.")

        # Wait for decision from shared file
        print("⏳ Waiting for human decision from frontend...")
        
        # Import shared decision
        import shared_decision
        
        # Wait for decision in shared file
        max_wait_time = 300  # 5 minutes
        wait_interval = 0.5  # Check every 0.5 seconds
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            # Check if decision is available in shared file
            decision = shared_decision.get_decision()
            if decision:
                # Handle both old format (string) and new format (dict)
                if isinstance(decision, dict):
                    choice = decision.get("choice")
                    feedback = decision.get("feedback")
                    print(f"👤 Human decision received: {choice}")
                    if feedback and feedback.strip():
                        print(f"💬 Human feedback: {feedback}")
                else:
                    choice = decision
                    feedback = None
                    print(f"👤 Human decision received: {choice}")

                # Clear the decision
                shared_decision.clear_decision()

                # Clear the awaiting human input flag since we received a decision
                try:
                    import requests
                    requests.post("http://localhost:8000/api/set-awaiting-human-input", json={"awaiting": False}, timeout=1)
                except:
                    pass  # Ignore if API call fails

                if choice in ['c', 'continue']:
                    result = {"action": "continue"}
                    if feedback and feedback.strip():
                        result["feedback"] = feedback
                    return result
                elif choice in ['e', 'edit']:
                    if feedback and feedback.strip():
                        result = {"action": "edit", "feedback": feedback}
                        return result
                    else:
                        # Edit requires feedback - this should not happen due to frontend validation
                        print("⚠️ Edit action requires feedback, treating as continue")
                        result = {"action": "continue"}
                        return result
                elif choice in ['s', 'synthesize']:
                    result = {"action": "synthesize"}
                    if feedback and feedback.strip():
                        result["feedback"] = feedback
                    return result
                elif choice in ['q', 'quit']:
                    result = {"action": "quit"}
                    if feedback and feedback.strip():
                        result["feedback"] = feedback
                    return result
                else:
                    result = {"action": "continue"}  # Default fallback
                    if feedback and feedback.strip():
                        result["feedback"] = feedback
                    return result
            
            # Debug: Print what we're checking every 10 seconds
            if int(elapsed_time) % 10 == 0 and elapsed_time > 0:
                print(f"🔍 Still waiting... Decision in shared file: {decision}")
            
            # Wait before checking again
            await asyncio.sleep(wait_interval)
            elapsed_time += wait_interval
        
        # Timeout - force continue as fallback
        print("⏰ Timeout waiting for frontend decision, defaulting to continue...")
        return {"action": "continue"}

    async def run_diagnostic_workflow(self, initial_query: str) -> str:
        """
        Runs the complete diagnostic workflow from planning to synthesis with conversation support.
        """
        # Calculate turn number
        turn_number = len(self.conversation_history) + 1
        
        # Get conversation context for follow-up questions
        conversation_context = self._get_conversation_context(initial_query)
        
        # Initialize the shared state with conversation support
        state: DiagnosticState = {
            "input": initial_query,
            "plan": [],
            "past_steps": [],
            "response": "",
            "ready_for_synthesis": False,
            "conversation_history": self.conversation_history,
            "current_turn_context": conversation_context,
            "turn_number": turn_number
        }
        
        print(f"\n--- Starting Diagnostic Workflow (Turn: {turn_number}) ---")
        print(f"Query: '{initial_query}'")
        
        if conversation_context and turn_number > 1:
            print(f"📚 Using conversation context from previous turns...")

        # 1. Planner Step (with conversation context)
        print("\n--- Planner Step ---")
        planner_output = self.planner_agent.create_plan(state)
        state["plan"] = planner_output.get("plan", [])
        if not state["plan"]:
            state["response"] = "The planner could not create a valid plan. Please try a different query."
            print(f"🛑 {self.name}: Planner failed to create a plan. Ending workflow.")
            return state["response"]
        
        # Main execution loop
        max_iterations = 5
        current_iteration = 0
        while not state["ready_for_synthesis"] and not state["response"] and current_iteration < max_iterations:
            current_iteration += 1
            print(f"\n--- Execution Loop Iteration {current_iteration} ---")

            if not state["plan"]:
                print(f"⚠️ {self.name}: Plan is empty, but not ready for synthesis. Forcing replan decision.")
                state["ready_for_synthesis"] = True

            if state["plan"]:
                # 2. Executor Step
                print("--- Executor Step ---")
                executor_output = self.executor_agent.execute_step(state)
                state["past_steps"] = state["past_steps"] + executor_output.get("past_steps", [])

                # Remove the executed step from the plan
                state["plan"] = state["plan"][1:]
                if state["plan"]:
                    print(f"📋 Remaining plan steps: {state['plan']}")
                else:
                    print("📋 All planned steps completed.")

            # 3. Replan Step
            print("\n--- Replan Step ---")
            
            replan_output = self.replan_agent.decide_next_action(state)

            # Clear human feedback and edit mode flag after processing
            state.pop("human_feedback", None)
            state.pop("edit_mode", None)

            # Update state based on replan agent's decision
            if "ready_for_synthesis" in replan_output:
                state["ready_for_synthesis"] = replan_output["ready_for_synthesis"]
            if "response" in replan_output:
                state["response"] = replan_output["response"]
            if "plan" in replan_output and replan_output["plan"]:
                # Prevent duplicate steps from being added
                new_steps = replan_output["plan"]
                existing_steps = state["plan"]

                unique_new_steps = [step for step in new_steps if step not in existing_steps]

                if unique_new_steps:
                    state["plan"] = existing_steps + unique_new_steps
                    print(f"📋 Replan Agent: Added {len(unique_new_steps)} new step(s)")
                    print(f"   Updated plan: {state['plan']}")
                else:
                    print(f"📋 Replan Agent: No new steps added (duplicates detected)")
                    print(f"   Current plan: {state['plan']}")
            elif "plan" in replan_output and not replan_output["plan"] and not state["ready_for_synthesis"] and not state["response"]:
                print(f"⚠️ {self.name}: Replan Agent returned empty plan without synthesis signal. Forcing synthesis.")
                state["ready_for_synthesis"] = True

            # Check for warnings
            has_warnings = any([
                replan_output.get("duplicate_warning", False),
                replan_output.get("too_many_steps_warning", False),
                replan_output.get("replan_failed_warning", False)
            ])

            # HUMAN IN THE LOOP - Always ask unless ready for synthesis
            if not state["ready_for_synthesis"] and not state["response"]:
                duplicate_warning = replan_output.get("duplicate_warning", False)
                too_many_steps_warning = replan_output.get("too_many_steps_warning", False)
                replan_failed_warning = replan_output.get("replan_failed_warning", False)
                synthesis_recommended = replan_output.get("synthesis_recommended", False)
                
                # Always trigger human review if there are warnings or synthesis is recommended
                should_review = has_warnings or synthesis_recommended or current_iteration >= 1
                
                if should_review:
                    print("🤝 HUMAN IN THE LOOP: Review Required")
                    
                    # Set the awaiting human input flag in the API server
                    try:
                        import requests
                        requests.post("http://localhost:8000/api/set-awaiting-human-input", json={"awaiting": True}, timeout=1)
                    except:
                        pass  # Ignore if API call fails
                    
                    human_decision = await self._human_in_the_loop_review(state, duplicate_warning, too_many_steps_warning, replan_failed_warning)
                    
                    # Check if a valid human decision was received
                    if human_decision is None:
                        print(f"⚠️ {self.name}: No valid human decision received. Waiting for proper input...")
                        # Continue waiting for human input
                        continue

                    # Process the human decision
                    if human_decision and human_decision["action"] == "quit":
                        state["response"] = "Workflow aborted by human."
                        print(f"🛑 {self.name}: Workflow aborted by human. Ending.")
                        break
                    elif human_decision["action"] == "synthesize":
                        state["ready_for_synthesis"] = True
                        print(f"➡️ {self.name}: Human forced synthesis.")
                        # Store feedback even for synthesis decisions (only if feedback is provided)
                        feedback_text = human_decision.get("feedback", "").strip()
                        if feedback_text:
                            state["human_feedback"] = feedback_text
                    elif human_decision["action"] == "edit":
                        # Use planner agent to create a completely new plan based on feedback
                        feedback_text = human_decision.get("feedback", "").strip()
                        if feedback_text:
                            print(f"✏️ {self.name}: Human chose to edit plan with feedback: {feedback_text}")
                            # Generate new plan using planner agent
                            new_plan_output = self.planner_agent.create_plan_from_feedback(state, feedback_text)
                            new_plan = new_plan_output.get("plan", [])
                            if new_plan:
                                # Replace the current plan completely
                                state["plan"] = new_plan
                                print(f"📋 {self.name}: Plan replaced with {len(new_plan)} new steps based on feedback")
                            else:
                                print(f"⚠️ {self.name}: Failed to generate new plan from feedback, keeping current plan")
                        else:
                            print(f"⚠️ {self.name}: Edit requested but no feedback provided")
                    elif human_decision["action"] == "continue":
                        # Handle continue with feedback by modifying existing plan
                        feedback_text = human_decision.get("feedback", "").strip()
                        if feedback_text:
                            print(f"🔄 {self.name}: Human chose to continue with feedback: {feedback_text}")
                            # Use planner to modify existing plan based on feedback
                            modified_plan_output = self.planner_agent.modify_plan_with_feedback(state, feedback_text)
                            modified_plan = modified_plan_output.get("plan", [])
                            if modified_plan:
                                # Replace the remaining plan with modified version
                                state["plan"] = modified_plan
                                print(f"📋 {self.name}: Plan modified with {len(modified_plan)} steps incorporating feedback")
                            else:
                                print(f"⚠️ {self.name}: Failed to modify plan with feedback, keeping original plan")
                        else:
                            print(f"➡️ {self.name}: Human chose to continue without feedback")

        # Additional human review if we exited the loop without synthesis
        if not state["ready_for_synthesis"] and not state["response"] and current_iteration > 0:
            human_decision = await self._human_in_the_loop_review(
                state, 
                False,  # No specific warnings
                False, 
                False
            )
            
            if human_decision["action"] == "quit":
                state["response"] = "Workflow aborted by human."
                print(f"🛑 {self.name}: Workflow aborted by human. Ending.")
            elif human_decision["action"] == "edit":
                # Use planner agent to create a completely new plan based on feedback
                feedback_text = human_decision.get("feedback", "").strip()
                if feedback_text:
                    print(f"✏️ {self.name}: Human chose to edit plan with feedback: {feedback_text}")
                    # Generate new plan using planner agent
                    new_plan_output = self.planner_agent.create_plan_from_feedback(state, feedback_text)
                    new_plan = new_plan_output.get("plan", [])
                    if new_plan:
                        # Replace the current plan completely
                        state["plan"] = new_plan
                        print(f"📋 {self.name}: Plan replaced with {len(new_plan)} new steps based on feedback")
                    else:
                        print(f"⚠️ {self.name}: Failed to generate new plan from feedback, keeping current plan")
                else:
                    print(f"⚠️ {self.name}: Edit requested but no feedback provided")
            elif human_decision["action"] == "synthesize":
                state["ready_for_synthesis"] = True
                print(f"➡️ {self.name}: Human forced synthesis.")
                # Store feedback even for synthesis decisions (only if feedback is provided)
                feedback_text = human_decision.get("feedback", "").strip()
                if feedback_text:
                    state["human_feedback"] = feedback_text 
            elif human_decision["action"] == "continue":
                # Handle continue with feedback by modifying existing plan
                feedback_text = human_decision.get("feedback", "").strip()
                if feedback_text:
                    print(f"🔄 {self.name}: Human chose to continue with feedback: {feedback_text}")
                    # Use planner to modify existing plan based on feedback
                    modified_plan_output = self.planner_agent.modify_plan_with_feedback(state, feedback_text)
                    modified_plan = modified_plan_output.get("plan", [])
                    if modified_plan:
                        # Replace the remaining plan with modified version
                        state["plan"] = modified_plan
                        print(f"📋 {self.name}: Plan modified with {len(modified_plan)} steps incorporating feedback")
                    else:
                        print(f"⚠️ {self.name}: Failed to modify plan with feedback, keeping original plan")
                else:
                    print(f"➡️ {self.name}: Human chose to continue without feedback")

        # 4. Synthesizer Step
        if state["ready_for_synthesis"] and not state["response"]:
            print("\n--- Synthesizer Step ---")
            synthesizer_output = self.synthesizer_agent.synthesize_response(state)
            state["response"] = synthesizer_output.get("response", "An error occurred during final synthesis.")
            print(f"✅ {self.name}: Final response synthesized.")
        elif not state["response"]:
            state["response"] = "The diagnostic process completed without a final synthesized response."
            print(f"🛑 {self.name}: Workflow ended without synthesis or response.")

        # 5. Save conversation turn to history
        conversation_turn: ConversationTurn = {
            "timestamp": datetime.now().isoformat(),
            "user_query": initial_query,
            "diagnostic_steps": state["past_steps"],
            "final_response": state["response"],
            "context_summary": self._generate_context_summary(state)
        }
        
        self._add_conversation_turn(conversation_turn)
        
        print(f"\n--- Diagnostic Workflow Completed (Turn: {turn_number}) ---")
        print("=" * 60)
        return state["response"]

    def _generate_context_summary(self, state: DiagnosticState) -> str:
        """Generate a summary of key findings for conversation context"""
        try:
            # Use Groq API to generate a concise summary
            import requests
            import os
            
            groq_api_key = os.getenv("GROQ_API_KEY")
            if not groq_api_key:
                return "Key findings from diagnostic analysis"
            
            # Create summary prompt
            summary_prompt = f"""Summarize the key findings from this diagnostic session in 2-3 sentences:

User Query: {state['input']}
Steps Executed: {len(state['past_steps'])} diagnostic steps
Final Response: {state['response'][:500]}...

Provide a concise summary focusing on the most important findings and recommendations."""

            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {groq_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama3-8b-8192",
                    "messages": [
                        {"role": "system", "content": "You are a technical writer. Create concise, clear summaries of diagnostic findings."},
                        {"role": "user", "content": summary_prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 150
                }
            )
            
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            else:
                return "Key findings from diagnostic analysis"
                
        except Exception as e:
            print(f"⚠️ Context summary generation failed: {e}")
            return "Key findings from diagnostic analysis"

    def get_conversation_history(self) -> List[ConversationTurn]:
        """Get the conversation history"""
        return self.conversation_history

    def clear_conversation_history(self):
        """Clear the conversation history"""
        self.conversation_history = []

