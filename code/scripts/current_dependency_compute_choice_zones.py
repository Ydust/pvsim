"""Regional NPV-maximizing choices on the existing Figure4 scan, no new external inputs."""
from pathlib import Path
import sys,json,hashlib
sys.dont_write_bytecode=True
O=Path(__file__).resolve().parents[1];sys.path.insert(0,str(O/'code'))
import numpy as np,pandas as pd
from scripts.finance import lifecycle
SD=O/'Source_Data';Q=O/'qa'
reg=json.loads((Q/'Figure4_analysis_register.json').read_text(encoding='utf-8'))
city=pd.read_csv(O/'inputs/Figure1_region_values.csv',dtype={'adcode':str}).sort_values('adcode').reset_index(drop=True)
states=pd.read_csv(O/'inputs/regional_path_states.csv',dtype={'adcode':str})
def state(s):
 t=states[states.state_id.eq(s)].set_index('adcode').loc[city.adcode]
 assert len(t)==369 and t.index.is_unique
 return t
s=state('single_00');t=state('tandem_00')
ys=np.c_[s.csi_yield_kwh_kwp,s.candidate_yield_kwh_kwp,t.candidate_yield_kwh_kwp]
assert np.allclose(s.csi_yield_kwh_kwp,t.csi_yield_kwh_kwp,rtol=0,atol=1e-10)
base=pd.read_csv(SD/'Figure5_policy_baseline_all_technology_NPV.csv',dtype={'adcode':str})
grid=pd.read_csv(SD/'Figure4_national_coverage_grid.csv')
front=pd.read_csv(SD/'Figure4_common_start_frontiers.csv',dtype={'adcode':str})
techs=['csi','single_junction','tandem'];names=['no_build',*techs]
cap=np.array(reg['capex2035_usd_kwp']);den=np.array(reg['density_W_m2']);u=city.utilization_low.to_numpy()
lives=np.sort(grid.lifetime_years.unique());assert len(lives)==41
baseline_factors=np.array([lifecycle(reg['baseline_lifetime'][j],reg['degradation'][j],reg['burn_in'][j],reg['discount_rate'],reg['horizon']) for j in range(3)])
winner=np.empty((2,2,2,41,201,369),dtype=np.uint8);cost_axes=[];rows=[];checks=[];tie_total=0
contexts=['capacity','site_area'];responses=['baseline','target']
for ci,j in enumerate([1,2]):
 candidate=techs[j];price_grid=np.sort(grid[grid.candidate.eq(candidate)].initial_system_cost_usd_wp.unique());assert len(price_grid)==201;cost_axes.append(price_grid)
 for z,ct in enumerate(contexts):
  price=reg['prices'][z];per=np.ones(3) if z==0 else den*reg['packing']/1000;fee=0 if z==0 else reg['site_charge']
  n0=(ys*u[:,None]*baseline_factors[:,0]*price-cap*baseline_factors[:,1])*per-fee
  observed=base[base.context.eq(ct)].pivot(index='adcode',columns='technology',values='npv_per_resource').loc[city.adcode,techs].to_numpy()
  assert np.allclose(n0,observed,rtol=0,atol=1e-9)
  baseline_res=float(np.max(np.abs(n0-observed)))
  rivals=np.delete(n0,j,axis=1);target=np.maximum(0,rivals.max(axis=1))
  for ri,response in enumerate(responses):
   yy=ys[:,j] if ri==0 else state(['single_10','tandem_10'][ci]).candidate_yield_kwh_kwp.to_numpy()
   for li,life in enumerate(lives):
    ef,cf,_=lifecycle(life,reg['degradation'][j],reg['burn_in'][j],reg['discount_rate'],reg['horizon'])
    at0=(yy*u*ef*price-cap[j]*(cf-1))*per[j]-fee
    candidate_npv=at0[None,:]-1000*price_grid[:,None]*per[j]
    scores=np.broadcast_to(np.c_[np.zeros(369),n0],(201,369,4)).copy();scores[:,:,j+1]=candidate_npv
    w=scores.argmax(axis=2);winner[ci,z,ri,li]=w
    maximum=scores.max(axis=2);ties=(np.abs(scores-maximum[:,:,None])<=1e-10).sum(axis=2)>1;tie_total+=int(ties.sum())
    counts=np.stack([(w==k).sum(axis=1) for k in range(4)],axis=1)
    assert (counts.sum(axis=1)==369).all()
    majority=np.where(counts.max(axis=1)>369/2,counts.argmax(axis=1),4)
    parity=(candidate_npv>=target[None,:]-1e-9).sum(axis=1)/369*100
    old=grid[grid.candidate.eq(candidate)&grid.context.eq(ct)&grid.response_state.eq(response)&grid.lifetime_years.eq(life)].sort_values('initial_system_cost_usd_wp')
    assert len(old)==201 and np.allclose(old.initial_system_cost_usd_wp,price_grid,rtol=0,atol=1e-14)
    assert np.allclose(old.coverage_pct,parity,rtol=0,atol=1e-9)
    numeric_boundary=(at0-target)/(1000*per[j])
    oldfront=front[front.candidate.eq(candidate)&front.context.eq(ct)&front.response_state.eq(response)&front.lifetime_years.eq(life)].set_index('adcode').loc[city.adcode]
    assert np.allclose(numeric_boundary,oldfront.parity_initial_cost_usd_wp,rtol=0,atol=1e-10)
    for k,cost in enumerate(price_grid):
     rows.append(dict(candidate=candidate,context=ct,response_state=response,lifetime_years=life,initial_system_cost_usd_wp=cost,
      no_build_regions=int(counts[k,0]),csi_regions=int(counts[k,1]),single_junction_regions=int(counts[k,2]),tandem_regions=int(counts[k,3]),
      majority_category=int(majority[k]),majority_choice=(names+['mixed'])[majority[k]],largest_choice_share_pct=float(counts[k].max()/369*100),candidate_parity_coverage_pct=float(parity[k])))
   checks.append(dict(candidate=candidate,context=ct,response_state=response,max_baseline_npv_residual=baseline_res,all_8241_grid_coverages_match=True,all_15129_frontier_values_match=True))
