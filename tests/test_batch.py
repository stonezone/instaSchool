"""
Test script for batch functionality
Uses mock generation for cost-effective testing
"""

import time
import random
from pathlib import Path

# Import and test batch functionality
try:
    from services.batch_service import BatchManager, BatchJob, BatchRequest, BatchStatus
    from services.template_service import TemplateManager
    
    print("✓ All imports successful")
    
except ImportError as e:
    print(f"Import error: {e}")
    exit(1)


def mock_curriculum_generator(params: dict) -> dict:
    """Mock curriculum generator for testing"""
    # Simulate generation time
    time.sleep(random.uniform(0.5, 2.0))
    
    # Randomly fail 10% of the time to test error handling
    if random.random() < 0.1:
        raise Exception("Mock generation failure")
    
    # Return mock curriculum
    return {
        "meta": {
            "subject": params.get("subject_str", "Unknown"),
            "grade": params.get("grade", "Unknown"),
            "generated": "mock_generation"
        },
        "units": [
            {"title": f"Unit 1: Introduction to {params.get('subject_str', 'Topic')}"},
            {"title": f"Unit 2: Advanced {params.get('subject_str', 'Topic')}"}
        ]
    }


def test_batch_creation():
    """Test batch creation and management"""
    print("\n=== Testing Batch Creation ===")
    
    # Initialize batch manager with test directory
    batch_manager = BatchManager("test_batches", max_concurrent=2)
    
    # Create custom batch
    job_configs = [
        {"subject_str": "Science", "grade": "3", "lesson_style": "Hands-on"},
        {"subject_str": "Mathematics", "grade": "3", "lesson_style": "Standard"},
        {"subject_str": "Science", "grade": "4", "lesson_style": "Hands-on"},
        {"subject_str": "Mathematics", "grade": "4", "lesson_style": "Standard"}
    ]
    
    print("1. Creating custom batch...")
    batch_id = batch_manager.create_custom_batch(
        job_configs=job_configs,
        name="Test Batch",
        description="Test batch for multiple subjects and grades"
    )
    print(f"   Batch created: {batch_id} ✓")
    
    # Check batch status
    print("2. Checking initial batch status...")
    batch_status = batch_manager.get_batch_status(batch_id)
    if batch_status:
        print(f"   Batch name: {batch_status.name}")
        print(f"   Total jobs: {batch_status.total_jobs}")
        print(f"   Status: {batch_status.status.value} ✓")
    else:
        print("   Batch status retrieval failed ✗")
        return False
    
    return batch_id


def test_batch_execution(batch_id: str, batch_manager):
    """Test batch execution"""
    print("\n=== Testing Batch Execution ===")
    
    print("1. Starting batch execution...")
    success = batch_manager.start_batch(batch_id, mock_curriculum_generator)
    if success:
        print("   Batch started ✓")
    else:
        print("   Batch start failed ✗")
        return False
    
    # Monitor progress
    print("2. Monitoring batch progress...")
    start_time = time.time()
    max_wait = 30  # Maximum wait time in seconds
    
    while time.time() - start_time < max_wait:
        batch_status = batch_manager.get_batch_status(batch_id)
        if not batch_status:
            print("   Lost batch status ✗")
            return False
        
        print(f"   Progress: {batch_status.completed_jobs + batch_status.failed_jobs}/{batch_status.total_jobs} jobs")
        print(f"   Status: {batch_status.status.value}")
        
        if batch_status.status in [BatchStatus.COMPLETED, BatchStatus.FAILED, BatchStatus.CANCELLED]:
            break
        
        time.sleep(2)
    
    # Final status check
    final_status = batch_manager.get_batch_status(batch_id)
    if final_status:
        print(f"   Final status: {final_status.status.value}")
        print(f"   Completed jobs: {final_status.completed_jobs}")
        print(f"   Failed jobs: {final_status.failed_jobs}")
        
        success_rate = final_status.completed_jobs / final_status.total_jobs
        print(f"   Success rate: {success_rate:.1%} {'✓' if success_rate > 0.5 else '✗'}")
        
        return True
    else:
        print("   Final status check failed ✗")
        return False


def test_template_batch():
    """Test batch creation from templates"""
    print("\n=== Testing Template-Based Batch ===")
    
    # Initialize template manager
    template_manager = TemplateManager("test_templates")
    batch_manager = BatchManager("test_batches", max_concurrent=2)
    
    # Get a system template
    templates = template_manager.list_templates(include_user=False, include_shared=False)
    if not templates:
        print("   No system templates found ✗")
        return False
    
    template = templates[0]
    print(f"   Using template: {template.name}")
    
    # Create batch from template
    try:
        batch_id = batch_manager.create_batch_from_template(
            template_id=template.id,
            subjects=["Science", "Mathematics"],
            grades=["3", "4"],
            template_manager=template_manager,
            name=f"Template Batch - {template.name}",
            description=f"Batch using {template.name} template"
        )
        print(f"   Template batch created: {batch_id} ✓")
        
        # Check job count
        batch_status = batch_manager.get_batch_status(batch_id)
        expected_jobs = 2 * 2  # 2 subjects × 2 grades
        if batch_status and batch_status.total_jobs == expected_jobs:
            print(f"   Job count correct: {batch_status.total_jobs} ✓")
        else:
            print(f"   Job count incorrect: expected {expected_jobs}, got {batch_status.total_jobs if batch_status else 0} ✗")
        
        return batch_id
        
    except Exception as e:
        print(f"   Template batch creation failed: {e} ✗")
        return None


def test_batch_management():
    """Test batch management operations"""
    print("\n=== Testing Batch Management ===")
    
    batch_manager = BatchManager("test_batches", max_concurrent=2)
    
    # List batches
    print("1. Listing batches...")
    batches = batch_manager.list_batches()
    print(f"   Found {len(batches)} batches")
    
    if batches:
        batch = batches[0]
        print(f"   Latest batch: {batch.name}")
        
        # Test batch results retrieval
        print("2. Getting batch results...")
        results = batch_manager.get_batch_results(batch.id)
        print(f"   Results available: {len(results)}")
        
        for result in results[:2]:  # Show first 2 results
            job_name = result.get("job_name", "Unknown")
            subject = result.get("result", {}).get("meta", {}).get("subject", "Unknown")
            print(f"   - {job_name}: {subject}")
        
        print("   Batch results: ✓")
    
    return True


def cleanup_test_batches():
    """Clean up test batch directory"""
    import shutil
    test_dirs = ["test_batches", "test_templates"]
    for test_dir in test_dirs:
        test_path = Path(test_dir)
        if test_path.exists():
            shutil.rmtree(test_path)
            print(f"✓ {test_dir} cleaned up")


def main():
    """Run all batch tests"""
    print("⚡ Testing Batch Generation System")
    print("=" * 50)
    
    try:
        # Run tests
        batch_id = test_batch_creation()
        if batch_id:
            batch_manager = BatchManager("test_batches", max_concurrent=2)
            test_batch_execution(batch_id, batch_manager)
        
        template_batch_id = test_template_batch()
        test_batch_management()
        
        print("\n" + "=" * 50)
        print("✅ All batch tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        cleanup_test_batches()


if __name__ == "__main__":
    main()