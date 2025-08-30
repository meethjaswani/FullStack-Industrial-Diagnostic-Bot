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

            # Handle different response formats and fix common issues
            if model_class == Plan:
                # If the response has a nested structure, try to extract the steps
                if "steps" not in data:
                    # Try common alternative structures
                    if "diagnosticPlan" in data and "steps" in data["diagnosticPlan"]:
                        data = {"steps": data["diagnosticPlan"]["steps"]}
                    elif "plan" in data and isinstance(data["plan"], list):
                        data = {"steps": data["plan"]}
                    elif "actions" in data and isinstance(data["actions"], list):
                        data = {"steps": data["actions"]}
                    else:
                        # If no steps found, create a default plan
                        print(f"⚠️ Groq API returned unexpected format: {data}")
                        data = {"steps": ["SCADA: Get system information"]}
                
                # Ensure steps are strings, not objects
                if "steps" in data and isinstance(data["steps"], list):
                    processed_steps = []
                    for step in data["steps"]:
                        if isinstance(step, dict):
                            # Extract the step description from object
                            if "step" in step:
                                processed_steps.append(step["step"])
                            elif "description" in step:
                                processed_steps.append(step["description"])
                            elif "action" in step:
                                processed_steps.append(step["action"])
                            else:
                                # Convert entire object to string
                                processed_steps.append(str(step))
                        elif isinstance(step, str):
                            processed_steps.append(step)
                        else:
                            processed_steps.append(str(step))
                    data["steps"] = processed_steps

            # Handle Act model specially - extract the inner action
            if model_class == Act:
                act = model_class.model_validate(data)
                return act.action  # Return the inner Response or Plan
            else:
                return model_class.model_validate(data)
        else:

            raise Exception(f"API error: {response.status_code}")
    except Exception as e:
        print(f"❌ Groq API call failed. Error: {str(e)}")
        print(f"❌ Exception type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        
        # Provide a default fallback based on the model_class expected
        if model_class == Act:
            # For Act, return a Plan by default
            return Plan(steps=["SCADA: Get system information"])
        elif model_class == Plan:
            return Plan(steps=["SCADA: Get system information"])
        else:
            return Response(response="I encountered an error processing your request.")