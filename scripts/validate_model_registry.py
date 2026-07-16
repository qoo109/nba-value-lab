#!/usr/bin/env python3
"""Validate NBA Value Lab model registry and executable configs."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Invalid JSON {path.relative_to(ROOT)}: {exc}") from exc


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def validate_v(config: dict, version: str) -> None:
    require(config.get("engine_id") == "V", "V config engine_id must be V")
    require(str(config.get("version")) == str(version), "V config version mismatch")
    scope = config.get("odds_scope", {})
    require(isinstance(scope.get("min"), (int, float)), "V odds_scope.min must be numeric")
    require(isinstance(scope.get("max"), (int, float)), "V odds_scope.max must be numeric")
    require(1 < scope["min"] < scope["max"], "V odds scope is invalid")
    require(config.get("required_margin_pp", 0) > 0, "V required_margin_pp must be positive")
    require(config.get("early_preview_extra_margin_pp", -1) >= 0, "V early preview margin must be non-negative")


def validate_g(config: dict, version: str) -> None:
    require(config.get("engine_id") == "G", "G config engine_id must be G")
    require(str(config.get("version")) == str(version), "G config version mismatch")
    bands = config.get("price_bands")
    require(isinstance(bands, list) and bands, "G price_bands must be a non-empty list")
    previous_max = None
    for index, band in enumerate(bands):
        for key in ("min", "max", "required_margin_pp"):
            require(isinstance(band.get(key), (int, float)), f"G band {index} {key} must be numeric")
        require(band["min"] < band["max"], f"G band {index} min must be below max")
        require(band["required_margin_pp"] > 0, f"G band {index} margin must be positive")
        require(isinstance(band.get("eligible"), bool), f"G band {index} eligible must be boolean")
        if previous_max is not None:
            require(band["min"] >= previous_max, f"G price bands overlap near index {index}")
        previous_max = band["max"]
    gate = config.get("core_gate", {})
    require(0 <= gate.get("coverage_min_pct", -1) <= 100, "G coverage_min_pct must be 0..100")
    require(gate.get("interval_width_max_pp", 0) > 0, "G interval width must be positive")
    require(gate.get("threshold_buffer_min_pp", -1) >= 0, "G threshold buffer must be non-negative")
    require(gate.get("core_max") in (0, 1), "G core_max must be 0 or 1")
    require(isinstance(gate.get("priority_max"), int) and gate["priority_max"] >= 0, "G priority_max must be non-negative integer")


def main() -> int:
    manifest_path = ROOT / "models" / "manifest.json"
    manifest = load_json(manifest_path)
    require(manifest.get("schema_version") == 1, "manifest schema_version must be 1")
    active = manifest.get("active", {})

    for engine in ("V", "G"):
        entry = active.get(engine)
        require(isinstance(entry, dict), f"manifest active.{engine} is missing")
        require(entry.get("engine_id") == engine, f"manifest {engine} engine_id mismatch")
        version = str(entry.get("version", ""))
        require(version, f"manifest {engine} version is missing")
        config_path = ROOT / entry.get("config", "")
        spec_path = ROOT / entry.get("spec", "")
        require(config_path.is_file(), f"missing config: {config_path.relative_to(ROOT)}")
        require(spec_path.is_file(), f"missing spec: {spec_path.relative_to(ROOT)}")
        config = load_json(config_path)
        if engine == "V":
            validate_v(config, version)
        else:
            validate_g(config, version)

    schema_path = ROOT / "schemas" / "prediction-record.schema.json"
    require(schema_path.is_file(), "prediction record schema is missing")
    load_json(schema_path)
    print(f"Model registry valid: V{active['V']['version']} × G{active['G']['version']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
