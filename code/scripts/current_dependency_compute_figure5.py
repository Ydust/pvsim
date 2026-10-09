"""Paired regional decision consequences; numerical definitions match Figure4."""
from pathlib import Path
import sys,json,hashlib
sys.dont_write_bytecode=True
O=Path(__file__).resolve().parents[1];sys.path.insert(0,str(O/'code'))
import numpy as np,pandas as pd
from scripts.finance import evaluate,lifecycle
from scripts.cost_paths import capex_and_lcoe,TECHS
from pvsim.economic_priors import CENTRAL_LEARNING_RATES,CENTRAL_CAPEX_FLOORS_USD_W,CENTRAL_BREAKTHROUGH_YEAR,CENTRAL_POST_BREAKTHROUGH_LIFETIME_YR
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,x):pd.DataFrame(x).to_csv(O/'Source_Data'/(name+'.csv'),index=False,encoding='utf-8-sig')
for k,v in json.loads((O/'inputs/frozen_dependency_hashes.json').read_text(encoding='utf-8')).items():assert sha(O/k)==v
c=pd.read_csv(O/'inputs/Figure1_region_values.csv',dtype={'adcode':str}).sort_values('adcode').reset_index(drop=True)
path=pd.read_csv(O/'inputs/regional_path_states.csv',dtype={'adcode':str});idx=c.adcode.to_numpy();assert len(c)==369
def state(s):return path[path.state_id.eq(s)].set_index('adcode').loc[idx]
s=state('single_00');t=state('tandem_00');y=np.c_[s.csi_yield_kwh_kwp,s.candidate_yield_kwh_kwp,t.candidate_yield_kwh_kwp]
reg=json.loads((O/'qa/Figure4_analysis_register.json').read_text());d=np.array(reg['density_W_m2']);cap=np.array(reg['capex2035_usd_kwp'])
_,cost=capex_and_lcoe({k:1400 for k in TECHS},CENTRAL_LEARNING_RATES,CENTRAL_CAPEX_FLOORS_USD_W,CENTRAL_BREAKTHROUGH_YEAR,CENTRAL_POST_BREAKTHROUGH_LIFETIME_YR,return_capex=True)
base=evaluate(c,y,d,cost);prior=pd.read_csv(O/'Source_Data/Figure4_paired_region_economic_changes.csv',dtype={'adcode':str})
names=['no_build','csi','single_junction','tandem'];rows=[];summary=[];transitions=[];maxerr=0.;maxidentity=0.;ties=0
for j,tech in [(1,'single'),(2,'tandem')]:
 end=state(tech+'_10').candidate_yield_kwh_kwp.to_numpy();new_y=y.copy();new_y[:,j]=end
 # Only the candidate's response is changed; all rivals and financial inputs are identical.
 changed=evaluate(c,new_y,d,cost)
 for z,ct in enumerate(['capacity','site_area']):
  key='npv_cap' if z==0 else 'npv_area';v0=base[key];v1=changed[key]
  assert np.array_equal(v0[:,[k for k in range(3) if k!=j]],v1[:,[k for k in range(3) if k!=j]])
  rival=np.c_[np.zeros(369),v0[:,[k for k in range(3) if k!=j]]];tar=rival.max(axis=1)
  denom=cap[j]*(1. if z==0 else d[j]*reg['packing']/1000)
  m0=v0[:,j]-tar;m1=v1[:,j]-tar;bm=100*m0/denom;tm=100*m1/denom
  q=prior[prior.candidate.eq(names[j+1])&prior.context.eq(ct)].set_index('adcode').loc[idx]
  err=float(max(np.max(np.abs(v0[:,j]-q.baseline_npv.to_numpy())),np.max(np.abs(v1[:,j]-q.target_npv.to_numpy())),np.max(np.abs(tar-q.fixed_rival_target_npv.to_numpy()))));assert err<1e-8;maxerr=max(maxerr,err)
  identity=100*(q.baseline_cost_boundary_usd_wp.to_numpy()/(cap[j]/1000)-1)
  identity1=100*(q.target_cost_boundary_usd_wp.to_numpy()/(cap[j]/1000)-1)
  ie=float(max(np.max(np.abs(identity-bm)),np.max(np.abs(identity1-tm))));assert ie<1e-10;maxidentity=max(maxidentity,ie)
  p0=q.baseline_at_parity.to_numpy();p1=q.target_at_parity.to_numpy()
  assert np.array_equal(p0,m0>=-1e-9) and np.array_equal(p1,m1>=-1e-9)
  status=np.select([p0&p1,~p0&p1,p0&~p1],['retained','new','lost'],default='remaining_gap')
  choice0=np.array(names)[np.c_[np.zeros(369),v0].argmax(axis=1)];choice1=np.array(names)[np.c_[np.zeros(369),v1].argmax(axis=1)]
  near=(np.abs(m0)<=1e-9)|(np.abs(m1)<=1e-9);ties+=int(near.sum())
  assert np.array_equal(choice0==names[j+1],p0) and np.array_equal(choice1==names[j+1],p1)
  frame=c[['adcode','city','province','lat','lon','ghi_kwh_m2']].copy()
  frame=frame.assign(candidate=names[j+1],context=ct,baseline_npv=v0[:,j],target_npv=v1[:,j],fixed_target_npv=tar,baseline_margin=m0,target_margin=m1,npv_unit='USD/kWp' if z==0 else 'USD/m2 site',normalization_initial_system_expenditure=denom,baseline_margin_pct=bm,target_margin_pct=tm,margin_change_pp=tm-bm,baseline_at_parity=p0,target_at_parity=p1,transition_class=status,baseline_choice=choice0,target_choice=choice1,baseline_tie_or_target_tie=near,display_main=((j==1 and z==0)or(j==2 and z==1)))
  order=frame.sort_values(['baseline_margin_pct','adcode'],kind='stable').adcode.tolist();rank={code:k+1 for k,code in enumerate(order)}
  frame['baseline_rank']=frame.adcode.map(rank);assert sorted(frame.baseline_rank)==list(range(1,370))
  rows.append(frame)
  summary.append(dict(candidate=names[j+1],context=ct,retained=int((status=='retained').sum()),new=int((status=='new').sum()),lost=int((status=='lost').sum()),remaining_gap=int((status=='remaining_gap').sum()),baseline_competitive=int(p0.sum()),target_competitive=int(p1.sum()),declining_margin_regions=int((tm<bm-1e-10).sum()),improving_margin_regions=int((tm>bm+1e-10).sum()),display_main=bool(frame.display_main.iloc[0])))
  tr=frame.groupby(['baseline_choice','target_choice']).size().reset_index(name='regions');tr['candidate']=names[j+1];tr['context']=ct;transitions.append(tr)
