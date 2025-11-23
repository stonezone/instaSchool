"""
Test script for the Socratic Tutor Agent
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tutor_agent import TutorAgent
from unittest.mock import Mock, MagicMock


def test_tutor_basic():
    """Test basic tutor functionality"""
    print("Testing TutorAgent...")

    # Create mock client
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [
        Mock(message=Mock(content="That's a great question! Let me help you think about it..."))
    ]
    mock_client.chat.completions.create.return_value = mock_response

    # Initialize tutor
    tutor = TutorAgent(mock_client, model="gpt-4.1-nano")
    print("✅ TutorAgent initialized")

    # Set lesson context
    tutor.set_lesson_context(
        unit_content="This lesson is about photosynthesis. Plants use sunlight to make food.",
        unit_title="How Plants Make Food",
        subject="Science",
        grade="Grade 5"
    )
    print("✅ Context set successfully")

    # Test getting example questions
    examples = tutor.get_example_questions()
    print(f"✅ Example questions generated: {examples[:2]}")

    # Test response generation (mocked)
    response = tutor.get_response("What is photosynthesis?")
    print(f"✅ Response generated: {response[:50]}...")

    # Test conversation history
    summary = tutor.get_conversation_summary()
    print(f"✅ Conversation tracked: {summary['message_count']} messages")

    # Test clearing conversation
    tutor.clear_conversation()
    print("✅ Conversation cleared")

    print("\n✅ All tests passed!")


def test_tutor_without_context():
    """Test tutor behavior without context"""
    print("\nTesting tutor without context...")

    mock_client = Mock()
    tutor = TutorAgent(mock_client)

    # Should return a message asking to select a lesson
    response = tutor.get_response("Help me!")
    assert "select a lesson" in response.lower()
    print("✅ Handles missing context correctly")


def test_tutor_conversation_memory():
    """Test conversation memory management"""
    print("\nTesting conversation memory...")

    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="Response"))]
    mock_client.chat.completions.create.return_value = mock_response

    tutor = TutorAgent(mock_client)
    tutor.max_history = 2  # Set small history for testing

    tutor.set_lesson_context("Content", "Title", "Subject", "Grade")

    # Add multiple messages
    for i in range(5):
        tutor.get_response(f"Question {i}")

    # Check that history is limited
    assert len(tutor.conversation_history) <= tutor.max_history * 2
    print(f"✅ History limited to {len(tutor.conversation_history)} messages (max: {tutor.max_history * 2})")


if __name__ == "__main__":
    print("🧪 Running TutorAgent Tests\n")
    print("=" * 50)

    test_tutor_basic()
    test_tutor_without_context()
    test_tutor_conversation_memory()

    print("\n" + "=" * 50)
    print("🎉 All tests completed successfully!")
    print("\nTo test in the actual app:")
    print("1. Run: streamlit run main.py")
    print("2. Switch to Student Mode")
    print("3. Select a curriculum")
    print("4. Navigate to a content section")
    print("5. Try the tutor chat at the bottom!")