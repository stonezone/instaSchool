"""
Dynamic OpenAI Model Detection for InstaSchool
Detects available models from OpenAI API and filters for curriculum generation use cases.

This module provides functionality to query the OpenAI API for available models
and filter them into categories useful for curriculum generation:
- Text models: GPT-4, GPT-3.5-turbo, O1, O3 series
- Image models: DALL-E and GPT-Image series
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


@dataclass
class ModelCache:
    """Cache for model data with expiration"""
    text_models: List[str] = field(default_factory=list)
    image_models: List[str] = field(default_factory=list)
    all_models: List[str] = field(default_factory=list)
    timestamp: Optional[datetime] = None
    cache_duration: timedelta = timedelta(hours=1)
    
    def is_expired(self) -> bool:
        """Check if cache is expired"""
        if self.timestamp is None:
            return True
        return datetime.now() - self.timestamp > self.cache_duration
    
    def update(self, text_models: List[str], image_models: List[str], all_models: List[str]):
        """Update cache with new data"""
        self.text_models = text_models
        self.image_models = image_models
        self.all_models = all_models
        self.timestamp = datetime.now()


# Global cache instance
_model_cache = ModelCache()


def get_available_models(
    client: Optional[OpenAI] = None,
    force_refresh: bool = False
) -> Dict[str, List[str]]:
    """
    Get available OpenAI models filtered for curriculum generation.
    
    Args:
        client: OpenAI client instance (optional, will create if not provided)
        force_refresh: Force refresh cache even if not expired
        
    Returns:
        Dictionary with keys:
        - 'text_models': List of text generation models
        - 'image_models': List of image generation models
        - 'all_models': List of all detected models
        - 'error': Error message if detection failed (optional)
    """
    global _model_cache
    
    # Return cached data if valid and not forcing refresh
    if not force_refresh and not _model_cache.is_expired():
        return {
            'text_models': _model_cache.text_models,
            'image_models': _model_cache.image_models,
            'all_models': _model_cache.all_models
        }
    
    # Check if OpenAI library is available
    if OpenAI is None:
        error_msg = "OpenAI library not installed. Run: pip install openai"
        sys.stderr.write(f"Model detection error: {error_msg}\n")
        return {
            'text_models': [],
            'image_models': [],
            'all_models': [],
            'error': error_msg
        }
    
    # Create client if not provided
    if client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            error_msg = "OPENAI_API_KEY not set in environment"
            sys.stderr.write(f"Model detection error: {error_msg}\n")
            return {
                'text_models': [],
                'image_models': [],
                'all_models': [],
                'error': error_msg
            }
        
        try:
            client = OpenAI(api_key=api_key)
        except Exception as e:
            error_msg = f"Failed to initialize OpenAI client: {e}"
            sys.stderr.write(f"Model detection error: {error_msg}\n")
            return {
                'text_models': [],
                'image_models': [],
                'all_models': [],
                'error': error_msg
            }
    
    # Fetch models from API
    try:
        response = client.models.list()
        all_models = [m.id for m in response.data]
        
        # Filter for text models - ONLY cheap variants (mini, nano)
        # Expensive models (gpt-4o, gpt-4-turbo, o1, o3) excluded to save costs
        # GPT 3.x REMOVED - outdated
        # Use Kimi or DeepSeek for heavy text generation instead
        cheap_text_patterns = ['gpt-4o-mini', 'gpt-4.1-mini', 'gpt-4.1-nano', 'gpt-5-mini', 'gpt-4-mini', 'nano']
        # Exclude 3.x models explicitly
        exclude_patterns = ['gpt-3', 'gpt-3.5']
        text_models = [
            m for m in all_models
            if any(pattern in m.lower() for pattern in cheap_text_patterns)
            and not any(excl in m.lower() for excl in exclude_patterns)
        ]
        
        # Filter for image models (DALL-E, GPT-Image series)
        image_prefixes = ['dall-e', 'gpt-image']
        image_models = [
            m for m in all_models 
            if any(prefix in m.lower() for prefix in image_prefixes)
        ]
        
        # Sort models for consistent ordering
        text_models.sort(reverse=True)  # Reverse to get latest versions first
        image_models.sort(reverse=True)
        
        # Update cache
        _model_cache.update(text_models, image_models, all_models)
        
        # Log success to stderr
        sys.stderr.write(f"Model detection successful: {len(text_models)} text models, {len(image_models)} image models\n")
        
        return {
            'text_models': text_models,
            'image_models': image_models,
            'all_models': all_models
        }
        
    except Exception as e:
        error_msg = f"Error fetching models from OpenAI API: {e}"
        sys.stderr.write(f"Model detection error: {error_msg}\n")
        return {
            'text_models': [],
            'image_models': [],
            'all_models': [],
            'error': error_msg
        }


def get_fallback_models(config: Optional[Dict] = None) -> Dict[str, List[str]]:
    """
    Get fallback model lists from config.yaml.
    
    Args:
        config: Configuration dictionary (optional)
        
    Returns:
        Dictionary with 'text_models' and 'image_models' lists
    """
    if config is None:
        # Return hardcoded fallbacks - cheap OpenAI models only
        # GPT 3.x REMOVED - Use Kimi/DeepSeek for main text generation
        return {
            'text_models': ['gpt-4o-mini', 'gpt-4.1-mini', 'gpt-4.1-nano', 'gpt-5-mini'],
            'image_models': ['dall-e-3', 'dall-e-2', 'gpt-image-1']
        }
    
    # Extract from config
    defaults = config.get('defaults', {})
    return {
        'text_models': defaults.get('text_models', ['gpt-4o', 'gpt-4o-mini']),
        'image_models': defaults.get('image_models', ['dall-e-3', 'dall-e-2'])
    }


def validate_model_exists(model_name: str, model_type: str = 'text', client: Optional[OpenAI] = None) -> Tuple[bool, str]:
    """
    Validate that a specific model exists in the available models.
    
    Args:
        model_name: Name of the model to validate
        model_type: Type of model ('text' or 'image')
        client: OpenAI client instance (optional)
        
    Returns:
        Tuple of (is_valid, message)
    """
    models = get_available_models(client)
    
    if 'error' in models:
        return False, f"Could not validate model: {models['error']}"
    
    model_list = models.get(f'{model_type}_models', [])
    
    if model_name in model_list:
        return True, f"Model '{model_name}' is available"
    else:
        return False, f"Model '{model_name}' not found in available {model_type} models"


def get_recommended_models() -> Dict[str, str]:
    """
    Get recommended default models for different use cases.
    
    Returns:
        Dictionary with recommended model names for different roles
    """
    models = get_available_models()
    
    text_models = models.get('text_models', [])
    image_models = models.get('image_models', [])
    
    recommendations = {
        'orchestrator': None,
        'worker': None,
        'image': None
    }
    
    # Recommend orchestrator model (highest capability)
    for model in ['gpt-4o', 'gpt-4-turbo', 'gpt-4']:
        if model in text_models or any(m.startswith(model) for m in text_models):
            matching = [m for m in text_models if m.startswith(model)]
            if matching:
                recommendations['orchestrator'] = matching[0]
                break
    
    # Recommend worker model (balance of quality and cost)
    for model in ['gpt-4o-mini', 'gpt-3.5-turbo']:
        if model in text_models or any(m.startswith(model) for m in text_models):
            matching = [m for m in text_models if m.startswith(model)]
            if matching:
                recommendations['worker'] = matching[0]
                break
    
    # Recommend image model
    if image_models:
        # Prefer dall-e-3 if available, otherwise take first available
        dalle3_models = [m for m in image_models if 'dall-e-3' in m]
        if dalle3_models:
            recommendations['image'] = dalle3_models[0]
        else:
            recommendations['image'] = image_models[0]
    
    return recommendations


if __name__ == "__main__":
    """Test the model detection functionality"""
    print("Testing OpenAI Model Detection")
    print("=" * 60)
    
    # Test basic model detection
    print("\nDetecting available models...")
    models = get_available_models()
    
    if 'error' in models:
        print(f"❌ Error: {models['error']}")
    else:
        print(f"\n✅ Found {len(models['text_models'])} text models:")
        for model in models['text_models'][:10]:  # Show first 10
            print(f"  - {model}")
        if len(models['text_models']) > 10:
            print(f"  ... and {len(models['text_models']) - 10} more")
        
        print(f"\n✅ Found {len(models['image_models'])} image models:")
        for model in models['image_models']:
            print(f"  - {model}")
    
    # Test recommendations
    print("\nRecommended models:")
    recommendations = get_recommended_models()
    for role, model in recommendations.items():
        status = "✅" if model else "❌"
        print(f"  {status} {role}: {model or 'Not found'}")
    
    # Test cache
    print("\nTesting cache (should be instant)...")
    import time
    start = time.time()
    models_cached = get_available_models()
    elapsed = time.time() - start
    print(f"  Cache retrieval took {elapsed*1000:.2f}ms")
    
    print("\n" + "=" * 60)
    print("Test complete!")
