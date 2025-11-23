"""
Test script for template functionality
Uses gpt-4.1-nano for cost-effective testing
"""

import os
import json
from pathlib import Path

# Import and test template functionality
try:
    from services.template_service import TemplateManager, TemplateMetadata, TemplateStructure
    
    print("✓ All imports successful")
    
except ImportError as e:
    print(f"Import error: {e}")
    exit(1)


def test_template_creation():
    """Test template creation and management"""
    print("\n=== Testing Template Creation ===")
    
    # Initialize template manager with test directory
    template_manager = TemplateManager("test_templates")
    
    # Test creating a template from mock curriculum
    mock_curriculum = {
        "meta": {
            "subject": "Science",
            "grade": "5",
            "style": "Hands-on",
            "language": "English",
            "media_richness": 3,
            "include_quizzes": True,
            "include_summary": True,
            "include_resources": True,
            "include_keypoints": True
        },
        "units": [
            {"title": "Introduction to Photosynthesis"},
            {"title": "Plant Structure and Function"},
            {"title": "Energy and Light"},
            {"title": "Real-World Applications"}
        ]
    }
    
    print("1. Creating template from curriculum...")
    try:
        template_id = template_manager.create_template(
            name="Test Science Template",
            description="A test template for elementary science",
            curriculum=mock_curriculum,
            tags=["science", "elementary", "test"],
            is_public=False
        )
        print(f"   Template created: {template_id} ✓")
    except Exception as e:
        print(f"   Template creation failed: {e} ✗")
        return False
    
    # Test template retrieval
    print("2. Retrieving template...")
    template = template_manager.get_template(template_id)
    if template:
        metadata = template["metadata"]
        structure = template["structure"]
        print(f"   Template name: {metadata.name} ✓")
        print(f"   Topic count: {structure.topic_count} ✓")
    else:
        print("   Template retrieval failed ✗")
        return False
    
    # Test template listing
    print("3. Listing templates...")
    templates = template_manager.list_templates()
    found_template = any(t.id == template_id for t in templates)
    print(f"   Found {len(templates)} templates")
    print(f"   Test template found: {'✓' if found_template else '✗'}")
    
    return True


def test_builtin_templates():
    """Test built-in template functionality"""
    print("\n=== Testing Built-in Templates ===")
    
    template_manager = TemplateManager("test_templates")
    
    # Check for built-in templates
    system_templates = template_manager.list_templates(include_user=False, include_shared=False)
    
    print(f"1. Found {len(system_templates)} system templates")
    
    expected_templates = ["elementary_science", "high_school_inquiry", "math_problem_solving"]
    
    for expected in expected_templates:
        found = any(t.id == expected for t in system_templates)
        print(f"   {expected}: {'✓' if found else '✗'}")
    
    # Test applying a built-in template
    if system_templates:
        print("2. Testing template application...")
        try:
            template = system_templates[0]
            params = template_manager.apply_template(
                template.id,
                "Science",
                "3",
                custom_params={"custom_prompt": "Focus on hands-on activities"}
            )
            
            required_keys = ["subject_str", "grade", "lesson_style", "template_id"]
            has_all_keys = all(key in params for key in required_keys)
            print(f"   Template application: {'✓' if has_all_keys else '✗'}")
            print(f"   Template name: {params.get('template_name', 'Unknown')}")
            
        except Exception as e:
            print(f"   Template application failed: {e} ✗")
            return False
    
    return True


def test_template_search():
    """Test template search functionality"""
    print("\n=== Testing Template Search ===")
    
    template_manager = TemplateManager("test_templates")
    
    # Test search
    print("1. Testing search functionality...")
    
    # Search for science templates
    science_templates = template_manager.search_templates("science")
    print(f"   Science templates found: {len(science_templates)}")
    
    # Search for elementary templates  
    elementary_templates = template_manager.search_templates("elementary")
    print(f"   Elementary templates found: {len(elementary_templates)}")
    
    # Test filtering
    print("2. Testing filtering...")
    science_filtered = template_manager.list_templates(subject_filter="Science")
    print(f"   Science subject filter: {len(science_filtered)} templates")
    
    grade_3_filtered = template_manager.list_templates(grade_filter="3")
    print(f"   Grade 3 filter: {len(grade_3_filtered)} templates")
    
    return True


def test_template_stats():
    """Test template statistics"""
    print("\n=== Testing Template Statistics ===")
    
    template_manager = TemplateManager("test_templates")
    
    try:
        stats = template_manager.get_template_stats()
        
        print(f"1. Total templates: {stats['total_templates']}")
        print(f"2. User templates: {stats['user_templates']}")
        print(f"3. System templates: {stats['system_templates']}")
        print(f"4. Total usage: {stats['total_usage']}")
        print(f"5. Subjects covered: {len(stats['subjects'])}")
        print(f"6. Grade levels: {len(stats['grades'])}")
        
        if stats["popular_templates"]:
            print(f"7. Most popular: {stats['popular_templates'][0].name}")
        
        print("   Statistics generation: ✓")
        return True
        
    except Exception as e:
        print(f"   Statistics failed: {e} ✗")
        return False


def cleanup_test_templates():
    """Clean up test template directory"""
    import shutil
    test_dir = Path("test_templates")
    if test_dir.exists():
        shutil.rmtree(test_dir)
        print("✓ Test templates cleaned up")


def main():
    """Run all template tests"""
    print("📋 Testing Template System")
    print("=" * 50)
    
    try:
        # Run tests
        test_template_creation()
        test_builtin_templates()
        test_template_search()
        test_template_stats()
        
        print("\n" + "=" * 50)
        print("✅ All template tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        cleanup_test_templates()


if __name__ == "__main__":
    main()