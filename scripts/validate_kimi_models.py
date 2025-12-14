#!/usr/bin/env python3
"""
Validate Kimi/Moonshot chat models against InstaSchool's curriculum JSON needs.

This script tests each model with the same kinds of JSON outputs the app requires:
- outline (topics JSON)
- chart suggestion (chart JSON)
- quiz generation (quiz JSON)

It does NOT print API keys.

Usage:
  python scripts/validate_kimi_models.py
  python scripts/validate_kimi_models.py --write-config   # update config.yaml with only passing models
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, List, Tuple

import yaml
from dotenv import load_dotenv
from openai import OpenAI

from src.agent_framework import OutlineAgent, ChartAgent, QuizAgent
from services.provider_service import AIProviderService


def _load_config(path: str = "config.yaml") -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _get_kimi_key() -> str:
    # Prefer explicit KIMI_API_KEY, fallback to MOONSHOT_API_KEY (common in config.yaml)
    return os.getenv("KIMI_API_KEY") or os.getenv("MOONSHOT_API_KEY") or ""


def _validate_outline(agent: OutlineAgent) -> Tuple[bool, str]:
    agent.cache = None  # avoid cross-model cache contamination
    topics = agent.generate_outline(
        subject="Science",
        grade="Kindergarten",
        style="Standard",
        extra="",
        min_topics=3,
        max_topics=5,
        language="English",
    )
    if not isinstance(topics, list) or len(topics) < 3:
        return False, "outline returned <3 topics"
    if any(not isinstance(t, dict) or not isinstance(t.get("title"), str) or not t["title"].strip() for t in topics):
        return False, "outline topics malformed"
    return True, "ok"


def _validate_chart(agent: ChartAgent) -> Tuple[bool, str]:
    data = agent.suggest_chart(
        topic="Plants, Seeds, and Our Food",
        subject="Science",
        grade="Kindergarten",
        style="Standard",
        language="English",
    )
    if not isinstance(data, dict):
        return False, "chart suggestion missing"
    chart_type = data.get("chart_type")
    title = data.get("title")
    chart_data = data.get("data")
    if not isinstance(chart_type, str) or not chart_type.strip():
        return False, "chart_type missing"
    if not isinstance(title, str) or not title.strip():
        return False, "chart title missing"
    if not isinstance(chart_data, dict):
        return False, "chart data missing"
    labels = chart_data.get("labels")
    values = chart_data.get("values")
    if not isinstance(labels, list) or not isinstance(values, list) or not labels or not values:
        return False, "chart labels/values missing"
    return True, "ok"


def _validate_quiz(agent: QuizAgent) -> Tuple[bool, str]:
    quiz = agent.generate_quiz(
        topic="Our Senses Explore the World",
        subject="Science",
        grade="Kindergarten",
        style="Standard",
        language="English",
    )
    if not isinstance(quiz, dict):
        return False, "quiz missing"
    questions = quiz.get("questions")
    if not isinstance(questions, list) or not questions:
        return False, "quiz questions missing"
    q0 = questions[0]
    if not isinstance(q0, dict) or not isinstance(q0.get("question"), str) or not q0.get("question", "").strip():
        return False, "quiz question text missing"
    return True, "ok"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument(
        "--write-config",
        action="store_true",
        help="Overwrite ai_providers.providers.kimi.text_models with only passing models.",
    )
    args = parser.parse_args()

    load_dotenv()

    cfg = _load_config(args.config)
    provider_service = AIProviderService(cfg)

    kimi_key = _get_kimi_key()
    if not kimi_key:
        print("❌ Missing KIMI_API_KEY or MOONSHOT_API_KEY in the environment.")
        return 2

    base_url = provider_service.PROVIDERS["kimi"]["base_url"]
    client = OpenAI(api_key=kimi_key, base_url=base_url)

    # Confirm auth + fetch provider-visible models (source of truth for this key)
    try:
        listed = client.models.list()
        available = sorted({m.id for m in (getattr(listed, "data", None) or []) if getattr(m, "id", None)})
    except Exception as e:
        print(f"❌ Failed to list Moonshot models (check your key): {type(e).__name__}: {str(e)[:180]}")
        return 2

    candidates = provider_service.PROVIDERS["kimi"].get("text_models", [])
    if not isinstance(candidates, list) or not candidates:
        candidates = available

    # Only test models actually available to this key
    candidates = [m for m in candidates if isinstance(m, str) and m in set(available)]
    if not candidates:
        print("❌ No candidate models matched models.list() output for this key.")
        return 2

    passing: List[str] = []
    failing: Dict[str, Dict[str, str]] = {}

    print("Checking Kimi.ai (Moonshot)...")
    print("-" * 60)

    for model in candidates:
        if not isinstance(model, str) or not model.strip():
            continue

        outline_agent = OutlineAgent(client, model, cfg)
        chart_agent = ChartAgent(client, model, cfg)
        quiz_agent = QuizAgent(client, model, cfg)

        try:
            ok, reason = _validate_outline(outline_agent)
            if not ok:
                failing[model] = {"stage": "outline", "reason": reason}
                print(f"❌ {model}: outline failed ({reason})")
                continue

            ok, reason = _validate_chart(chart_agent)
            if not ok:
                failing[model] = {"stage": "chart", "reason": reason}
                print(f"❌ {model}: chart failed ({reason})")
                continue

            ok, reason = _validate_quiz(quiz_agent)
            if not ok:
                failing[model] = {"stage": "quiz", "reason": reason}
                print(f"❌ {model}: quiz failed ({reason})")
                continue

            passing.append(model)
            print(f"✅ {model}: ok")
        except Exception as e:
            failing[model] = {"stage": "exception", "reason": f"{type(e).__name__}: {e}"}
            print(f"❌ {model}: exception ({type(e).__name__})")

    print("-" * 60)
    print(f"Passing models ({len(passing)}):")
    for m in passing:
        print(m)

    if failing:
        print("\nFailing models:")
        print(json.dumps(failing, indent=2)[:4000])

    if args.write_config:
        ai_providers = cfg.get("ai_providers") or {}
        providers = ai_providers.get("providers") or {}
        kimi = providers.get("kimi") or {}
        kimi["text_models"] = passing
        providers["kimi"] = kimi
        ai_providers["providers"] = providers
        cfg["ai_providers"] = ai_providers

        with open(args.config, "w", encoding="utf-8") as f:
            yaml.safe_dump(cfg, f, sort_keys=False, allow_unicode=True)
        print(f"\n✅ Wrote passing models to {args.config} (ai_providers.providers.kimi.text_models).")

    return 0 if passing and not failing else 1


if __name__ == "__main__":
    raise SystemExit(main())
