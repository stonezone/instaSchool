"""
Retry Service with Enhanced Error Handling
Implements exponential backoff and intelligent retry mechanisms for API calls
"""

import time
import random
import traceback
from typing import Callable, Any, Optional, Dict, List
from functools import wraps
from enum import Enum

from openai import APIError, RateLimitError, APIConnectionError, AuthenticationError, BadRequestError


class RetryError(Exception):
    """Custom exception for retry-related errors"""

    def __init__(self, message: str, errors: Optional[List[Exception]] = None):
        super().__init__(message)
        self.errors = errors or []

    def __str__(self) -> str:
        base = super().__str__()
        if not self.errors:
            return base
        error_details = "\n".join(
            f"  Attempt {i + 1}: {e}" for i, e in enumerate(self.errors)
        )
        return f"{base}\nPrevious errors:\n{error_details}"


class ErrorType(Enum):
    """Classification of different error types for retry strategies"""
    RATE_LIMIT = "rate_limit"
    NETWORK = "network"
    SERVER_ERROR = "server_error"
    AUTHENTICATION = "authentication"
    QUOTA_EXCEEDED = "quota_exceeded"
    CONTENT_FILTER = "content_filter"
    UNKNOWN = "unknown"


class RetryConfig:
    """Configuration for retry behavior"""
    
    def __init__(self, 
                 max_retries: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 exponential_base: float = 2.0,
                 jitter: bool = True):
        """Initialize retry configuration
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds for exponential backoff
            max_delay: Maximum delay between retries
            exponential_base: Base for exponential backoff calculation
            jitter: Whether to add random jitter to delays
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


class ErrorClassifier:
    """Classifies errors and determines retry strategies"""

    @staticmethod
    def classify_error(error: Exception) -> ErrorType:
        """Classify an error to determine retry strategy

        Uses isinstance() checks for OpenAI exceptions, falls back to string matching
        for other error types and backward compatibility.

        Args:
            error: The exception to classify

        Returns:
            ErrorType classification
        """
        # Use isinstance() for OpenAI-specific exceptions (most reliable)
        if isinstance(error, RateLimitError):
            return ErrorType.RATE_LIMIT

        if isinstance(error, AuthenticationError):
            return ErrorType.AUTHENTICATION

        if isinstance(error, APIConnectionError):
            return ErrorType.NETWORK

        if isinstance(error, BadRequestError):
            # BadRequestError could be content filter or other issues
            error_msg = str(error).lower()
            if any(term in error_msg for term in ['content_filter', 'safety', 'policy', 'moderation']):
                return ErrorType.CONTENT_FILTER
            # Otherwise treat as unknown (non-retryable via should_retry logic)
            return ErrorType.UNKNOWN

        if isinstance(error, APIError):
            # Check if it's a quota error specifically
            error_msg = str(error).lower()
            if any(term in error_msg for term in ['quota', 'insufficient_quota', 'billing']):
                return ErrorType.QUOTA_EXCEEDED
            # Check for server errors in API errors
            if any(term in error_msg for term in ['500', '502', '503', '504']):
                return ErrorType.SERVER_ERROR
            # Generic API error - retryable
            return ErrorType.SERVER_ERROR

        # Fallback to string matching for non-OpenAI exceptions or older code
        error_msg = str(error).lower()

        # Rate limiting errors (fallback)
        if any(term in error_msg for term in ['rate limit', 'too many requests', '429']):
            return ErrorType.RATE_LIMIT

        # Network errors (fallback)
        if any(term in error_msg for term in ['connection', 'timeout', 'network', 'dns']):
            return ErrorType.NETWORK

        # Server errors (5xx) (fallback)
        if any(term in error_msg for term in ['server error', '500', '502', '503', '504']):
            return ErrorType.SERVER_ERROR

        # Authentication errors (fallback)
        if any(term in error_msg for term in ['unauthorized', '401', 'api key', 'authentication']):
            return ErrorType.AUTHENTICATION

        # Quota errors (fallback)
        if any(term in error_msg for term in ['quota', 'insufficient_quota', 'billing']):
            return ErrorType.QUOTA_EXCEEDED

        # Content filtering (fallback)
        if any(term in error_msg for term in ['content_filter', 'safety', 'policy', 'moderation']):
            return ErrorType.CONTENT_FILTER

        return ErrorType.UNKNOWN
    
    @staticmethod
    def should_retry(error_type: ErrorType) -> bool:
        """Determine if an error type should be retried
        
        Args:
            error_type: The classified error type
            
        Returns:
            True if the error should be retried
        """
        # Don't retry authentication, quota, or content filter errors
        non_retryable = {
            ErrorType.AUTHENTICATION,
            ErrorType.QUOTA_EXCEEDED,
            ErrorType.CONTENT_FILTER
        }
        
        return error_type not in non_retryable
    
    @staticmethod
    def get_retry_config(error_type: ErrorType) -> RetryConfig:
        """Get retry configuration based on error type
        
        Args:
            error_type: The classified error type
            
        Returns:
            Appropriate retry configuration
        """
        if error_type == ErrorType.RATE_LIMIT:
            # More aggressive backoff for rate limits
            return RetryConfig(max_retries=5, base_delay=2.0, max_delay=120.0)
        elif error_type == ErrorType.NETWORK:
            # Quick retries for network issues
            return RetryConfig(max_retries=4, base_delay=0.5, max_delay=30.0)
        elif error_type == ErrorType.SERVER_ERROR:
            # Standard backoff for server errors
            return RetryConfig(max_retries=3, base_delay=1.0, max_delay=60.0)
        else:
            # Default configuration
            return RetryConfig()


class RetryHandler:
    """Handles retry logic with exponential backoff"""
    
    def __init__(self, logger=None):
        """Initialize retry handler
        
        Args:
            logger: Optional logger for retry events
        """
        self.logger = logger
    
    def calculate_delay(self, attempt: int, config: RetryConfig) -> float:
        """Calculate delay for exponential backoff with jitter
        
        Args:
            attempt: Current attempt number (0-based)
            config: Retry configuration
            
        Returns:
            Delay in seconds
        """
        # Exponential backoff
        delay = config.base_delay * (config.exponential_base ** attempt)
        
        # Cap at maximum delay
        delay = min(delay, config.max_delay)
        
        # Add jitter to prevent thundering herd
        if config.jitter:
            jitter_amount = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_amount, jitter_amount)
        
        return max(0, delay)
    
    def retry_with_backoff(self, 
                          func: Callable,
                          *args,
                          config: Optional[RetryConfig] = None,
                          context: str = "operation",
                          **kwargs) -> Any:
        """Execute function with retry and exponential backoff
        
        Args:
            func: Function to execute
            *args: Positional arguments for function
            config: Optional retry configuration
            context: Description of operation for logging
            **kwargs: Keyword arguments for function
            
        Returns:
            Function result
            
        Raises:
            RetryError: If all retries failed
        """
        if config is None:
            config = RetryConfig()
        
        last_error: Optional[Exception] = None
        errors: List[Exception] = []
        
        for attempt in range(config.max_retries + 1):
            try:
                if self.logger and attempt > 0:
                    self.logger.log_debug(f"Retry attempt {attempt} for {context}")
                
                result = func(*args, **kwargs)
                
                if attempt > 0 and self.logger:
                    self.logger.log_debug(f"Success on attempt {attempt + 1} for {context}")
                
                return result
                
            except Exception as e:
                last_error = e
                errors.append(e)
                error_type = ErrorClassifier.classify_error(e)
                
                # Log the error
                if self.logger:
                    self.logger.log_error(
                        error=e, 
                        context=f"{context} (attempt {attempt + 1}) - {error_type.value}"
                    )
                
                # Check if we should retry
                if not ErrorClassifier.should_retry(error_type):
                    if self.logger:
                        self.logger.log_debug(f"Not retrying {error_type.value} error for {context}")
                    raise e
                
                # If this was the last attempt, don't sleep
                if attempt >= config.max_retries:
                    break
                
                # Get error-specific retry config if needed
                error_config = ErrorClassifier.get_retry_config(error_type)
                if error_type in [ErrorType.RATE_LIMIT, ErrorType.NETWORK]:
                    config = error_config
                
                # Calculate delay and sleep
                delay = self.calculate_delay(attempt, config)
                
                if self.logger:
                    self.logger.log_debug(f"Waiting {delay:.2f}s before retry {attempt + 1} for {context}")
                
                time.sleep(delay)
        
        # All retries failed
        error_msg = f"All {config.max_retries + 1} attempts failed for {context}"
        if last_error:
            error_msg += f". Last error: {last_error}"
        
        if self.logger:
            self.logger.log_error(error=RetryError(error_msg, errors=errors), context=context)
        
        raise RetryError(error_msg, errors=errors) from last_error


def with_retry(config: Optional[RetryConfig] = None, context: str = "operation"):
    """Decorator for adding retry logic to functions
    
    Args:
        config: Optional retry configuration
        context: Description of operation for logging
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Try to get logger from the first argument if it's an agent
            logger = None
            if args and hasattr(args[0], 'logger'):
                logger = args[0].logger
            
            retry_handler = RetryHandler(logger)
            return retry_handler.retry_with_backoff(
                func, *args, config=config, context=context, **kwargs
            )
        return wrapper
    return decorator


