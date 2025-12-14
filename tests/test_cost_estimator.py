"""
Tests for cost_estimator - P1.3 regression tests for cost estimation.

These tests verify that:
1. No KeyError for known and unknown models
2. Totals are consistent and non-negative
3. Output schema is stable
4. calculate_savings returns correct dict structure
"""

import pytest


class TestCalculateCost:
    """Test _calculate_cost_impl function."""

    def test_known_model_no_error(self):
        """Verify known models don't raise KeyError."""
        from src.cost_estimator import _calculate_cost_impl, MODEL_COSTS

        for model in MODEL_COSTS.keys():
            # Should not raise
            cost = _calculate_cost_impl(model, 1000, 1000)
            assert isinstance(cost, (int, float))
            assert cost >= 0

    def test_unknown_model_fallback(self):
        """Verify unknown models use fallback pricing."""
        from src.cost_estimator import _calculate_cost_impl

        # Should not raise - uses fallback
        cost = _calculate_cost_impl("unknown-model-xyz", 1000, 1000)
        assert isinstance(cost, (int, float))
        assert cost >= 0

    def test_kimi_models_recognized(self):
        """Verify Kimi/Moonshot models are recognized."""
        from src.cost_estimator import _calculate_cost_impl

        kimi_models = [
            "kimi-k2-thinking",
            "kimi-k2-turbo-preview",
            "moonshot-v1-auto",
            "kimi-latest",
        ]

        for model in kimi_models:
            cost = _calculate_cost_impl(model, 1000, 1000)
            assert isinstance(cost, (int, float))
            # Kimi models should be cheap/free
            assert cost < 1.0, f"{model} cost unexpectedly high: {cost}"

    def test_gpt_models_recognized(self):
        """Verify GPT model variants are recognized."""
        from src.cost_estimator import _calculate_cost_impl

        gpt_models = [
            "gpt-4.1-nano",
            "gpt-4.1-mini",
            "gpt-4.1",
            "gpt-5-nano",
            "gpt-5-mini",
            "gpt-5",
            "gpt-4o",
            "gpt-4o-mini",
        ]

        for model in gpt_models:
            cost = _calculate_cost_impl(model, 1000, 1000)
            assert isinstance(cost, (int, float))
            assert cost >= 0

    def test_image_models_recognized(self):
        """Verify image models are recognized."""
        from src.cost_estimator import _calculate_cost_impl

        image_models = [
            "gpt-image-1",
            "gpt-image-1-mini",
            "dall-e-3",  # Should map to gpt-image
            "dalle-2",   # Should map to gpt-image
        ]

        for model in image_models:
            cost = _calculate_cost_impl(model, 0, 1)  # Images use output tokens
            assert isinstance(cost, (int, float))
            assert cost >= 0

    def test_cost_proportional_to_tokens(self):
        """Verify cost increases with token count."""
        from src.cost_estimator import _calculate_cost_impl

        cost_1k = _calculate_cost_impl("gpt-4.1-mini", 1000, 1000)
        cost_10k = _calculate_cost_impl("gpt-4.1-mini", 10000, 10000)

        assert cost_10k > cost_1k
        # Should be roughly 10x (with some tolerance for floating point)
        assert 9 < cost_10k / cost_1k < 11

    def test_zero_tokens_zero_cost(self):
        """Verify zero tokens results in zero cost."""
        from src.cost_estimator import _calculate_cost_impl

        cost = _calculate_cost_impl("gpt-4.1-mini", 0, 0)
        assert cost == 0.0


