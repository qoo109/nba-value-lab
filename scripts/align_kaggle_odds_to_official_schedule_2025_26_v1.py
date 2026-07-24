#!/usr/bin/env python3
"""Private diagnostic alignment of Kaggle NBA odds to official 2025-26 schedule.

The source ZIP and quote rows stay local. Source ``timestamp`` is preserved and
is only treated as a collector-created league-batch timestamp assumed UTC. It
is never promoted to provider quote time or exact T-60.
"""
from __future__ import annotations

import argparse, hashlib, json, zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

ALIASES={"LA Clippers":"Los Angeles Clippers"}
ALL_STAR={"USA Stars","USA Stripes","World"}
REG_END=pd.Timestamp("2026-04-13T00:00:00Z")
CUP_LO=pd.Timestamp("2025-12-16T00:00:00Z"); CUP_HI=pd.Timestamp("2025-12-18T00:00:00Z")
CUP_TIP=pd.Timestamp("2025-12-17T01:30:00Z"); CUP_ID="0062500001"


def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""): h.update(chunk)
    return "sha256:"+h.hexdigest()


def read_archive(path:Path):
    with zipfile.ZipFile(path) as z:
        main=pd.read_csv(z.open(next(n for n in z.namelist() if n.endswith("/nba_main_lines.csv"))))
        detail=pd.read_csv(z.open(next(n for n in z.namelist() if n.endswith("/nba_detailed_odds.csv"))))
    main["event_id"]=main.game_link.astype(str).str.extract(r"/(\d+)/?$")[0]
    if main.event_id.isna().any(): raise ValueError("missing source event ID")
    main["timestamp_dt"]=pd.to_datetime(main.timestamp,utc=True)
    return main,detail


def events(main):
    return main.groupby("event_id").agg(team1=("team1","first"),team2=("team2","first"),tmin=("timestamp_dt","min"),tmax=("timestamp_dt","max"),snapshot_count=("timestamp_dt","size")).reset_index()


def load_json(path:Path,state:str):
    p=json.loads(path.read_text())
    if p.get("formal_state")!=state: raise ValueError(f"invalid evidence: {path}")
    return p


def schedule_rows(schedule_payload,subset_payload,event_df):
    base=pd.DataFrame(schedule_payload["games"])
    base["tipoff_dt"]=pd.to_datetime(base.scheduled_tipoff_utc,utc=True)
    base["alignment_provenance"]="OFFICIAL_SCHEDULE_RELEASE_PDF"
    base["source_url"]=schedule_payload.get("source_url")
    base["source_payload_sha256"]=schedule_payload.get("source_payload_sha256")
    sub=pd.DataFrame(subset_payload["games"])
    sub["official_away_team"]=sub.official_away_team.replace(ALIASES)
    sub["official_home_team"]=sub.official_home_team.replace(ALIASES)
    sub["tipoff_dt"]=pd.to_datetime(sub.scheduled_tipoff_utc,utc=True)
    recon=sub[sub.subset_reason!="NBA_CUP_DETERMINED_REGULAR_SEASON_GAME"]
    pair_idx={}
    for i,r in base.iterrows():
        if r.venue_relation=="at": pair_idx.setdefault((r.official_team1,r.official_team2),[]).append(i)
    remove=[]
    for r in recon.itertuples():
        ev=event_df[(event_df.team1==r.official_away_team)&(event_df.team2==r.official_home_team)].copy()
        if ev.empty: raise ValueError(f"no private event for {r.official_game_id}")
        e=ev.loc[(ev.tmax-r.tipoff_dt).abs().idxmin()]
        ids=pair_idx[(r.official_away_team,r.official_home_team)]
        remove.append(min(ids,key=lambda i:abs((base.loc[i,"tipoff_dt"]-e.tmax).total_seconds())))
    if len(set(remove))!=len(recon): raise ValueError("duplicate release reconciliation")
    base=base.drop(index=remove)
    add=[]
    for r in sub.to_dict("records"):
        add.append({
          "official_schedule_row_id":"nba-game-"+r["official_game_id"],"official_game_id":r["official_game_id"],
          "schedule_source_type":"official_liveData_boxscore","schedule_version_date":"2026-07-24",
          "schedule_subject_to_change":False,"venue_relation":"at","official_team1":r["official_away_team"],
          "official_team2":r["official_home_team"],"official_away_team":r["official_away_team"],
          "official_home_team":r["official_home_team"],"scheduled_tipoff_et":None,
          "scheduled_tipoff_utc":r["scheduled_tipoff_utc"],"published_local_time":r.get("game_time_local"),
          "published_et_time":r.get("game_et"),"game_status":r.get("game_status"),
          "game_status_text":r.get("game_status_text"),"game_label":"NBA regular season",
          "game_sub_label":r["subset_reason"],"week_name":None,"arena_name":r.get("arena_name"),
          "arena_city":r.get("arena_city"),"arena_state":r.get("arena_state"),"postponed_status":None,
          "source_url":r.get("source_url"),"source_payload_sha256":r.get("source_payload_sha256"),
          "alignment_provenance":r["subset_reason"]})
    out=pd.concat([base,pd.DataFrame(add)],ignore_index=True,sort=False)
    out["tipoff_dt"]=pd.to_datetime(out.scheduled_tipoff_utc,utc=True)
    if len(out)!=1230 or out.official_schedule_row_id.nunique()!=1230: raise ValueError("schedule reconciliation count/ID failure")
    if out.duplicated(["official_team1","official_team2","scheduled_tipoff_utc"]).any(): raise ValueError("duplicate schedule matchup/tipoff")
    return out


