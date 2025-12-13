#!/usr/bin/env python3
"""
Verify third-party provider connectivity (Kimi/Moonshot + DeepSeek).

This script:
- Detects which provider keys are present (without printing them).
- Attempts a minimal `chat.completions.create` call for each provider.

Usage:
  python scripts/verify_providers.py
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

import yaml

from services.provider_service import AIProviderService


def _load_config() -> Dict[str, Any]:
    with open("config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _bool_env(name: str) -> bool:
    return bool(os.getenv(name))


def _try_chat(ps: AIProviderService, provider: str, model: str) -> Dict[str, Any]:
    try:
        client = ps.get_client(provider)
    except Exception as e:
        return {
            "provider": provider,
            "model": model,
            "ok": False,
            "stage": "client_init",
            "error": f"{type(e).__name__}: {e}",
        }

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Reply with exactly: OK"},
                {"role": "user", "content": "OK"},
            ],
        )
        content = resp.choices[0].message.content if resp and resp.choices else ""
        return {
            "provider": provider,
            "model": model,
            "ok": True,
            "reply": (content or "").strip()[:200],
        }
    except Exception as e:
        return {
            "provider": provider,
            "model": model,
            "ok": False,
            "stage": "request",
            "error": f"{type(e).__name__}: {e}",
        }


def main() -> int:
    cfg = _load_config()
    ps = AIProviderService(cfg)

    env_presence = {
        "OPENAI_API_KEY": _bool_env("OPENAI_API_KEY"),
        "KIMI_API_KEY": _bool_env("KIMI_API_KEY"),
        "MOONSHOT_API_KEY": _bool_env("MOONSHOT_API_KEY"),
        "DEEPSEEK_API_KEY": _bool_env("DEEPSEEK_API_KEY"),
    }

    available = ps.get_available_providers()
    print("Keys present:", json.dumps(env_presence, indent=2))
    print("Available providers:", available)

    results = []

    if "kimi" in available:
        kimi_models = ps.get_text_models("kimi")
        chosen = next(
            (m for m in ["kimi-k2-thinking", "kimi-latest", "moonshot-v1-auto"] if m in kimi_models),
            (kimi_models[0] if kimi_models else None),
        )
        if chosen:
            results.append(_try_chat(ps, "kimi", chosen))
        else:
            results.append({"provider": "kimi", "ok": False, "error": "no models available"})
    else:
        results.append({"provider": "kimi", "ok": False, "error": "provider not available (missing key?)"})

    if "deepseek" in available:
        deepseek_models = ps.get_text_models("deepseek")
        chosen = next(
            (m for m in ["deepseek-chat", "deepseek-reasoner"] if m in deepseek_models),
            (deepseek_models[0] if deepseek_models else None),
        )
        if chosen:
            results.append(_try_chat(ps, "deepseek", chosen))
        else:
            results.append({"provider": "deepseek", "ok": False, "error": "no models available"})
    else:
        results.append({"provider": "deepseek", "ok": False, "error": "provider not available (missing key?)"})

    print("Results:", json.dumps(results, indent=2))

    ok = all(r.get("ok") for r in results if r.get("provider") in {"kimi", "deepseek"})
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())

