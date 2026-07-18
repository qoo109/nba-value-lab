#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,math
from datetime import datetime,timezone
from pathlib import Path
import numpy as np,pandas as pd
from scipy.optimize import minimize
from sklearn.metrics import log_loss,brier_score_loss,roc_auc_score,accuracy_score,mean_absolute_error,mean_squared_error

FEATURES=["weighted_unavailable_minutes_home_minus_away","weighted_absence_impact_positive_home_minus_away"]
CLIP=(1e-6,1-1e-6)
def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def sig(x): return 1/(1+np.exp(-np.clip(x,-40,40)))
def logit(p):
 p=np.clip(p,*CLIP); return np.log(p/(1-p))
def pm(y,p):
 p=np.clip(p,*CLIP); auc=None if len(np.unique(y))<2 else float(roc_auc_score(y,p))
 order=np.argsort(p); ece=0.0
 for idx in np.array_split(order,10):
  if len(idx): ece+=len(idx)/len(y)*abs(float(p[idx].mean())-float(y[idx].mean()))
 x=logit(p)
 def obj(t): return float(log_loss(y,sig(t[0]+t[1]*x),labels=[0,1]))
 r=minimize(obj,np.array([0.,1.]),method='BFGS',options={'maxiter':2000,'gtol':1e-10})
 return {'log_loss':float(log_loss(y,p,labels=[0,1])),'brier_score':float(brier_score_loss(y,p)),'roc_auc':auc,'accuracy':float(accuracy_score(y,p>=.5)),'calibration_intercept':float(r.x[0]) if r.success else None,'calibration_slope':float(r.x[1]) if r.success else None,'expected_calibration_error_10_equal_frequency_bins':float(ece)}
def mm(y,p): return {'mae':float(mean_absolute_error(y,p)),'rmse':float(math.sqrt(mean_squared_error(y,p)))}
def stdize(tr,te):
 a=tr[FEATURES].to_numpy(float); b=te[FEATURES].to_numpy(float); m=a.mean(0); s=a.std(0)
 if np.any(~np.isfinite(s)) or np.any(s<=0): raise ValueError('zero/nonfinite training variance')
 return (a-m)/s,(b-m)/s,m,s
def fit_prob(tr,x,pol):
 y=tr.actual_home_win.to_numpy(int); base=tr.predicted_home_win_probability.to_numpy(float); f=pol['primary_candidate']['fit']; alpha=float(f['l2_alpha'])
 def obj(beta): return float(log_loss(y,sig(logit(base)+x@beta),labels=[0,1])+.5*alpha*np.sum(beta**2))
 r=minimize(obj,np.asarray(f['initial_coefficients'],float),method=f['optimizer'],bounds=[tuple(f['coefficient_bounds'])]*2,options={'maxiter':int(f['maximum_iterations']),'ftol':float(f['tolerance']),'gtol':float(f['tolerance'])})
 if not r.success: raise ValueError('probability optimizer failed: '+str(r.message))
 return r.x,{'success':True,'iterations':int(r.nit),'objective':float(r.fun)}
def fit_margin(tr,x,pol):
 y=tr.actual_home_margin.to_numpy(float); base=tr.predicted_home_margin.to_numpy(float); f=pol['secondary_margin_candidate']; alpha=float(f['l2_alpha'])
 def obj(g):
  e=y-(base+x@g); return float(np.mean(e**2)+.5*alpha*np.sum(g**2))
 r=minimize(obj,np.zeros(2),method=f['optimizer'],bounds=[tuple(f['coefficient_bounds'])]*2,options={'maxiter':2000,'ftol':1e-9,'gtol':1e-9})
 if not r.success: raise ValueError('margin optimizer failed: '+str(r.message))
 return r.x,{'success':True,'iterations':int(r.nit),'objective':float(r.fun)}
def boot(y,b,c,reps,seed):
 rng=np.random.default_rng(seed); b=np.clip(b,*CLIP); c=np.clip(c,*CLIP); n=len(y)
 ld=-(y*np.log(b)+(1-y)*np.log(1-b))+y*np.log(c)+(1-y)*np.log(1-c); bd=(y-b)**2-(y-c)**2
 ls=[]; bs=[]
 for st in range(0,reps,1000):
  idx=rng.integers(0,n,size=(min(1000,reps-st),n)); ls.append(ld[idx].mean(1)); bs.append(bd[idx].mean(1))
 def sm(v):
  v=np.concatenate(v); return {'probability_positive':float(np.mean(v>0)),'mean':float(v.mean()),'interval_80':[float(np.quantile(v,.1)),float(np.quantile(v,.9))],'interval_95':[float(np.quantile(v,.025)),float(np.quantile(v,.975))]}
 return {'log_loss_gain':sm(ls),'brier_gain':sm(bs)}
