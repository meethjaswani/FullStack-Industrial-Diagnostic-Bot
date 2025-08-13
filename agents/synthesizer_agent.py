# agents/synthesizer_agent.py
# agents/synthesizer_agent.py
import os
import json
import requests
# from dotenv import load_dotenv # Already loaded in utils.py

from .diagnostic_state import DiagnosticState

# Load environment variable for API key if not already loaded globally by utils.py
# (It's good practice to ensure it's loaded where used, or rely on global setup)
# load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY") # Changed back to GROQ_API_KEY

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable not set. Please set it in your .env file.")

class SynthesizerAgent:
    """
    Synthesizer Agent: Analyzes all gathered information and creates a comprehensive
    diagnostic answer for the user.
    """
    def __init__(self):
        self.name = "SynthesizerAgent"
        self.groq_api_key = GROQ_API_KEY # Store for direct use

    def synthesize_response(self, state: DiagnosticState) -> dict:
        """
        Analyzes all executed steps and their results to create a final, comprehensive
        diagnostic answer for the user.
        """
        print(f"🧬 {self.name}: Analyzing all steps and creating final answer...")

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
1. Directly answers the user's question.
2. Synthesizes insights from all gathered data.
3. Provides actionable recommendations.
4. Uses clear, professional language.

Format:
🔧 COMPREHENSIVE DIAGNOSTIC ANALYSIS
Question: {user_question}

📊 Data Analysis: [Key findings from SCADA data]
📘 Procedural Guidance: [Relevant steps from manuals]
💡 Recommendations: [Specific actions to take]
⚠️ Priority: [Most critical actions first]

Keep it thorough but concise (300-400 words)."""

        try:
            # Direct call to Groq for unstructured text generation
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama3-8b-8192", # Using llama3-8b-8192 as a good default
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
                print(f"✅ {self.name}: Created comprehensive diagnostic analysis.")
            else:
                print(f"❌ {self.name}: Groq API error during synthesis: {response.status_code} - {response.text}")
                final_response = f"🔧 DIAGNOSTIC SUMMARY\nQuestion: {user_question}\n\nBased on {len(state['past_steps'])} completed diagnostic steps, the system has gathered relevant information. Please review the detailed results above for specific findings and recommendations. An error occurred during final synthesis."

        except Exception as e:
            print(f"❌ {self.name}: Synthesis error: {e}")
            final_response = f"🔧 DIAGNOSTIC SUMMARY\nQuestion: {user_question}\n\nCompleted {len(state['past_steps'])} diagnostic steps successfully. An unexpected error prevented full synthesis."

        return {"response": final_response}