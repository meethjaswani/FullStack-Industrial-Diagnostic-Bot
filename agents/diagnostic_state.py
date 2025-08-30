# agents/diagnostic_state.py
import operator
from typing import Annotated, List, Tuple, Dict, Any, Optional
from typing_extensions import TypedDict
from datetime import datetime

class ConversationTurn(TypedDict):
    """Represents a single conversation turn with query and response"""
    timestamp: str
    user_query: str
    diagnostic_steps: List[Tuple[str, str]]  # (step, result) pairs
    final_response: str
    context_summary: str  # AI-generated summary of this turn's key findings

class DiagnosticState(TypedDict):
    """
    State for the multi-agent diagnostic system with conversation support.
    """
    # Current query context
    input: str                                          # User's diagnostic query
    plan: List[str]                                     # List of execution steps
    past_steps: Annotated[List[Tuple], operator.add]   # History of (step, result) pairs
    response: str                                       # Final diagnostic answer
    ready_for_synthesis: bool                           # Signal for synthesizer routing
    
    # Conversation context
    conversation_history: List[ConversationTurn]        # Previous conversation turns
    current_turn_context: str                           # Context from previous turns for current query
    turn_number: int                                    # Current turn number in conversation