def cb(x): return '0.75_to_below_0.90' if x<.9 else ('0.90_to_below_1.00' if x<1 else '1.00')
def mb(x): return '60_to_below_120' if x<120 else ('120_to_below_240' if x<240 else '240_plus')
def validate(i,b,p):
 blockers=[]; ri={'historical_game_id','game_date','home_team_abbr','away_team_abbr','matchup_snapshot_complete','matchup_feature_available','minutes_before_tip','minimum_expected_minutes_coverage','source_wave',*FEATURES}; rb={'game_id','game_date','home_team_abbr','away_team_abbr','actual_home_win','actual_home_margin','predicted_home_win_probability','predicted_home_margin'}
 if ri-set(i): blockers.append('missing injury columns')
 if rb-set(b): blockers.append('missing baseline columns')
 if blockers:return pd.DataFrame(),blockers,{}
 i.historical_game_id=i.historical_game_id.astype(str); b.game_id=b.game_id.astype(str)
 if i.historical_game_id.duplicated().any(): blockers.append('duplicate injury game ids')
 if b.game_id.duplicated().any(): blockers.append('duplicate baseline game ids')
 j=i.merge(b,left_on='historical_game_id',right_on='game_id',how='left',suffixes=('_injury','_baseline'),validate='one_to_one')
 bad=((j.game_date_injury!=j.game_date_baseline)|(j.home_team_abbr_injury!=j.home_team_abbr_baseline)|(j.away_team_abbr_injury!=j.away_team_abbr_baseline)).fillna(True)
 if int(bad.sum()): blockers.append(f'game identity mismatches: {int(bad.sum())}')
 j=j.rename(columns={'game_date_injury':'game_date','home_team_abbr_injury':'home_team_abbr','away_team_abbr_injury':'away_team_abbr'})
 pop=p['frozen_population']
 if len(i)!=int(pop['combined_selected_independent_games']): blockers.append('population count mismatch')
 if j.game_id.isna().any(): blockers.append('missing baseline joins')
 if (j.matchup_snapshot_complete!=1).any() or (j.matchup_feature_available!=1).any(): blockers.append('incomplete feature rows')
 if j[FEATURES].isna().any().any(): blockers.append('missing injury feature values')
 if (j.minutes_before_tip<float(pop['minimum_minutes_before_tip'])).any(): blockers.append('T-60 violations')
 if j.game_date.min()!=pop['game_date_start'] or j.game_date.max()!=pop['game_date_end']: blockers.append('date boundary mismatch')
 q={'population_games':len(i),'unique_injury_game_ids':int(i.historical_game_id.nunique()),'baseline_join_games':int(j.game_id.notna().sum()),'game_identity_mismatches':int(bad.sum()),'feature_rows_with_missing_values':int(j[FEATURES].isna().any(axis=1).sum()),'snapshot_rows_before_t60_violations':int((j.minutes_before_tip<float(pop['minimum_minutes_before_tip'])).sum())}
 return j,blockers,q
