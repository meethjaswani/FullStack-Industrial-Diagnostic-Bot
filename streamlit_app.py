#!/usr/bin/env python3
"""
Simple Readable SentientGrid Frontend - Just make existing output cleaner
"""
import streamlit as st
import time
import requests
import os
from typing import Optional, Dict
import json

# Page config
st.set_page_config(
    page_title="SentientGrid - Terminal View",
    page_icon="🔧",
    layout="wide"
)

# Initialize session state
if 'is_processing' not in st.session_state:
    st.session_state.is_processing = False
if 'current_query' not in st.session_state:
    st.session_state.current_query = ""
if 'awaiting_decision' not in st.session_state:
    st.session_state.awaiting_decision = False
if 'last_decision_time' not in st.session_state:
    st.session_state.last_decision_time = 0
if 'terminal_data' not in st.session_state:
    st.session_state.terminal_data = {"general_output": [], "iterations": {}}
if 'groq_api_key' not in st.session_state:
    st.session_state.groq_api_key = ""
if 'api_key_set' not in st.session_state:
    st.session_state.api_key_set = False
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []
if 'query_input' not in st.session_state:
    st.session_state.query_input = ""
if 'feedback_input' not in st.session_state:
    st.session_state.feedback_input = ""

def call_api(endpoint: str, method: str = "GET", data: Optional[Dict] = None):
    """API call function with better error handling"""
    try:
        # Use Docker service name when running in container, localhost when running locally
        api_host = os.environ.get('API_HOST', 'localhost')
        url = f"http://{api_host}:8000{endpoint}"
        headers = {}
        
        # Add API key to headers if available
        if st.session_state.groq_api_key:
            headers["X-Groq-API-Key"] = st.session_state.groq_api_key
        
        if method == "GET":
            response = requests.get(url, timeout=10, headers=headers)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10, headers=headers)
        elif method == "DELETE":
            response = requests.delete(url, timeout=10, headers=headers)
        else:
            st.error(f"Unsupported method: {method}")
            return None
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to API server. Make sure it's running on port 8000.")
        return None
    except requests.exceptions.Timeout:
        st.error("⏰ API request timed out")
        return None
    except Exception as e:
        st.error(f"Error: {e}")
        return None

def send_human_decision(choice: str, feedback: str = None):
    """Send human decision to API with optional natural language feedback"""
    current_time = time.time()

    # Prevent duplicate submissions (within 2 seconds)
    if current_time - st.session_state.last_decision_time < 2:
        st.warning("⏳ Please wait a moment before making another decision...")
        return False

    # Check if system is actually waiting for input
    if not st.session_state.is_processing:
        st.error("❌ No active workflow. Please submit a query first.")
        return False

    decision_data = {"choice": choice}
    if feedback and feedback.strip():
        decision_data["feedback"] = feedback.strip()

    result = call_api("/api/human-decision", "POST", decision_data)

    if result:
        st.session_state.last_decision_time = current_time
        st.success(f"✅ Decision sent: {choice}")

        # Clear the feedback input field after successful decision
        st.session_state.feedback_input = ""

        # Show what the choice means
        choice_meanings = {
            "c": "Continue with current plan (feedback modifies existing steps)",
            "e": "Edit plan using feedback (replaces with new AI-generated plan)",
            "s": "Synthesize final answer now (incorporates feedback if provided)",
            "q": "Quit the workflow"
        }
        st.info(f"📋 Action: {choice_meanings.get(choice, 'Unknown action')}")

        # Show feedback if provided (only if it's different from previous)
        if feedback and feedback.strip():
            st.info(f"💬 {feedback}")

        time.sleep(1)  # Brief pause for user feedback
        st.rerun()
        return True
    else:
        # Check if the error is because system isn't waiting
        if "not awaiting" in str(result) or result is None:
            st.warning("⚠️ System is not currently waiting for human input. Your decision was noted but may not be processed until the system reaches a decision point.")
        else:
            st.error("❌ Failed to send decision")
        return False

