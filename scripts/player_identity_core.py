#!/usr/bin/env python3
"""Deterministic player-name normalization helpers for identity matching."""
from __future__ import annotations

import re
import unicodedata
from typing import Any

SUFFIX_MAP = {
    "junior": "jr",
    "jr": "jr",
    "senior": "sr",
    "sr": "sr",
    "ii": "ii",
    "iii": "iii",
    "iv": "iv",
    "v": "v",
}
SUFFIXES = set(SUFFIX_MAP.values())


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _ascii_fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(character for character in normalized if not unicodedata.combining(character))


def reorder_comma_name(value: str) -> str:
    """Convert official `Last, First` names to `First Last` without guessing."""
    parts = [part.strip() for part in value.split(",") if part.strip()]
    if len(parts) != 2:
        return value
    family, given = parts
    return f"{given} {family}"


def normalize_player_name(value: Any) -> str:
    text = clean_text(value)
    if not text:
        return ""
    text = reorder_comma_name(text)
    text = _ascii_fold(text).lower()
    text = text.replace("’", "'").replace("`", "'")
    text = re.sub(r"['.-]", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    tokens = [SUFFIX_MAP.get(token, token) for token in text.split()]
    return " ".join(tokens)


def suffixless_player_name(value: Any) -> str:
    key = normalize_player_name(value)
    tokens = key.split()
    if tokens and tokens[-1] in SUFFIXES:
        tokens.pop()
    return " ".join(tokens)


def player_name_keys(value: Any) -> tuple[str, str]:
    return normalize_player_name(value), suffixless_player_name(value)