class TestEstimateCurriculumCost:
    """Test _estimate_curriculum_cost_impl function."""

    def test_returns_expected_schema(self):
        """Verify output has all expected keys."""
        from src.cost_estimator import _estimate_curriculum_cost_impl

        result = _estimate_curriculum_cost_impl(
            orchestrator_model="gpt-5-nano",
            worker_model="gpt-5-nano",
            num_units=4,
        )

        assert "total" in result
        assert "total_tokens" in result
        assert "breakdown" in result
        assert "orchestrator_model" in result
        assert "worker_model" in result
        assert "savings_vs_full" in result

    def test_total_is_non_negative(self):
        """Verify total cost is non-negative."""
        from src.cost_estimator import _estimate_curriculum_cost_impl

        result = _estimate_curriculum_cost_impl(
            orchestrator_model="gpt-5-nano",
            worker_model="gpt-5-nano",
            num_units=4,
        )

        assert result["total"] >= 0

    def test_breakdown_components_sum_to_total(self):
        """Verify breakdown components sum to total (approximately)."""
        from src.cost_estimator import _estimate_curriculum_cost_impl

        result = _estimate_curriculum_cost_impl(
            orchestrator_model="gpt-5-nano",
            worker_model="gpt-5-nano",
            num_units=4,
            include_quizzes=True,
            include_summary=True,
            include_resources=True,
        )

        breakdown_sum = sum(result["breakdown"].values())
        total = result["total"]

        # Allow small floating point tolerance
        assert abs(breakdown_sum - total) < 0.0001

    def test_more_units_higher_cost(self):
        """Verify more units means higher cost."""
        from src.cost_estimator import _estimate_curriculum_cost_impl

        result_4 = _estimate_curriculum_cost_impl(
            orchestrator_model="gpt-5-nano",
            worker_model="gpt-5-nano",
            num_units=4,
        )

        result_8 = _estimate_curriculum_cost_impl(
            orchestrator_model="gpt-5-nano",
            worker_model="gpt-5-nano",
            num_units=8,
        )

        assert result_8["total"] > result_4["total"]

    def test_optional_components_affect_cost(self):
        """Verify optional components affect total cost."""
        from src.cost_estimator import _estimate_curriculum_cost_impl

        result_full = _estimate_curriculum_cost_impl(
            orchestrator_model="gpt-5-nano",
            worker_model="gpt-5-nano",
            num_units=4,
            include_quizzes=True,
            include_summary=True,
            include_resources=True,
        )

        result_minimal = _estimate_curriculum_cost_impl(
            orchestrator_model="gpt-5-nano",
            worker_model="gpt-5-nano",
            num_units=4,
            include_quizzes=False,
            include_summary=False,
            include_resources=False,
        )

        assert result_full["total"] > result_minimal["total"]


class TestCalculateSavings:
    """Test calculate_savings function."""

    def test_returns_dict_with_expected_keys(self):
        """Verify calculate_savings returns dict with expected keys."""
        from src.cost_estimator import calculate_savings

        result = calculate_savings("gpt-5-nano", "gpt-5-nano", 1.0)

        assert isinstance(result, dict)
        assert "amount" in result
        assert "percent" in result
        assert "full_cost" in result

    def test_savings_amount_non_negative(self):
        """Verify savings amount can be calculated."""
        from src.cost_estimator import calculate_savings

        result = calculate_savings("gpt-5-nano", "gpt-5-nano", 0.5)

        # The full_cost should be positive
        assert result["full_cost"] > 0

        # Amount is full_cost - actual_cost
        expected_amount = result["full_cost"] - 0.5
        assert abs(result["amount"] - expected_amount) < 0.0001

    def test_percent_calculation(self):
        """Verify percent savings is calculated correctly."""
        from src.cost_estimator import calculate_savings

        # If actual cost is 0, savings should be 100%
        result = calculate_savings("gpt-5-nano", "gpt-5-nano", 0.0)

        assert result["percent"] == 100.0


class TestModelCosts:
    """Test MODEL_COSTS structure."""

    def test_all_models_have_required_keys(self):
        """Verify all models have required cost keys."""
        from src.cost_estimator import MODEL_COSTS

        for model_name, costs in MODEL_COSTS.items():
            assert "input" in costs, f"{model_name} missing 'input' key"
            assert "output" in costs, f"{model_name} missing 'output' key"
            assert "name" in costs, f"{model_name} missing 'name' key"
            assert "relative_cost" in costs, f"{model_name} missing 'relative_cost' key"

    def test_costs_are_non_negative(self):
        """Verify all costs are non-negative."""
        from src.cost_estimator import MODEL_COSTS

        for model_name, costs in MODEL_COSTS.items():
            assert costs["input"] >= 0, f"{model_name} has negative input cost"
            assert costs["output"] >= 0, f"{model_name} has negative output cost"