def get_conversation_history():
    """Get conversation history from API"""
    try:
        result = call_api("/api/conversation-history")
        if result and "conversation_history" in result:
            return result["conversation_history"]
    except:
        pass
    return []

def update_conversation_history():
    """Update conversation history from API"""
    st.session_state.conversation_history = get_conversation_history()

def is_important_message(message):
    """Check if message is important enough to show"""
    # Skip debug and HTTP log messages
    skip_patterns = [
        "Still waiting",
        "127.0.0.1",
        "HTTP/1.1",
        "INFO:",
        "GET /api",
        "POST /api",
        "--- Execution Loop Iteration",
        "--- Executor Step ---",
        "ExecutorAgent: Executing step:",
        "ScadaAgent: Querying SCADA",
        "ManualAgent: Searching manuals",
        "ScadaAgent: SCADA query successful",
        "ManualAgent: Manual search successful"
    ]
    
    for pattern in skip_patterns:
        if pattern in message:
            return False
    return True

def format_message_simple(entry):
    """Format message in a simple, clean way"""
    msg_type = entry.get('type', 'info')
    message = entry.get('message', '')
    timestamp = entry.get('timestamp', '')
    
    # Skip unimportant messages
    if not is_important_message(message):
        return
    
    # Clean up message (remove timestamps)
    clean_message = message.strip()
    
    # Remove leading timestamp pattern like "**00:48:01**"
    import re
    clean_message = re.sub(r'^\*\*\d{2}:\d{2}:\d{2}\*\*\s*', '', clean_message)
    
    # Format based on content and type
    if "✅" in clean_message or "SUCCESS" in clean_message.upper():
        st.success(clean_message)
    elif "⚠️" in clean_message or "WARNING" in clean_message.upper():
        st.warning(clean_message)
    elif ("❌" in clean_message or "ERROR" in clean_message.upper()) and "Remaining plan steps" not in clean_message and "Current plan" not in clean_message and "SCADA: Check error codes" not in clean_message:
        st.error(clean_message)
    elif "👤" in clean_message or "Human decision" in clean_message:
        st.info(clean_message)
    elif any(emoji in clean_message for emoji in ["🧠", "🔧", "📊", "📖", "🤔", "🧬"]):
        st.info(clean_message)
    elif "Remaining plan steps" in clean_message or "Current plan" in clean_message or "SCADA: Check error codes" in clean_message:
        st.text(clean_message)  # Display plan-related messages as plain text
    else:
        st.text(clean_message)

def group_messages_by_stage(entries):
    """Group messages by workflow stage"""
    planner_messages = []
    replan_messages = []
    human_loop_messages = []
    synthesizer_messages = []
    other_messages = []
    
    current_stage = "other"
    
    for entry in entries:
        message = entry.get('message', '')
        
        # Skip unimportant messages
        if not is_important_message(message):
            continue
        
        # Skip detailed human loop text - keep only essential parts
        if any(skip in message for skip in [
            "--- HUMAN IN THE LOOP: Review Required ---",
            "Current State Overview:",
            "User Query:",
            "Result Preview:",
            "Options:",
            "'c' / 'continue':",
            "'s' / 'synthesize':",
            "'e' / 'edit':",
            "'q' / 'quit':"
        ]):
            continue
        
        # Skip final diagnostic answer from workflow stages (it will be shown separately)
        if "FINAL DIAGNOSTIC ANSWER" in message or "COMPREHENSIVE DIAGNOSTIC ANALYSIS" in message:
            continue
            
        # Determine stage based on content
        if "Planner Step" in message or "PlannerAgent" in message or "Plan created" in message:
            current_stage = "planner"
        elif "Replan Step" in message or "ReplanAgent" in message:
            current_stage = "replan"
        elif "HUMAN IN THE LOOP" in message or "Waiting for human decision" in message or "Human decision received" in message:
            current_stage = "human_loop"
        elif "Synthesizer Step" in message or "SynthesizerAgent" in message:
            current_stage = "synthesizer"
        elif "Executor Step" in message or "ExecutorAgent" in message:
            current_stage = "other"  # Keep executor in general flow
        
        # Add to appropriate group
        if current_stage == "planner":
            planner_messages.append(entry)
        elif current_stage == "replan":
            replan_messages.append(entry)
        elif current_stage == "human_loop":
            human_loop_messages.append(entry)
        elif current_stage == "synthesizer":
            synthesizer_messages.append(entry)
        else:
            other_messages.append(entry)
    
    return planner_messages, replan_messages, human_loop_messages, synthesizer_messages, other_messages

