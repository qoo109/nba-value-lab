#!/usr/bin/env python3
"""Build the frozen 30-game / 180-slot no-price pilot manifest.

Uses Historical Gold only for exact game identity and NBA Official LiveData only for
scheduled tipoff metadata. It never reads THE_ODDS_API_KEY or calls a paid odds endpoint.
"""
from __future__ import annotations
import argparse,csv,gzip,hashlib,json,re,shutil,sqlite3,tempfile,time,urllib.error,urllib.request
from datetime import datetime,timezone
from pathlib import Path
from typing import Any,Callable
from qualify_timestamped_odds_v1 import build_request_manifest

VERSION="timestamped-odds-pilot-manifest-v1"
URL="https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{official_game_id}.json"
def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def write_csv(path:Path,rows:list[dict[str,Any]]):
 path.parent.mkdir(parents=True,exist_ok=True); fields=list(rows[0]) if rows else []
 with path.open('w',encoding='utf-8',newline='') as h:
  w=csv.DictWriter(h,fieldnames=fields); w.writeheader(); w.writerows(rows)
def official_id(game_id:Any)->str:
 raw=re.sub(r'\.0$','',str(game_id or '').strip())
 if not re.fullmatch(r'\d{8}|\d{10}',raw): raise ValueError(f'unsupported game id {game_id!r}')
 return raw.zfill(10)
def fetch(url:str,attempts:int=3)->tuple[dict[str,Any],dict[str,Any]]:
 last=None
 for n in range(1,attempts+1):
  try:
   req=urllib.request.Request(url,headers={'User-Agent':'NBA-Value-Lab-Research/1.0','Accept':'application/json'})
   with urllib.request.urlopen(req,timeout=60) as r: raw=r.read(); status=int(getattr(r,'status',200))
   if status!=200: raise ValueError(f'HTTP {status}')
   data=json.loads(raw.decode('utf-8'))
   if not isinstance(data,dict): raise ValueError('JSON root not object')
   return data,{'retrieved_at':now(),'http_status':status,'source_bytes':len(raw),'source_sha256':hashlib.sha256(raw).hexdigest(),'attempts':n}
  except (urllib.error.URLError,TimeoutError,ValueError,json.JSONDecodeError) as e:
   last=e
   if n<attempts: time.sleep(n)
 raise RuntimeError(f'official schedule fetch failed: {last}')
def open_gold(path:Path):
 if path.suffix=='.gz':
  temp=tempfile.NamedTemporaryFile(suffix='.sqlite',delete=False); temp.close()
  with gzip.open(path,'rb') as a,open(temp.name,'wb') as b: shutil.copyfileobj(a,b)
  return sqlite3.connect(temp.name),Path(temp.name)
 return sqlite3.connect(path),None
def gold_rows(path:Path,sample:list[dict[str,Any]])->tuple[list[dict[str,str]],dict[str,Any]]:
 con,tmp=open_gold(path)
 try:
  ids=[str(x['game_id']) for x in sample]; q=','.join('?' for _ in ids)
  rows=con.execute(f'SELECT game_id,game_date,home_team_abbr,away_team_abbr FROM gold_matchup_features WHERE game_id IN ({q})',ids).fetchall()
 finally:
  con.close()
  if tmp: tmp.unlink(missing_ok=True)
 by={str(r[0]):{'historical_game_id':str(r[0]),'game_date':str(r[1]),'home_team_abbr':str(r[2]),'away_team_abbr':str(r[3])} for r in rows}
 missing=[]; mismatch=[]; out=[]
 for s in sample:
  gid=str(s['game_id']); r=by.get(gid)
  if not r: missing.append(gid); continue
  if (r['game_date'],r['home_team_abbr'],r['away_team_abbr'])!=(str(s['game_date']),str(s['home']),str(s['away'])): mismatch.append(gid); continue
  out.append(r)
 return out,{'gold_rows':len(rows),'matched_sample_games':len(out),'missing_gold_games':missing,'gold_identity_mismatches':mismatch}
