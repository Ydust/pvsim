from pathlib import Path
import json,numpy as np,pandas as pd
from scipy.stats import pearsonr,spearmanr
O=Path(__file__).resolve().parent;S=O/'Source_Data';checks={}
c=pd.read_csv(S/'Figure1_region_values.csv',dtype={'adcode':str});assert len(c)==369 and c.adcode.is_unique
checks['regions']=369
m=pd.read_csv(S/'Figure1bd_association_metrics.csv')
for row in m.itertuples():
 assert np.isclose(pearsonr(c.ghi_kwh_m2,c[row.yield_field]).statistic,row.pearson_r,atol=1e-14)
 assert np.isclose(spearmanr(c.ghi_kwh_m2,c[row.yield_field]).statistic,row.spearman_rho,atol=1e-14)
checks['figure1_correlations_recomputed']=True
t=pd.read_csv(S/'Figure3_single_coverage_thresholds.csv')
for coverage,expected in [(50,[10.196816564576473,9.79]),(100,[13.50,13.72])]:
 q=t[t.coverage_pct.eq(coverage)].sort_values('progress')
 assert len(q)==11 and np.isclose(q.required_density_gain_pct.iloc[0],expected[0],atol=.005) and np.isclose(q.required_density_gain_pct.iloc[-1],expected[1],atol=.005)
checks['common_start_coverage_thresholds']=True
p=pd.read_csv(S/'Figure5_policy_all369_paired_choices.csv',dtype={'adcode':str})
for key,q in p.groupby(['context','policy']):
 assert len(q)==369 and q.adcode.is_unique
 base=q[['baseline_csi_npv_usd','baseline_single_junction_npv_usd','baseline_tandem_npv_usd']].to_numpy()
 supported=q[['supported_csi_npv_usd','supported_single_junction_npv_usd','supported_tandem_npv_usd']].to_numpy()
 choices=np.array(['no_build','csi','single_junction','tandem'])
 assert np.array_equal(choices[np.c_[np.zeros(369),base].argmax(axis=1)],q.before_choice)
 assert np.array_equal(choices[np.c_[np.zeros(369),supported].argmax(axis=1)],q.after_choice)
 assert np.allclose(q.public_cost_usd,q.direct_support_usd+q.admin_usd)
checks['four_policy_groups_369_each_and_NPV_choice_recomputed']=True
w=pd.read_csv(S/'Figure5_v33_waterfall_display.csv')
for key,q in w.groupby(['candidate','context']):
 net=q[q.response_class.eq('net')].contribution_gwh.sum();parts=q[~q.response_class.eq('net')].contribution_gwh.sum()
 assert np.isclose(net,parts,atol=1e-10),(key,net,parts)
checks['signed_generation_contributions_reconcile']=True
th=pd.read_csv(S/'Figure4_coverage_thresholds.csv');paired=th.pivot(index=['candidate','context','minimum_coverage_pct','lifetime_years'],columns='response_state',values='initial_system_cost_usd_wp')
assert len(th)==656 and len(paired)==328 and paired.notna().all().all()
checks['absolute_and_paired_cost_thresholds']=[656,328]
checks['status']='PASS';(O/'qa/current_consistency.json').write_text(json.dumps(checks,indent=2));print(json.dumps(checks,indent=2))
