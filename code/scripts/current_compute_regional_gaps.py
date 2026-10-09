"""Reconstruct all regional upfront-only gaps from current common-start inputs."""
from pathlib import Path
import sys,json,hashlib
sys.dont_write_bytecode=True
O=Path(__file__).resolve().parent;SD=O/'Source_Data';Q=O/'qa'
sys.path.insert(0,str(O/'code'))
import numpy as np,pandas as pd
from scripts.finance import evaluate,lifecycle
from scripts.cost_paths import capex_and_lcoe,TECHS
from pvsim.economic_priors import CENTRAL_LEARNING_RATES,CENTRAL_CAPEX_FLOORS_USD_W,CENTRAL_BREAKTHROUGH_YEAR,CENTRAL_POST_BREAKTHROUGH_LIFETIME_YR
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for k,v in json.loads((O/'inputs/frozen_dependency_hashes.json').read_text()).items():assert sha(O/k)==v
c=pd.read_csv(O/'inputs/Figure1_region_values.csv',dtype={'adcode':str}).sort_values('adcode').reset_index(drop=True)
st=pd.read_csv(O/'inputs/regional_path_states.csv',dtype={'adcode':str})
def state(k):return st[st.state_id.eq(k)].set_index('adcode').loc[c.adcode]
s=state('single_00');t=state('tandem_00')
y=np.c_[s.csi_yield_kwh_kwp,s.candidate_yield_kwh_kwp,t.candidate_yield_kwh_kwp]
reg=json.loads((Q/'Figure4_analysis_register.json').read_text())
_,cost=capex_and_lcoe({k:1400 for k in TECHS},CENTRAL_LEARNING_RATES,CENTRAL_CAPEX_FLOORS_USD_W,CENTRAL_BREAKTHROUGH_YEAR,CENTRAL_POST_BREAKTHROUGH_LIFETIME_YR,return_capex=True)
ev=evaluate(c,y,np.array(reg['density_W_m2']),cost)
names=['csi','single_junction','tandem'];rows=[];summary=[];sensitivity=[];residual=[];reverse=[]
base=pd.read_csv(SD/'Figure5_policy_baseline_all_technology_NPV.csv',dtype={'adcode':str})
for ct in ['capacity','site_area']:
 area=ct=='site_area';scale=10000 if area else 1000
 v=ev['npv_area' if area else 'npv_cap']
 ref=base[base.context.eq(ct)].pivot(index='adcode',columns='technology',values='npv_per_resource').loc[c.adcode,names].to_numpy()
 residual.append(float(np.max(np.abs(v-ref))));assert np.allclose(v,ref,rtol=0,atol=1e-10)
 for j in [1,2]:
  target=np.c_[np.zeros(369),v[:,[k for k in range(3) if k!=j]]].max(axis=1)
  unit=ev['density'][j]*ev['packing']/1000 if area else 1.
  upfront=ev['initial_cap'][j]*unit
  gap=np.maximum(0,target-v[:,j]);cut=100*gap/upfront
  # Independent forward evaluation: reconstruct revenue and ongoing expenditure,
  # change only the initial payment, and leave all later payments at baseline.
  revenue=ev['delivered_pv_kwh_kwp'][:,j]*reg['prices'][int(area)]*unit
  later=(ev['discounted_cost_kwp'][j]-ev['initial_cap'][j])*unit
  newupfront=upfront*(1-cut/100)
  after=revenue-later-newupfront-(reg['site_charge'] if area else 0)
  reverse.append(float(np.max(np.abs(after-np.maximum(v[:,j],target)))))
  cls=np.where(cut<=1e-9,'at_parity',np.where(cut<=5,'small_gap','remaining_gap'))
  for i,r in c.iterrows():
   rows.append(dict(adcode=r.adcode,city=r.city,province=r.province,context=ct,candidate=names[j],
    baseline_candidate_npv_usd=float(v[i,j]*scale),fixed_rival_or_no_build_npv_usd=float(target[i]*scale),
    npv_gap_usd=float(gap[i]*scale),initial_system_capex_usd=float(upfront*scale),
    upfront_only_reduction_for_parity_pct=float(cut[i]),gap_class=cls[i],
    parity_at_nonnegative_upfront_cost=bool(cut[i]<=100),
    forward_at_required_cut_npv_usd=float(after[i]*scale)))
  losing=cut>1e-9
  summary.append(dict(context=ct,candidate=names[j],regions=369,at_parity=int((cls=='at_parity').sum()),
   small_gap=int((cls=='small_gap').sum()),remaining_gap=int((cls=='remaining_gap').sum()),
   median_cut_among_losing_pct=float(np.median(cut[losing])),max_cut_pct=float(cut.max()),above100_count=int((cut>100).sum())))
  for limit in [1.,5.,10.]:sensitivity.append(dict(context=ct,candidate=names[j],descriptive_threshold_pct=limit,
   at_parity=int((~losing).sum()),small_gap=int((losing&(cut<=limit)).sum()),remaining_gap=int((cut>limit).sum())))
