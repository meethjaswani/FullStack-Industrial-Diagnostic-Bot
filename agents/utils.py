# agents/utils.py
import os
import json
import requests
from pydantic import BaseModel, Field
from typing import Union
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY") # Changed back to GROQ_API_KEY for Groq

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable not set. Please set it in your .env file.")

# =============================================================================
# PYDANTIC MODELS (Copied from original plan_execute_graph.py for structured output)
# These are used by call_groq_structured.
# =============================================================================

class Plan(BaseModel):
    """Plan to follow in future"""
    steps: list[str] = Field(
        description="different steps to follow, should be in sorted order"
    )

class Response(BaseModel):
    """Response to user."""
    response: str

class Act(BaseModel):
    """Action to perform."""
    action: Union[Response, Plan] = Field(
        description="Action to perform. If you want to respond to user, use Response. "
        "If you need to further use tools to get the answer, use Plan."
    )

# =============================================================================
# GROQ API HELPER
# =============================================================================

def call_groq_structured(prompt: str, model_class: BaseModel, model_name: str = "llama3-8b-8192"):
    """Call Groq API and return structured output"""
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": model_name, # Use the model_name parameter
                "messages": [
                    {"role": "system", "content": f"You are a helpful assistant. Respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0,
                "max_tokens": 500
            }
        )

        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"]
            data = json.loads(content)
            return model_class.model_validate(data)
        else:
            print(f"❌ Groq API error: {response.status_code} - {response.text}")
            raise Exception(f"API error: {response.status_code}")
    except Exception as e:
        print(f"❌ Groq error: {e}")
        # Provide a default fallback based on the model_class expected
        if model_class == Plan:
            return Plan(steps=["SCADA: Get system information"])
        else:
            return Act(action=Response(response="I encountered an error processing your request."))