def align_events(event_df,schedule):
    ordered={}; neutral=[]
    for i,r in schedule.iterrows():
        (ordered.setdefault((r.official_team1,r.official_team2),[]).append(i) if r.venue_relation=="at" else neutral.append(i))
    rows=[]
    for e in event_df.to_dict("records"):
        x=dict(e); teams={e["team1"],e["team2"]}
        if teams & ALL_STAR:
            x.update(status="EXCLUDED_ALL_STAR",competition_bucket="ALL_STAR",match_method="team_name_rule"); rows.append(x); continue
        if teams=={"San Antonio Spurs","New York Knicks"} and CUP_LO<=e["tmax"]<CUP_HI:
            x.update(status="EXCLUDED_NBA_CUP_CHAMPIONSHIP",competition_bucket="NBA_CUP_CHAMPIONSHIP_NON_STANDINGS",match_method="official_cup_championship_page",official_schedule_row_id="nba-game-"+CUP_ID,official_game_id=CUP_ID,official_team1="San Antonio Spurs",official_team2="New York Knicks",official_away_team=None,official_home_team=None,venue_relation="vs",scheduled_tipoff_utc=CUP_TIP.isoformat().replace("+00:00","Z"),alignment_provenance="OFFICIAL_NBA_CUP_CHAMPIONSHIP_PAGE",schedule_subject_to_change=False,source_url="https://www.nba.com/game/sas-vs-nyk-0062500001",source_payload_sha256=None); rows.append(x); continue
        cand=ordered.get((e["team1"],e["team2"]),[]); method="ordered_away_home"
        if not cand:
            cand=[i for i in neutral if {schedule.loc[i,"official_team1"],schedule.loc[i,"official_team2"]}==teams]; method="neutral_unordered"
        if cand:
            i=min(cand,key=lambda j:abs((schedule.loc[j,"tipoff_dt"]-e["tmax"]).total_seconds()))
            r=schedule.loc[i]; gap=abs((r.tipoff_dt-e["tmax"]).total_seconds())/3600
            if gap<=24:
                if r.venue_relation=="vs": status="MATCHED_NEUTRAL_SITE_REGULAR_SEASON"
                elif "ADJUSTMENT" in str(r.alignment_provenance): status="MATCHED_SCHEDULE_ADJUSTED"
                else: status="MATCHED_HIGH_CONFIDENCE_REGULAR_SEASON"
                x.update(status=status,competition_bucket="REGULAR_SEASON",match_method=method,match_abs_gap_hours=gap,official_schedule_row_id=r.official_schedule_row_id,official_game_id=r.get("official_game_id"),official_away_team=r.get("official_away_team"),official_home_team=r.get("official_home_team"),official_team1=r.official_team1,official_team2=r.official_team2,scheduled_tipoff_utc=r.scheduled_tipoff_utc,alignment_provenance=r.alignment_provenance,venue_relation=r.venue_relation,schedule_subject_to_change=r.schedule_subject_to_change,source_url=r.source_url,source_payload_sha256=r.source_payload_sha256); rows.append(x); continue
        if e["tmax"]>=REG_END: x.update(status="EXCLUDED_POSTSEASON_OR_PLAY_IN",competition_bucket="POSTSEASON_OR_PLAY_IN",match_method="post_regular_season_date_rule")
        else: x.update(status="UNMATCHED_OR_AMBIGUOUS",competition_bucket="UNMATCHED_OR_AMBIGUOUS",match_method="no_schedule_candidate_within_24h")
        rows.append(x)
    out=pd.DataFrame(rows); out["quote_time_exact_verified"]=False; out["provider_origin_quote_time_verified"]=False
    return out


