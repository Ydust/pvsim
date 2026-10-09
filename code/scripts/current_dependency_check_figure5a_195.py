"""Independent cash-flow recalculation and complete explanation of Figure5a categories."""
from pathlib import Path
import sys,json,hashlib
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve();O=HERE.parents[1] if HERE.parent.name=='code' else HERE.parents[1]/'deliverables/Main_figures_preview_20261008_v23'
sys.path.insert(0,str(O/'code'))
import pandas as pd,numpy as np
from scripts.finance import evaluate,lifecycle
from scripts.cost_paths import capex_and_lcoe,TECHS
from pvsim.economic_priors import CENTRAL_LEARNING_RATES,CENTRAL_CAPEX_FLOORS_USD_W,CENTRAL_BREAKTHROUGH_YEAR,CENTRAL_POST_BREAKTHROUGH_LIFETIME_YR
SD=O/'Source_Data';Q=O/'qa'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for k,v in json.loads((O/'inputs/frozen_dependency_hashes.json').read_text(encoding='utf-8')).items():assert sha(O/k)==v
c=pd.read_csv(O/'inputs/Figure1_region_values.csv',dtype={'adcode':str}).sort_values('adcode').reset_index(drop=True)
states=pd.read_csv(O/'inputs/regional_path_states.csv',dtype={'adcode':str})
def st(s):return states[states.state_id.eq(s)].set_index('adcode').loc[c.adcode]
s=st('single_00');t=st('tandem_00');end=st('single_10')
y=np.c_[s.csi_yield_kwh_kwp,s.candidate_yield_kwh_kwp,t.candidate_yield_kwh_kwp]
reg=json.loads((Q/'Figure4_analysis_register.json').read_text(encoding='utf-8'))
_,cost=capex_and_lcoe({k:1400 for k in TECHS},CENTRAL_LEARNING_RATES,CENTRAL_CAPEX_FLOORS_USD_W,CENTRAL_BREAKTHROUGH_YEAR,CENTRAL_POST_BREAKTHROUGH_LIFETIME_YR,return_capex=True)
base=evaluate(c,y,np.array(reg['density_W_m2']),cost);yt=y.copy();yt[:,1]=end.candidate_yield_kwh_kwp.to_numpy();target=evaluate(c,yt,np.array(reg['density_W_m2']),cost)
src=pd.read_csv(SD/'Figure5_all_four_case_region_decisions.csv',dtype={'adcode':str});src=src[src.candidate.eq('single_junction')&src.context.eq('capacity')].set_index('adcode').loc[c.adcode]
names=np.array(['no_build','csi','single_junction','tandem']);v0=base['npv_cap'];v1=target['npv_cap'];best0=names[np.c_[np.zeros(369),v0].argmax(axis=1)];best1=names[np.c_[np.zeros(369),v1].argmax(axis=1)]
threshold=np.c_[np.zeros(369),v0[:,[0,2]]].max(axis=1);margin=v1[:,1]-threshold
maxerr=float(max(np.max(np.abs(v1[:,1]-src.target_npv.to_numpy())),np.max(np.abs(threshold-src.fixed_target_npv.to_numpy())),np.max(np.abs(v0[:,1]-src.baseline_npv.to_numpy()))))
assert maxerr<1e-8 and np.array_equal(best0,src.baseline_choice) and np.array_equal(best1,src.target_choice)
below=margin<-1e-9;assert np.array_equal(below,~src.target_at_parity) and np.array_equal(below,src.transition_class.eq('remaining_gap'))
assert below.sum()==195 and (best1[below]=='csi').sum()==131 and (best1[below]=='no_build').sum()==64
assert np.all(v1[(best1=='csi'),1]>0) and np.all(v1[best1=='no_build']<0)
costgap=float(target['discounted_cost_kwp'][1]-target['discounted_cost_kwp'][0]);revdiff=reg['prices'][0]*(target['delivered_pv_kwh_kwp'][:,1]-target['delivered_pv_kwh_kwp'][:,0])
assert np.allclose(v1[:,1]-v1[:,0],revdiff-costgap,rtol=0,atol=2e-10)
assert (revdiff[best1=='csi']<costgap).all()
details=c[['adcode','city','province','lat','lon','ghi_kwh_m2']].copy()
details=details.assign(baseline_choice=best0,endpoint_choice=best1,baseline_sj_npv_usd_kwp=v0[:,1],endpoint_sj_npv_usd_kwp=v1[:,1],endpoint_csi_npv_usd_kwp=v1[:,0],endpoint_tandem_npv_usd_kwp=v1[:,2],no_build_npv_usd_kwp=0.,fixed_competition_threshold_npv_usd_kwp=threshold,sj_margin_usd_kwp=margin,sj_margin_pct_initial_system_cost=100*margin/reg['capex2035_usd_kwp'][1],below_threshold=below,source_transition_class=src.transition_class.to_numpy(),reason=np.where(best1=='csi','SJ positive but c-Si NPV higher',np.where(best1=='no_build','All three technology NPVs negative','SJ reaches highest-NPV threshold')),annual_sj_gain_vs_csi_pct=100*(target['annual_delivered'][:,1]/target['annual_delivered'][:,0]-1),discounted_sj_generation_kwh_kwp=target['delivered_pv_kwh_kwp'][:,1],discounted_csi_generation_kwh_kwp=target['delivered_pv_kwh_kwp'][:,0],sj_minus_csi_discounted_revenue_usd_kwp=revdiff,sj_minus_csi_discounted_cost_usd_kwp=costgap)
details.to_csv(SD/'Figure5a_all369_competition_recheck.csv',index=False,encoding='utf-8-sig')
details[below].to_csv(SD/'Figure5a_below_threshold_195_details.csv',index=False,encoding='utf-8-sig')
summary=details[below].groupby(['endpoint_choice','reason']).agg(regions=('adcode','size'),median_shortfall_usd_kwp=('sj_margin_usd_kwp',lambda x:float(np.median(-x)))).reset_index()
summary.to_csv(SD/'Figure5a_195_reason_summary.csv',index=False,encoding='utf-8-sig')
life=[]
for j,name in enumerate(['csi','single_junction','tandem']):
 ef,cf,undisc=lifecycle(reg['baseline_lifetime'][j],reg['degradation'][j],reg['burn_in'][j]);life.append(dict(technology=name,lifetime=reg['baseline_lifetime'][j],degradation=reg['degradation'][j],burn_in=reg['burn_in'][j],discounted_generation_factor=ef,discounted_cost_usd_kwp=float(target['discounted_cost_kwp'][j])))
