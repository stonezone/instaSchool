"""
Cost Estimator for InstaSchool
Provides cost estimation for different model configurations
"""

try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

# Costs per 1K tokens (updated Dec 2025)
# Based on typical pricing patterns where nano < mini < full
MODEL_COSTS = {
    # Kimi K2 (Moonshot) - FREE tier / very cheap
    "kimi-k2-thinking": {
        "input": 0.001,
        "output": 0.003,
        "name": "Kimi K2 Thinking (Reasoning)",
        "relative_cost": "$"
    },
    "kimi-k2-turbo-preview": {
        "input": 0.0005,
        "output": 0.0015,
        "name": "Kimi K2 Turbo (Fast)",
        "relative_cost": "$"
    },
    "kimi-k2-thinking-turbo": {
        "input": 0.0008,
        "output": 0.0024,
        "name": "Kimi K2 Thinking Turbo",
        "relative_cost": "$"
    },
    "kimi-latest": {
        "input": 0.0003,
        "output": 0.001,
        "name": "Kimi Latest (Vision)",
        "relative_cost": "$"
    },
    "moonshot-v1-auto": {
        "input": 0.0002,
        "output": 0.0008,
        "name": "Moonshot Auto",
        "relative_cost": "$"
    },
    "kimi-k2-0905-preview": {
        "input": 0.0,       # Free tier
        "output": 0.0,      # Free tier
        "name": "Kimi K2 (FREE)",
        "relative_cost": "FREE"
    },
    # Image models (ONLY gpt-image allowed)
    "gpt-image-1": {
        "input": 0.0,       # Per-image pricing, not token-based
        "output": 0.04,     # ~$0.04 per image (standard)
        "name": "GPT Image 1",
        "relative_cost": "$$"
    },
    "gpt-image-1-mini": {
        "input": 0.0,       # Per-image pricing
        "output": 0.02,     # ~$0.02 per image (mini)
        "name": "GPT Image 1 Mini",
        "relative_cost": "$"
    },
    # GPT-5 Series (Current)
    "gpt-5-nano": {
        "input": 0.001,     # $1 per 1M tokens
        "output": 0.004,    # $4 per 1M tokens
        "name": "GPT-5 Nano (Most Affordable)",
        "relative_cost": "$"
    },
    "gpt-5-mini": {
        "input": 0.003,     # $3 per 1M tokens
        "output": 0.012,    # $12 per 1M tokens
        "name": "GPT-5 Mini (Balanced)",
        "relative_cost": "$$"
    },
    "gpt-5": {
        "input": 0.02,      # $20 per 1M tokens
        "output": 0.06,     # $60 per 1M tokens
        "name": "GPT-5 (High Quality)",
        "relative_cost": "$$$"
    },
    # GPT-4o Series
    "gpt-4o": {
        "input": 0.005,     # $5 per 1M tokens
        "output": 0.015,    # $15 per 1M tokens
        "name": "GPT-4o",
        "relative_cost": "$$"
    },
    "chatgpt-4o-latest": {
        "input": 0.005,
        "output": 0.015,
        "name": "ChatGPT-4o Latest",
        "relative_cost": "$$"
    },
    "gpt-4o-mini": {
        "input": 0.00015,   # $0.15 per 1M tokens
        "output": 0.0006,   # $0.60 per 1M tokens
        "name": "GPT-4o Mini",
        "relative_cost": "$"
    },
    "gpt-4o-nano": {
        "input": 0.0001,
        "output": 0.0004,
        "name": "GPT-4o Nano",
        "relative_cost": "$"
    },
    # GPT-4.1 Series (Legacy)
    "gpt-4.1-nano": {
        "input": 0.0005,
        "output": 0.0015,
        "name": "GPT-4.1 Nano",
        "relative_cost": "$"
    },
    "gpt-4.1-mini": {
        "input": 0.0015,
        "output": 0.002,
        "name": "GPT-4.1 Mini",
        "relative_cost": "$$"
    },
    "gpt-4.1": {
        "input": 0.01,
        "output": 0.03,
        "name": "GPT-4.1",
        "relative_cost": "$$$"
    },
}

# Estimated token usage for curriculum generation
ESTIMATED_TOKENS = {
    "orchestrator": {"input": 2000, "output": 1000},
    "outline": {"input": 1500, "output": 800},
    "content_per_unit": {"input": 2000, "output": 3000},
    "quiz_per_unit": {"input": 1000, "output": 500},
    "summary_per_unit": {"input": 500, "output": 300},
    "resources_per_unit": {"input": 500, "output": 400},
    "image_prompt": {"input": 1000, "output": 200}
}