# Main interface
st.title("🔧 SentientGrid - Diagnostic System")
st.markdown("**Real-time diagnostic workflow with clean output**")

# API Key Configuration Section
if not st.session_state.api_key_set:
    st.warning("⚠️ **Groq API Key Required** - Please enter your API key to use the system")
    
    with st.expander("🔑 API Key Setup", expanded=True):
        st.markdown("""
        **Get your free Groq API key:**
        1. Go to [Groq Console](https://console.groq.com/)
        2. Create an account (free)
        3. Generate an API key
        4. Paste it below
        """)
        
        api_key_input = st.text_input(
            "Enter your Groq API Key:",
            type="password",
            placeholder="gsk_...",
            help="Your API key will be stored securely in your browser session"
        )
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("🔐 Set API Key", type="primary"):
                if api_key_input.strip():
                    st.session_state.groq_api_key = api_key_input.strip()
                    st.session_state.api_key_set = True
                    st.success("✅ API Key set successfully!")
                    st.rerun()
                else:
                    st.error("❌ Please enter a valid API key")
        
        with col2:
            if st.button("🔄 Use .env File Instead"):
                st.session_state.api_key_set = True
                st.info("💡 Using API key from .env file (if available)")
                st.rerun()

else:
    # Show API key status
    with st.expander("🔑 API Key Status", expanded=False):
        if st.session_state.groq_api_key:
            masked_key = st.session_state.groq_api_key[:8] + "..." + st.session_state.groq_api_key[-4:]
            st.success(f"✅ API Key loaded: {masked_key}")
        else:
            st.info("💡 Using API key from .env file")
        
        if st.button("🔄 Change API Key"):
            st.session_state.api_key_set = False
            st.session_state.groq_api_key = ""
            st.rerun()

# Only show main interface if API key is configured
if st.session_state.api_key_set:
    # Sidebar for system status
    with st.sidebar:
        st.header("📊 System Status")
    
                # Test connection
        if st.button("🔍 Test Connection"):
            status = call_api("/api/status")
            if status:
                st.success("✅ API Connected")
            else:
                st.error("❌ API Not Connected")
        
        # Conversation information
        if st.session_state.conversation_history:
            st.subheader("💬 Current Conversation")
            st.info(f"**Turns:** {len(st.session_state.conversation_history)}")
            
            if st.session_state.conversation_history:
                last_turn = st.session_state.conversation_history[-1]
                st.markdown("**Last Query:**")
                st.text(last_turn['user_query'][:50] + "..." if len(last_turn['user_query']) > 50 else last_turn['user_query'])
                
                st.markdown("**Last Findings:**")
                st.text(last_turn['context_summary'][:100] + "..." if len(last_turn['context_summary']) > 100 else last_turn['context_summary'])
        
        # Clear history
        if st.button("🗑️ Clear History"):
            result = call_api("/api/history", "DELETE")
            if result:
                st.success("✅ History cleared")
                st.session_state.terminal_data = {"general_output": [], "iterations": {}}
            else:
                st.error("❌ Failed to clear history")
    
    # System info
    status = call_api("/api/status")
    if status:
        if status.get('is_processing'):
            st.success("🟢 Processing Query")
        else:
            st.info("⭕ Ready for Query")
        
        if status.get('awaiting_human_input'):
            st.warning("🤝 Awaiting Human Input")
    else:
        st.error("🔴 API Offline")

# Get current status for the entire page
status = call_api("/api/status")
is_processing = status.get('is_processing', False) if status else False

# Main content area
col1, col2 = st.columns([3, 1])