def run(ip,bp,pp,out):
 p=json.loads(Path(pp).read_text()); i=pd.read_csv(ip,dtype={'historical_game_id':str}); b=pd.read_csv(bp,dtype={'game_id':str}); j,blockers,quality=validate(i,b,p); folds=[]; tests=[]
 if not blockers:
  for f in p['chronological_folds']:
   tr=j[(j.game_date>=f['train_start'])&(j.game_date<=f['train_end'])].copy(); te=j[(j.game_date>=f['test_start'])&(j.game_date<=f['test_end'])].copy()
   if len(tr)!=int(f['expected_train_games']) or len(te)!=int(f['expected_test_games']): blockers.append(f["fold_id"]+' count mismatch'); break
   if set(tr.historical_game_id)&set(te.historical_game_id): blockers.append(f["fold_id"]+' overlap'); break
   xt,xs,m,s=stdize(tr,te); beta,fi=fit_prob(tr,xt,p); gamma,mi=fit_margin(tr,xt,p); bpv=te.predicted_home_win_probability.to_numpy(float); cp=sig(logit(bpv)+xs@beta); bmarg=te.predicted_home_margin.to_numpy(float); cmarg=bmarg+xs@gamma; y=te.actual_home_win.to_numpy(int); ym=te.actual_home_margin.to_numpy(float); bmet=pm(y,bpv); cmet=pm(y,cp)
   q=np.quantile(np.abs(tr[FEATURES[0]].to_numpy(float)),[.25,.5,.75]); a=np.abs(te[FEATURES[0]].to_numpy(float)); ql=np.where(a<=q[0],'q1',np.where(a<=q[1],'q2',np.where(a<=q[2],'q3','q4')))
   t=te[['historical_game_id','actual_home_win','source_wave','minimum_expected_minutes_coverage','minutes_before_tip']].copy(); t['test_fold']=f['fold_id']; t['baseline_probability']=bpv; t['candidate_probability']=cp; t['coverage_band']=t.minimum_expected_minutes_coverage.map(cb); t['minutes_before_tip_band']=t.minutes_before_tip.map(mb); t['training_abs_unavailable_quartile']=ql; tests.append(t)
   folds.append({'fold_id':f['fold_id'],'role':f['role'],'train_games':len(tr),'test_games':len(te),'feature_training_mean':dict(zip(FEATURES,map(float,m))),'feature_training_population_std':dict(zip(FEATURES,map(float,s))),'probability_coefficients':dict(zip(FEATURES,map(float,beta))),'probability_fit':fi,'margin_coefficients':dict(zip(FEATURES,map(float,gamma))),'margin_fit':mi,'baseline':bmet,'candidate':cmet,'log_loss_gain':float(bmet['log_loss']-cmet['log_loss']),'brier_gain':float(bmet['brier_score']-cmet['brier_score']),'baseline_margin':mm(ym,bmarg),'candidate_margin':mm(ym,cmarg),'average_absolute_probability_shift':float(np.mean(abs(cp-bpv))),'maximum_absolute_probability_shift':float(np.max(abs(cp-bpv)))})
 state='STRUCTURAL_BLOCKED'; promotion={}; combined=None; sub=[]
 if not blockers:
  allf=pd.concat(tests,ignore_index=True)
  if len(allf)!=int(p['combined_forward_test_games']) or allf.historical_game_id.duplicated().any(): blockers.append('combined forward integrity failure')
 if not blockers:
  y=allf.actual_home_win.to_numpy(int); bpv=allf.baseline_probability.to_numpy(float); cp=allf.candidate_probability.to_numpy(float); bmet=pm(y,bpv); cmet=pm(y,cp); bo=p['paired_bootstrap']; cbx=boot(y,bpv,cp,int(bo['replicates']),int(bo['seed'])); fin=allf[allf.test_fold=='final_untouched_holdout']; fbx=boot(fin.actual_home_win.to_numpy(int),fin.baseline_probability.to_numpy(float),fin.candidate_probability.to_numpy(float),int(bo['replicates']),int(bo['seed'])); worst=0.; minn=int(p['monitored_subgroups']['minimum_rows_for_safety_gate'])
  for dim in ['source_wave','test_fold','coverage_band','minutes_before_tip_band','training_abs_unavailable_quartile']:
   for val,g in allf.groupby(dim):
    yy=g.actual_home_win.to_numpy(int); bb=g.baseline_probability.to_numpy(float); cc=g.candidate_probability.to_numpy(float); bl=float(log_loss(yy,bb,labels=[0,1])); cl=float(log_loss(yy,cc,labels=[0,1])); eligible=len(g)>=minn; worst=max(worst,cl-bl) if eligible else worst; sub.append({'dimension':dim,'value':str(val),'n':len(g),'baseline_log_loss':bl,'candidate_log_loss':cl,'candidate_minus_baseline_log_loss':cl-bl,'safety_gate_eligible':eligible})
  combined={'games':len(allf),'baseline':bmet,'candidate':cmet,'log_loss_gain':float(bmet['log_loss']-cmet['log_loss']),'brier_gain':float(bmet['brier_score']-cmet['brier_score']),'paired_bootstrap':cbx,'average_absolute_probability_shift':float(np.mean(abs(cp-bpv))),'maximum_absolute_probability_shift':float(np.max(abs(cp-bpv))),'worst_monitored_subgroup_log_loss_degradation':float(worst)}; g=p['promotion_gates']; fm={x['fold_id']:x for x in folds}
  checks={'combined_forward_log_loss_gain':combined['log_loss_gain']>=float(g['minimum_combined_forward_log_loss_gain']),'final_holdout_log_loss_gain':fm['final_untouched_holdout']['log_loss_gain']>float(g['minimum_final_holdout_log_loss_gain']),'development_fold_log_loss_gain':fm['development_forward_1']['log_loss_gain']>=float(g['minimum_development_fold_log_loss_gain']),'combined_forward_brier_gain':combined['brier_gain']>=float(g['minimum_combined_forward_brier_gain']),'final_holdout_brier_gain':fm['final_untouched_holdout']['brier_gain']>=float(g['minimum_final_holdout_brier_gain']),'combined_bootstrap_probability_log_loss_gain_positive':cbx['log_loss_gain']['probability_positive']>=float(g['minimum_combined_bootstrap_probability_log_loss_gain_positive']),'final_bootstrap_probability_log_loss_gain_positive':fbx['log_loss_gain']['probability_positive']>=float(g['minimum_final_holdout_bootstrap_probability_log_loss_gain_positive']),'average_absolute_probability_shift':combined['average_absolute_probability_shift']<=float(g['maximum_average_absolute_probability_shift']),'maximum_single_game_probability_shift':combined['maximum_absolute_probability_shift']<=float(g['maximum_single_game_absolute_probability_shift']),'monitored_subgroup_log_loss_degradation':combined['worst_monitored_subgroup_log_loss_degradation']<=float(g['maximum_monitored_subgroup_log_loss_degradation']),'candidate_coefficients_non_positive':all(v<=1e-12 for x in folds for v in x['probability_coefficients'].values())}; promotion={'checks':checks,'failed':sorted(k for k,v in checks.items() if not v),'all_passed':all(checks.values()),'final_holdout_bootstrap':fbx}; state='HOLDOUT_RESEARCH_PASS' if promotion['all_passed'] else 'VALID_NEGATIVE_RESULT'
 perm=dict(p['post_decision_permissions'].get(state,{})); perm.update({'ready_for_timestamped_odds_execution':False,'ready_for_production_model_training':False,'ready_for_probability_adjustment':False,'ready_for_betting_edge_claim':False,'formal_stake':0})
 report={'schema_version':'injury-feature-walk-forward-holdout-result-v1','generated_at':now(),'policy_schema_version':p['schema_version'],'formal_state':state,'structural':quality,'structural_blockers':blockers,'folds':folds,'combined_forward':combined,'promotion':promotion,'privacy':{'aggregate_only_artifact':True,'game_level_rows_retained':False,'player_level_rows_retained':False,'player_names_retained':False,'injury_reasons_retained':False},'guardrails':{'random_shuffle_used':False,'test_fold_statistics_used_for_standardization':False,'hyperparameter_tuning_performed':False,'market_odds_used':False,'target_game_participation_used_as_feature':False,'post_result_policy_edits':False},'permissions':perm}
 out=Path(out); out.mkdir(parents=True,exist_ok=True); (out/'injury-feature-walk-forward-holdout-v1.json').write_text(json.dumps(report,indent=2)+'\n'); pd.DataFrame(sub).to_csv(out/'injury-feature-walk-forward-holdout-v1-subgroups.csv',index=False); return report
