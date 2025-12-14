"""
Tests for AIProviderService - P1.4 regression tests for config isolation.

These tests verify that:
1. Instance-scoped provider configs (no cross-session bleed)
2. Config overrides don't affect class-level PROVIDERS
3. Multiple instances are independent
"""

import pytest
import copy


class TestProviderServiceIsolation:
    """Test AIProviderService config isolation."""

    def test_instance_has_own_providers_copy(self):
        """Verify each instance has its own providers dict."""
        from services.provider_service import AIProviderService

        config1 = {"defaults": {}, "providers": {}}
        config2 = {"defaults": {}, "providers": {}}

        service1 = AIProviderService(config1)
        service2 = AIProviderService(config2)

        # Should be different objects
        assert service1.providers is not service2.providers
        assert service1.providers is not AIProviderService.PROVIDERS

    def test_instance_modification_doesnt_affect_class(self):
        """Verify modifying instance doesn't affect class PROVIDERS."""
        from services.provider_service import AIProviderService

        # Save original class state
        original_openai_base = AIProviderService.PROVIDERS["openai"]["base_url"]

        config = {
            "defaults": {},
            "providers": {
                "openai": {
                    "api_base": "https://custom.api.com/v1",
                }
            },
        }

        service = AIProviderService(config)

        # Instance should have custom URL
        assert service.providers["openai"]["base_url"] == "https://custom.api.com/v1"

        # Class PROVIDERS should be unchanged
        assert AIProviderService.PROVIDERS["openai"]["base_url"] == original_openai_base

    def test_multiple_instances_independent(self):
        """Verify multiple instances don't share state."""
        from services.provider_service import AIProviderService

        config1 = {
            "defaults": {},
            "providers": {
                "openai": {
                    "api_base": "https://instance1.api.com/v1",
                }
            },
        }

        config2 = {
            "defaults": {},
            "providers": {
                "openai": {
                    "api_base": "https://instance2.api.com/v1",
                }
            },
        }

        service1 = AIProviderService(config1)
        service2 = AIProviderService(config2)

        # Each should have its own URL
        assert service1.providers["openai"]["base_url"] == "https://instance1.api.com/v1"
        assert service2.providers["openai"]["base_url"] == "https://instance2.api.com/v1"

    def test_defaults_are_deep_copied(self):
        """Verify config defaults are deep copied."""
        from services.provider_service import AIProviderService

        config = {
            "defaults": {
                "provider": "openai",
                "nested": {"key": "value"},
            },
            "providers": {},
        }

        service = AIProviderService(config)

        # Modify the service defaults
        service.defaults["nested"]["key"] = "modified"

        # Original config should be unchanged
        assert config["defaults"]["nested"]["key"] == "value"


class TestProviderServiceProviders:
    """Test AIProviderService provider management."""

    def test_known_providers_exist(self):
        """Verify expected providers are configured."""
        from services.provider_service import AIProviderService

        assert "openai" in AIProviderService.PROVIDERS
        assert "kimi" in AIProviderService.PROVIDERS
        assert "deepseek" in AIProviderService.PROVIDERS

    def test_provider_has_required_fields(self):
        """Verify each provider has required fields."""
        from services.provider_service import AIProviderService

        required_fields = [
            "base_url",
            "api_key_env",
            "requires_key",
            "default_settings",
            "models",
            "text_models",
        ]

        for provider_name, provider_config in AIProviderService.PROVIDERS.items():
            for field in required_fields:
                assert field in provider_config, (
                    f"Provider '{provider_name}' missing field '{field}'"
                )

    def test_model_tasks_defined(self):
        """Verify each provider has main/worker model defined."""
        from services.provider_service import AIProviderService

        for provider_name, provider_config in AIProviderService.PROVIDERS.items():
            models = provider_config["models"]
            assert "main" in models, f"{provider_name} missing 'main' model"
            assert "worker" in models, f"{provider_name} missing 'worker' model"
            assert "image" in models, f"{provider_name} missing 'image' model"