def enrich(main,detail,event_map):
    cols=["event_id","status","competition_bucket","match_method","official_schedule_row_id","official_game_id","official_away_team","official_home_team","scheduled_tipoff_utc","alignment_provenance","venue_relation","schedule_subject_to_change","source_url","source_payload_sha256","quote_time_exact_verified","provider_origin_quote_time_verified"]
    m=main.merge(event_map[cols],on="event_id",how="left",validate="many_to_one")
    m["scheduled_tipoff_dt"]=pd.to_datetime(m.scheduled_tipoff_utc,utc=True,errors="coerce")
    m["collector_batch_timestamp_utc_assumed"]=m.timestamp_dt.dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    m["batch_minutes_before_published_tipoff"]=(m.scheduled_tipoff_dt-m.timestamp_dt).dt.total_seconds()/60
    m["batch_pre_tip_by_assumed_utc"]=m.batch_minutes_before_published_tipoff>0
    m["t60_absolute_error_minutes"]=(m.batch_minutes_before_published_tipoff-60).abs(); m["t60_batch_candidate"]=False
    pre=m[(m.competition_bucket=="REGULAR_SEASON")&(m.batch_minutes_before_published_tipoff>0)]
    m.loc[pre.groupby("event_id").t60_absolute_error_minutes.idxmin(),"t60_batch_candidate"]=True
    for c,v in {"strict_t60_qualified":False,"quote_strictly_pre_tip_verified":False,"collector_timestamp_semantics":"LEAGUE_BATCH_TIMESTAMP_CREATED_BY_COLLECTOR_ASSUMED_UTC","quote_observation_time_semantics":"UNKNOWN_WITHIN_SEQUENTIAL_BATCH","data_scope_decision":"PRIVATE_DIAGNOSTIC_ONLY"}.items(): m[c]=v
    m["alignment_status"]=m.status
    m["scheduled_tipoff_authority"]=m.alignment_provenance.map(lambda v:"OFFICIAL_NBA_SCHEDULE_RELEASE_2025_08_14" if v=="OFFICIAL_SCHEDULE_RELEASE_PDF" else ("OFFICIAL_NBA_LIVEDATA_OR_GAME_PAGE" if pd.notna(v) else None))
    m["scheduled_tipoff_finalized_from_livedata"]=m.alignment_provenance.isin({"NBA_CUP_DETERMINED_REGULAR_SEASON_GAME","KNOWN_SCHEDULE_TIME_ADJUSTMENT_RECONCILIATION","KNOWN_SCHEDULE_DATE_ADJUSTMENT_RECONCILIATION"})
    key=m[["event_id","team1","team2","timestamp","t60_batch_candidate","collector_batch_timestamp_utc_assumed","batch_minutes_before_published_tipoff","batch_pre_tip_by_assumed_utc","t60_absolute_error_minutes"]].copy(); key["matchup"]=key.team1+" vs "+key.team2
    d=detail.merge(key[["matchup","timestamp","event_id","t60_batch_candidate","collector_batch_timestamp_utc_assumed","batch_minutes_before_published_tipoff","batch_pre_tip_by_assumed_utc","t60_absolute_error_minutes"]],on=["matchup","timestamp"],how="left",validate="many_to_one")
    ecols=["event_id","status","competition_bucket","official_schedule_row_id","official_game_id","official_away_team","official_home_team","scheduled_tipoff_utc","alignment_provenance","venue_relation","schedule_subject_to_change","quote_time_exact_verified","provider_origin_quote_time_verified"]
    d=d.merge(event_map[ecols],on="event_id",how="left",validate="many_to_one")
    d["alignment_status"]=d.status
    for c,v in {"strict_t60_qualified":False,"quote_strictly_pre_tip_verified":False,"collector_timestamp_semantics":"LEAGUE_BATCH_TIMESTAMP_CREATED_BY_COLLECTOR_ASSUMED_UTC","quote_observation_time_semantics":"UNKNOWN_WITHIN_SEQUENTIAL_BATCH","data_scope_decision":"PRIVATE_DIAGNOSTIC_ONLY"}.items(): d[c]=v
    return m,d


