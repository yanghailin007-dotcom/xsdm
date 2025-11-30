"""Utilities for normalizing creative seed data."""
import json
from typing import Any, Dict

def ensure_seed_dict(creative_seed: Any) -> Dict[str, Any]:
    """Return a dict representation of creative_seed.

    - If creative_seed is already a dict, return it.
    - If it's a JSON string, attempt to parse it.
    - Otherwise wrap it into {'coreSetting': str(creative_seed)}.
    """
    if isinstance(creative_seed, dict):
        return creative_seed

    if isinstance(creative_seed, str):
        # try to parse JSON
        try:
            parsed = json.loads(creative_seed)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
        return {"coreSetting": creative_seed}

    # fallback for other types
    try:
        return dict(creative_seed)
    except Exception:
        return {"coreSetting": str(creative_seed)}
