"""
Test script for caching functionality
Uses gpt-4.1-nano for cost-effective testing
"""

import os
import time
from pathlib import Path

# Set test API key and import libraries
try:
    from dotenv import load_dotenv
    load_dotenv()
    
    from openai import OpenAI
    from services.cache_service import SmartCache, ContentCache
    from src.agent_framework import ContentAgent
    import yaml
    
    print("✓ All imports successful")
    
except ImportError as e:
    print(f"Import error: {e}")
    exit(1)

def test_content_cache():
    """Test basic content caching functionality"""
    print("\n=== Testing Content Cache ===")
    
    # Initialize cache
    cache = ContentCache(cache_dir="test_cache", max_age_days=1)
    
    # Test parameters
    test_params = {
        'topic': 'Photosynthesis',
        'subject': 'Science',
        'grade': '5',
        'style': 'Standard',
        'language': 'English'
    }
    
    test_content = "Plants make their own food through photosynthesis..."
    
    # Test caching
    print("1. Testing cache storage...")
    success = cache.cache_content("content", test_params, test_content)
    print(f"   Cache storage: {'✓' if success else '✗'}")
    
    # Test retrieval
    print("2. Testing cache retrieval...")
    cached = cache.get_cached_content("content", test_params)
    print(f"   Cache retrieval: {'✓' if cached == test_content else '✗'}")
    
    # Test cache miss
    print("3. Testing cache miss...")
    different_params = test_params.copy()
    different_params['topic'] = 'Different Topic'
    missed = cache.get_cached_content("content", different_params)
    print(f"   Cache miss: {'✓' if missed is None else '✗'}")
    
    # Test cache stats
    print("4. Testing cache stats...")
    stats = cache.get_cache_stats()
    print(f"   Total files: {stats['total_files']}")
    print(f"   Total size: {stats['total_size_mb']} MB")
    
    return True

def test_smart_cache():
    """Test smart cache with similarity detection"""
    print("\n=== Testing Smart Cache ===")
    
    cache = SmartCache(cache_dir="test_cache")
    
    # Test similar content detection
    original_params = {
        'topic': 'photosynthesis',
        'subject': 'science',
        'grade': '5',
        'style': 'standard',
        'language': 'english'
    }
    
    similar_params = {
        'topic': 'Photosynthesis',  # Different case
        'subject': 'Science',       # Different case
        'grade': '5',
        'style': 'Standard',        # Different case
        'language': 'English',      # Different case
        'extra': 'some extra text'  # Additional parameter
    }
    
    # Cache original content
    test_content = "Test content about photosynthesis"
    cache.content_cache.cache_content("content", original_params, test_content)
    
    # Test similarity detection
    print("1. Testing similarity detection...")
    similar_content = cache.get_similar_content("content", similar_params)
    print(f"   Similarity match: {'✓' if similar_content == test_content else '✗'}")
    
    return True

def test_agent_caching():
    """Test caching integration with agents"""
    print("\n=== Testing Agent Caching Integration ===")
    
    # Initialize OpenAI client
    client = OpenAI()
    
    # Load config with test model
    config_path = "config.yaml"
    if not Path(config_path).exists():
        print("   ⚠️  config.yaml not found, skipping agent test")
        return True
        
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Override with test model for cost savings
    original_model = config["defaults"]["worker_model"]
    config["defaults"]["worker_model"] = "gpt-4.1-nano"
    
    print(f"   Using test model: gpt-4.1-nano (instead of {original_model})")
    
    # Initialize content agent
    content_agent = ContentAgent(client, "gpt-4.1-nano", config)
    
    # Test parameters
    test_params = {
        'topic': 'Simple Addition',
        'subject': 'Mathematics', 
        'grade': '1',
        'style': 'Playful',
        'extra': '',
        'language': 'English',
        'include_keypoints': True
    }
    
    print("1. First generation (should call API)...")
    start_time = time.time()
    content1 = content_agent.generate_content(**test_params)
    first_duration = time.time() - start_time
    print(f"   Duration: {first_duration:.2f}s")
    print(f"   Content generated: {'✓' if content1 and len(content1) > 50 else '✗'}")
    
    print("2. Second generation (should use cache)...")
    start_time = time.time()
    content2 = content_agent.generate_content(**test_params)
    second_duration = time.time() - start_time
    print(f"   Duration: {second_duration:.2f}s")
    print(f"   Content matches: {'✓' if content1 == content2 else '✗'}")
    print(f"   Speed improvement: {first_duration/second_duration:.1f}x faster")
    
    return True

def cleanup_test_cache():
    """Clean up test cache directory"""
    import shutil
    test_cache_dir = Path("test_cache")
    if test_cache_dir.exists():
        shutil.rmtree(test_cache_dir)
        print("✓ Test cache cleaned up")

def main():
    """Run all cache tests"""
    print("🧪 Testing Caching System")
    print("=" * 50)
    
    try:
        # Run tests
        test_content_cache()
        test_smart_cache()
        test_agent_caching()
        
        print("\n" + "=" * 50)
        print("✅ All caching tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        cleanup_test_cache()

if __name__ == "__main__":
    main()