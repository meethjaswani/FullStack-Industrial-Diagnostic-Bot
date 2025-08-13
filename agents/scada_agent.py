# agents/scada_agent.py
# Import the actual SCADA query tool from your existing scada directory
from scada.scada_query_tool import query_scada

class ScadaAgent:
    """
    Scada Agent: Interfaces with the SCADA system to retrieve real-time and historical sensor data.
    """
    def __init__(self):
        self.name = "ScadaAgent"

    def query(self, user_query: str) -> str:
        """
        Queries the SCADA system for data based on the provided user query or context.
        The user_query here refers to the specific detail needed for the SCADA tool,
        derived from the original overall user input or the current plan step.
        """
        print(f"📊 {self.name}: Querying SCADA for '{user_query}'...")
        try:
            # Call your actual SCADA query function
            result = query_scada(user_query)
            print(f"✅ {self.name}: SCADA query successful.")
            return result
        except Exception as e:
            print(f"❌ {self.name}: SCADA error during query: {str(e)}")
            return f"SCADA error: {str(e)}"