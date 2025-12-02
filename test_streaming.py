#!/usr/bin/env python3
"""
Simple test script to verify streaming functionality works correctly.
Tests both the BaseAgent streaming method and ContentAgent integration.
"""

import os
import sys
from openai import OpenAI
from dotenv import load_dotenv

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.types import BaseAgent
from src.agent_framework import ContentAgent
from config import load_config


def test_base_agent_streaming():
    """Test BaseAgent._call_model_streaming() method"""
    print("\n" + "="*70)
    print("TEST 1: BaseAgent Streaming")
    print("="*70)

    # Load environment and create client
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found in environment")
        return False

    client = OpenAI(api_key=api_key)

    # Create a simple agent with nano model for fast testing
    agent = BaseAgent(client, model="gpt-5-nano")

    # Test messages
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Count from 1 to 5, one number per line."}
    ]

    print("\nStreaming response:")
    print("-" * 70)

    full_response = ""
    chunk_count = 0

    # Stream the response
    for chunk in agent._call_model_streaming(messages, temperature=0.7):
        print(chunk, end='', flush=True)
        full_response += chunk
        chunk_count += 1

    print("\n" + "-" * 70)
    print(f"\nReceived {chunk_count} chunks")
    print(f"Total response length: {len(full_response)} characters")

    if chunk_count > 0 and len(full_response) > 0:
        print("✓ BaseAgent streaming test PASSED")
        return True
    else:
        print("✗ BaseAgent streaming test FAILED")
        return False


def test_content_agent_streaming():
    """Test ContentAgent.generate_content() with stream=True"""
    print("\n" + "="*70)
    print("TEST 2: ContentAgent Streaming")
    print("="*70)

    # Load environment and create client
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found in environment")
        return False

    client = OpenAI(api_key=api_key)

    # Load config
    config = load_config()

    # Create content agent with nano model for fast testing
    agent = ContentAgent(client, model="gpt-5-nano", config=config)

    # Test parameters
    topic = "The Water Cycle"
    subject = "Science"
    grade = "5th Grade"
    style = "engaging"
    extra = "Keep it brief for testing"
    language = "English"
    include_keypoints = True

    print(f"\nGenerating content for: {topic}")
    print("-" * 70)

    full_content = ""
    chunk_count = 0

    # Stream the content
    content_stream = agent.generate_content(
        topic=topic,
        subject=subject,
        grade=grade,
        style=style,
        extra=extra,
        language=language,
        include_keypoints=include_keypoints,
        stream=True  # Enable streaming
    )

    for chunk in content_stream:
        print(chunk, end='', flush=True)
        full_content += chunk
        chunk_count += 1

    print("\n" + "-" * 70)
    print(f"\nReceived {chunk_count} chunks")
    print(f"Total content length: {len(full_content)} characters")

    if chunk_count > 0 and len(full_content) > 0:
        print("✓ ContentAgent streaming test PASSED")
        return True
    else:
        print("✗ ContentAgent streaming test FAILED")
        return False


def test_backward_compatibility():
    """Test that non-streaming mode still works (backward compatibility)"""
    print("\n" + "="*70)
    print("TEST 3: Backward Compatibility (Non-Streaming)")
    print("="*70)

    # Load environment and create client
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found in environment")
        return False

    client = OpenAI(api_key=api_key)

    # Load config
    config = load_config()

    # Create content agent with nano model for fast testing
    agent = ContentAgent(client, model="gpt-5-nano", config=config)

    # Test parameters
    topic = "Photosynthesis"
    subject = "Biology"
    grade = "6th Grade"
    style = "clear"
    extra = "Very brief"
    language = "English"
    include_keypoints = False

    print(f"\nGenerating content for: {topic} (non-streaming)")
    print("-" * 70)

    # Call without streaming (default behavior)
    content = agent.generate_content(
        topic=topic,
        subject=subject,
        grade=grade,
        style=style,
        extra=extra,
        language=language,
        include_keypoints=include_keypoints
        # stream parameter defaults to False
    )

    print(content)
    print("-" * 70)
    print(f"Content length: {len(content)} characters")

    if isinstance(content, str) and len(content) > 0:
        print("✓ Backward compatibility test PASSED")
        return True
    else:
        print("✗ Backward compatibility test FAILED")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("STREAMING FUNCTIONALITY TESTS")
    print("="*70)
    print("\nThis script tests the new streaming capabilities added to InstaSchool.")
    print("It will make API calls using gpt-5-nano for speed and cost efficiency.")

    results = []

    # Run all tests
    results.append(("BaseAgent Streaming", test_base_agent_streaming()))
    results.append(("ContentAgent Streaming", test_content_agent_streaming()))
    results.append(("Backward Compatibility", test_backward_compatibility()))

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name}: {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests PASSED! Streaming functionality is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) FAILED. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
