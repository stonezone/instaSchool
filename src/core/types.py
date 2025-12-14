"""
Core Type Definitions for InstaSchool
Contains BaseAgent and shared type definitions to prevent circular dependencies.
This module should have minimal dependencies to serve as a foundation.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional, Callable
import contextvars
import re
from openai import APIError, RateLimitError, APIConnectionError, AuthenticationError, BadRequestError


TraceHook = Callable[[Dict[str, Any]], None]

_TRACE_HOOK: contextvars.ContextVar[Optional[TraceHook]] = contextvars.ContextVar(
    "instaschool_trace_hook", default=None
)
_TRACE_MAX_CHARS: contextvars.ContextVar[int] = contextvars.ContextVar(
    "instaschool_trace_max_chars", default=900
)


def set_trace_hook(hook: Optional[TraceHook], *, max_chars: int = 900) -> None:
    """Install a per-execution trace hook for LLM request/response telemetry."""
    _TRACE_HOOK.set(hook)
    try:
        _TRACE_MAX_CHARS.set(int(max_chars))
    except Exception:
        _TRACE_MAX_CHARS.set(900)


def get_trace_hook() -> Optional[TraceHook]:
    return _TRACE_HOOK.get()


class BaseAgent:
    """Base class for all agents with common functionality.
    
    This class provides core functionality for:
    - API calls with retry logic
    - Caching support
    - Logging support
    - Error handling
    
    Agents should inherit from this class to get standard behavior.
    """
    
    def __init__(self, client, model: str = "gpt-5-nano"):
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

    _SECRET_PATTERNS = [
        # OpenAI-style keys (best-effort)
        re.compile(r"\bsk-[A-Za-z0-9]{10,}\b"),
        re.compile(r"\bsk-proj-[A-Za-z0-9]{10,}\b"),
    ]

    def _redact(self, text: str) -> str:
        if not isinstance(text, str) or not text:
            return ""
        redacted = text
        for pat in self._SECRET_PATTERNS:
            redacted = pat.sub("[REDACTED]", redacted)
        return redacted

    def _summarize_messages(
        self, messages: Any, *, max_chars: int
    ) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        if not isinstance(messages, list):
            return out
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            role = msg.get("role")
            content = msg.get("content")
            summary: Dict[str, Any] = {"role": role}
            if isinstance(content, str):
                safe = self._redact(content)
                summary["content"] = safe[:max_chars] + ("… [truncated]" if len(safe) > max_chars else "")
                summary["content_len"] = len(content)
            elif isinstance(content, list):
                parts = []
                for part in content:
                    if isinstance(part, dict):
                        parts.append(part.get("type") or "part")
                    else:
                        parts.append(type(part).__name__)
                summary["content"] = f"[{', '.join(parts)}]"
                summary["content_len"] = len(content)
            else:
                summary["content"] = f"[{type(content).__name__}]"
            out.append(summary)
        return out

    def _emit_trace(self, payload: Dict[str, Any]) -> None:
        hook = get_trace_hook()
        if hook is None:
            return
        try:
            hook(payload)
        except Exception:
            return

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

        # Optional trace hook (UI opt-in; no Streamlit calls here)
        try:
            max_chars = int(_TRACE_MAX_CHARS.get())
        except Exception:
            max_chars = 900
        self._emit_trace(
            {
                "type": "llm.request",
                "model": self.model,
                "agent": self.__class__.__name__,
                "endpoint": "chat.completions",
                "supports_temperature": supports_temperature,
                "temperature": params.get("temperature"),
                "response_format": bool(response_format),
                "messages": self._summarize_messages(messages, max_chars=max_chars),
            }
        )

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

        def _call_chat_completions(call_params: Dict[str, Any]):
            return self.client.chat.completions.create(**call_params)

        def _supports_response_format_error(exc: Exception) -> bool:
            msg = str(exc).lower()
            # Many OpenAI-compatible providers reject this param with slightly different wording.
            return (
                "response_format" in msg
                or "json_object" in msg
                or "unsupported" in msg and "format" in msg
                or "unknown parameter" in msg and "response_format" in msg
            )

        # Define the API call function for retry
        def make_api_call():
            call_params = params
            try:
                response = _call_chat_completions(call_params)
            except BadRequestError as e:
                # Some providers (e.g., non-OpenAI OpenAI-compatible APIs) don't support `response_format`.
                # Retry once without it so curriculum JSON outputs can still work.
                if call_params.get("response_format") and _supports_response_format_error(e):
                    call_params = {k: v for k, v in call_params.items() if k != "response_format"}
                    response = _call_chat_completions(call_params)
                else:
                    raise

            # Log the response if logger is available
            if self.logger:
                self.logger.log_api_response(model=self.model, response=response)

            # Trace response (bounded; best-effort)
            try:
                content = ""
                finish_reason = None
                if getattr(response, "choices", None):
                    choice0 = response.choices[0]
                    finish_reason = getattr(choice0, "finish_reason", None)
                    msg0 = getattr(choice0, "message", None)
                    content = getattr(msg0, "content", "") if msg0 else ""

                usage_obj = getattr(response, "usage", None)
                usage = None
                if usage_obj is not None:
                    usage = {
                        "prompt_tokens": getattr(usage_obj, "prompt_tokens", None),
                        "completion_tokens": getattr(usage_obj, "completion_tokens", None),
                        "total_tokens": getattr(usage_obj, "total_tokens", None),
                    }

                safe_content = self._redact(content) if isinstance(content, str) else ""
                self._emit_trace(
                    {
                        "type": "llm.response",
                        "model": self.model,
                        "agent": self.__class__.__name__,
                        "finish_reason": finish_reason,
                        "usage": usage,
                        "content": safe_content[:max_chars]
                        + ("… [truncated]" if isinstance(safe_content, str) and len(safe_content) > max_chars else ""),
                        "content_len": len(content) if isinstance(content, str) else None,
                    }
                )
            except Exception:
                pass

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
            self._emit_trace(
                {
                    "type": "llm.error",
                    "model": self.model,
                    "agent": self.__class__.__name__,
                    "error_type": type(e).__name__,
                    "message": str(e),
                }
            )
            raise  # Let retry handler deal with this

        except AuthenticationError as e:
            # Authentication failed - non-retryable
            if self.logger:
                self.logger.log_error(error=e, model=self.model, context="Authentication failed")
            print(f"Authentication error: {e}")
            self._emit_trace(
                {
                    "type": "llm.error",
                    "model": self.model,
                    "agent": self.__class__.__name__,
                    "error_type": type(e).__name__,
                    "message": str(e),
                }
            )
            return None

        except APIConnectionError as e:
            # Connection error - retryable
            if self.logger:
                self.logger.log_error(error=e, model=self.model, context="Connection error")
            print(f"Connection error: {e}")
            self._emit_trace(
                {
                    "type": "llm.error",
                    "model": self.model,
                    "agent": self.__class__.__name__,
                    "error_type": type(e).__name__,
                    "message": str(e),
                }
            )
            raise  # Let retry handler deal with this

        except BadRequestError as e:
            # Bad request - non-retryable
            if self.logger:
                self.logger.log_error(error=e, model=self.model, context="Bad request")
            print(f"Bad request error: {e}")
            self._emit_trace(
                {
                    "type": "llm.error",
                    "model": self.model,
                    "agent": self.__class__.__name__,
                    "error_type": type(e).__name__,
                    "message": str(e),
                }
            )
            return None

        except APIError as e:
            # Generic API error - retryable
            error_msg = str(e)
            if self.logger:
                self.logger.log_error(error=e, model=self.model, context="API error")
            print(f"API error: {e}")
            self._emit_trace(
                {
                    "type": "llm.error",
                    "model": self.model,
                    "agent": self.__class__.__name__,
                    "error_type": type(e).__name__,
                    "message": error_msg,
                }
            )

            # Check for quota error specifically
            if "insufficient_quota" in error_msg.lower() or "quota" in error_msg.lower():
                return None  # Don't retry quota errors

            raise  # Let retry handler deal with other API errors

        except Exception as e:
            # Unexpected error - non-retryable
            if self.logger:
                self.logger.log_error(error=e, model=self.model, context="Unexpected error in API call")
            print(f"Unexpected error: {e}")
            self._emit_trace(
                {
                    "type": "llm.error",
                    "model": self.model,
                    "agent": self.__class__.__name__,
                    "error_type": type(e).__name__,
                    "message": str(e),
                }
            )
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

        # Optional trace hook (UI opt-in; bounded)
        try:
            max_chars = int(_TRACE_MAX_CHARS.get())
        except Exception:
            max_chars = 900
        self._emit_trace(
            {
                "type": "llm.request",
                "model": self.model,
                "agent": self.__class__.__name__,
                "endpoint": "chat.completions (streaming)",
                "supports_temperature": supports_temperature,
                "temperature": params.get("temperature"),
                "response_format": bool(response_format),
                "messages": self._summarize_messages(messages, max_chars=max_chars),
            }
        )

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

            # Trace complete response (bounded)
            try:
                safe_content = self._redact(full_response) if isinstance(full_response, str) else ""
                self._emit_trace(
                    {
                        "type": "llm.response",
                        "model": self.model,
                        "agent": self.__class__.__name__,
                        "finish_reason": "stream_end",
                        "usage": None,
                        "content": safe_content[:max_chars]
                        + ("… [truncated]" if isinstance(safe_content, str) and len(safe_content) > max_chars else ""),
                        "content_len": len(full_response) if isinstance(full_response, str) else None,
                    }
                )
            except Exception:
                pass

            return full_response

        except RateLimitError as e:
            if self.logger:
                self.logger.log_error(error=e, model=self.model, context="Rate limit exceeded (streaming)")
            self._emit_trace(
                {
                    "type": "llm.error",
                    "model": self.model,
                    "agent": self.__class__.__name__,
                    "error_type": type(e).__name__,
                    "message": str(e),
                }
            )
            yield f"[Error: Rate limit exceeded - {str(e)}]"
            return None

        except AuthenticationError as e:
            if self.logger:
                self.logger.log_error(error=e, model=self.model, context="Authentication failed (streaming)")
            self._emit_trace(
                {
                    "type": "llm.error",
                    "model": self.model,
                    "agent": self.__class__.__name__,
                    "error_type": type(e).__name__,
                    "message": str(e),
                }
            )
            yield f"[Error: Authentication failed - {str(e)}]"
            return None

        except APIConnectionError as e:
            if self.logger:
                self.logger.log_error(error=e, model=self.model, context="Connection error (streaming)")
            self._emit_trace(
                {
                    "type": "llm.error",
                    "model": self.model,
                    "agent": self.__class__.__name__,
                    "error_type": type(e).__name__,
                    "message": str(e),
                }
            )
            yield f"[Error: Connection error - {str(e)}]"
            return None

        except BadRequestError as e:
            if self.logger:
                self.logger.log_error(error=e, model=self.model, context="Bad request (streaming)")
            self._emit_trace(
                {
                    "type": "llm.error",
                    "model": self.model,
                    "agent": self.__class__.__name__,
                    "error_type": type(e).__name__,
                    "message": str(e),
                }
            )
            yield f"[Error: Bad request - {str(e)}]"
            return None

        except APIError as e:
            error_msg = str(e)
            if self.logger:
                self.logger.log_error(error=e, model=self.model, context="API error (streaming)")
            self._emit_trace(
                {
                    "type": "llm.error",
                    "model": self.model,
                    "agent": self.__class__.__name__,
                    "error_type": type(e).__name__,
                    "message": error_msg,
                }
            )

            if "insufficient_quota" in error_msg.lower() or "quota" in error_msg.lower():
                yield f"[Error: API quota exceeded - {str(e)}]"
                return None

            yield f"[Error: API error - {str(e)}]"
            return None

        except Exception as e:
            if self.logger:
                self.logger.log_error(error=e, model=self.model, context="Unexpected error in streaming call")
            self._emit_trace(
                {
                    "type": "llm.error",
                    "model": self.model,
                    "agent": self.__class__.__name__,
                    "error_type": type(e).__name__,
                    "message": str(e),
                }
            )
            yield f"[Error: Unexpected error - {str(e)}]"
            return None
