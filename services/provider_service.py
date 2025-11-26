"""
AI Provider Service
Multi-provider abstraction for AI APIs (OpenAI, Kimi, Ollama)
"""

import os
from typing import Dict, Any, List, Optional
from openai import OpenAI


class AIProviderService:
    """Manages multiple AI provider configurations and provides unified client access"""

    # Provider configurations
    PROVIDERS = {
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "api_key_env": "OPENAI_API_KEY",
            "requires_key": True,
            "default_settings": {
                "temperature": 0.7,
            },
            "models": {
                "main": "gpt-4.1",
                "worker": "gpt-4.1-mini",
                "image": "gpt-image-1"
            }
        },
        "kimi": {
            "base_url": "https://api.moonshot.ai/v1",
            "api_key_env": "MOONSHOT_API_KEY",
            "requires_key": True,
            "default_settings": {
                "temperature": 0.6,  # Kimi recommends 0.6
            },
            "models": {
                "main": "kimi-k2-0905-preview",
                "worker": "kimi-k2-0905-preview",
                "image": None  # Kimi doesn't support image generation
            }
        },
        "ollama": {
            "base_url": "http://localhost:11434/v1",
            "api_key_env": None,
            "requires_key": False,
            "default_settings": {
                "temperature": 0.7,
            },
            "models": {
                "main": "llama3.1",
                "worker": "llama3.1",
                "image": None  # Ollama doesn't typically support image generation via OpenAI API
            }
        }
    }

    def __init__(self, config: Dict[str, Any]):
        """Initialize provider service with configuration

        Args:
            config: Configuration dictionary from config.yaml
        """
        self.config = config
        self.defaults = config.get("defaults", {})

        # Override provider configs from config.yaml if present
        provider_config = config.get("providers", {})
        if provider_config:
            for provider_name, provider_data in provider_config.items():
                if provider_name in self.PROVIDERS:
                    self.PROVIDERS[provider_name].update(provider_data)

        # Cache of available providers (lazy loaded)
        self._available_providers: Optional[List[str]] = None

        # Cache of provider clients
        self._client_cache: Dict[str, OpenAI] = {}

    def get_available_providers(self) -> List[str]:
        """Get list of providers with valid API keys or no key requirement

        Returns:
            List of available provider names
        """
        if self._available_providers is not None:
            return self._available_providers

        available = []

        for provider_name, provider_config in self.PROVIDERS.items():
            if not provider_config["requires_key"]:
                # No key required (e.g., Ollama)
                available.append(provider_name)
            else:
                # Check if API key is set
                api_key_env = provider_config["api_key_env"]
                if api_key_env and os.getenv(api_key_env):
                    available.append(provider_name)

        self._available_providers = available
        print(f"Available AI providers: {', '.join(available) if available else 'None'}")

        return available

    def get_default_provider(self) -> str:
        """Get default provider from config or first available

        Returns:
            Provider name

        Raises:
            RuntimeError: If no providers are available
        """
        # Check config for explicit default
        default_from_config = self.config.get("defaults", {}).get("provider")
        if default_from_config and default_from_config in self.get_available_providers():
            return default_from_config

        # Return first available provider
        available = self.get_available_providers()
        if not available:
            raise RuntimeError(
                "No AI providers available. Please set OPENAI_API_KEY, "
                "MOONSHOT_API_KEY, or configure Ollama."
            )

        return available[0]

    def get_client(self, provider: Optional[str] = None) -> OpenAI:
        """Get configured OpenAI client for the specified provider

        Args:
            provider: Provider name, uses default if None

        Returns:
            Configured OpenAI client instance

        Raises:
            ValueError: If provider is invalid or unavailable
        """
        if provider is None:
            provider = self.get_default_provider()

        # Validate provider
        if provider not in self.PROVIDERS:
            raise ValueError(
                f"Invalid provider '{provider}'. "
                f"Valid options: {', '.join(self.PROVIDERS.keys())}"
            )

        if provider not in self.get_available_providers():
            provider_config = self.PROVIDERS[provider]
            if provider_config["requires_key"]:
                key_name = provider_config["api_key_env"]
                raise ValueError(
                    f"Provider '{provider}' is not available. "
                    f"Please set {key_name} environment variable."
                )
            else:
                raise ValueError(
                    f"Provider '{provider}' is not available. "
                    f"Please ensure the service is running."
                )

        # Return cached client if available
        if provider in self._client_cache:
            return self._client_cache[provider]

        # Create new client
        provider_config = self.PROVIDERS[provider]

        client_kwargs = {
            "base_url": provider_config["base_url"]
        }

        # Add API key if required
        if provider_config["requires_key"]:
            api_key = os.getenv(provider_config["api_key_env"])
            if not api_key:
                raise ValueError(
                    f"API key not found for provider '{provider}'. "
                    f"Please set {provider_config['api_key_env']}."
                )
            client_kwargs["api_key"] = api_key
        else:
            # Ollama and similar providers may not need a real key,
            # but OpenAI client requires one, so use a dummy value
            client_kwargs["api_key"] = "ollama"

        client = OpenAI(**client_kwargs)

        # Cache the client
        self._client_cache[provider] = client

        print(f"Created client for provider: {provider}")

        return client

    def get_model_for_task(self, provider: Optional[str] = None, task: str = "main") -> str:
        """Get appropriate model name for a task from the specified provider

        Args:
            provider: Provider name, uses default if None
            task: Task type - 'main', 'worker', or 'image'

        Returns:
            Model name string

        Raises:
            ValueError: If provider is invalid or task type is unknown
        """
        if provider is None:
            provider = self.get_default_provider()

        if provider not in self.PROVIDERS:
            raise ValueError(
                f"Invalid provider '{provider}'. "
                f"Valid options: {', '.join(self.PROVIDERS.keys())}"
            )

        if task not in ["main", "worker", "image"]:
            raise ValueError(
                f"Invalid task '{task}'. "
                f"Valid options: 'main', 'worker', 'image'"
            )

        provider_config = self.PROVIDERS[provider]
        model = provider_config["models"].get(task)

        if model is None:
            raise ValueError(
                f"Provider '{provider}' does not support task type '{task}'"
            )

        # Allow config override
        config_override_key = f"{task}_model"
        if config_override_key in self.defaults:
            config_model = self.defaults[config_override_key]
            # Only use override if it looks like it might be compatible
            if config_model and isinstance(config_model, str):
                model = config_model

        return model

    def get_provider_settings(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """Get provider-specific settings (temperature, etc.)

        Args:
            provider: Provider name, uses default if None

        Returns:
            Dictionary of provider settings

        Raises:
            ValueError: If provider is invalid
        """
        if provider is None:
            provider = self.get_default_provider()

        if provider not in self.PROVIDERS:
            raise ValueError(
                f"Invalid provider '{provider}'. "
                f"Valid options: {', '.join(self.PROVIDERS.keys())}"
            )

        provider_config = self.PROVIDERS[provider]
        return provider_config.get("default_settings", {}).copy()

    def invalidate_cache(self, provider: Optional[str] = None) -> None:
        """Invalidate cached client for a provider

        Args:
            provider: Provider name, or None to invalidate all
        """
        if provider is None:
            self._client_cache.clear()
            self._available_providers = None
            print("Invalidated all provider caches")
        else:
            if provider in self._client_cache:
                del self._client_cache[provider]
                print(f"Invalidated cache for provider: {provider}")

    def get_provider_info(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """Get detailed information about a provider

        Args:
            provider: Provider name, uses default if None

        Returns:
            Dictionary with provider information
        """
        if provider is None:
            provider = self.get_default_provider()

        if provider not in self.PROVIDERS:
            raise ValueError(
                f"Invalid provider '{provider}'. "
                f"Valid options: {', '.join(self.PROVIDERS.keys())}"
            )

        provider_config = self.PROVIDERS[provider]

        info = {
            "name": provider,
            "base_url": provider_config["base_url"],
            "requires_key": provider_config["requires_key"],
            "is_available": provider in self.get_available_providers(),
            "models": provider_config["models"].copy(),
            "settings": provider_config["default_settings"].copy()
        }

        if provider_config["requires_key"]:
            api_key = os.getenv(provider_config["api_key_env"])
            info["has_api_key"] = bool(api_key)
            info["api_key_env"] = provider_config["api_key_env"]

        return info

    def list_all_providers(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all configured providers

        Returns:
            Dictionary mapping provider names to their info
        """
        return {
            provider: self.get_provider_info(provider)
            for provider in self.PROVIDERS.keys()
        }

    # Cross-provider orchestration support
    def set_task_provider(self, task: str, provider: str) -> None:
        """Set provider for a specific task (enables cross-provider orchestration)

        Args:
            task: Task type - 'main' (orchestration), 'worker', or 'image'
            provider: Provider name to use for this task

        Raises:
            ValueError: If task or provider is invalid
        """
        if task not in ["main", "worker", "image"]:
            raise ValueError(f"Invalid task '{task}'. Valid: 'main', 'worker', 'image'")

        if provider not in self.get_available_providers():
            raise ValueError(f"Provider '{provider}' not available")

        if "task_providers" not in self.config:
            self.config["task_providers"] = {}

        self.config["task_providers"][task] = provider
        print(f"Set {task} task to use provider: {provider}")

    def get_task_provider(self, task: str) -> str:
        """Get the provider assigned to a specific task

        Args:
            task: Task type - 'main', 'worker', or 'image'

        Returns:
            Provider name for this task
        """
        task_providers = self.config.get("task_providers", {})
        return task_providers.get(task, self.get_default_provider())

    def get_client_for_task(self, task: str) -> "OpenAI":
        """Get client configured for a specific task

        Args:
            task: Task type - 'main', 'worker', or 'image'

        Returns:
            Configured OpenAI client for the task's provider
        """
        provider = self.get_task_provider(task)
        return self.get_client(provider)

    def get_model_and_client_for_task(self, task: str) -> tuple:
        """Get both model name and client for a task (convenience method)

        Args:
            task: Task type - 'main', 'worker', or 'image'

        Returns:
            Tuple of (model_name, client)
        """
        provider = self.get_task_provider(task)
        model = self.get_model_for_task(provider, task)
        client = self.get_client(provider)
        return model, client

    def get_task_config_summary(self) -> Dict[str, Dict[str, str]]:
        """Get summary of current task-to-provider configuration

        Returns:
            Dict mapping task names to provider and model info
        """
        summary = {}
        for task in ["main", "worker", "image"]:
            provider = self.get_task_provider(task)
            try:
                model = self.get_model_for_task(provider, task)
            except ValueError:
                model = "N/A"
            summary[task] = {
                "provider": provider,
                "model": model
            }
        return summary


# Convenience function for backward compatibility
def get_provider_service(config: Dict[str, Any]) -> AIProviderService:
    """Create and return a provider service instance

    Args:
        config: Configuration dictionary from config.yaml

    Returns:
        AIProviderService instance
    """
    return AIProviderService(config)