def parse_game(selected:dict[str,str],payload:dict[str,Any],oid:str)->dict[str,str]:
 meta=payload.get('meta') if isinstance(payload.get('meta'),dict) else {}; game=payload.get('game') if isinstance(payload.get('game'),dict) else {}
 if str(meta.get('code',200)) not in {'200','200.0'}: raise ValueError('official meta code not 200')
 if str(game.get('gameId') or '')!=oid: raise ValueError('official game id mismatch')
 home=game.get('homeTeam') if isinstance(game.get('homeTeam'),dict) else {}; away=game.get('awayTeam') if isinstance(game.get('awayTeam'),dict) else {}
 if (str(home.get('teamTricode') or ''),str(away.get('teamTricode') or ''))!=(selected['home_team_abbr'],selected['away_team_abbr']): raise ValueError('official team mismatch')
 code=str(game.get('gameCode') or ''); source_date=code[:8] if re.match(r'^\d{8}/',code) else ''
 if source_date and source_date!=selected['game_date'].replace('-',''): raise ValueError('official date mismatch')
 tip=str(game.get('gameTimeUTC') or '').strip()
 parsed=datetime.fromisoformat(tip.replace('Z','+00:00'))
 if parsed.tzinfo is None: raise ValueError('gameTimeUTC lacks timezone')
 return {**selected,'official_game_id':oid,'scheduled_tipoff_utc':parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')}
def run(policy_path:Path,gold_path:Path,out:Path,fetcher:Callable=fetch)->dict[str,Any]:
 policy=json.loads(policy_path.read_text()); sample=policy['qualification_pilot']['sample']; gold,qa=gold_rows(gold_path,sample)
 schedule=[]; provenance=[]; failures=[]
 for row in gold:
  oid=official_id(row['historical_game_id']); url=URL.format(official_game_id=oid)
  try:
   payload,src=fetcher(url); schedule.append(parse_game(row,payload,oid)); provenance.append({'historical_game_id':row['historical_game_id'],'official_game_id':oid,'source_url':url,**src})
  except Exception as e: failures.append({'historical_game_id':row['historical_game_id'],'error_type':type(e).__name__,'error':str(e)[:240]})
 manifest,mreport=build_request_manifest(policy,schedule)
 credits=int(mreport['coverage']['estimated_quota_credits'])
 decision='PILOT_MANIFEST_READY' if len(schedule)==30 and not failures and mreport['decision']['manifest_structurally_ready'] and credits==1800 else 'PILOT_MANIFEST_STRUCTURAL_BLOCKED'
 report={'schema_version':VERSION,'generated_at':now(),'formal_state':decision,'coverage':{**qa,'official_schedule_games':len(schedule),'official_source_failures':len(failures),'request_manifest_rows':len(manifest),'unique_requested_timestamps':mreport['coverage']['unique_requested_timestamps'],'estimated_paid_quota_credits':credits},'quality':{'official_failures':failures,'duplicate_schedule_games':mreport['quality']['duplicate_schedule_games'],'missing_schedule_games':mreport['quality']['missing_schedule_games'],'identity_mismatches':mreport['quality']['identity_mismatches'],'duplicate_requested_timestamps':mreport['quality']['duplicate_requested_timestamps'],'prices_in_manifest':False,'network_calls_to_paid_odds_provider':0,'api_key_read':False,'paid_endpoint_called':False,'opening_labels':sum(1 for r in manifest if r['snapshot_label'].lower().startswith('opening'))},'decision':{'manifest_structurally_ready':decision=='PILOT_MANIFEST_READY','ready_for_paid_qualification_execution':False,'paid_execution_requires_explicit_user_approval':True,'paid_execution_requires_private_secret':True,'ready_for_market_backtest':False,'ready_for_clv_ev_roi':False,'ready_for_betting_edge_claim':False,'formal_stake':0}}
 out.mkdir(parents=True,exist_ok=True); write_csv(out/'timestamped-odds-pilot-exact-schedule-v1.csv',schedule); write_csv(out/'timestamped-odds-pilot-request-manifest-v1.csv',manifest); write_csv(out/'timestamped-odds-pilot-schedule-provenance-v1.csv',provenance); (out/'timestamped-odds-pilot-manifest-v1.json').write_text(json.dumps(report,indent=2)+'\n')
 return report
def selftest(policy:Path,out:Path):
 p=json.loads(policy.read_text()); sample=p['qualification_pilot']['sample']; sched=[]
 for s in sample: sched.append({'historical_game_id':str(s['game_id']),'game_date':s['game_date'],'home_team_abbr':s['home'],'away_team_abbr':s['away'],'scheduled_tipoff_utc':f"{s['game_date']}T20:00:00Z"})
 rows,rep=build_request_manifest(p,sched)
 assert len(rows)==180, rep
 assert rep['coverage']['estimated_quota_credits']==1800, rep
 assert rep['decision']['manifest_structurally_ready'], rep
 assert not any(r['snapshot_label'].lower().startswith('opening') for r in rows)
 out.mkdir(parents=True,exist_ok=True); (out/'self-test.json').write_text(json.dumps({'success':True,'rows':len(rows),'credits':1800,'manifest_report':rep},indent=2)+'\n')
def main():
 a=argparse.ArgumentParser(); a.add_argument('--policy',type=Path,required=True); a.add_argument('--gold',type=Path); a.add_argument('--output-dir',type=Path,required=True); a.add_argument('--self-test',action='store_true'); x=a.parse_args()
 if x.self_test:
  selftest(x.policy,x.output_dir)
  print('pilot manifest self-test passed')
  return
 if not x.gold:
  a.error('--gold required')
 r=run(x.policy,x.gold,x.output_dir)
 print(json.dumps({'formal_state':r['formal_state'],'coverage':r['coverage']},indent=2))
if __name__=='__main__':main()
