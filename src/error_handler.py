"""
Error Handler for InstaSchool Application
Provides comprehensive error handling with user-friendly messages
"""
import streamlit as st
from typing import Optional, Callable, Any, Dict
from functools import wraps
import traceback
from services.retry_service import RetryHandler

class ErrorHandler:
    """Centralized error handling for the application"""
    
    # User-friendly error messages
    ERROR_MESSAGES = {
        'api_key': "🔑 API Key Issue: Please check your OpenAI API key in the sidebar.",
        'quota': "💳 Quota Exceeded: Your OpenAI API quota has been exceeded. Please check your billing.",
        'rate_limit': "⏱️ Rate Limited: Too many requests. Please wait a moment and try again.",
        'network': "🌐 Network Error: Unable to connect to OpenAI. Please check your connection.",
        'content_filter': "🚫 Content Filtered: The content was blocked by safety filters. Try rephrasing.",
        'model_not_found': "🤖 Model Error: The selected model is not available. Please choose another.",
        'generation_failed': "❌ Generation Failed: Unable to generate content. Please try again.",
        'image_failed': "🖼️ Image Generation Failed: Unable to create images. Will continue without them.",
        'unknown': "⚠️ Unexpected Error: Something went wrong. Please try again."
    }
    
    @classmethod
    def handle_api_error(cls, error: Exception) -> str:
        """Convert API errors to user-friendly messages"""
        error_str = str(error).lower()
        
        if 'api key' in error_str or 'authentication' in error_str:
            return cls.ERROR_MESSAGES['api_key']
        elif 'quota' in error_str or 'insufficient_quota' in error_str:
            return cls.ERROR_MESSAGES['quota']
        elif 'rate limit' in error_str or 'rate_limit' in error_str:
            return cls.ERROR_MESSAGES['rate_limit']
        elif 'connection' in error_str or 'network' in error_str:
            return cls.ERROR_MESSAGES['network']
        elif 'content_policy' in error_str or 'filtered' in error_str:
            return cls.ERROR_MESSAGES['content_filter']
        elif 'model' in error_str and 'not found' in error_str:
            return cls.ERROR_MESSAGES['model_not_found']
        else:
            return cls.ERROR_MESSAGES['unknown']
    
    @classmethod
    def safe_api_call(cls, func: Callable, *args, **kwargs) -> Optional[Any]:
        """Execute API call with error handling"""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_msg = cls.handle_api_error(e)
            st.error(error_msg)
            
            # Log detailed error for debugging
            if st.session_state.get('verbose_mode', False):
                st.expander("Error Details").code(traceback.format_exc())
            
            return None
    
    @classmethod
    def with_error_boundary(cls, operation_name: str = "operation"):
        """Decorator for adding error boundaries to functions"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_msg = cls.handle_api_error(e)
                    st.error(f"{operation_name} failed: {error_msg}")
                    
                    if st.session_state.get('verbose_mode', False):
                        st.expander("Error Details").code(traceback.format_exc())
                    
                    # Return safe default based on function name
                    if 'generate' in func.__name__:
                        return None
                    elif 'create' in func.__name__:
                        return []
                    else:
                        return None
            return wrapper
        return decorator
    
    @classmethod
    def handle_generation_error(cls, error: Exception, component: str):
        """Handle errors during content generation with graceful degradation"""
        error_msg = cls.handle_api_error(error)
        
        # Show appropriate warning based on component
        if component == 'image':
            st.warning(f"Image generation skipped: {error_msg}")
        elif component == 'quiz':
            st.warning(f"Quiz generation skipped: {error_msg}")
        elif component == 'chart':
            st.warning(f"Chart generation skipped: {error_msg}")
        else:
            st.error(f"{component} generation failed: {error_msg}")
    
    @classmethod
    def validate_api_response(cls, response: Any, expected_type: type) -> bool:
        """Validate API response structure"""
        if response is None:
            return False
        
        if not isinstance(response, expected_type):
            st.warning(f"Unexpected response format. Expected {expected_type.__name__}")
            return False
        
        return True