"""
Cost Estimator for InstaSchool
Provides cost estimation for different model configurations
"""

# Hypothetical costs per 1K tokens (you should update these with actual costs)
# Based on typical pricing patterns where nano < mini < full
MODEL_COSTS = {
    "gpt-4.1-nano": {
        "input": 0.00015,   # $0.15 per 1M tokens
        "output": 0.0006,   # $0.60 per 1M tokens
        "name": "Nano (Most Affordable)",
        "relative_cost": "$"
    },
    "gpt-4.1-mini": {
        "input": 0.003,     # $3 per 1M tokens
        "output": 0.012,    # $12 per 1M tokens
        "name": "Mini (Balanced)",
        "relative_cost": "$$$"
    },
    "gpt-4.1": {
        "input": 0.03,      # $30 per 1M tokens
        "output": 0.12,     # $120 per 1M tokens
        "name": "Full (Premium)",
        "relative_cost": "$$$$$"
    }
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

def estimate_curriculum_cost(orchestrator_model: str, worker_model: str, 
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
    orch_cost = calculate_cost(orchestrator_model, orch_tokens["input"], orch_tokens["output"])
    breakdown["orchestration"] = orch_cost
    total_cost += orch_cost
    
    # Outline generation
    outline_tokens = ESTIMATED_TOKENS["outline"]
    outline_cost = calculate_cost(worker_model, outline_tokens["input"], outline_tokens["output"])
    breakdown["outline"] = outline_cost
    total_cost += outline_cost
    
    # Content generation per unit
    content_tokens = ESTIMATED_TOKENS["content_per_unit"]
    content_cost = calculate_cost(worker_model, 
                                 content_tokens["input"] * num_units, 
                                 content_tokens["output"] * num_units)
    breakdown["content"] = content_cost
    total_cost += content_cost
    
    # Optional components
    if include_quizzes:
        quiz_tokens = ESTIMATED_TOKENS["quiz_per_unit"]
        quiz_cost = calculate_cost(worker_model,
                                  quiz_tokens["input"] * num_units,
                                  quiz_tokens["output"] * num_units)
        breakdown["quizzes"] = quiz_cost
        total_cost += quiz_cost
    
    if include_summary:
        summary_tokens = ESTIMATED_TOKENS["summary_per_unit"]
        summary_cost = calculate_cost(worker_model,
                                     summary_tokens["input"] * num_units,
                                     summary_tokens["output"] * num_units)
        breakdown["summaries"] = summary_cost
        total_cost += summary_cost
    
    if include_resources:
        resources_tokens = ESTIMATED_TOKENS["resources_per_unit"]
        resources_cost = calculate_cost(worker_model,
                                       resources_tokens["input"] * num_units,
                                       resources_tokens["output"] * num_units)
        breakdown["resources"] = resources_cost
        total_cost += resources_cost
    
    # Image prompt generation (if images are included)
    image_tokens = ESTIMATED_TOKENS["image_prompt"]
    image_cost = calculate_cost(worker_model,
                               image_tokens["input"] * num_units,
                               image_tokens["output"] * num_units)
    breakdown["image_prompts"] = image_cost
    total_cost += image_cost
    
    # Calculate total tokens for display
    total_tokens = 0
    for component, tokens in ESTIMATED_TOKENS.items():
        if component == "orchestrator":
            total_tokens += tokens["input"] + tokens["output"]
        elif component in ["content", "outline", "media", "chart", "quiz"]:
            total_tokens += (tokens["input"] + tokens["output"]) * num_units
        elif component == "summary_per_unit" and include_summary:
            total_tokens += (tokens["input"] + tokens["output"]) * num_units
        elif component == "resources_per_unit" and include_resources:
            total_tokens += (tokens["input"] + tokens["output"]) * num_units
        elif component == "quiz_per_unit" and include_quizzes:
            total_tokens += (tokens["input"] + tokens["output"]) * num_units
        elif component == "image_prompt":
            total_tokens += (tokens["input"] + tokens["output"]) * num_units

    return {
        "total": total_cost,
        "total_tokens": total_tokens,
        "breakdown": breakdown,
        "orchestrator_model": orchestrator_model,
        "worker_model": worker_model,
        "savings_vs_full": calculate_savings(orchestrator_model, worker_model, total_cost)
    }

def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost for given model and token counts"""
    if model not in MODEL_COSTS:
        return 0.0
    
    costs = MODEL_COSTS[model]
    input_cost = (input_tokens / 1000) * costs["input"]
    output_cost = (output_tokens / 1000) * costs["output"]
    
    return input_cost + output_cost

def calculate_savings(orchestrator_model: str, worker_model: str, actual_cost: float) -> float:
    """Calculate savings compared to using full model for everything"""
    # Calculate what it would cost with full model (without recursive call to calculate_savings)
    full_orch_cost = calculate_cost("gpt-4.1", 2000, 1500)  # Orchestrator usage
    full_worker_cost = calculate_cost("gpt-4.1", 8000, 6000) * 6  # 6 workers
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