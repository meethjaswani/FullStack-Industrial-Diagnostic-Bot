# agents/orchestrator.py (COMPLETE FIXED VERSION)
import copy
import asyncio
import time

from typing import Dict, Any
from .diagnostic_state import DiagnosticState
from .planner_agent import PlannerAgent
from .executor_agent import ExecutorAgent
from .scada_agent import ScadaAgent
from .manual_agent import ManualAgent
from .replan_agent import ReplanAgent
from .synthesizer_agent import SynthesizerAgent

class Orchestrator:
    """
    Orchestrator: Manages the flow of the multi-agent diagnostic system.
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

        print(f"✅ {self.name}: All agents initialized.")

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
        print(" 'Continue': Proceed with the current plan.")
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
                choice = decision
                print(f"✅ Human decision received from frontend: {choice}")
                
                # Clear the decision
                shared_decision.clear_decision()
                
                if choice in ['c', 'continue']:
                    return {"action": "continue"}
                elif choice in ['s', 'synthesize']:
                    return {"action": "synthesize"}
                elif choice in ['q', 'quit']:
                    return {"action": "quit"}
                else:
                    return {"action": "continue"}  # Default fallback
            
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
        Runs the complete diagnostic workflow from planning to synthesis.
        """
        # Initialize the shared state
        state: DiagnosticState = {
            "input": initial_query,
            "plan": [],
            "past_steps": [],
            "response": "",
            "ready_for_synthesis": False
        }
        print(f"\n--- Starting Diagnostic Workflow for: '{initial_query}' ---")

        # 1. Planner Step
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
                print(f"📋 Remaining plan steps: {state['plan']}")

            # 3. Replan Step
            print("\n--- Replan Step ---")
            replan_output = self.replan_agent.decide_next_action(state)

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
                    print(f"📋 Replan Agent added {len(unique_new_steps)} unique new steps. Total plan: {state['plan']}")
                else:
                    print(f"⚠️ Replan Agent tried to add duplicate steps. No new steps added.")
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
                
                if has_warnings:
                    pass  # Warnings already printed by individual agents
                
                human_decision = await self._human_in_the_loop_review(
                    state, 
                    duplicate_warning, 
                    too_many_steps_warning, 
                    replan_failed_warning
                )

                if human_decision["action"] == "quit":
                    state["response"] = "Workflow aborted by human."
                    print(f"🛑 {self.name}: Workflow aborted by human. Ending.")
                    break
                elif human_decision["action"] == "synthesize":
                    state["ready_for_synthesis"] = True
                    print(f"➡️ {self.name}: Human forced synthesis.")
                elif human_decision["action"] == "edit":
                    state["plan"] = human_decision.get("new_plan", state["plan"])
                    print(f"✏️ {self.name}: Human edited plan to: {state['plan']}")
                    current_iteration = 0
                # If "continue", loop proceeds as normal
                elif human_decision["action"] == "continue":
                    print(f"▶️ {self.name}: Human chose to continue with current plan.")

        # 4. Synthesizer Step
        if state["ready_for_synthesis"] and not state["response"]:
            print("\n--- Synthesizer Step ---")
            synthesizer_output = self.synthesizer_agent.synthesize_response(state)
            state["response"] = synthesizer_output.get("response", "An error occurred during final synthesis.")
            print(f"✅ {self.name}: Final response synthesized.")
        elif not state["response"]:
            state["response"] = "The diagnostic process completed without a final synthesized response."
            print(f"🛑 {self.name}: Workflow ended without synthesis or response.")

        print("\n--- Diagnostic Workflow Completed ---")
        return state["response"]