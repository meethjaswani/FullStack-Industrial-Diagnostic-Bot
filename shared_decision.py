human_decision = None

def set_decision(choice):
    global human_decision
    human_decision = choice

def get_decision():
    global human_decision
    return human_decision

def clear_decision():
    global human_decision
    human_decision = None