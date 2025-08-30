# Global variables for human decision
human_decision = None

def set_decision(choice: str, feedback: str = None):
    """Set the human decision choice and optional natural language feedback"""
    global human_decision
    human_decision = {
        "choice": choice,
        "feedback": feedback,
        "timestamp": None  # Will be set when decision is processed
    }

def get_decision():
    """Get the current human decision (returns dict with choice and feedback)"""
    global human_decision
    return human_decision

def get_decision_choice():
    """Get just the choice string for backward compatibility"""
    global human_decision
    if human_decision and isinstance(human_decision, dict):
        return human_decision.get("choice")
    return human_decision

def get_decision_feedback():
    """Get the natural language feedback if provided"""
    global human_decision
    if human_decision and isinstance(human_decision, dict):
        return human_decision.get("feedback")
    return None

def clear_decision():
    """Clear the current human decision"""
    global human_decision
    human_decision = None

def is_awaiting_decision():
    """Check if we're waiting for a human decision"""
    return human_decision is None

def has_feedback():
    """Check if the current decision includes natural language feedback"""
    global human_decision
    if human_decision and isinstance(human_decision, dict):
        feedback = human_decision.get("feedback")
        return feedback is not None and feedback.strip() != ""
    return False