def selftest(policy,out):
 p=json.loads(Path(policy).read_text()); rng=np.random.default_rng(20260718); n=189; x1=rng.normal(0,20,n); x2=rng.normal(0,.3,n); base=np.clip(sig(rng.normal(0,.8,n)),.05,.95); y=rng.binomial(1,sig(logit(base)-.1*(x1-x1.mean())/x1.std())); tr=pd.DataFrame({FEATURES[0]:x1,FEATURES[1]:x2,'actual_home_win':y,'predicted_home_win_probability':base,'actual_home_margin':rng.normal(0,12,n),'predicted_home_margin':rng.normal(0,5,n)}); xt,xs,_,_=stdize(tr.iloc[:124],tr.iloc[124:]); beta,info=fit_prob(tr.iloc[:124],xt,p); assert info['success'] and np.all(beta<=1e-12); Path(out).mkdir(parents=True,exist_ok=True); (Path(out)/'self-test.json').write_text(json.dumps({'success':True,'beta':beta.tolist()},indent=2)+'\n')
def main():
 a=argparse.ArgumentParser(); a.add_argument('--injury-panel',type=Path); a.add_argument('--baseline-predictions',type=Path); a.add_argument('--policy',type=Path,required=True); a.add_argument('--output-dir',type=Path,required=True); a.add_argument('--self-test',action='store_true'); x=a.parse_args()
 if x.self_test:selftest(x.policy,x.output_dir); print('holdout v1 self-test passed'); return
 if not x.injury_panel or not x.baseline_predictions:a.error('--injury-panel and --baseline-predictions required')
 r=run(x.injury_panel,x.baseline_predictions,x.policy,x.output_dir); print(json.dumps({'formal_state':r['formal_state'],'structural_blockers':r['structural_blockers'],'failed_promotion_gates':r.get('promotion',{}).get('failed',[])},indent=2))
if __name__=='__main__':main()