def _estimate_curriculum_cost_impl(orchestrator_model: str, worker_model: str,
                           num_units: int = 4, include_quizzes: bool = True,
                           include_summary: bool = True, include_resources: bool = True) -> dict:
    """
    Estimate the cost of generating a curriculum
    
    Args:
        orchestrator_model: Model for orchestration
        worker_model: Model for content generation
        num_units: Number of curriculum units
        include_quizzes: Whether to include quizzes
        include_summary: Whether to include summaries
        include_resources: Whether to include resources
        
    Returns:
        Dictionary with cost breakdown
    """
    total_cost = 0.0
    breakdown = {}
    
    # Orchestrator costs
    orch_tokens = ESTIMATED_TOKENS["orchestrator"]
    orch_cost = _calculate_cost_impl(orchestrator_model, orch_tokens["input"], orch_tokens["output"])
    breakdown["orchestration"] = orch_cost
    total_cost += orch_cost

    # Outline generation
    outline_tokens = ESTIMATED_TOKENS["outline"]
    outline_cost = _calculate_cost_impl(worker_model, outline_tokens["input"], outline_tokens["output"])
    breakdown["outline"] = outline_cost
    total_cost += outline_cost

    # Content generation per unit
    content_tokens = ESTIMATED_TOKENS["content_per_unit"]
    content_cost = _calculate_cost_impl(worker_model,
                                 content_tokens["input"] * num_units,
                                 content_tokens["output"] * num_units)
    breakdown["content"] = content_cost
    total_cost += content_cost

    # Optional components
    if include_quizzes:
        quiz_tokens = ESTIMATED_TOKENS["quiz_per_unit"]
        quiz_cost = _calculate_cost_impl(worker_model,
                                  quiz_tokens["input"] * num_units,
                                  quiz_tokens["output"] * num_units)
        breakdown["quizzes"] = quiz_cost
        total_cost += quiz_cost

    if include_summary:
        summary_tokens = ESTIMATED_TOKENS["summary_per_unit"]
        summary_cost = _calculate_cost_impl(worker_model,
                                     summary_tokens["input"] * num_units,
                                     summary_tokens["output"] * num_units)
        breakdown["summaries"] = summary_cost
        total_cost += summary_cost

    if include_resources:
        resources_tokens = ESTIMATED_TOKENS["resources_per_unit"]
        resources_cost = _calculate_cost_impl(worker_model,
                                       resources_tokens["input"] * num_units,
                                       resources_tokens["output"] * num_units)
        breakdown["resources"] = resources_cost
        total_cost += resources_cost

    # Image prompt generation (if images are included)
    image_tokens = ESTIMATED_TOKENS["image_prompt"]
    image_cost = _calculate_cost_impl(worker_model,
                               image_tokens["input"] * num_units,
                               image_tokens["output"] * num_units)
    breakdown["image_prompts"] = image_cost
    total_cost += image_cost
    
    # Calculate total tokens for display
    total_tokens = (
        (ESTIMATED_TOKENS["orchestrator"]["input"] + ESTIMATED_TOKENS["orchestrator"]["output"]) +
        (ESTIMATED_TOKENS["outline"]["input"] + ESTIMATED_TOKENS["outline"]["output"]) +
        (ESTIMATED_TOKENS["content_per_unit"]["input"] + ESTIMATED_TOKENS["content_per_unit"]["output"]) * num_units +
        (ESTIMATED_TOKENS["image_prompt"]["input"] + ESTIMATED_TOKENS["image_prompt"]["output"]) * num_units
    )

    if include_quizzes:
        total_tokens += (ESTIMATED_TOKENS["quiz_per_unit"]["input"] + ESTIMATED_TOKENS["quiz_per_unit"]["output"]) * num_units
    if include_summary:
        total_tokens += (ESTIMATED_TOKENS["summary_per_unit"]["input"] + ESTIMATED_TOKENS["summary_per_unit"]["output"]) * num_units
    if include_resources:
        total_tokens += (ESTIMATED_TOKENS["resources_per_unit"]["input"] + ESTIMATED_TOKENS["resources_per_unit"]["output"]) * num_units

    return {
        "total": total_cost,
        "total_tokens": total_tokens,
        "breakdown": breakdown,
        "orchestrator_model": orchestrator_model,
        "worker_model": worker_model,
        "savings_vs_full": calculate_savings(orchestrator_model, worker_model, total_cost)
    }