def main():
    p=argparse.ArgumentParser(); p.add_argument("--archive",type=Path,required=True); p.add_argument("--official-schedule",type=Path,required=True); p.add_argument("--official-subset",type=Path,required=True); p.add_argument("--output-dir",type=Path,required=True); a=p.parse_args()
    main,detail=read_archive(a.archive); ev=events(main)
    sched_payload=load_json(a.official_schedule,"OFFICIAL_NBA_2025_26_SCHEDULE_FETCH_VALID")
    subset_payload=load_json(a.official_subset,"OFFICIAL_NBA_BOXSCORE_METADATA_SUBSET_VALID")
    sched=schedule_rows(sched_payload,subset_payload,ev); amap=align_events(ev,sched)
    if (amap.status=="UNMATCHED_OR_AMBIGUOUS").any(): raise ValueError("unmatched source event remains")
    m,d=enrich(main,detail,amap)
    if d.event_id.isna().any(): raise ValueError("detailed row mapping failure")
    a.output_dir.mkdir(parents=True,exist_ok=True)
    sched.drop(columns=["tipoff_dt"]).to_csv(a.output_dir/"official_nba_2025_26_reconciled_schedule_v1.csv",index=False)
    amap.to_csv(a.output_dir/"kaggle_official_schedule_full_alignment_events_v1.csv",index=False)
    m.drop(columns=["timestamp_dt","scheduled_tipoff_dt"]).to_csv(a.output_dir/"kaggle_nba_main_lines_officially_aligned_2025_26_v1.csv",index=False)
    d.to_csv(a.output_dir/"kaggle_nba_detailed_odds_officially_aligned_2025_26_v1.csv",index=False)
    reg=amap[amap.competition_bucket=="REGULAR_SEASON"]; rm=m[m.competition_bucket=="REGULAR_SEASON"]; cand=rm[rm.t60_batch_candidate]
    summary={"schema_version":"kaggle-official-schedule-full-alignment-summary-v1","generated_at_utc":datetime.now(timezone.utc).isoformat(),"formal_state":"KAGGLE_OFFICIAL_SCHEDULE_FULL_ALIGNMENT_DIAGNOSTIC_VALID","source_archive_sha256":sha(a.archive),"reconciled_schedule_rows":len(sched),"source_events_classified":len(amap),"classification_counts":amap.status.value_counts().to_dict(),"regular_season_events_matched":len(reg),"regular_main_rows_enriched":len(rm),"regular_detailed_rows_enriched":int((d.competition_bucket=="REGULAR_SEASON").sum()),"regular_events_with_pretip_batch_candidate":int(cand.event_id.nunique()),"regular_events_without_pretip_batch_candidate":int(len(reg)-cand.event_id.nunique()),"t60_candidate_counts":{str(x):int((cand.t60_absolute_error_minutes<=x).sum()) for x in (5,15,30,60)},"median_t60_batch_error_minutes":float(cand.t60_absolute_error_minutes.median()),"provider_origin_quote_time_verified":False,"quote_level_exact_observed_at_verified":False,"strict_t60_qualified":False,"point_in_time_qualified":False,"historical_backfill_qualified":False,"market_backtest_unlocked":False,"formal_stake":0,"decision":"KEEP_PRIVATE_DIAGNOSTIC_ALIGNMENT_OFFICIAL_SCHEDULE_REPAIRED_QUOTE_TIME_UNRESOLVED","next_unique_mainline":"AWAIT_REAL_GOVERNED_2026_27_T60_INPUT_AND_QUALIFIED_TIMESTAMPED_ODDS"}
    (a.output_dir/"kaggle_official_schedule_full_alignment_summary_v1.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(summary,ensure_ascii=False,indent=2)); return 0

if __name__=="__main__": raise SystemExit(main())
