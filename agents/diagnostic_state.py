# agents/diagnostic_state.py
import operator
from typing import Annotated, List, Tuple
from typing_extensions import TypedDict

class DiagnosticState(TypedDict):
    """
    State for the multi-agent diagnostic system.
    """
    input: str                                          # User's diagnostic query
    plan: List[str]                                     # List of execution steps
    past_steps: Annotated[List[Tuple], operator.add]   # History of (step, result) pairs
    response: str                                       # Final diagnostic answer
    ready_for_synthesis: bool                           # Signal for synthesizer routing