"""
JSON parsing helpers.

These utilities exist because some OpenAI-compatible providers may return JSON
wrapped in code fences or preceded/followed by extra text, even when prompted
to output strict JSON.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional


_CODE_FENCE_RE = re.compile(
    r"```(?:json)?\s*(?P<body>\{.*?\}|\[.*?\])\s*```",
    flags=re.DOTALL | re.IGNORECASE,
)


def parse_json_relaxed(text: Any) -> Optional[Any]:
    """Parse JSON with a few common fallbacks.

    Tries:
    - direct `json.loads(text)`
    - JSON inside ```json ... ``` fences
    - first {...} or [...] substring
    """
    if not isinstance(text, str):
        return None

    s = text.strip()
    if not s:
        return None

    try:
        return json.loads(s)
    except Exception:
        pass

    match = _CODE_FENCE_RE.search(s)
    if match:
        body = (match.group("body") or "").strip()
        try:
            return json.loads(body)
        except Exception:
            pass

    obj_start = s.find("{")
    obj_end = s.rfind("}")
    if obj_start != -1 and obj_end != -1 and obj_end > obj_start:
        candidate = s[obj_start : obj_end + 1]
        try:
            return json.loads(candidate)
        except Exception:
            pass

    arr_start = s.find("[")
    arr_end = s.rfind("]")
    if arr_start != -1 and arr_end != -1 and arr_end > arr_start:
        candidate = s[arr_start : arr_end + 1]
        try:
            return json.loads(candidate)
        except Exception:
            pass

    return None

