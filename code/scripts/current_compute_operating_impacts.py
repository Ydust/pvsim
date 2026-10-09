"""Derive paired gaps and selected-portfolio energy from current common-start states."""
from pathlib import Path
import sys,json,hashlib
sys.dont_write_bytecode=True
O=Path(__file__).resolve().parent;SD=O/'Source_Data';Q=O/'qa'
sys.path.insert(0,str(O/'code'))
import numpy as np,pandas as pd
from scripts.finance import lifecycle
reg=json.loads((Q/'Figure4_analysis_register.json').read_text(encoding='utf-8'))
city=pd.read_csv(O/'inputs/Figure1_region_values.csv',dtype={'adcode':str}).sort_values('adcode').reset_index(drop=True)
states=pd.read_csv(O/'inputs/regional_path_states.csv',dtype={'adcode':str})
def state(key):
 z=states[states.state_id.eq(key)].set_index('adcode').loc[city.adcode].reset_index()
 assert len(z)==369 and z.adcode.is_unique
 return z
s=state('single_00');t=state('tandem_00')
y0=np.c_[s.csi_yield_kwh_kwp,s.candidate_yield_kwh_kwp,t.candidate_yield_kwh_kwp]
assert np.allclose(s.csi_yield_kwh_kwp,t.csi_yield_kwh_kwp,atol=1e-10,rtol=0)
cap=np.array(reg['capex2035_usd_kwp']);den=np.array(reg['density_W_m2'])
factors=np.array([lifecycle(reg['baseline_lifetime'][i],reg['degradation'][i],reg['burn_in'][i],reg['discount_rate'],reg['horizon']) for i in range(3)])
u=city.utilization_low.to_numpy();packing=reg['packing']
techs=['csi','single_junction','tandem'];choices=np.array(['no_build',*techs])
base=pd.read_csv(SD/'Figure5_policy_baseline_all_technology_NPV.csv',dtype={'adcode':str})
previous=pd.read_csv(SD/'Figure5_all_four_case_region_decisions.csv',dtype={'adcode':str})
fig4=pd.read_csv(SD/'Figure4_paired_region_economic_changes.csv',dtype={'adcode':str})
oldg=pd.read_csv(SD/'Figure5_regional_competitiveness_gaps.csv',dtype={'adcode':str})
gaprows=[];impactrows=[];summary=[];decomp=[];residuals=[]
for candidate,sid,j in [('single_junction','single_10',1),('tandem','tandem_10',2)]:
 endpoint=state(sid);y1=y0.copy();y1[:,j]=endpoint.candidate_yield_kwh_kwp
 assert np.allclose(endpoint.density_W_m2,den[j],rtol=0,atol=1e-9)
 e0=y0*u[:,None]*factors[:,0];e1=y1*u[:,None]*factors[:,0]
 for ct,scale,price,unit in [('capacity',1000.,reg['prices'][0],'USD/kWp'),('site_area',10000.,reg['prices'][1],'USD/m2')]:
  per=np.ones(3) if ct=='capacity' else den*packing/1000
  n0=(e0*price-cap*factors[:,1])*per-(reg['site_charge'] if ct=='site_area' else 0)
  n1=(e1*price-cap*factors[:,1])*per-(reg['site_charge'] if ct=='site_area' else 0)
  v0=base[base.context.eq(ct)].pivot(index='adcode',columns='technology',values='npv_per_resource').loc[city.adcode,techs].to_numpy()
  residuals.append(float(np.max(np.abs(n0-v0))))
  assert np.allclose(n0,v0,rtol=0,atol=1e-9)
  old=previous[previous.candidate.eq(candidate)&previous.context.eq(ct)].set_index('adcode').loc[city.adcode]
  f4=fig4[fig4.candidate.eq(candidate)&fig4.context.eq(ct)].set_index('adcode').loc[city.adcode]
  assert np.allclose(n0[:,j],old.baseline_npv,atol=1e-9,rtol=0) and np.allclose(n1[:,j],old.target_npv,atol=1e-9,rtol=0)
  assert np.allclose(n1[:,j],f4.target_npv,atol=1e-9,rtol=0)
  before=choices[np.c_[np.zeros(369),n0].argmax(axis=1)];after=choices[np.c_[np.zeros(369),n1].argmax(axis=1)]
  assert np.array_equal(before,old.baseline_choice) and np.array_equal(after,old.target_choice)
  response=np.select([(before=='no_build')&(after!='no_build'),(before!='no_build')&(after=='no_build'),(before!='no_build')&(after!='no_build')&(before!=after)],['entry','exit','switch'],default='unchanged')
  E0=np.c_[np.zeros(369),e0*per*scale];E1=np.c_[np.zeros(369),e1*per*scale]
  bidx=np.c_[np.zeros(369),n0].argmax(axis=1);aidx=np.c_[np.zeros(369),n1].argmax(axis=1)
  selected0=E0[np.arange(369),bidx];selected1=E1[np.arange(369),aidx];delta=selected1-selected0
  rivals=np.maximum(0,np.delete(n0,j,axis=1).max(axis=1))*scale
  initial=cap[j]*per[j]*scale
  for st,n in [('baseline',n0),('endpoint',n1)]:
   g=np.maximum(0,rivals-n[:,j]*scale);cut=100*g/initial
   if st=='baseline':
    og=oldg[oldg.context.eq(ct)&oldg.candidate.eq(candidate)].set_index('adcode').loc[city.adcode]
    assert np.allclose(cut,og.upfront_only_reduction_for_parity_pct,rtol=0,atol=1e-9)
   for i,row in city.iterrows():
    gaprows.append(dict(adcode=row.adcode,city=row.city,province=row.province,candidate=candidate,context=ct,response_state=st,
     candidate_npv_usd=n[i,j]*scale,fixed_rival_or_no_build_npv_usd=rivals[i],initial_system_capex_usd=initial,
     npv_gap_usd=g[i],required_upfront_cut_pct=cut[i],at_parity=cut[i]<1e-9,parity_at_nonnegative_upfront_cost=cut[i]<=100,
     forward_at_required_cut_npv_usd=n[i,j]*scale+g[i]))
  for i,row in city.iterrows():
   impactrows.append(dict(adcode=row.adcode,city=row.city,province=row.province,candidate=candidate,context=ct,
    baseline_state='single_00 / tandem_00',endpoint_state=sid,opportunity_scale=scale,opportunity_unit='kWp' if ct=='capacity' else 'm2',
    before_choice=before[i],after_choice=after[i],response_class=response[i],
    baseline_candidate_npv_per_resource=n0[i,j],endpoint_candidate_npv_per_resource=n1[i,j],npv_unit=unit,
    baseline_selected_discounted_generation_kwh=selected0[i],endpoint_selected_discounted_generation_kwh=selected1[i],
    net_discounted_generation_kwh=delta[i],candidate_discounted_generation_change_kwh=(e1[i,j]-e0[i,j])*per[j]*scale))
  sr=dict(candidate=candidate,context=ct,regions=369,baseline_built=int((before!='no_build').sum()),endpoint_built=int((after!='no_build').sum()),
   baseline_parity=int((n0[:,j]*scale>=rivals-1e-8).sum()),endpoint_parity=int((n1[:,j]*scale>=rivals-1e-8).sum()),
   candidate_npv_decrease=int((n1[:,j]<n0[:,j]-1e-9).sum()),
   net_discounted_generation_kwh=float(delta.sum()),positive_generation_change_kwh=float(delta[delta>0].sum()),negative_generation_change_kwh=float(delta[delta<0].sum()))
  for cls in ['entry','switch','unchanged','exit']:
   mask=response==cls;sr[cls]=int(mask.sum());sr[cls+'_discounted_generation_kwh']=float(delta[mask].sum())
   decomp.append(dict(candidate=candidate,context=ct,response_class=cls,regions=int(mask.sum()),
    net_discounted_generation_kwh=float(delta[mask].sum()),positive_generation_change_kwh=float(delta[mask&(delta>0)].sum()),negative_generation_change_kwh=float(delta[mask&(delta<0)].sum())))
  assert sum(sr[c] for c in ['entry','switch','unchanged','exit'])==369
  assert np.isclose(sum(sr[c+'_discounted_generation_kwh'] for c in ['entry','switch','unchanged','exit']),delta.sum(),atol=1e-5,rtol=0)
  summary.append(sr)