class TestProviderServiceMethods:
    """Test AIProviderService methods."""

    def test_get_text_models_returns_list(self):
        """Verify get_text_models returns a list."""
        from services.provider_service import AIProviderService

        config = {"defaults": {}, "providers": {}}
        service = AIProviderService(config)

        models = service.get_text_models("openai")
        assert isinstance(models, list)
        assert len(models) > 0

    def test_get_text_models_no_duplicates(self):
        """Verify get_text_models returns no duplicates."""
        from services.provider_service import AIProviderService

        config = {"defaults": {}, "providers": {}}
        service = AIProviderService(config)

        for provider in ["openai", "kimi", "deepseek"]:
            models = service.get_text_models(provider)
            assert len(models) == len(set(models)), (
                f"Provider '{provider}' has duplicate models"
            )

    def test_get_model_for_task_valid_tasks(self):
        """Verify get_model_for_task works for valid tasks."""
        from services.provider_service import AIProviderService

        config = {"defaults": {}, "providers": {}}
        service = AIProviderService(config)

        # Mock available providers
        service._available_providers = ["openai"]

        for task in ["main", "worker"]:
            model = service.get_model_for_task("openai", task)
            assert isinstance(model, str)
            assert len(model) > 0

    def test_get_model_for_task_invalid_task_raises(self):
        """Verify get_model_for_task raises for invalid task."""
        from services.provider_service import AIProviderService

        config = {"defaults": {}, "providers": {}}
        service = AIProviderService(config)

        with pytest.raises(ValueError, match="Invalid task"):
            service.get_model_for_task("openai", "invalid_task")

    def test_get_provider_settings_returns_copy(self):
        """Verify get_provider_settings returns a copy."""
        from services.provider_service import AIProviderService

        config = {"defaults": {}, "providers": {}}
        service = AIProviderService(config)

        # Mock available providers
        service._available_providers = ["openai"]

        settings1 = service.get_provider_settings("openai")
        settings2 = service.get_provider_settings("openai")

        # Should be different objects
        assert settings1 is not settings2

        # Modifying one shouldn't affect the other
        settings1["modified"] = True
        assert "modified" not in settings2

    def test_invalidate_cache_clears_clients(self):
        """Verify invalidate_cache clears client cache."""
        from services.provider_service import AIProviderService

        config = {"defaults": {}, "providers": {}}
        service = AIProviderService(config)

        # Add dummy client to cache
        service._client_cache["test"] = "dummy_client"
        service._available_providers = ["test"]

        service.invalidate_cache()

        assert len(service._client_cache) == 0
        assert service._available_providers is None


class TestProviderServiceConfigOverrides:
    """Test AIProviderService config override handling."""

    def test_api_base_override_from_providers(self):
        """Verify api_base can be overridden from config.providers."""
        from services.provider_service import AIProviderService

        config = {
            "defaults": {},
            "providers": {
                "openai": {
                    "api_base": "https://custom.openai.com/v1",
                }
            },
        }

        service = AIProviderService(config)

        assert service.providers["openai"]["base_url"] == "https://custom.openai.com/v1"

    def test_api_base_override_from_ai_providers(self):
        """Verify api_base can be overridden from config.ai_providers.providers."""
        from services.provider_service import AIProviderService

        config = {
            "defaults": {},
            "ai_providers": {
                "default": "kimi",
                "providers": {
                    "kimi": {
                        "api_base": "https://custom.moonshot.ai/v1",
                    }
                },
            },
        }

        service = AIProviderService(config)

        assert service.providers["kimi"]["base_url"] == "https://custom.moonshot.ai/v1"
        assert service.defaults.get("provider") == "kimi"

    def test_model_override_from_config(self):
        """Verify models can be overridden from config."""
        from services.provider_service import AIProviderService

        config = {
            "defaults": {},
            "providers": {
                "openai": {
                    "models": {
                        "main": "custom-main-model",
                        "worker": "custom-worker-model",
                    }
                }
            },
        }

        service = AIProviderService(config)

        assert service.providers["openai"]["models"]["main"] == "custom-main-model"
        assert service.providers["openai"]["models"]["worker"] == "custom-worker-model"