allrows=pd.concat(rows,ignore_index=True);assert len(allrows)==1476
save('Figure5_all_four_case_region_decisions',allrows);save('Figure5_transition_summary',summary);save('Figure5_joint_choice_transitions',pd.concat(transitions,ignore_index=True))
save('Figure5_displayed_region_pairs',allrows[allrows.display_main].sort_values(['context','baseline_rank']))
defs=[dict(parameter='baseline/target margin',definition='candidate NPV-max(other2 fixed baseline NPVs,0)',unit='USD/kWp or USD/m2 site',identity='derived model value'),dict(parameter='normalized margin',definition='100*margin/(baseline system CAPEX per comparison unit); excludes the common site charge from denominator',unit='percent of initial system expenditure',identity='author display normalization; not a yield gain'),dict(parameter='baseline rank',definition='ascending baseline normalized margin, stable adcode tie-break; target retains the identical district rank',unit='1..369',identity='deterministic paired display order'),dict(parameter='parity',definition='same Figure4 parity flags; independent NPV tolerance1e-9USD matches all flags',unit='boolean',identity='same economic parity, including ties'),dict(parameter='main cases',definition='SJ/capacity and tandem/site; all4 cases and all369 regions retained in source',unit='case',identity='resource-constrained pathway roles predetermined by research question')]
save('Figure5_derived_display_definitions',defs)
out=dict(status='PASS',regions_per_case=369,all_case_rows=1476,displayed_pairs=738,maximum_Figure4_NPV_residual=maxerr,maximum_boundary_margin_identity_error_pp=maxidentity,near_ties=ties,all_competitive_regions_match_unique_joint_choice=True,no_new_external_inputs=True,baseline_and_target_finance_identical=True,summary=summary)
(O/'qa/Figure5_numerical_checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(pd.DataFrame(summary).to_string(index=False));print('Figure4 NPV residual',maxerr,'identity residual',maxidentity,flush=True)