with col1:
    st.header("📝 Submit Query")
    
    # Query input
    def update_query_input():
        st.session_state.query_input = st.session_state.query_input_widget

    query_input = st.text_input(
        "Enter your diagnostic query:",
        value=st.session_state.query_input,
        key="query_input_widget",
        placeholder="e.g., 'Pressure is high, what should I do?'",
        disabled=is_processing,
        on_change=update_query_input
    )

    # Submit button
    if st.button("🚀 Submit Query", disabled=not query_input.strip() or is_processing):
        if query_input.strip():
            st.session_state.current_query = query_input.strip()
            st.session_state.terminal_data = {"general_output": [], "iterations": {}}

            # Clear the query input field after submission
            st.session_state.query_input = ""

            # Prepare query data
            query_data = {"query": query_input.strip()}

            # Submit query to API
            result = call_api("/api/query", "POST", query_data)
            if result:
                st.success("✅ Query submitted! Check output below...")
                st.session_state.is_processing = True
            else:
                st.error("❌ Failed to submit query")
            
            st.rerun()

with col2:
    st.header("🎯 Quick Examples")
    
    examples = [
        "Pressure is high, what should I do?",
        "What's the pressure in March?",
        "Check SCADA readings",
        "Find troubleshooting procedures"
    ]
    
    # Add follow-up examples if in a conversation
    if st.session_state.conversation_history:
        st.markdown("**💬 Follow-up Examples:**")
        follow_up_examples = [
            "What about the temperature data from my last query?",
            "Check the pressure trends we discussed earlier",
            "Compare with previous results",
            "What else should I check?"
        ]
        
        for example in follow_up_examples:
            if st.button(example, key=f"followup_{example}", disabled=is_processing):
                st.session_state.query_input = example
                st.rerun()
        
        st.markdown("---")
        st.markdown("**🔍 New Queries:**")
    
    for example in examples:
        if st.button(example, key=f"ex_{example}", disabled=is_processing):
            st.session_state.query_input = example
            st.rerun()

# Get terminal output and update display
terminal_response = call_api("/api/terminal-output")
if terminal_response:
    st.session_state.terminal_data = {
        "general_output": terminal_response.get("general_output", []),
        "iterations": terminal_response.get("iterations", {}),
        "current_iteration": terminal_response.get("current_iteration", 0)
    }

# Update processing status
if status:
    st.session_state.is_processing = status.get('is_processing', False)
    st.session_state.awaiting_decision = status.get('awaiting_human_input', False)
    current_query = status.get('current_query')
    if current_query:
        st.session_state.current_query = current_query

# Display terminal output organized by iterations
st.header("💻 Diagnostic Output")

if st.session_state.current_query:
    st.info(f"**Current Query:** {st.session_state.current_query}")

# Manual refresh button
if st.button("🔄 Refresh Output"):
    st.rerun()

# Display organized output
terminal_data = st.session_state.terminal_data

# Show general output (initialization, planning)
if terminal_data.get("general_output"):
    with st.expander("🔧 System Initialization & Planning", expanded=True):
        planner_msg, replan_msg, human_msg, synth_msg, other_msg = group_messages_by_stage(terminal_data["general_output"])
        
        # Show other messages first (general workflow)
        for entry in other_msg:
            format_message_simple(entry)
        
        # Show planner messages in separate box
        if planner_msg:
            st.markdown("#### 🧠 Planner Agent")
            for entry in planner_msg:
                format_message_simple(entry)
            st.markdown("---")
        
        # Show replan messages in separate box  
        if replan_msg:
            st.markdown("#### 🤔 Replan Agent")
            for entry in replan_msg:
                format_message_simple(entry)
            st.markdown("---")
        
        # Show human loop messages in separate box
        if human_msg:
            st.markdown("#### 🤝 Human In The Loop")
            for entry in human_msg:
                format_message_simple(entry)
            st.markdown("---")
        
        # Show synthesizer messages in separate box
        if synth_msg:
            st.markdown("#### 🧬 Synthesized Answer")
            for entry in synth_msg:
                format_message_simple(entry)