class GracefulDegradation:
    """Handles graceful degradation when services fail"""
    
    @staticmethod
    def create_fallback_content(content_type: str, params: Dict[str, Any]) -> Any:
        """Create fallback content when generation fails
        
        Args:
            content_type: Type of content to create fallback for
            params: Original generation parameters
            
        Returns:
            Fallback content
        """
        topic = params.get('topic', 'this topic')
        grade = params.get('grade', 'students')
        subject = params.get('subject', 'subject')
        
        fallbacks = {
            'content': f"""# {topic}
            
*This lesson content is temporarily unavailable. Please try regenerating or check your connection.*

## Overview
This lesson was designed to teach {grade} level students about {topic} in {subject}.

## What to do next:
- Try regenerating this content using the regenerate button
- Check your internet connection
- Verify your API key is valid
- Contact support if the problem persists

*We apologize for the inconvenience.*
            """,
            
            'quiz': [
                {
                    "question": f"What is the main topic of this lesson about {topic}?",
                    "type": "FILL",
                    "options": [],
                    "answer": topic
                }
            ],
            
            'summary': f"This lesson covered important concepts about {topic}. Please regenerate this content for a complete summary.",
            
            'resources': f"• Try searching for '{topic}' on educational websites\n• Check your textbook for related information\n• Ask your teacher for additional resources"
        }
        
        return fallbacks.get(content_type, f"Fallback content for {content_type}")
    
    @staticmethod
    def handle_partial_failure(curriculum: Dict[str, Any], failed_components: List[str]) -> Dict[str, Any]:
        """Handle partial failures in curriculum generation
        
        Args:
            curriculum: Partially generated curriculum
            failed_components: List of failed component types
            
        Returns:
            Curriculum with fallback content for failed components
        """
        for unit in curriculum.get('units', []):
            for component in failed_components:
                if component not in unit or not unit[component]:
                    # Create fallback content
                    params = {
                        'topic': unit.get('title', 'Unknown Topic'),
                        'grade': curriculum.get('meta', {}).get('grade', 'students'),
                        'subject': curriculum.get('meta', {}).get('subject', 'subject')
                    }
                    
                    fallback = GracefulDegradation.create_fallback_content(component, params)
                    unit[component] = fallback
                    
                    # Mark as fallback content
                    unit[f'{component}_is_fallback'] = True
        
        # Add metadata about partial failure
        curriculum.setdefault('meta', {})['partial_failure'] = True
        curriculum['meta']['failed_components'] = failed_components
        
        return curriculum
