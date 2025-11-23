#!/usr/bin/env python
"""
Test script to verify Phase 1 and 2 integration fixes
"""
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all new modules can be imported"""
    print("Testing imports...")
    try:
        from src.state_manager import StateManager
        print("✓ StateManager imported successfully")
    except Exception as e:
        print(f"✗ StateManager import failed: {e}")
        return False
    
    try:
        from src.error_handler import ErrorHandler
        print("✓ ErrorHandler imported successfully")
    except Exception as e:
        print(f"✗ ErrorHandler import failed: {e}")
        return False
    
    try:
        from utils.regeneration_fix import RegenerationHandler
        print("✓ RegenerationHandler imported successfully")
    except Exception as e:
        print(f"✗ RegenerationHandler import failed: {e}")
        return False
    
    try:
        from services.thread_manager import ThreadManager, thread_manager
        print("✓ ThreadManager imported successfully")
    except Exception as e:
        print(f"✗ ThreadManager import failed: {e}")
        return False
    
    return True

def test_state_manager():
    """Test StateManager functionality"""
    print("\nTesting StateManager...")
    try:
        # Mock streamlit session_state
        class MockSessionState(dict):
            pass
        
        import streamlit as st
        st.session_state = MockSessionState()
        
        from src.state_manager import StateManager
        
        # Test initialization
        StateManager.initialize_state()
        assert 'curriculum' in st.session_state
        assert 'quiz_answers' in st.session_state
        print("✓ State initialization works")
        
        # Test update
        StateManager.update_state('test_key', 'test_value')
        assert st.session_state.get('test_key') == 'test_value'
        print("✓ State update works")
        
        # Test batch update
        StateManager.batch_update({'key1': 'value1', 'key2': 'value2'})
        assert st.session_state.get('key1') == 'value1'
        assert st.session_state.get('key2') == 'value2'
        print("✓ Batch update works")
        
        return True
    except Exception as e:
        print(f"✗ StateManager test failed: {e}")
        return False

def test_error_handler():
    """Test ErrorHandler functionality"""
    print("\nTesting ErrorHandler...")
    try:
        from src.error_handler import ErrorHandler
        
        # Test error message mapping
        class MockError(Exception):
            pass
        
        api_key_error = MockError("Invalid API key")
        msg = ErrorHandler.handle_api_error(api_key_error)
        assert "API Key" in msg
        print("✓ Error message mapping works")
        
        # Test safe API call
        def failing_func():
            raise MockError("Test error")
        
        result = ErrorHandler.safe_api_call(failing_func)
        assert result is None
        print("✓ Safe API call handles errors")
        
        return True
    except Exception as e:
        print(f"✗ ErrorHandler test failed: {e}")
        return False

def test_thread_manager():
    """Test ThreadManager functionality"""
    print("\nTesting ThreadManager...")
    try:
        from services.thread_manager import thread_manager
        import time
        
        # Test thread creation
        def test_task():
            time.sleep(0.1)
        
        thread = thread_manager.start_thread("test_thread", test_task)
        assert thread.is_alive()
        print("✓ Thread creation works")
        
        # Wait for completion
        thread.join(timeout=1.0)
        assert thread.is_completed()
        print("✓ Thread completion tracking works")
        
        return True
    except Exception as e:
        print(f"✗ ThreadManager test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Running InstaSchool Phase 1 & 2 Integration Tests")
    print("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("StateManager", test_state_manager),
        ("ErrorHandler", test_error_handler),
        ("ThreadManager", test_thread_manager)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("Test Summary:")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)