assert len(rows)==1476 and max(reverse)<1e-8
for name,data in [('Figure5_regional_competitiveness_gaps',rows),('Figure5_regional_gap_summary',summary),('Figure5_regional_gap_threshold_sensitivity',sensitivity)]:
 pd.DataFrame(data).to_csv(SD/(name+'.csv'),index=False,encoding='utf-8-sig')
paired=pd.read_csv(SD/'Figure5_policy_all369_paired_choices.csv',dtype={'adcode':str})
bridge=pd.DataFrame(rows).merge(paired[['adcode','context','policy','before_choice','after_choice','response_class','public_cost_usd','discounted_generation_change_kwh']],on=['adcode','context'],validate='many_to_many')
assert len(bridge)==2952 and not bridge.duplicated(['adcode','context','candidate','policy']).any()
bridge.to_csv(SD/'Figure5_regional_gap_policy_bridge.csv',index=False,encoding='utf-8-sig')
identities=[dict(parameter='descriptive_near_threshold',value=5,unit='percent of initial system CAPEX',identity='Author descriptive classification; not external empirical input',numeric_locator='figure5_contract.json:gap_definition; compute_regional_gaps.py: cls; threshold sensitivity 1/5/10'),
 dict(parameter='gap_denominator',value='candidate initial system CAPEX',unit='USD per standardized opportunity',identity='Derived from current common financial baseline',numeric_locator='qa/Figure4_analysis_register.json:capex2035_usd_kwp,density_W_m2,packing; code/scripts/finance.py:evaluate'),
 dict(parameter='gap_target',value='max(0,NPV_other1,NPV_other2)',unit='USD per standardized opportunity',identity='Decision definition',numeric_locator='Source_Data/Figure5_policy_baseline_all_technology_NPV.csv; compute_regional_gaps.py:target')]
pd.DataFrame(identities).to_csv(SD/'Figure5_regional_gap_parameter_identities.csv',index=False,encoding='utf-8-sig')
inputs={str(p.relative_to(O)).replace('\\','/'):sha(p) for p in [O/'inputs/Figure1_region_values.csv',O/'inputs/regional_path_states.csv',O/'code/scripts/finance.py',O/'code/scripts/cost_paths.py',SD/'Figure5_policy_baseline_all_technology_NPV.csv',Q/'Figure4_analysis_register.json']}
(Q/'Figure5_regional_gap_checks.json').write_text(json.dumps(dict(status='PASS',rows=1476,regions_per_group=369,baseline_reconstruction_max_residual_per_resource=max(residual),reverse_cost_max_residual_per_resource=max(reverse),upstream_hashes=inputs,summary=summary,new_external_numeric_inputs=0,ongoing_costs_fixed=True,policy_threshold_not_equated_to_gap=True),ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
