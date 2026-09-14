"""Policy-informed counterfactuals; no claim of nationwide policy eligibility."""
from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[2]));sys.dont_write_bytecode=True
sys.stdout.reconfigure(encoding='utf-8')
import numpy as np,pandas as pd
from scripts.analyse_regional_policy import load,evaluate,winners
Q=Path(__file__).resolve().parent;O=Q/'deliverables';S=O/'Source_Data'
S.mkdir(parents=True,exist_ok=True)
city,y,density,cost=load();ev=evaluate(city,y,density,cost);ix=np.arange(len(city))
old=pd.read_csv('outputs/figure5_integrated_20260906/Figure5b_city_choices.csv',dtype={'adcode':str}).set_index('adcode').loc[city.adcode]
summ=[];details=[];curves=[];baseline=[]
for ctx,scale in [('cap',1000.),('area',10000.)]:
 p=ev['npv_'+ctx]*scale;w=winners(p);before=np.maximum(0,p.max(axis=1))
 assert np.allclose(ev['npv_'+ctx],old[[f'{k}_npv_{ctx}' for k in ['csi','perovskite','tandem']]],atol=1e-9)
 # Construction only: site cost is excluded for every technology.
 capex=ev['initial_cap']*(1 if ctx=='cap' else density*.65/1000)*scale
 energy=ev['delivered_pv_kwh_kwp']*(scale if ctx=='cap' else density*.65/1000*scale)/1000
 eb=np.where(w>=0,energy[ix,np.maximum(w,0)],0)
 for j,tech in enumerate(['Si','SJ','T']):
  baseline.append(pd.DataFrame(dict(context=ctx,adcode=city.adcode,city=city.city,province=city.province,technology=tech,npv_usd=p[:,j],construction_usd=capex[j],discounted_mwh=energy[:,j],selected=(w==j).astype(int))))
 def record(strategy,s,transfer,chosen=None,keep=False):
  pp=p+transfer;v=winners(pp)
  if chosen is not None:assert np.array_equal(v,chosen)
  after=np.maximum(0,pp.max(axis=1));paid=np.where(v>=0,transfer[ix,np.maximum(v,0)],0)
  ea=np.where(v>=0,energy[ix,np.maximum(v,0)],0)
  new=(w<0)&(v>=0);switch=(w>=0)&(v>=0)&(v!=w);same=(w>=0)&(v==w)
  rec=dict(context=ctx,strategy=strategy,share=s,before_viable=int((w>=0).sum()),after_viable=int((v>=0).sum()),new_viable=int(new.sum()),before_si=int((w==0).sum()),after_si=int((v==0).sum()),before_sj=int((w==1).sum()),after_sj=int((v==1).sum()),before_t=int((w==2).sum()),after_t=int((v==2).sum()),switches=int(switch.sum()),before_npv_usd=float(before.sum()),after_npv_usd=float(after.sum()),private_gain_usd=float((after-before).sum()),direct_support_usd=float(paid.sum()),admin_usd=float(paid.sum()*.05),total_public_usd=float(paid.sum()*1.05),additional_discounted_mwh=float((ea-eb).sum()),new_support_usd=float(paid[new].sum()),switch_support_usd=float(paid[switch].sum()),same_support_usd=float(paid[same].sum()))
  assert np.isclose(rec['new_support_usd']+rec['switch_support_usd']+rec['same_support_usd'],paid.sum())
  assert (after>=before-1e-7).all()
  if keep:
   summ.append(rec)
   details.append(pd.DataFrame(dict(context=ctx,strategy=strategy,share=s,adcode=city.adcode,city=city.city,province=city.province,before_choice=w,after_choice=v,before_npv_usd=before,after_npv_usd=after,support_usd=paid,admin_usd=paid*.05,private_gain_usd=after-before,before_discounted_mwh=eb,after_discounted_mwh=ea,additional_discounted_mwh=ea-eb,new_viable=new.astype(int),switch=switch.astype(int),support_si_usd=transfer[:,0],support_sj_usd=transfer[:,1],support_t_usd=transfer[:,2])))
  curves.append(rec)
  return v
 for s in np.linspace(0,.3,301):
  keep=any(np.isclose(s,v) for v in [0,.1,.2,.3])
  general=np.broadcast_to(capex*s,p.shape).copy()
  v=record('General',float(s),general,keep=keep)
  newtech=general.copy();newtech[:,0]=0
  record('New technology',float(s),newtech,keep=keep)
  # Minimum non-negative transfer to reproduce every general-programme choice.
  # USD 1 breaks exact indifference; it is not an empirically validated incentive.
  target=np.zeros_like(p);changed=(v>=0)&(v!=w)
  required=np.maximum(0,before-p[ix,np.maximum(v,0)])
  target[ix[changed],v[changed]]=required[changed]+1.
  assert (target<=general+1e-5).all()
  record('Matched gap',float(s),target,chosen=v,keep=keep)
pd.DataFrame(summ).to_csv(S/'Figure5_policy_summary.csv',index=False)
pd.DataFrame(curves).to_csv(S/'Figure5_policy_curves.csv',index=False)
pd.concat(details,ignore_index=True).to_csv(S/'Figure5_policy_city.csv',index=False)
pd.concat(baseline,ignore_index=True).to_csv(S/'Figure5_baseline_technology.csv',index=False)
checks={'cities':337,'contexts':2,'technologies':3,'shares':[0,.1,.2,.3],'baseline_regression_pass':True,'all_602_general_portfolios_reproduced_by_gap_transfers':True,'construction_denominator':'initial PV system investment, excludes site cost, O&M and future replacements','transfer_timing':'initial investment time; single payment','programme_scope':'counterfactual common eligibility across 337 standardized opportunities; no claim of actual city-level entitlement or future policy','general':'all three technologies','new_technology':'single-junction perovskite and tandem; Si receives zero under this scenario','matched_gap':'exact general-programme city and technology choices; minimum necessary transfers assuming known NPVs and acceptance just above indifference','admin_fraction':.05,'currency':'same model USD price basis as Figure 4; no RMB/USD conversion is needed for dimensionless investment shares','policy_basis':'Beijing 2023 public/park projects up to20% construction; Beijing2026 perovskite/new technologies up to30%; 10% intermediate sensitivity, common20% benchmark isolates eligibility; no universal actual entitlement'}
(Q/'checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
print(pd.DataFrame(summ).query('share > 0')[['context','strategy','share','after_viable','after_si','after_sj','after_t','total_public_usd','private_gain_usd','additional_discounted_mwh']].to_string(index=False))