# Show execution iterations
iterations = terminal_data.get("iterations", {})
if iterations:
    for iteration_num in sorted(iterations.keys(), key=int):
        iteration_entries = iterations[iteration_num]
        with st.expander(f"🔄 Execution Loop Iteration {iteration_num}", expanded=True):
            
            # Group iteration messages by stage
            planner_msg, replan_msg, human_msg, synth_msg, other_msg = group_messages_by_stage(iteration_entries)
            
            # Show other messages first (executor, scada, manual)
            for entry in other_msg:
                format_message_simple(entry)
            
            # Show planner messages in separate box
            if planner_msg:
                st.markdown("#### 🧠 Planner Agent")
                for entry in planner_msg:
                    format_message_simple(entry)
                st.markdown("---")
            
            # Show replan messages in separate box  
            if replan_msg:
                st.markdown("#### 🤔 Replan Agent")
                for entry in replan_msg:
                    format_message_simple(entry)
                st.markdown("---")
            
            # Show human loop messages in separate box
            if human_msg:
                st.markdown("#### 🤝 Human In The Loop")
                for entry in human_msg:
                    format_message_simple(entry)
                st.markdown("---")
            
            # Show synthesizer messages in separate box
            if synth_msg:
                st.markdown("#### 🧬 Synthesized Answer")
                for entry in synth_msg:
                    format_message_simple(entry)

elif st.session_state.is_processing:
    st.info("**Output will appear here as the system processes your query...**")
else:
    st.info("**No active processing. Submit a query to see diagnostic output.**")

# Human Decision Interface - Show only when system is awaiting decision
if st.session_state.awaiting_decision:
    st.header("🤝 Human Decision Required")
    st.warning("🔄 **The system is waiting for your decision!** Please choose an action below.")

    # Natural Language Feedback Input
    st.subheader("💬 Natural Language Feedback")

    def update_feedback_input():
        st.session_state.feedback_input = st.session_state.feedback_input_widget

    feedback_input = st.text_area(
        "Provide additional instructions or feedback:",
        value=st.session_state.feedback_input,
        key="feedback_input_widget",
        placeholder="e.g., 'search for high pressure troubleshooting methods', 'get historical temperature data', 'find pump noise procedures'...",
        height=80,
        help="🔤 Optional for Continue, Synthesize, Quit. 🔴 Required for Edit (creates new plan).",
        on_change=update_feedback_input
    )

    # Decision buttons - Only shown when decision is required
    st.subheader("🎯 Choose Action")
    decision_col1, decision_col2, decision_col3, decision_col4 = st.columns(4)

    with decision_col1:
        if st.button("▶️ Continue", key="btn_continue", type="primary"):
            send_human_decision("c", feedback_input)

    with decision_col2:
        if st.button("✏️ Edit", key="btn_edit"):
            if feedback_input and feedback_input.strip():
                send_human_decision("e", feedback_input)
            else:
                st.warning("⚠️ Please provide feedback in the text area above before clicking Edit.")

    with decision_col3:
        if st.button("🔬 Synthesize", key="btn_synthesize", type="secondary"):
            send_human_decision("s", feedback_input)

    with decision_col4:
        if st.button("🛑 Quit", key="btn_quit"):
            send_human_decision("q", feedback_input)

    # Enhanced helpful info
    st.info("""
    **Decision Interface:**
    - **Continue**: Proceed with the current plan (feedback optional - adds to existing plan)
    - **✏️ Edit**: Replace current plan with new AI-generated plan (feedback required)
    - **Synthesize**: Force the system to provide a final answer now (feedback optional)
    - **Quit**: Stop the current workflow (feedback optional)

    **💡 Edit Feedback Examples:**
    - "search for high pressure troubleshooting methods"
    - "get historical temperature data for last month"
    - "find pump noise diagnostic procedures"
    - "check for recent alarm logs and error codes"
    - "look up calibration procedures for pressure sensors"
    """)
elif st.session_state.is_processing and not st.session_state.awaiting_decision:
    st.header("🤝 Human Decision Interface")
    st.info("⏳ **System is processing your query...** The decision interface will appear when your input is needed.")
