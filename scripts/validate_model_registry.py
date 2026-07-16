#!/usr/bin/env python3
"""Validate NBA Value Lab model registry and executable configs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Invalid JSON {path.relative_to(ROOT)}: {exc}") from exc


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def numeric(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def contains_boundary_overlap(previous: dict[str, Any], current: dict[str, Any]) -> bool:
    previous_max = previous.get("max")
    current_min = current.get("min")
    if previous_max is None:
        return True
    if current_min < previous_max:
        return True
    if current_min > previous_max:
        return False
    return bool(previous.get("max_inclusive", True) and current.get("min_inclusive", True))


def validate_segments(segments: list[dict[str, Any]], prefix: str, allow_open_max: bool) -> None:
    require(bool(segments), f"{prefix} segments must not be empty")
    previous: dict[str, Any] | None = None
    for index, segment in enumerate(segments):
        require(numeric(segment.get("min")), f"{prefix} segment {index} min must be numeric")
        maximum = segment.get("max")
        require((allow_open_max and maximum is None) or numeric(maximum), f"{prefix} segment {index} max must be numeric or null")
        if maximum is not None:
            require(segment["min"] < maximum, f"{prefix} segment {index} min must be below max")
        margin = segment.get("required_margin_pp")
        require(margin is None or numeric(margin) and margin > 0, f"{prefix} segment {index} margin must be positive or null")
        require(isinstance(segment.get("label"), str) and segment["label"], f"{prefix} segment {index} label is required")
        if "eligible" in segment:
            require(isinstance(segment["eligible"], bool), f"{prefix} segment {index} eligible must be boolean")
        if "eligible_b" in segment:
            require(isinstance(segment["eligible_b"], bool), f"{prefix} segment {index} eligible_b must be boolean")
        if previous is not None:
            require(not contains_boundary_overlap(previous, segment), f"{prefix} segments overlap near index {index}")
        previous = segment
        if maximum is None:
            require(index == len(segments) - 1, f"{prefix} open-ended segment must be last")


def validate_v(config: dict[str, Any], entry: dict[str, Any]) -> None:
    require(config.get("engine_id") == "V", "V config engine_id must be V")
    require(str(config.get("version")) == str(entry.get("version")), "V config version mismatch")
    if entry.get("revision_id"):
        require(config.get("revision_id") == entry["revision_id"], "V revision_id mismatch")
    scope = config.get("odds_scope", {})
    require(numeric(scope.get("min")) and numeric(scope.get("max")), "V odds_scope bounds must be numeric")
    require(1 < scope["min"] < scope["max"], "V odds scope is invalid")
    require(numeric(config.get("required_margin_pp")) and config["required_margin_pp"] > 0, "V required_margin_pp must be positive")
    policy = config.get("price_policy", {})
    segments = policy.get("price_segments")
    require(isinstance(segments, list), "V price_policy.price_segments must be a list")
    validate_segments(segments, "V", allow_open_max=False)
    require(any(segment.get("eligible_b") for segment in segments), "V must have at least one B-eligible segment")
    coverage = config.get("coverage", {})
    require(coverage.get("critical_fields_non_compensable") is True, "V critical fields must be non-compensable")
    require(config.get("object_model", {}).get("price_evaluation_is_append_only") is True, "V price evaluations must be append-only")
    require(config.get("blind_review", {}).get("required") is True, "V blind review must be required")


def validate_g(config: dict[str, Any], entry: dict[str, Any]) -> None:
    require(config.get("engine_id") == "G", "G config engine_id must be G")
    require(str(config.get("version")) == str(entry.get("version")), "G config version mismatch")
    if entry.get("revision_id"):
        require(config.get("revision_id") == entry["revision_id"], "G revision_id mismatch")
    bands = config.get("price_bands")
    require(isinstance(bands, list), "G price_bands must be a list")
    validate_segments(bands, "G", allow_open_max=True)
    require(any(band.get("eligible") for band in bands), "G must have at least one eligible core band")

    gate = config.get("core_gate", {})
    require(0 <= gate.get("coverage_min_pct", -1) <= 100, "G coverage_min_pct must be 0..100")
    require(numeric(gate.get("interval_width_max_pp")) and gate["interval_width_max_pp"] > 0, "G interval width must be positive")
    require(numeric(gate.get("threshold_buffer_min_pp")) and gate["threshold_buffer_min_pp"] >= 0, "G threshold buffer must be non-negative")
    require(isinstance(gate.get("comparison_sources_min"), int) and gate["comparison_sources_min"] >= 3, "G main selection requires at least 3 comparison sources")
    require(isinstance(gate.get("core_max"), int) and 0 <= gate["core_max"] <= 3, "G core_max must be 0..3")

    selection = config.get("selection", {})
    target = selection.get("official_main_target")
    maximum = selection.get("official_main_max")
    require(isinstance(target, int) and 0 <= target <= 3, "G official_main_target must be 0..3")
    require(isinstance(maximum, int) and 0 <= maximum <= 3, "G official_main_max must be 0..3")
    require(target <= maximum, "G official_main_target must not exceed official_main_max")
    require(gate.get("core_max") == maximum, "G core_max must equal official_main_max")
    require(selection.get("allow_zero_main") is True, "G must permit zero main selections")
    require(selection.get("ui_priority_is_official_g1_grade") is False, "UI priority candidates must not be presented as official G1 grade")

    third = selection.get("third_slot_policy", {})
    if maximum >= 3:
        require(third.get("enabled") is True, "G third-slot policy must be enabled when max is 3")
        require(third.get("requires_all_base_gates") is True, "Third slot must require every base gate")
        require(third.get("coverage_min_pct", 0) >= gate["coverage_min_pct"], "Third-slot coverage cannot be weaker than base gate")
        require(third.get("interval_width_max_pp", 999) <= gate["interval_width_max_pp"], "Third-slot interval cannot be wider than base gate")
        require(third.get("comparison_sources_min", 0) >= gate["comparison_sources_min"], "Third-slot source count cannot be weaker than base gate")
        require(third.get("threshold_buffer_min_pp", -1) >= gate["threshold_buffer_min_pp"], "Third-slot buffer cannot be weaker than base gate")
        require(third.get("news_risk_max", 9) <= gate["news_risk_max"], "Third-slot risk cannot be weaker than base gate")

    consistency = config.get("dual_side_consistency", {})
    require(consistency.get("both_sides_b_math_triggers_conflict") is True, "G dual-side B conflict rule is required")
    require(consistency.get("conflict_blocks_main_selection") is True, "G dual-side conflict must block main selection")


def validate_coordination(config: dict[str, Any], manifest: dict[str, Any]) -> None:
    entry = manifest.get("coordination", {})
    require(entry.get("coordination_id") == config.get("coordination_id"), "coordination_id mismatch")
    require(str(entry.get("version")) == str(config.get("version")), "coordination version mismatch")
    require(config.get("no_probability_blending") is True, "coordination must forbid unvalidated probability blending")
    require(config.get("same_analysis_cutoff_required") is True, "coordination requires the same analysis cutoff")
    policy = config.get("combined_policy", {})
    require(policy.get("dual_side_conflict_blocks_combined_b") is True, "combined policy must block dual-side conflict")
    require(policy.get("formal_stake_fraction") == 0, "formal stake must remain zero")
    ui = config.get("ui_policy", {})
    require(ui.get("official_main_target") <= ui.get("official_main_max"), "coordination main target exceeds max")
    require(ui.get("official_main_max") <= 3, "coordination main max cannot exceed 3")


def main() -> int:
    manifest_path = ROOT / "models" / "manifest.json"
    manifest = load_json(manifest_path)
    require(manifest.get("schema_version") in (1, 2), "manifest schema_version must be 1 or 2")
    active = manifest.get("active", {})

    for engine in ("V", "G"):
        entry = active.get(engine)
        require(isinstance(entry, dict), f"manifest active.{engine} is missing")
        require(entry.get("engine_id") == engine, f"manifest {engine} engine_id mismatch")
        require(str(entry.get("version", "")), f"manifest {engine} version is missing")
        config_path = ROOT / entry.get("config", "")
        spec_path = ROOT / entry.get("spec", "")
        require(config_path.is_file(), f"missing config: {config_path.relative_to(ROOT)}")
        require(spec_path.is_file(), f"missing spec: {spec_path.relative_to(ROOT)}")
        config = load_json(config_path)
        if engine == "V":
            validate_v(config, entry)
        else:
            validate_g(config, entry)

    coordination_entry = manifest.get("coordination")
    if coordination_entry:
        coordination_path = ROOT / coordination_entry.get("config", "")
        require(coordination_path.is_file(), f"missing coordination config: {coordination_path.relative_to(ROOT)}")
        validate_coordination(load_json(coordination_path), manifest)

    schema_path = ROOT / "schemas" / "prediction-record.schema.json"
    require(schema_path.is_file(), "prediction record schema is missing")
    load_json(schema_path)
    label = f"V{active['V']['version']} × G{active['G']['version']}"
    revision = active["G"].get("revision_id")
    print(f"Model registry valid: {label}{' (' + revision + ')' if revision else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
