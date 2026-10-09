"""Reconstruct Figure4 baseline regional gaps without new model inputs."""
from pathlib import Path
import json,hashlib
import numpy as np,pandas as pd
O=Path(__file__).resolve().parent;S=O/'Source_Data';Q=O/'qa'
c=pd.read_csv(O/'inputs/Figure1_region_values.csv',dtype={'adcode':str}).sort_values('adcode').reset_index(drop=True)
r=json.loads((Q/'Figure4_analysis_register.json').read_text());cap=np.array(r['capex2035_usd_kwp']);den=np.array(r['density_W_m2']);names=['csi','single_junction','tandem']
n=pd.read_csv(S/'Figure5_policy_baseline_all_technology_NPV.csv',dtype={'adcode':str});inherited=pd.read_csv(S/'Figure6_regional_classification.csv',dtype={'adcode':str})
rows=[];allg=[];summary=[];sensitivity=[]
for z,ct in enumerate(['capacity','site_area']):
 v=n[n.context.eq(ct)].pivot(index='adcode',columns='technology',values='npv_per_resource').loc[c.adcode,names].to_numpy();win=np.c_[np.zeros(369),v].argmax(axis=1)
 per=den*r['packing']/1000 if z else np.ones(3);cuts=[]
 for j in [1,2]:
  target=np.maximum(0,np.delete(v,j,axis=1).max(axis=1));gap=np.maximum(0,target-v[:,j]);cut=100*gap/(cap[j]*per[j]);cuts.append(cut)
  after=v[:,j]+cap[j]*per[j]*cut/100;assert np.allclose(after,np.maximum(v[:,j],target),rtol=0,atol=1e-9)
  for i,region in c.iterrows():allg.append(dict(adcode=region.adcode,city=region.city,province=region.province,context=ct,candidate=names[j],candidate_npv_per_resource=v[i,j],rival_or_no_build_target=target[i],required_cost_cut_pct=cut[i],initial_cost_at_parity_usd_wp=cap[j]/1000*(1-cut[i]/100),upfront_only=True))
 cuts=np.array(cuts).T;minimum=cuts.min(axis=1)
 for limit in [1,5,10]:
  cl=np.where(win==2,'substitution-favorable',np.where(win==3,'tandem-favorable',np.where(minimum<=limit,'near-transition',np.where(win==1,'c-Si-dominant','entry-limited'))))
  for i,region in c.iterrows():sensitivity.append(dict(adcode=region.adcode,context=ct,cutoff_pct=limit,classification=cl[i]))
  if limit!=5:continue
  q=c[['adcode','city','province']].copy();q['context']=ct;q['minimum_cost_cut_pct']=minimum;q['classification']=cl;q['baseline_choice']=(np.array(['no_build']+names))[win];q['nearest_perovskite']=np.array(names[1:])[cuts.argmin(axis=1)];q['unbuilt_baseline']=win==0
  old=inherited[inherited.context.eq(ct)].set_index('adcode').loc[c.adcode]
  assert np.allclose(old.minimum_cost_cut_pct,minimum,rtol=0,atol=1e-10) and np.array_equal(old.classification,cl) and np.array_equal(old.baseline_choice,q.baseline_choice)
  q=q.sort_values(['minimum_cost_cut_pct','adcode']).reset_index(drop=True);q['cumulative_share_pct']=100*(np.arange(369)+1)/369;q['source_midrank_pct']=100*(np.arange(369)+.5)/369
  assert len(q)==369 and q.adcode.is_unique and q.cumulative_share_pct.iloc[-1]==100
  q.to_csv(S/('Figure4'+['c','d'][z]+'_regional_gaps.csv'),index=False,encoding='utf-8-sig');rows.extend(q.to_dict('records'))
  for k,num in q.classification.value_counts().items():summary.append(dict(context=ct,classification=k,regions=int(num)))
pd.DataFrame(rows).to_csv(S/'Figure4_baseline_regional_gap_classification.csv',index=False,encoding='utf-8-sig')
pd.DataFrame(allg).to_csv(S/'Figure4_baseline_candidate_gaps.csv',index=False,encoding='utf-8-sig')
pd.DataFrame(summary).to_csv(S/'Figure4_baseline_gap_class_counts.csv',index=False,encoding='utf-8-sig')
pd.DataFrame(sensitivity).to_csv(S/'Figure4_gap_cutoff_sensitivity.csv',index=False,encoding='utf-8-sig')
report=dict(status='PASS',regions_per_context=369,regional_gap_records=738,candidate_gap_records=1476,unchanged_Figure6_gap_values_and_classes=True,independent_forward_inverse_check=True,no_policy_in_gap_calculation=True,new_external_numeric_inputs=0,cumulative_share_definition='100*(sorted regional row + 1)/369; tied values stack.',threshold_pct=5,inputs_sha256={str(p.relative_to(O)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in [O/'inputs/Figure1_region_values.csv',Q/'Figure4_analysis_register.json',S/'Figure5_policy_baseline_all_technology_NPV.csv',S/'Figure6_regional_classification.csv']})
(Q/'Figure4_v55_gap_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2))