else:
    st.header("🤝 Human Decision Interface")
    st.info("💡 **Submit a query above** to start the diagnostic process. The decision interface will appear when your input is needed.")



# Footer
st.markdown("---")

# Check for final diagnostic answer
final_answer = None
terminal_response = call_api("/api/terminal-output")
if terminal_response:
    terminal_output = terminal_response.get('terminal_output', [])
    
    # Look for final answer
    collecting_answer = False
    answer_parts = []
    
    for entry in terminal_output:
        message = entry.get('message', '')
        
        if "FINAL DIAGNOSTIC ANSWER" in message:
            collecting_answer = True
            continue
        
        if collecting_answer:
            if "====" in message:
                break
            if message.strip():
                answer_parts.append(message.strip())
    
    if answer_parts:
        final_answer = "\n".join(answer_parts)

# Show final results if available
if final_answer:
    st.header("📊 Diagnostic Results")
    
    # Parse the answer into clean sections
    sections = final_answer.split('📊')
    if len(sections) > 1:
        data_section = sections[1].split('📘')[0].strip()
        st.markdown("#### 📊 What We Found")
        st.info(data_section)
    
    sections = final_answer.split('📘')
    if len(sections) > 1:
        procedure_section = sections[1].split('💡')[0].strip()
        st.markdown("#### 📘 Relevant Procedures")
        st.info(procedure_section)
    
    sections = final_answer.split('💡')
    if len(sections) > 1:
        recommendations_section = sections[1].split('⚠️')[0].strip()
        st.markdown("#### 💡 Our Recommendations")
        st.success(recommendations_section)
    
    sections = final_answer.split('⚠️')
    if len(sections) > 1:
        priority_section = sections[1].strip()
        st.markdown("#### ⚠️ Priority Actions")
        st.warning(priority_section)
    
    # Reset button for new analysis
    if st.button("🔄 Start New Analysis", type="primary"):
        st.session_state.current_query = ""
        st.session_state.is_processing = False
        st.session_state.conversation_history = []
        call_api("/api/history", "DELETE")
        st.rerun()

    st.markdown("*SentientGrid Diagnostic System - Industrial Workflow Automation*")

# Conversation History Section
st.header("💬 Conversation History")

# Update conversation history
update_conversation_history()

if st.session_state.conversation_history:
    for i, turn in enumerate(st.session_state.conversation_history):
        with st.expander(f"Turn {i+1}: {turn['user_query'][:50]}...", expanded=False):
            col1, col2 = st.columns([1, 3])
            
            with col1:
                st.markdown(f"**Query:** {turn['user_query']}")
                st.markdown(f"**Time:** {turn['timestamp'][:19]}")
                st.markdown(f"**Steps:** {len(turn['diagnostic_steps'])}")
            
            with col2:
                st.markdown("**Key Findings:**")
                st.info(turn['context_summary'])
                
                if turn['diagnostic_steps']:
                    st.markdown("**Diagnostic Steps:**")
                    for j, (step, result) in enumerate(turn['diagnostic_steps']):
                        st.markdown(f"{j+1}. **{step}**")
                        st.text(result[:200] + "..." if len(result) > 200 else result)
    
    # Conversation management
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Clear History"):
            if call_api("/api/conversation-history", "DELETE"):
                st.session_state.conversation_history = []
                st.success("✅ Conversation history cleared")
                st.rerun()
            else:
                st.error("❌ Failed to clear history")
    
    with col2:
        if st.button("🔄 Refresh History"):
            update_conversation_history()
            st.rerun()
else:
    st.info("No conversation history yet. Submit a query to start a conversation.")

# Show message when API key is not configured
st.info("👆 **Please configure your Groq API key above to start using the diagnostic system.**")

st.markdown("""
### 🚀 What you can do once configured:
- Ask diagnostic questions in plain English
- Get real-time SCADA data analysis  
- Search technical manual procedures
- Receive comprehensive troubleshooting guidance
- Control the workflow with human-in-the-loop decisions
- **NEW: Multi-turn conversations with context awareness**
""")

st.markdown("---")
st.markdown("*SentientGrid Diagnostic System - Industrial Workflow Automation*")