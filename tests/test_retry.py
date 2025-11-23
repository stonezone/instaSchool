"""
Test script for retry functionality
Uses gpt-4.1-nano for cost-effective testing
"""

import time
from typing import Any

# Import and test retry functionality
try:
    from services.retry_service import (
        RetryHandler, ErrorClassifier, ErrorType, RetryConfig,
        with_retry, GracefulDegradation
    )
    from openai import OpenAI
    import yaml
    
    print("✓ All imports successful")
    
except ImportError as e:
    print(f"Import error: {e}")
    exit(1)


class MockAPIError(Exception):
    """Mock API error for testing"""
    pass


def test_error_classification():
    """Test error classification logic"""
    print("\n=== Testing Error Classification ===")
    
    test_cases = [
        ("Rate limit exceeded", ErrorType.RATE_LIMIT),
        ("Too many requests", ErrorType.RATE_LIMIT),
        ("Connection timeout", ErrorType.NETWORK),
        ("Server error 503", ErrorType.SERVER_ERROR),
        ("Unauthorized access", ErrorType.AUTHENTICATION),
        ("Insufficient quota", ErrorType.QUOTA_EXCEEDED),
        ("Content policy violation", ErrorType.CONTENT_FILTER),
        ("Unknown weird error", ErrorType.UNKNOWN)
    ]
    
    for error_msg, expected_type in test_cases:
        error = Exception(error_msg)
        classified = ErrorClassifier.classify_error(error)
        status = "✓" if classified == expected_type else "✗"
        print(f"   {error_msg}: {classified.value} {status}")
    
    return True


def test_retry_logic():
    """Test retry logic with mock failures"""
    print("\n=== Testing Retry Logic ===")
    
    retry_handler = RetryHandler()
    
    # Test function that fails twice then succeeds
    call_count = 0
    def mock_function_partial_failure():
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise MockAPIError("Temporary failure")
        return "Success!"
    
    print("1. Testing partial failure (fails 2x, then succeeds)...")
    call_count = 0
    start_time = time.time()
    
    try:
        config = RetryConfig(max_retries=3, base_delay=0.1)  # Fast for testing
        result = retry_handler.retry_with_backoff(
            mock_function_partial_failure,
            config=config,
            context="mock test"
        )
        duration = time.time() - start_time
        print(f"   Result: {result}")
        print(f"   Attempts: {call_count}")
        print(f"   Duration: {duration:.2f}s")
        print(f"   Status: {'✓' if result == 'Success!' and call_count == 3 else '✗'}")
    except Exception as e:
        print(f"   Unexpected error: {e}")
    
    # Test function that always fails
    def mock_function_always_fails():
        raise MockAPIError("Permanent failure")
    
    print("2. Testing permanent failure...")
    try:
        config = RetryConfig(max_retries=2, base_delay=0.1)
        result = retry_handler.retry_with_backoff(
            mock_function_always_fails,
            config=config,
            context="mock test"
        )
        print(f"   Unexpected success: {result} ✗")
    except Exception as e:
        print(f"   Expected failure: {type(e).__name__} ✓")
    
    return True


def test_retry_decorator():
    """Test the retry decorator"""
    print("\n=== Testing Retry Decorator ===")
    
    call_count = 0
    
    @with_retry(config=RetryConfig(max_retries=2, base_delay=0.1), context="decorator test")
    def decorated_function():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise MockAPIError("First call fails")
        return f"Success on attempt {call_count}"
    
    call_count = 0
    try:
        result = decorated_function()
        print(f"   Result: {result}")
        print(f"   Total attempts: {call_count}")
        print(f"   Status: {'✓' if call_count == 2 else '✗'}")
    except Exception as e:
        print(f"   Unexpected error: {e} ✗")
    
    return True


def test_graceful_degradation():
    """Test graceful degradation functionality"""
    print("\n=== Testing Graceful Degradation ===")
    
    # Test fallback content creation
    params = {
        'topic': 'Photosynthesis',
        'subject': 'Science',
        'grade': '5'
    }
    
    content_types = ['content', 'quiz', 'summary', 'resources']
    
    for content_type in content_types:
        fallback = GracefulDegradation.create_fallback_content(content_type, params)
        has_content = fallback and len(str(fallback)) > 10
        print(f"   {content_type}: {'✓' if has_content else '✗'}")
    
    # Test partial failure handling
    curriculum = {
        'meta': {'grade': '5', 'subject': 'Science'},
        'units': [
            {'title': 'Photosynthesis', 'content': 'Good content'},
            {'title': 'Respiration', 'content': '', 'quiz': None}
        ]
    }
    
    failed_components = ['quiz', 'summary']
    result = GracefulDegradation.handle_partial_failure(curriculum, failed_components)
    
    # Check if fallback content was added
    unit = result['units'][1]
    has_fallback_quiz = unit.get('quiz') is not None
    has_fallback_summary = unit.get('summary') is not None
    has_partial_failure_flag = result['meta'].get('partial_failure', False)
    
    print(f"   Partial failure handling: {'✓' if all([has_fallback_quiz, has_fallback_summary, has_partial_failure_flag]) else '✗'}")
    
    return True


def test_with_real_api():
    """Test with real API using cheap model"""
    print("\n=== Testing with Real API ===")
    
    try:
        # Load config and use nano model
        from dotenv import load_dotenv
        load_dotenv()
        
        client = OpenAI()
        
        # Import agent with retry functionality
        from src.agent_framework import ContentAgent
        
        with open("config.yaml", 'r') as f:
            config = yaml.safe_load(f)
        
        # Use nano model for cost savings
        agent = ContentAgent(client, "gpt-4.1-nano", config)
        
        print("   Testing real API call with retry (using gpt-4.1-nano)...")
        
        start_time = time.time()
        content = agent.generate_content(
            topic="Testing",
            subject="Mathematics",
            grade="1",
            style="Simple",
            extra="",
            language="English",
            include_keypoints=False
        )
        duration = time.time() - start_time
        
        success = content and len(content) > 20 and "Error" not in content
        print(f"   Duration: {duration:.2f}s")
        print(f"   Content length: {len(content) if content else 0}")
        print(f"   Status: {'✓' if success else '✗'}")
        
        if not success:
            print(f"   Content: {content[:100]}...")
        
    except Exception as e:
        print(f"   API test failed: {e}")
        return False
    
    return True


def main():
    """Run all retry tests"""
    print("🔄 Testing Retry System")
    print("=" * 50)
    
    try:
        test_error_classification()
        test_retry_logic()
        test_retry_decorator()
        test_graceful_degradation()
        test_with_real_api()
        
        print("\n" + "=" * 50)
        print("✅ All retry tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()