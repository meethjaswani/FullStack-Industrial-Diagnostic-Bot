# Global variables for human decision
human_decision = None

def set_decision(choice: str):
    """Set the human decision choice"""
    global human_decision
    human_decision = choice

def get_decision():
    """Get the current human decision choice"""
    global human_decision
    return human_decision

def clear_decision():
    """Clear the current human decision"""
    global human_decision
    human_decision = None

def is_awaiting_decision():
    """Check if we're waiting for a human decision"""
    return human_decision is None