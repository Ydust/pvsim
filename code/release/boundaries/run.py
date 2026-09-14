from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[2]));sys.dont_write_bytecode=True
import numpy as np,pandas as pd
from scripts.analyse_regional_policy import load,evaluate,lifecycle,winners
Q=Path(__file__).resolve().parent;S=Q/'deliverables/Source_Data';S.mkdir(parents=True,exist_ok=True)
c,y,d,cost=load();base=evaluate(c,y,d,cost);C=base['initial_cap'];annual=base['annual_delivered'];ix=np.arange(len(c));disc=np.sum(1.05**(-np.arange(1,26)))
dur=[(25,.005,.01),(21.5,.01505,.0675),(25,.012,.04)];fac=np.array([lifecycle(*x) for x in dur]);policies=[('No subsidy',0,np.array([0,0,0.])),('General20',.2,np.array([1,1,1.])),('New20',.2,np.array([0,1,1.]))]
def arrays(om=None,cap=None,td=None):
 cc=C if cap is None else np.asarray(cap);ff=fac.copy()
 if td is not None:ff[2]=lifecycle(*td)
 energy=annual*ff[:,0]
 whole=cc*ff[:,1] if om is None else cc*(ff[:,1]-.015*disc)+np.asarray(om)*disc
 return energy,whole,cc
def portfolio(case,om=None,cap=None,td=None):
 energy,whole,cc=arrays(om,cap,td);out=[]
 for ctx,f,price,land,scale in [('cap',np.ones(3),.04,0,1000),('area',d*.65/1000,.08,25,10000)]:
  npv=(energy*price-whole)*f-land;w0=winners(npv);b=np.maximum(0,npv.max(axis=1))*scale
  eb=np.where(w0>=0,(energy*f)[ix,np.maximum(w0,0)]*scale,0)
  for pol,share,elig in policies:
   tr=cc*share*elig*f;after=npv+tr;w=winners(after);best=np.maximum(0,after.max(axis=1))*scale
   paid=np.where(w>=0,tr[np.maximum(w,0)]*scale,0);ea=np.where(w>=0,(energy*f)[ix,np.maximum(w,0)]*scale,0)
   out.append(dict(case=case,context=ctx,policy=pol,viable=int((w>=0).sum()),si=int((w==0).sum()),sj=int((w==1).sum()),t=int((w==2).sum()),public_usd=paid.sum()*1.05,private_gain_usd=(best-b).sum(),additional_discounted_mwh=(ea-eb).sum()/1000))
 return out
cases=[('Original proportional O&M',None,None),('Common China surveyed O&M 3.2',np.full(3,3.2),None),('Common non-OECD assumed O&M 10.95',np.full(3,10.95),None),('China Si anchor only',None,[591.,C[1],C[2]]),('China Si anchor and common 3.2',np.full(3,3.2),[591.,C[1],C[2]]),('China Si anchor and common 10.95',np.full(3,10.95),[591.,C[1],C[2]])]
rows=[]
for case,om,cap in cases:rows+=portfolio(case,om,cap)
pd.DataFrame(rows).to_csv(S/'Anchored_cost_OM_cases.csv',index=False,encoding='utf-8-sig')
# Reverse feasibility boundaries retain the original baseline and competitors.
# Max degradation: all other candidate inputs fixed, including lifetime and burn-in.
bounds=[];costrows=[]
for ctx,f,price,land in [('cap',np.ones(3),.04,0),('area',d*.65/1000,.08,25)]:
 for pol,share,elig in policies:
  baseline=(base['delivered_pv_kwh_kwp']*price-C*fac[:,1])*f-land+C*f*share*elig
  assert np.allclose(baseline,base['npv_'+ctx]+C*f*share*elig)
  for j,tech in [(1,'SJ'),(2,'T')]:
   competitors=np.maximum(0,np.delete(baseline,j,axis=1).max(axis=1))
   life,centraldeg,burn=dur[j]
   def margin(deg):
    factor=lifecycle(life,deg,burn)[0]
    return (annual[:,j]*factor*price-C[j]*fac[j,1])*f[j]-land+C[j]*f[j]*share*elig[j]-competitors
   lo=np.zeros(len(c));hi=np.full(len(c),.05);m0=margin(0);m5=margin(.05)
   # Vectorised cohort retention and calendar allocation coefficient for each age.
   coefficients=[]
   for age in range(int(np.ceil(life))):
    weights=0.
    for start in np.arange(0,25,life):
     a=start+age;b=min(a+1,start+life,25)
     if a>=b:continue
     for year in range(max(1,int(np.floor(a))+1),min(25,int(np.ceil(b)))+1):
      weights+=max(0,min(b,year)-max(a,year-1))*1.05**(-year)
    coefficients.append(weights*(1-burn))
   def margin_v(deg):
    ef=np.sum(np.array(coefficients)[None,:]*(1-deg[:,None])**np.arange(len(coefficients)),axis=1)
    return (annual[:,j]*ef*price-C[j]*fac[j,1])*f[j]-land+C[j]*f[j]*share*elig[j]-competitors
   assert np.allclose(margin_v(np.full(len(c),centraldeg)),margin(centraldeg))
   for _ in range(45):
    mid=(lo+hi)/2;good=margin_v(mid)>0;lo=np.where(good,mid,lo);hi=np.where(good,hi,mid)
   interior=(m0>0)&(m5<=0);threshold=(lo+hi)/2
   assert np.max(np.abs(margin_v(threshold)[interior]),initial=0)<1e-8
   for i in ix:
    status='never wins at nonnegative degradation' if m0[i]<=0 else ('wins throughout 0-5% range' if m5[i]>0 else 'interior boundary')
    bounds.append(dict(context=ctx,policy=pol,technology=tech,adcode=c.adcode.iloc[i],city=c.city.iloc[i],status=status,max_degradation_fraction=float(threshold[i]) if interior[i] else np.nan,baseline_margin_usd_per_unit=float(margin(centraldeg)[i]),lifetime_years=life,burn_in=burn,central_degradation=centraldeg))
   for dg in [0,.005,.007,.012,.01505,.02,.03]:
    ef=lifecycle(life,dg,burn)[0]
    ceiling=(annual[:,j]*ef*price*f[j]-land-competitors)/(f[j]*(fac[j,1]-share*elig[j]))
    if np.isclose(dg,centraldeg):assert np.array_equal(ceiling>C[j],margin(centraldeg)>0)
    for i in ix:costrows.append(dict(context=ctx,policy=pol,technology=tech,adcode=c.adcode.iloc[i],degradation_fraction=dg,cost_ceiling_usd_kwdc=float(ceiling[i]),central_cost_usd_kwdc=C[j],positive_cost_possible=bool(ceiling[i]>0)))