for name,rows in [('Figure5_path_gap_comparison',gaprows),('Figure5_operating_path_region_impacts',impactrows),('Figure5_operating_path_summary',summary),('Figure5_operating_path_response_decomposition',decomp)]:
 pd.DataFrame(rows).to_csv(SD/(name+'.csv'),index=False,encoding='utf-8-sig')
expected=[(4,7,358,0),(0,0,369,0),(0,0,369,0),(0,80,289,0)]
assert [tuple(r[c] for c in ['entry','switch','unchanged','exit']) for r in summary]==expected
prov=[dict(derived_output='Paired initial-CAPEX gap',formula='100*max(0,max(0,fixed rival NPVs)-candidate NPV)/candidate initial system CAPEX',
 upstream_numeric_locator='Source_Data/Figure4_paired_region_economic_changes.csv: baseline_npv,target_npv,fixed_rival_target_npv; qa/Figure4_analysis_register.json: capex2035_usd_kwp,density_W_m2,packing'),
 dict(derived_output='Selected-portfolio discounted generation',formula='state yield * utilization_low * lifecycle energy factor * resource multiplier * opportunity scale; then endpoint selected minus baseline selected',
 upstream_numeric_locator='inputs/regional_path_states.csv: single_00,single_10,tandem_00,tandem_10; inputs/Figure1_region_values.csv: utilization_low; code/scripts/finance.py:lifecycle; qa/Figure4_analysis_register.json: all financial/durability values'),
 dict(derived_output='Entry/switch/unchanged/exit',formula='Argmax over no-build=0 and three current NPV alternatives, independently changing one candidate response',
 upstream_numeric_locator='Source_Data/Figure5_policy_baseline_all_technology_NPV.csv; Source_Data/Figure4_paired_region_economic_changes.csv; inherited Source_Data/Figure5_all_four_case_region_decisions.csv cross-check'),
 dict(derived_output='External numerical provenance unchanged',formula='No new external numeric inputs; model-derived quantities do not require an external source reporting the same value',
 upstream_numeric_locator='sources/physical_provenance/active_parameter_numeric_provenance.csv; sources/physical_provenance/external_numeric_source_index.csv; Source_Data/Numeric_parameter_scope_and_locator_resolution.csv; Source_Data/Figure4_financial_parameter_identities.csv; Source_Data/Figure5_policy_parameter_identities.csv; inputs/frozen_dependency_hashes.json')]
pd.DataFrame(prov).to_csv(SD/'Figure5_v31_derivation_register.csv',index=False,encoding='utf-8-sig')
checks=dict(status='PASS',rows_gap=len(gaprows),rows_impacts=len(impactrows),all_regions_per_group=369,max_npv_residual=max(residuals),
 inherited_Fig4_and_Fig5_choices_match=True,new_external_numeric_inputs=0,independent_candidate_paths=True,all_costs_and_durability_fixed=True,
 formula_forward_checks=True,entry_switch_unchanged_exit=expected,summary=summary)
(Q/'Figure5_v31_numerical_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
print(pd.DataFrame(summary).to_string(index=False))
