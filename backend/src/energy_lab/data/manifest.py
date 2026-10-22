"""Stable content hashes and independent named random seeds."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any


def _canonical(value: Any) -> Any:
    if is_dataclass(value):
        return _canonical(asdict(value))
    if isinstance(value, dict):
        return {str(k): _canonical(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple)):
        return [_canonical(v) for v in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(f"cannot canonicalize {type(value).__name__}")


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(_canonical(value), sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def named_seed(root_seed: int, stream_name: str) -> int:
    if isinstance(root_seed, bool) or not isinstance(root_seed, int):
        raise ValueError("root seed must be an integer")
    digest = hashlib.sha256(f"{root_seed}:{stream_name}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")
