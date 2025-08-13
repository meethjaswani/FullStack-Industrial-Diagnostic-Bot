import operator
from typing import Annotated, List, Tuple
from typing_extensions import TypedDict

class PlanExecuteState(TypedDict):
    """
    State for Plan-and-Execute SentientGrid Agent
    Updated to support synthesizer flow
    """
    input: str                                          # User's diagnostic query
    plan: List[str]                                     # List of execution steps  
    past_steps: Annotated[List[Tuple], operator.add]   # [(step, result), ...]
    response: str                                       # Final diagnostic answer
    ready_for_synthesis: bool                           # Signal for synthesizer routing