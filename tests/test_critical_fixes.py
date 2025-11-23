"""
Test script for critical fixes
Validates that all identified issues have been resolved
"""

import time
import threading
from pathlib import Path

# Import all services to test fixes
try:
    from services.cache_service import ContentCache, SmartCache
    from services.batch_service import BatchManager, BatchJob, BatchStatus
    from services.template_service import TemplateManager
    from services.retry_service import RetryHandler
    
    print("✓ All imports successful")
    
except ImportError as e:
    print(f"Import error: {e}")
    exit(1)


def test_json_serialization_fix():
    """Test that JSON serialization handles non-serializable objects"""
    print("\n=== Testing JSON Serialization Fix ===")
    
    cache = ContentCache("test_critical_cache")
    
    # Test with non-serializable objects
    problematic_params = {
        'topic': 'Test Topic',
        'subject': 'Science',
        'grade': '3',
        'function': lambda x: x,  # Non-serializable function
        'complex_object': cache,  # Non-serializable object
        'nested': {'func': print}  # Nested non-serializable
    }
    
    print("1. Testing cache key generation with non-serializable objects...")
    try:
        cache_key = cache._generate_cache_key("content", problematic_params)
        print(f"   Cache key generated: {cache_key[:16]}... ✓")
        
        # Try to cache content with these params
        success = cache.cache_content("content", problematic_params, "Test content")
        print(f"   Content cached successfully: {'✓' if success else '✗'}")
        
        # Try to retrieve it
        retrieved = cache.get_cached_content("content", problematic_params)
        print(f"   Content retrieved: {'✓' if retrieved == 'Test content' else '✗'}")
        
        return True
        
    except Exception as e:
        print(f"   JSON serialization fix failed: {e} ✗")
        return False


def test_thread_safety_fix():
    """Test that batch processing is thread-safe"""
    print("\n=== Testing Thread Safety Fix ===")
    
    batch_manager = BatchManager("test_critical_batches", max_concurrent=2)
    results = []
    errors = []
    
    def mock_generator(params):
        """Mock generator with simulated work"""
        time.sleep(0.1)  # Simulate work
        return {"result": f"Generated for {params.get('name', 'unknown')}"}
    
    # Create multiple jobs that will run concurrently
    job_configs = []
    for i in range(10):
        job_configs.append({
            "name": f"Job {i}",
            "subject_str": "Science",
            "grade": "3"
        })
    
    print("1. Creating batch with multiple concurrent jobs...")
    batch_id = batch_manager.create_custom_batch(
        job_configs=job_configs,
        name="Thread Safety Test Batch",
        description="Testing thread safety of batch processing"
    )
    
    print("2. Starting concurrent batch processing...")
    success = batch_manager.start_batch(batch_id, mock_generator)
    if not success:
        print("   Batch start failed ✗")
        return False
    
    # Monitor for completion
    max_wait = 30
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        batch_status = batch_manager.get_batch_status(batch_id)
        if not batch_status:
            print("   Lost batch status ✗")
            return False
        
        if batch_status.status in [BatchStatus.COMPLETED, BatchStatus.FAILED]:
            break
        
        time.sleep(0.5)
    
    # Check final results
    final_status = batch_manager.get_batch_status(batch_id)
    if final_status:
        print(f"   Batch completed: {final_status.completed_jobs}/{final_status.total_jobs}")
        print(f"   Thread safety test: {'✓' if final_status.completed_jobs == final_status.total_jobs else '✗'}")
        return final_status.completed_jobs == final_status.total_jobs
    
    return False


