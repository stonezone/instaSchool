#!/usr/bin/env python
"""
Test Phase 3 integration - Model selection and cost estimation
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_cost_estimator():
    """Test cost estimation functionality"""
    print("Testing Cost Estimator...")
    try:
        from src.cost_estimator import estimate_curriculum_cost, get_model_info
        
        # Test with nano for everything (cheapest)
        nano_cost = estimate_curriculum_cost("gpt-4.1-nano", "gpt-4.1-nano")
        print(f"✓ Nano-only cost: ${nano_cost['total']:.2f}")
        
        # Test with mixed models
        mixed_cost = estimate_curriculum_cost("gpt-4.1", "gpt-4.1-nano")
        print(f"✓ Mixed (full+nano) cost: ${mixed_cost['total']:.2f}")
        
        # Test savings calculation
        savings = mixed_cost['savings_vs_full']
        print(f"✓ Savings vs full: ${savings['amount']:.2f} ({savings['percent']:.0f}%)")
        
        # Test model info
        nano_info = get_model_info("gpt-4.1-nano")
        assert nano_info['relative_cost'] == "$"
        print(f"✓ Model info working: {nano_info['name']}")
        
        return True
    except Exception as e:
        print(f"✗ Cost estimator test failed: {e}")
        return False

def test_config_defaults():
    """Test that nano is the default"""
    print("\nTesting Config Defaults...")
    try:
        import yaml
        
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        assert config['defaults']['text_model'] == 'gpt-4.1-nano'
        print("✓ Text model default is nano")
        
        assert config['defaults']['worker_model'] == 'gpt-4.1-nano'
        print("✓ Worker model default is nano")
        
        return True
    except Exception as e:
        print(f"✗ Config test failed: {e}")
        return False

def test_model_flow():
    """Test that models flow through the system"""
    print("\nTesting Model Flow...")
    try:
        # Mock the OpenAI client
        class MockClient:
            def __init__(self):
                self.last_model = None
                
            class Completions:
                def __init__(self, client):
                    self.client = client
                    
                def create(self, **kwargs):
                    self.client.last_model = kwargs.get('model')
                    # Return mock response
                    class MockChoice:
                        class Message:
                            content = '{"topics": [{"title": "Test"}]}'
                    class MockResponse:
                        choices = [MockChoice()]
                    return MockResponse()
            
            @property
            def chat(self):
                class Chat:
                    completions = self.Completions(self)
                return Chat()
        
        from src.agent_framework import OrchestratorAgent
        
        client = MockClient()
        
        # Test orchestrator uses correct model
        orchestrator = OrchestratorAgent(client, "gpt-4.1", "gpt-4.1-nano")
        assert orchestrator.model == "gpt-4.1"
        assert orchestrator.worker_model == "gpt-4.1-nano"
        print("✓ Orchestrator models set correctly")
        
        return True
    except Exception as e:
        print(f"✗ Model flow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all Phase 3 tests"""
    print("Running Phase 3 Integration Tests")
    print("=" * 50)
    
    tests = [
        ("Cost Estimator", test_cost_estimator),
        ("Config Defaults", test_config_defaults),
        ("Model Flow", test_model_flow)
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
    
    if passed == total:
        print("\n🎉 All tests passed! Ready to test with nano model.")
    else:
        print("\n⚠️ Some tests failed. Please fix before proceeding.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)