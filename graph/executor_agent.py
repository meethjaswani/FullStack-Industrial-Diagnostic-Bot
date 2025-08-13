from .plan_execute_state import PlanExecuteState
from scada.scada_query_tool import query_scada
from manual.manual_search_tool import ManualSearchTool

class ExecutorAgent:
    """
    Executor Agent: Executes plan steps using tool prefixes
    Simple logic: Read first word (SCADA: or MANUAL:) to decide tool
    """
    
    def __init__(self): 
        self.manual_tool = ManualSearchTool()
        print("🔧 Executor Agent initialized with SCADA and Manual tools")
    
    def execute_step(self, state: PlanExecuteState) -> dict:
        """Execute the next step by reading the tool prefix"""
        plan = state["plan"]
        
        if not plan:
            return {"past_steps": [("No steps in plan", "Execution completed or plan is empty")]}
        
        current_step = plan[0]
        user_query = state["input"]
        
        print(f"🔧 Executor Agent: Executing step '{current_step}'")
        
        # Simple tool selection by reading prefix
        if current_step.startswith("SCADA:"):
            try:
                print("📊 Using SCADA tool...")
                result = query_scada(user_query)
                tool_used = "SCADA"
            except Exception as e:
                result = f"❌ SCADA tool error: {str(e)}"
                tool_used = "SCADA (failed)"
                
        elif current_step.startswith("MANUAL:"):
            try:
                print("📖 Using Manual search tool...")
                search_results = self.manual_tool.search(user_query, top_k=3)
                
                formatted_results = []
                for i, res in enumerate(search_results, 1):
                    content_preview = res['content'][:200] + "..." if len(res['content']) > 200 else res['content']
                    source = res['metadata'].get('source', 'Unknown')
                    formatted_results.append(f"{i}. {content_preview} (Source: {source})")
                
                result = "\n".join(formatted_results) if formatted_results else "No relevant manual content found"
                tool_used = "MANUAL"
            except Exception as e:
                result = f"❌ Manual tool error: {str(e)}"
                tool_used = "MANUAL (failed)"
        else:
            # No valid prefix found
            result = f"❌ Invalid step format: {current_step}. Steps must start with 'SCADA:' or 'MANUAL:'"
            tool_used = "ERROR"
        
        print(f"✅ Step completed using {tool_used}")
        return {"past_steps": [(current_step, result)]}