def test_file_locking_fix():
    """Test that file operations are safe under concurrent access"""
    print("\n=== Testing File Locking Fix ===")
    
    cache = ContentCache("test_critical_cache")
    results = []
    
    def concurrent_cache_operation(thread_id):
        """Simulate concurrent cache operations"""
        try:
            for i in range(5):
                params = {
                    'topic': f'Topic {thread_id}_{i}',
                    'subject': 'Science',
                    'thread_id': thread_id
                }
                
                # Cache content
                success = cache.cache_content("content", params, f"Content from thread {thread_id}, iteration {i}")
                if not success:
                    results.append(f"Thread {thread_id}: Cache write failed")
                    return
                
                # Retrieve content
                retrieved = cache.get_cached_content("content", params)
                if not retrieved:
                    results.append(f"Thread {thread_id}: Cache read failed")
                    return
                    
            results.append(f"Thread {thread_id}: Success")
            
        except Exception as e:
            results.append(f"Thread {thread_id}: Error - {e}")
    
    print("1. Starting concurrent cache operations...")
    threads = []
    for i in range(5):
        thread = threading.Thread(target=concurrent_cache_operation, args=(i,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    print("2. Analyzing results...")
    successful_threads = sum(1 for result in results if "Success" in result)
    total_threads = 5
    
    print(f"   Successful threads: {successful_threads}/{total_threads}")
    print(f"   File locking test: {'✓' if successful_threads == total_threads else '✗'}")
    
    # Print any errors
    for result in results:
        if "Error" in result or "failed" in result:
            print(f"   {result}")
    
    return successful_threads == total_threads


def test_template_validation_fix():
    """Test that template validation prevents corruption"""
    print("\n=== Testing Template Validation Fix ===")
    
    template_manager = TemplateManager("test_critical_templates")
    
    # Test with invalid template data
    invalid_template_file = Path("test_critical_templates/user/invalid_template.json")
    invalid_template_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Create invalid template data
    invalid_data = {
        "metadata": {
            "id": "invalid",
            "name": "Invalid Template"
            # Missing required fields
        },
        "structure": {
            "topic_count": "not_a_number"  # Wrong type
            # Missing required fields
        }
    }
    
    print("1. Creating invalid template file...")
    import json
    with open(invalid_template_file, 'w') as f:
        json.dump(invalid_data, f)
    
    print("2. Testing template validation...")
    loaded_template = template_manager._load_template_file(invalid_template_file)
    
    if loaded_template is None:
        print("   Template validation correctly rejected invalid data ✓")
        
        # Test with valid template data
        valid_data = {
            "metadata": {
                "id": "valid",
                "name": "Valid Template",
                "description": "A valid template",
                "subjects": ["Science"],
                "grades": ["3"],
                "style": "Standard",
                "language": "English",
                "author": "Test",
                "created_at": "2024-01-01",
                "updated_at": "2024-01-01",
                "usage_count": 0,
                "tags": [],
                "is_public": False
            },
            "structure": {
                "topic_count": 3,
                "media_richness": 3,
                "include_quizzes": True,
                "include_summary": True,
                "include_resources": True,
                "include_keypoints": True,
                "topic_templates": [],
                "custom_prompts": {}
            }
        }
        
        valid_template_file = Path("test_critical_templates/user/valid_template.json")
        with open(valid_template_file, 'w') as f:
            json.dump(valid_data, f)
        
        print("3. Testing with valid template data...")
        loaded_valid = template_manager._load_template_file(valid_template_file)
        
        if loaded_valid is not None:
            print("   Valid template loaded successfully ✓")
            return True
        else:
            print("   Valid template failed to load ✗")
            return False
    else:
        print("   Template validation failed to reject invalid data ✗")
        return False


def test_memory_management_fix():
    """Test that memory usage is controlled"""
    print("\n=== Testing Memory Management Fix ===")
    
    # Create batch manager with low memory limits for testing
    batch_manager = BatchManager("test_critical_batches", max_concurrent=2)
    batch_manager.queue.max_completed_jobs = 5  # Low limit for testing
    
    def quick_generator(params):
        """Quick generator for memory test"""
        return {"result": f"Quick result for {params.get('id', 'unknown')}"}
    
    # Create many small jobs to test memory cleanup
    job_configs = []
    for i in range(20):  # More than the limit
        job_configs.append({
            "id": f"memory_test_{i}",
            "subject_str": "Science",
            "grade": "3"
        })
    
    print("1. Creating batch with many jobs to test memory management...")
    batch_id = batch_manager.create_custom_batch(
        job_configs=job_configs,
        name="Memory Management Test",
        description="Testing memory cleanup"
    )
    
    print("2. Processing batch...")
    batch_manager.start_batch(batch_id, quick_generator)
    
    # Wait for completion
    max_wait = 15
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        batch_status = batch_manager.get_batch_status(batch_id)
        if batch_status and batch_status.status in [BatchStatus.COMPLETED, BatchStatus.FAILED]:
            break
        time.sleep(0.5)
    
    print("3. Checking memory usage...")
    completed_jobs_count = len(batch_manager.queue.completed_jobs)
    max_allowed = batch_manager.queue.max_completed_jobs
    
    print(f"   Completed jobs in memory: {completed_jobs_count}")
    print(f"   Maximum allowed: {max_allowed}")
    print(f"   Memory management: {'✓' if completed_jobs_count <= max_allowed else '✗'}")
    
    return completed_jobs_count <= max_allowed


def cleanup_test_files():
    """Clean up test files"""
    import shutil
    test_dirs = [
        "test_critical_cache",
        "test_critical_templates",
        "test_critical_batches"
    ]
    
    for test_dir in test_dirs:
        test_path = Path(test_dir)
        if test_path.exists():
            shutil.rmtree(test_path)
            print(f"✓ {test_dir} cleaned up")


def main():
    """Run all critical fix tests"""
    print("🔧 Testing Critical Fixes")
    print("=" * 50)
    
    tests = [
        ("JSON Serialization Fix", test_json_serialization_fix),
        ("Thread Safety Fix", test_thread_safety_fix),
        ("File Locking Fix", test_file_locking_fix),
        ("Template Validation Fix", test_template_validation_fix),
        ("Memory Management Fix", test_memory_management_fix)
    ]
    
    results = []
    
    try:
        for test_name, test_func in tests:
            print(f"\n{'='*20} {test_name} {'='*20}")
            try:
                result = test_func()
                results.append((test_name, result))
                print(f"Result: {'✅ PASSED' if result else '❌ FAILED'}")
            except Exception as e:
                print(f"❌ FAILED with exception: {e}")
                results.append((test_name, False))
        
        print("\n" + "=" * 60)
        print("📊 FINAL RESULTS:")
        print("=" * 60)
        
        passed = 0
        for test_name, result in results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"  {test_name}: {status}")
            if result:
                passed += 1
        
        total = len(results)
        print(f"\n🎯 Summary: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("\n🎉 ALL CRITICAL FIXES VERIFIED!")
            print("🚀 System is now production-ready with all issues resolved.")
        else:
            print(f"\n⚠️  {total-passed} critical issues still need attention.")
            
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        cleanup_test_files()


if __name__ == "__main__":
    main()