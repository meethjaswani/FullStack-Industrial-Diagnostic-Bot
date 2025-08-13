# agents/executor_agent.py
from .diagnostic_state import DiagnosticState
from .scada_agent import ScadaAgent
from .manual_agent import ManualAgent

class ExecutorAgent:
    """
    Executor Agent: Executes a single step of the diagnostic plan by delegating to
    the appropriate specialized tool agent (SCADA or Manual).
    """
    def __init__(self, scada_agent: ScadaAgent, manual_agent: ManualAgent):
        self.name = "ExecutorAgent"
        self.scada_agent = scada_agent
        self.manual_agent = manual_agent

    def execute_step(self, state: DiagnosticState) -> dict:
        """
        Executes the current step in the plan and returns the result.
        Assumes the first step in state["plan"] is the one to execute.
        """
        plan = state["plan"]
        if not plan:
            print(f"⚠️ {self.name}: No steps left in plan to execute.")
            return {"past_steps": [("No steps in plan", "Execution completed or plan is empty")]}

        current_step_task = plan[0] # The current step to execute
        user_initial_query = state["input"] # Original user query for context if needed by tools

        print(f"🔧 {self.name}: Executing step: '{current_step_task}'")

        result = ""
        tool_used = "UNKNOWN"

        # Determine which agent to use based on the step prefix
        if current_step_task.startswith("SCADA:"):
            tool_used = "SCADA"
            # The SCADA agent's query method expects the context or specific query for SCADA
            # We're passing the original user_initial_query as it seems to be what query_scada expects.
            result = self.scada_agent.query(user_initial_query)

        elif current_step_task.startswith("MANUAL:"):
            tool_used = "MANUAL"
            # The Manual agent's search method expects the context or specific query for manuals
            # We're passing the original user_initial_query as it seems to be what manual_tool expects.
            result = self.manual_agent.search(user_initial_query)
        else:
            # Fallback logic for auto-detection, as seen in original plan_execute_graph.py
            # This logic should ideally be refined by the planner for explicit prefixes.
            if any(word in current_step_task.lower() for word in ["sensor", "pressure", "temperature", "data", "reading", "current", "error code"]):
                tool_used = "SCADA (auto-detected)"
                result = self.scada_agent.query(user_initial_query)
            else:
                tool_used = "MANUAL (auto-detected)"
                result = self.manual_agent.search(user_initial_query)

        print(f"✅ {self.name}: Step '{current_step_task}' completed using {tool_used}.")

        # Return the executed step and its result to be added to past_steps in the state
        return {"past_steps": [(current_step_task, result)]}