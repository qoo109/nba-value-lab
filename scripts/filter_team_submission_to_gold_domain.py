#!/usr/bin/env python3
"""Keep only Gold-matched team-ledger games; unmatched player-backed games are fatal."""
from __future__ import annotations
import argparse, csv, json
from datetime import datetime, timezone
from pathlib import Path

VERSION = "team-submission-gold-domain-v1"

def read_csv(path):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def write_csv(path, rows, fields):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)

def matched(row):
    return str(row.get("matched", "")).lower() in {"1", "true", "yes"} and bool(str(row.get("historical_game_id", "")).strip())

def build(team_rows, team_map, player_map, out):
    team_ids = [str(r.get("official_game_id", "")).strip() for r in team_map]
    player_ids = [str(r.get("official_game_id", "")).strip() for r in player_map]
    matched_team = {str(r["official_game_id"]).strip() for r in team_map if matched(r)}
    unmatched_team = {str(r["official_game_id"]).strip() for r in team_map if not matched(r)}
    matched_player = {str(r["official_game_id"]).strip() for r in player_map if matched(r)}
    unmatched_player = {str(r["official_game_id"]).strip() for r in player_map if not matched(r)}
    panel_ids = {str(r.get("game_id", "")).strip() for r in team_rows}
    excluded_player_backed = sorted(unmatched_team & set(player_ids))
    errors = []
    if len(team_ids) != len(set(team_ids)): errors.append("duplicate team map ids")
    if len(player_ids) != len(set(player_ids)): errors.append("duplicate player map ids")
    if unmatched_player: errors.append(f"unmatched player games: {sorted(unmatched_player)}")
    if excluded_player_backed: errors.append(f"excluded games appear in player map: {excluded_player_backed}")
    if panel_ids != matched_team | unmatched_team: errors.append("team panel/map game sets differ")
    if not matched_player.issubset(matched_team): errors.append("matched player games missing from team domain")
    kept = [r for r in team_rows if str(r.get("game_id", "")).strip() in matched_team]
    dropped = [r for r in team_rows if str(r.get("game_id", "")).strip() in unmatched_team]
    kept_map = [r for r in team_map if str(r.get("official_game_id", "")).strip() in matched_team]
    ready = not errors and bool(kept)
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    write_csv(out/"gold-domain-team-submission-panel.csv", kept, list(team_rows[0]) if team_rows else [])
    write_csv(out/"gold-domain-team-game-id-map.csv", kept_map, list(team_map[0]) if team_map else [])
    report = {
      "schema_version": VERSION,
      "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z"),
      "coverage": {"input_team_rows":len(team_rows),"input_team_games":len(panel_ids),"snapshot_rows":len(kept),"snapshot_games":len(matched_team),"matched_games":len(matched_team),"matched_snapshot_rows":len(kept),"excluded_team_only_rows":len(dropped),"excluded_team_only_games":len(unmatched_team),"player_map_games":len(set(player_ids))},
      "quality": {"game_match_rate":1.0 if ready else 0.0,"unmatched_games":0 if ready else len(unmatched_team),"duplicate_gold_schedule_keys":0,"unmatched_player_game_ids":sorted(unmatched_player),"excluded_team_only_game_ids":sorted(unmatched_team),"excluded_player_backed_games":excluded_player_backed,"validation_errors":errors,"outcomes_or_market_prices_used":False},
      "decision": {"ready_for_gold_domain_reconciliation":ready,"ready_for_historical_game_id_join":ready,"ready_for_model_training":False,"ready_for_betting_edge_claim":False},
      "guardrails": {"unmatched_player_backed_games_allowed":False,"excluded_games_must_be_absent_from_player_map":True,"fuzzy_schedule_matching_used":False}
    }
    (out/"team-submission-gold-domain-report.json").write_text(json.dumps(report,indent=2)+"\n")
    return report

def self_test(out):
    team=[{"game_id":"g1","team_abbr":"A"},{"game_id":"g1","team_abbr":"B"},{"game_id":"g2","team_abbr":"C"},{"game_id":"g2","team_abbr":"D"}]
    tm=[{"official_game_id":"g1","historical_game_id":"h1","matched":"True"},{"official_game_id":"g2","historical_game_id":"","matched":"False"}]
    pm=[{"official_game_id":"g1","historical_game_id":"h1","matched":"True"}]
    r=build(team,tm,pm,out); assert r["decision"]["ready_for_gold_domain_reconciliation"] and r["coverage"]["excluded_team_only_games"]==1
    bad=build(team,tm,pm+[{"official_game_id":"g2","historical_game_id":"","matched":"False"}],Path(out)/"bad"); assert not bad["decision"]["ready_for_gold_domain_reconciliation"]

def main():
    p=argparse.ArgumentParser(); p.add_argument("--team-panel"); p.add_argument("--team-game-map"); p.add_argument("--player-game-map"); p.add_argument("--output-dir",required=True); p.add_argument("--self-test",action="store_true"); a=p.parse_args()
    if a.self_test: self_test(a.output_dir); print("Gold-domain filter self-test passed"); return
    if not a.team_panel or not a.team_game_map or not a.player_game_map: p.error("all input files are required")
    r=build(read_csv(a.team_panel),read_csv(a.team_game_map),read_csv(a.player_game_map),a.output_dir); print(json.dumps(r["decision"],indent=2))
    if not r["decision"]["ready_for_gold_domain_reconciliation"]: raise SystemExit(2)
if __name__ == "__main__": main()
