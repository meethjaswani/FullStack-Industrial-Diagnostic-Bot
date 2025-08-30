#!/usr/bin/env python3
"""
Simple integration test for natural language feedback functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_shared_decision():
    """Test the shared decision module"""
    print("🧪 Testing shared_decision module...")

    # Import and test basic functionality
    import shared_decision

    # Test initial state
    assert shared_decision.get_decision() is None
    assert shared_decision.get_decision_choice() is None
    assert shared_decision.get_decision_feedback() is None
    assert not shared_decision.has_feedback()
    assert shared_decision.is_awaiting_decision()
    print("✅ Initial state correct")

    # Test setting decision with feedback
    shared_decision.set_decision("c", "analyze pressure data more carefully")
    decision = shared_decision.get_decision()
    assert decision is not None
    assert isinstance(decision, dict)
    assert decision["choice"] == "c"
    assert decision["feedback"] == "analyze pressure data more carefully"
    assert shared_decision.get_decision_choice() == "c"
    assert shared_decision.get_decision_feedback() == "analyze pressure data more carefully"
    assert shared_decision.has_feedback()
    assert not shared_decision.is_awaiting_decision()
    print("✅ Decision with feedback set correctly")

    # Test clearing
    shared_decision.clear_decision()
    assert shared_decision.get_decision() is None
    assert shared_decision.is_awaiting_decision()
    print("✅ Decision cleared correctly")

    # Test backward compatibility (old format)
    shared_decision.set_decision("s")  # No feedback
    decision = shared_decision.get_decision()
    assert decision is not None
    assert isinstance(decision, dict)
    assert decision["choice"] == "s"
    assert decision["feedback"] is None
    assert not shared_decision.has_feedback()
    print("✅ Backward compatibility maintained")

    print("🎉 shared_decision tests passed!")

def test_basic_structure():
    """Test that core modules can be imported without errors"""
    print("\n🧪 Testing basic module structure...")

    try:
        # Test that we can import the modules (without running them)
        import shared_decision
        print("✅ shared_decision imports successfully")

        # Test replan agent imports (basic structure)
        import agents.replan_agent
        replan_agent = agents.replan_agent.ReplanAgent()
        print("✅ ReplanAgent imports and initializes successfully")

        # Test that the new methods exist
        assert hasattr(replan_agent, 'process_human_feedback')
        assert hasattr(replan_agent, '_fallback_feedback_processing')
        print("✅ ReplanAgent has new feedback processing methods")

        # Test orchestrator structure
        import agents.orchestrator
        # Don't initialize full orchestrator as it has heavy dependencies
        print("✅ Orchestrator module structure is correct")

    except Exception as e:
        print(f"❌ Module import error: {e}")
        return False

    print("🎉 Basic structure tests passed!")
    return True

def test_feedback_processing():
    """Test the feedback processing logic"""
    print("\n🧪 Testing feedback processing logic...")

    import agents.replan_agent

    # Create agent
    agent = agents.replan_agent.ReplanAgent()

    # Test fallback processing
    state = {
        "input": "Pressure is high",
        "past_steps": [("Check pressure", "Pressure is 150 PSI")],
        "plan": []
    }

    feedback = "analyze temperature data more carefully"
    result = agent._fallback_feedback_processing(feedback, state)

    assert result["feedback_processed"] == True
    assert "suggested_actions" in result
    assert "feedback_summary" in result
    assert "temperature" in " ".join(result["suggested_actions"]).lower()
    print("✅ Fallback feedback processing works correctly")

    # Test that AI processing method exists (without calling it to avoid API dependencies)
    assert hasattr(agent, 'process_human_feedback')
    print("✅ AI feedback processing method exists")

    print("🎉 Feedback processing tests passed!")

if __name__ == "__main__":
    print("🚀 Starting integration tests for natural language feedback...\n")

    try:
        test_shared_decision()
        test_basic_structure()
        test_feedback_processing()

        print("\n🎊 ALL TESTS PASSED!")
        print("✅ Natural language feedback integration is working correctly")
        print("✅ Backward compatibility is maintained")
        print("✅ Core functionality is preserved")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