out=pd.DataFrame(rows);out.to_csv(SD/'Figure4_regional_choice_zones.csv',index=False,encoding='utf-8-sig')
np.savez_compressed(SD/'Figure4_all_regional_choices.npz',winner=winner,adcode=city.adcode.to_numpy(dtype='U'),lifetime_years=lives,initial_cost_usd_wp=np.array(cost_axes),candidate=np.array(techs[1:]),context=np.array(contexts),response_state=np.array(responses),choice=np.array(names))
provenance=[dict(derived_quantity='Regional NPV choices',formula='argmax(0,NPV_cSi,NPV_SJ,NPV_Tandem); existing order resolves ties',numeric_locator='inputs/regional_path_states.csv: single_00,tandem_00,single_10,tandem_10; inputs/Figure1_region_values.csv: utilization_low; qa/Figure4_analysis_register.json: all cost/durability/resource parameters; code/scripts/finance.py:lifecycle',identity='Model-derived; no new external numeric inputs'),
 dict(derived_quantity='Majority partition',formula='category k if regional choice count(k)>369/2; Mixed otherwise',numeric_locator='Source_Data/Figure4_regional_choice_zones.csv: *_regions,majority_category; Figure4_all_regional_choices.npz: every 369-region choice',identity='Author display rule; not empirical adoption or welfare optimum'),
 dict(derived_quantity='Original parity curves retained',formula='candidate NPV >= max(0, rival NPVs)',numeric_locator='Source_Data/Figure4_coverage_thresholds.csv; Figure4_national_coverage_grid.csv; Figure4_common_start_frontiers.csv',identity='Inherited numerical values; all grid cells and frontiers checked'),
 dict(derived_quantity='External inputs and author assumptions',formula='Unchanged existing model inputs and lifecycle assumptions',numeric_locator='Source_Data/Figure4_financial_parameter_identities.csv; Source_Data/Numeric_parameter_scope_and_locator_resolution.csv; sources/physical_provenance/active_parameter_numeric_provenance.csv; external_numeric_source_index.csv',identity='Source identities inherited; reasonable author scenarios not relabelled as observations')]
pd.DataFrame(provenance).to_csv(SD/'Figure4_choice_zone_derivation_register.csv',index=False,encoding='utf-8-sig')
input_names=['inputs/Figure1_region_values.csv','inputs/regional_path_states.csv','qa/Figure4_analysis_register.json','Source_Data/Figure5_policy_baseline_all_technology_NPV.csv','Source_Data/Figure4_national_coverage_grid.csv','Source_Data/Figure4_common_start_frontiers.csv','Source_Data/Figure4_coverage_thresholds.csv','code/scripts/finance.py']
report={'status':'PASS','regions':369,'excluded_regions':0,'new_external_numeric_inputs':0,'choice_cells':int(winner.size),'choice_shape':list(winner.shape),'summary_rows':len(out),'grid_checks':checks,'near_ties_1e_minus10':tie_total,'tie_rule':'Existing argmax order: no_build,csi,single_junction,tandem','majority_rule':'Strictly >50%; Mixed otherwise','baseline_zone_cell_counts':out[out.response_state.eq('baseline')].groupby(['candidate','context','majority_choice']).size().rename('cells').reset_index().to_dict('records'),'inputs_sha256':{p:hashlib.sha256((O/p).read_bytes()).hexdigest() for p in input_names}}
(Q/'Figure4_v50_numerical_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:report[k] for k in ['status','choice_cells','summary_rows','near_ties_1e_minus10','baseline_zone_cell_counts']},ensure_ascii=False,indent=2),flush=True)