def _calculate_cost_impl(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost with dynamic fallback and robust model matching"""

    # Normalize model name for matching
    model_lower = model.lower() if model else ""

    # 1. Direct/exact match
    if model in MODEL_COSTS:
        costs = MODEL_COSTS[model]

    # 2. Kimi / Moonshot models (FREE tier)
    elif "kimi" in model_lower or "moonshot" in model_lower:
        costs = MODEL_COSTS["kimi-k2-0905-preview"]

    # 3. Legacy image models (treat as closest supported tier)
    elif "dall-e" in model_lower or "dalle" in model_lower:
        costs = MODEL_COSTS["gpt-image-1"]
    elif "gpt-image" in model_lower or "image" in model_lower:
        if "mini" in model_lower:
            costs = MODEL_COSTS["gpt-image-1-mini"]
        else:
            costs = MODEL_COSTS["gpt-image-1"]

    # 4. GPT-5 series (newest)
    elif "gpt-5" in model_lower:
        if "nano" in model_lower:
            costs = MODEL_COSTS.get("gpt-5-nano", MODEL_COSTS["gpt-4.1-nano"])
        elif "mini" in model_lower:
            costs = MODEL_COSTS.get("gpt-5-mini", MODEL_COSTS["gpt-4.1-mini"])
        else:
            costs = MODEL_COSTS.get("gpt-5", MODEL_COSTS["gpt-4.1"])

    # 3. GPT-4.1 series
    elif "gpt-4.1" in model_lower:
        if "nano" in model_lower:
            costs = MODEL_COSTS["gpt-4.1-nano"]
        elif "mini" in model_lower:
            costs = MODEL_COSTS["gpt-4.1-mini"]
        else:
            costs = MODEL_COSTS["gpt-4.1"]

    # 4. GPT-4 series (including gpt-4-turbo, gpt-4-0613, gpt-4o, etc.)
    elif "gpt-4" in model_lower:
        if "mini" in model_lower or "turbo" in model_lower:
            costs = MODEL_COSTS["gpt-4.1-mini"]  # Proxy for 4-turbo/mini
        elif "o" in model_lower and "gpt-4o" in model_lower:
            costs = MODEL_COSTS["gpt-4.1-mini"]  # GPT-4o is efficient
        else:
            costs = MODEL_COSTS["gpt-4.1"]  # Base GPT-4 pricing

    # 5. GPT-3.5 series
    elif "gpt-3.5" in model_lower:
        costs = MODEL_COSTS["gpt-4.1-nano"]  # Very cheap, similar to nano

    # 6. O-series reasoning models (o1, o3, etc.)
    elif model_lower.startswith("o1") or model_lower.startswith("o3"):
        costs = MODEL_COSTS["gpt-4.1"]  # Premium pricing for reasoning

    # 7. Generic fallback by keywords
    elif "nano" in model_lower:
        costs = MODEL_COSTS["gpt-4.1-nano"]
    elif "mini" in model_lower:
        costs = MODEL_COSTS["gpt-4.1-mini"]

    # 8. Safe default fallback
    else:
        costs = MODEL_COSTS["gpt-4.1-mini"]

    input_cost = (input_tokens / 1000) * costs["input"]
    output_cost = (output_tokens / 1000) * costs["output"]

    return input_cost + output_cost

def calculate_savings(orchestrator_model: str, worker_model: str, actual_cost: float) -> dict:
    """Calculate savings compared to using full model for everything"""
    # Calculate what it would cost with full model (without recursive call to calculate_savings)
    full_orch_cost = _calculate_cost_impl("gpt-4.1", 2000, 1500)  # Orchestrator usage
    full_worker_cost = _calculate_cost_impl("gpt-4.1", 8000, 6000) * 6  # 6 workers
    full_cost = full_orch_cost + full_worker_cost
    
    savings_percent = ((full_cost - actual_cost) / full_cost) * 100 if full_cost > 0 else 0
    
    return {
        "amount": full_cost - actual_cost,
        "percent": savings_percent,
        "full_cost": full_cost
    }

def get_model_info(model: str) -> dict:
    """Get display information for a model"""
    return MODEL_COSTS.get(model, {
        "name": model,
        "relative_cost": "?"
    })


# ========== Cached Wrapper Functions ==========
if HAS_STREAMLIT:
    @st.cache_data
    def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost with caching (Streamlit version)"""
        return _calculate_cost_impl(model, input_tokens, output_tokens)

    @st.cache_data
    def estimate_curriculum_cost(orchestrator_model: str, worker_model: str,
                               num_units: int = 4, include_quizzes: bool = True,
                               include_summary: bool = True, include_resources: bool = True) -> dict:
        """Estimate curriculum cost with caching (Streamlit version)"""
        return _estimate_curriculum_cost_impl(orchestrator_model, worker_model, num_units,
                                             include_quizzes, include_summary, include_resources)
else:
    # Non-cached versions for non-Streamlit contexts
    def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost (non-cached fallback)"""
        return _calculate_cost_impl(model, input_tokens, output_tokens)

    def estimate_curriculum_cost(orchestrator_model: str, worker_model: str,
                               num_units: int = 4, include_quizzes: bool = True,
                               include_summary: bool = True, include_resources: bool = True) -> dict:
        """Estimate curriculum cost (non-cached fallback)"""
        return _estimate_curriculum_cost_impl(orchestrator_model, worker_model, num_units,
                                             include_quizzes, include_summary, include_resources)