bd=pd.DataFrame(bounds);bd.to_csv(S/'City_degradation_boundaries.csv',index=False,encoding='utf-8-sig')
cd=pd.DataFrame(costrows);cd.to_csv(S/'City_cost_degradation_boundaries.csv',index=False,encoding='utf-8-sig')
summary=[]
for key,g in bd.groupby(['context','policy','technology']):
 v=g.max_degradation_fraction.dropna()
 summary.append(dict(zip(['context','policy','technology'],key))|dict(interior=int(len(v)),never=int(g.status.str.startswith('never').sum()),above_range=int(g.status.str.startswith('wins').sum()),baseline_wins=int((g.baseline_margin_usd_per_unit>0).sum()),boundary_p10=v.quantile(.1),boundary_median=v.median(),boundary_p90=v.quantile(.9)))
pd.DataFrame(summary).to_csv(S/'Degradation_boundary_summary.csv',index=False,encoding='utf-8-sig')
# Combined O&M x tandem degradation envelope, not an empirical uncertainty distribution.
joint=[]
for om in [None,np.full(3,3.2),np.full(3,10.95)]:
 for deg in [.005,.012,.02]:joint+=portfolio('OM='+('proportional' if om is None else str(om[0]))+';Tdeg='+str(deg),om,td=(25,deg,.04))
pd.DataFrame(joint).to_csv(S/'Joint_OM_tandem_degradation.csv',index=False,encoding='utf-8-sig')
checks={'baseline_boundary_identity':True,'root_residual_tolerance_usd_per_unit':1e-8,'no_extrapolated_boundary_for_censored_cases':True,'boundary_rows':len(bd),'cost_boundary_rows':len(cd),'anchored_cases':len(cases),'joint_cases':9,'currency':'All new scenario monetary inputs explicitly defined as constant 2024 USD. Existing numerical values are assigned this author convention, not presented as inflation-converted historical quotes. Cordell MSP remains an external context reference, not a converted input.','OM_sources':'IRENA 2024 report p100 footnote34:10.95 non-OECD LCOE modelling assumption; p101:China surveyed all-in average3.2. Neither is observed perovskite/tandem O&M. Common rates isolate capex-linked cost scaling.','Si_anchor':'591 USD/kWDC observed2024China benchmark frozen into2035 comparison, NOT future forecast or learning calibration.','boundary_scope':'Each candidate varies alone against fixed other two technology NPVs and zero; fixed lifetime, burn-in, discount, electricity values and baseline proportional O&M; not simultaneous joint optimization.'}
(S/'Round2_definitions.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf8')
print(pd.DataFrame(rows).query("policy=='General20'")[['case','context','si','sj','t','viable']].to_string(index=False));print(pd.DataFrame(summary).to_string(index=False))
