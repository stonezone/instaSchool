"""
Core Type Definitions for InstaSchool
Contains BaseAgent and shared type definitions to prevent circular dependencies.
This module should have minimal dependencies to serve as a foundation.
"""

from typing import Dict, Any, List, Optional
from openai import APIError, RateLimitError, APIConnectionError, AuthenticationError, BadRequestError


class BaseAgent:
    """Base class for all agents with common functionality.
    
    This class provides core functionality for:
    - API calls with retry logic
    - Caching support
    - Logging support
    - Error handling
    
    Agents should inherit from this class to get standard behavior.
    """
    
    def __init__(self, client, model: str = "gpt-4.1"):
        """Initialize base agent.
        
        Args:
            client: OpenAI client instance
            model: Model identifier to use for generation
        """
        self.client = client
        self.model = model
        
        # Initialize caching with conditional import
        self.cache = None
        try:
            from services.cache_service import SmartCache
            self.cache = SmartCache()
        except ImportError:
            print("Warning: cache_service not available, caching disabled.")
        
        # Initialize retry handler with conditional import
        self.retry_handler = None
        try:
            from services.retry_service import RetryHandler
            self.retry_handler = RetryHandler()
        except ImportError:
            print("Warning: retry_service not available, retry disabled.")
        
        # Initialize logger with conditional import
        self.logger = None
        try:
            from src.verbose_logger import get_logger
            self.logger = get_logger()
            # Pass logger to retry handler if both exist
            if self.retry_handler and self.logger:
                self.retry_handler.logger = self.logger
        except ImportError:
            print("Warning: Could not import verbose_logger. API call logging will be disabled.")
    
    def _call_model_cached(
        self, 
        content_type: str, 
        cache_params: Dict[str, Any], 
        messages: List[Dict[str, str]], 
        response_format=None, 
        temperature: float = 0.7
    ):
        """Call model with caching support.
        
        Args:
            content_type: Type of content being generated (for cache key)
            cache_params: Parameters to use for cache key generation
            messages: Messages for the API call
            response_format: Optional response format
            temperature: Temperature setting
            
        Returns:
            API response or cached content
        """
        # Try cache first if available
        if self.cache:
            cached_content = self.cache.get_similar_content(content_type, cache_params)
            if cached_content:
                # Create a mock response object for consistency
                class CachedResponse:
                    def __init__(self, content):
                        self.choices = [
                            type('obj', (object,), {
                                'message': type('obj', (object,), {'content': content})()
                            })
                        ]
                        
                return CachedResponse(cached_content)
        
        # If no cache hit, make the API call
        response = self._call_model(messages, response_format, temperature)
        
        # Cache the response if successful
        if response and response.choices and self.cache:
            content = response.choices[0].message.content
            self.cache.content_cache.cache_content(content_type, cache_params, content)
            
        return response
    
    # Models that don't support temperature parameter
    NO_TEMPERATURE_MODELS = ['gpt-5-nano', 'o1', 'o3', 'o4']

    def _call_model(self, messages, response_format=None, temperature: float = 0.7):
        """Call the model with standard parameters and retry logic.

        Args:
            messages: List of message dictionaries for the API
            response_format: Optional response format specification
            temperature: Temperature parameter for generation

        Returns:
            API response or None on error
        """
        params = {
            "model": self.model,
            "messages": messages,
        }

        # Only add temperature if model supports it
        # Some models (gpt-5-nano, o1, o3, o4 series) don't support temperature
        model_lower = self.model.lower()
        supports_temperature = not any(
            model_lower.startswith(prefix) for prefix in self.NO_TEMPERATURE_MODELS
        )
        if supports_temperature:
            params["temperature"] = temperature

        if response_format:
            params["response_format"] = response_format

        # Create a safe copy of params for logging
        if self.logger:
            log_params = params.copy()
            # Truncate messages to avoid overwhelming logs
            if 'messages' in log_params and isinstance(log_params['messages'], list):
                truncated_messages = []
                for msg in log_params['messages']:
                    truncated_msg = msg.copy()
                    if 'content' in truncated_msg and isinstance(truncated_msg['content'], str) and len(truncated_msg['content']) > 500:
                        truncated_msg['content'] = truncated_msg['content'][:500] + "... [content truncated]"
                    truncated_messages.append(truncated_msg)
                log_params['messages'] = truncated_messages

            # Log the API request
            self.logger.log_api_request(model=self.model, endpoint="chat.completions", params=log_params)

        # Define the API call function for retry
        def make_api_call():
            response = self.client.chat.completions.create(**params)

            # Log the response if logger is available
            if self.logger:
                self.logger.log_api_response(model=self.model, response=response)

            return response

        try:
            # Use retry handler if available
            if self.retry_handler:
                return self.retry_handler.retry_with_backoff(
                    make_api_call,
                    context=f"{self.model} API call"
                )
            else:
                return make_api_call()

        except RateLimitError as e:
            # Rate limit exceeded - retryable
            if self.logger:
                self.logger.log_error(error=e, model=self.model, context="Rate limit exceeded")
            print(f"Rate limit exceeded: {e}")
            raise  # Let retry handler deal with this

        except AuthenticationError as e:
            # Authentication failed - non-retryable
            if self.logger:
                self.logger.log_error(error=e, model=self.model, context="Authentication failed")
            print(f"Authentication error: {e}")
            try:
                import streamlit as st
                st.error("⚠️ OpenAI API authentication failed. Please check your API key.")
            except ImportError:
                pass
            return None

        except APIConnectionError as e:
            # Connection error - retryable
            if self.logger:
                self.logger.log_error(error=e, model=self.model, context="Connection error")
            print(f"Connection error: {e}")
            raise  # Let retry handler deal with this

        except BadRequestError as e:
            # Bad request - non-retryable
            if self.logger:
                self.logger.log_error(error=e, model=self.model, context="Bad request")
            print(f"Bad request error: {e}")
            return None

        except APIError as e:
            # Generic API error - retryable
            error_msg = str(e)
            if self.logger:
                self.logger.log_error(error=e, model=self.model, context="API error")
            print(f"API error: {e}")

            # Check for quota error specifically
            if "insufficient_quota" in error_msg.lower() or "quota" in error_msg.lower():
                try:
                    import streamlit as st
                    st.error("⚠️ OpenAI API quota exceeded. Please check your billing details or try again later.")
                except ImportError:
                    pass
                return None  # Don't retry quota errors

            raise  # Let retry handler deal with other API errors

        except Exception as e:
            # Unexpected error - non-retryable
            if self.logger:
                self.logger.log_error(error=e, model=self.model, context="Unexpected error in API call")
            print(f"Unexpected error: {e}")
            return None

    def _call_model_streaming(self, messages, response_format=None, temperature: float = 0.7):
        """Call the model with streaming enabled for real-time output.

        Args:
            messages: List of message dictionaries for the API
            response_format: Optional response format specification (note: streaming may not support all formats)
            temperature: Temperature parameter for generation

        Yields:
            str: Content chunks as they arrive from the API

        Returns:
            str: The complete response text after streaming completes, or None on error
        """
        params = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }

        # Only add temperature if model supports it
        model_lower = self.model.lower()
        supports_temperature = not any(
            model_lower.startswith(prefix) for prefix in self.NO_TEMPERATURE_MODELS
        )
        if supports_temperature:
            params["temperature"] = temperature

        # Note: response_format may not be supported with streaming for all models
        if response_format:
            params["response_format"] = response_format

        # Log the streaming request
        if self.logger:
            log_params = params.copy()
            if 'messages' in log_params and isinstance(log_params['messages'], list):
                truncated_messages = []
                for msg in log_params['messages']:
                    truncated_msg = msg.copy()
                    if 'content' in truncated_msg and isinstance(truncated_msg['content'], str) and len(truncated_msg['content']) > 500:
                        truncated_msg['content'] = truncated_msg['content'][:500] + "... [content truncated]"
                    truncated_messages.append(truncated_msg)
                log_params['messages'] = truncated_messages

            self.logger.log_api_request(model=self.model, endpoint="chat.completions (streaming)", params=log_params)

        try:
            # Create the streaming request
            stream = self.client.chat.completions.create(**params)

            full_response = ""
            for chunk in stream:
                # Check if we have content in the delta
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        content = delta.content
                        full_response += content
                        yield content  # Yield each chunk for real-time display

            # Log the complete response
            if self.logger:
                # Create a mock response object for logging
                class StreamingResponse:
                    def __init__(self, content):
                        self.choices = [
                            type('obj', (object,), {
                                'message': type('obj', (object,), {'content': content})()
                            })
                        ]

                self.logger.log_api_response(model=self.model, response=StreamingResponse(full_response))

            return full_response

        except RateLimitError as e:
            if self.logger:
                self.logger.log_error(error=e, model=self.model, context="Rate limit exceeded (streaming)")
            yield f"[Error: Rate limit exceeded - {str(e)}]"
            return None

        except AuthenticationError as e:
            if self.logger:
                self.logger.log_error(error=e, model=self.model, context="Authentication failed (streaming)")
            yield f"[Error: Authentication failed - {str(e)}]"
            try:
                import streamlit as st
                st.error("⚠️ OpenAI API authentication failed. Please check your API key.")
            except ImportError:
                pass
            return None

        except APIConnectionError as e:
            if self.logger:
                self.logger.log_error(error=e, model=self.model, context="Connection error (streaming)")
            yield f"[Error: Connection error - {str(e)}]"
            return None

        except BadRequestError as e:
            if self.logger:
                self.logger.log_error(error=e, model=self.model, context="Bad request (streaming)")
            yield f"[Error: Bad request - {str(e)}]"
            return None

        except APIError as e:
            error_msg = str(e)
            if self.logger:
                self.logger.log_error(error=e, model=self.model, context="API error (streaming)")

            if "insufficient_quota" in error_msg.lower() or "quota" in error_msg.lower():
                yield f"[Error: API quota exceeded - {str(e)}]"
                try:
                    import streamlit as st
                    st.error("⚠️ OpenAI API quota exceeded. Please check your billing details or try again later.")
                except ImportError:
                    pass
                return None

            yield f"[Error: API error - {str(e)}]"
            return None

        except Exception as e:
            if self.logger:
                self.logger.log_error(error=e, model=self.model, context="Unexpected error in streaming call")
            yield f"[Error: Unexpected error - {str(e)}]"
            return None