out=dict(status='PASS',all_regions=369,retained_competitive=163,newly_competitive=11,new_from_csi=7,new_from_no_build=4,endpoint_competitive=174,below_threshold=195,below_because_csi_better_and_sj_profitable=131,below_because_all_technology_npvs_negative=64,maximum_recomputed_NPV_residual=maxerr,smallest_absolute_margin_usd_kwp=float(np.min(np.abs(margin))),classification_tolerance_usd=1e-9,missing_or_nonfinite_NPV=0,sj_lifetime_discounted_generation_below_csi_regions=int((target['delivered_pv_kwh_kwp'][:,1]<target['delivered_pv_kwh_kwp'][:,0]).sum()),sj_discounted_cost_saving_vs_csi_usd_kwp=-costgap,median_shortfall_195_usd_kwp=float(np.median(-margin[below])),lifecycle=life,scope='Existing conditional 2035 author costs, lifetime, retention, replacement and 0.04 USD/kWh capacity electricity value; independent financial re-evaluation from unchanged hourly-yield inputs.',no_new_external_numeric_input=True)
(Q/'Figure5a_195_independent_recheck.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
note=f'''图5a的195个地区逐项核对

分类核对：图a只判断单结/装机路径。全部369地区中，163个原有竞争地区保留，7个从晶硅切换，4个从不建设进入，因此174个达到最高NPV竞争门槛，195个未达到。

195的真实构成：131个单结NPV为正但晶硅NPV更高；64个三种技术NPV均为负，不建设最优。这两类不可都解释为单结项目亏损或光伏项目不可行。叠层不是这些195地区的最优选择。

为什么单结运行改善后仍会落后：当前只改变年度运行响应。单结21.5年寿命、1.505%年衰减、6.75%初损及全系统替换/无残值规则保留；晶硅采用25年、0.5%年衰减、1%初损。以上是作者情景/插值，不是195个地区的实测器件差异。按25年、5%折现，单结与晶硅的发电年因子分别约11.7173、13.3106。模型的369地区中，单结终点的折现生命周期发电量均低于晶硅；年度发电优势不能等同于生命周期收益优势。

与此同时，单结的折现生命周期成本约601.25USD/kWp，晶硅约676.86USD/kWp，单结省约75.61USD/kWp。131个晶硅更优地区中，单结相对晶硅的折现收入损失超过这项成本优势。64个不建设地区中，既定0.04USD/kWh收入不足以覆盖任何候选的折现成本。因此195由运行改善幅度、寿命/衰减/初损、更换支出和电力价值共同决定，不能仅归因于气候或年度发电性能。

从同一上游输入独立重算三个技术的基线和单结终点NPV，并逐地区对照旧源数据、选择、阈值及地图分类。最大NPV残差约{maxerr:.3g}USD/kWp；最接近门槛的地区差约{out['smallest_absolute_margin_usd_kwp']:.4g}USD/kWp，远大于1e-9数值容差，不是显示取整/缺失数据导致的195。原地图与全部数值保持不变。

经济竞争门槛与NPV=0、LCOE/电价平价不同。此次只更新独立图5预览术语，正式正文和SI未改动。全明细包含三技术NPV、获选方案、收入/成本差及分类依据，没有新增外源数值。
'''
(Q/'Figure5a_195_reason_note.txt').write_text(note,encoding='utf-8')
print(json.dumps({k:out[k] for k in ['status','below_threshold','below_because_csi_better_and_sj_profitable','below_because_all_technology_npvs_negative','maximum_recomputed_NPV_residual','sj_discounted_cost_saving_vs_csi_usd_kwp']},ensure_ascii=False),flush=True)
