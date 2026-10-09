"""Common-start Figure4 inversion; rivals and all financial assumptions fixed."""
from pathlib import Path
import sys,json,hashlib,math
sys.dont_write_bytecode=True
O=Path(__file__).resolve().parents[1];sys.path.insert(0,str(O/'code'))
import numpy as np,pandas as pd
from scripts.finance import evaluate,lifecycle
from scripts.cost_paths import capex_and_lcoe,TECHS,YEARS
from pvsim.economic_priors import CENTRAL_LEARNING_RATES,CENTRAL_CAPEX_FLOORS_USD_W,CENTRAL_BREAKTHROUGH_YEAR,CENTRAL_POST_BREAKTHROUGH_LIFETIME_YR
from pvsim.economics import perovskite_durability
I=O/'inputs';SD=O/'Source_Data';Q=O/'qa'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,x):pd.DataFrame(x).to_csv(SD/(name+'.csv'),index=False,encoding='utf-8-sig')
def js(name,x):(Q/name).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
assert all(sha(O/k)==v for k,v in json.loads((I/'frozen_dependency_hashes.json').read_text(encoding='utf-8')).items())
c=pd.read_csv(I/'Figure1_region_values.csv',dtype={'adcode':str}).sort_values('adcode').reset_index(drop=True)
p=pd.read_csv(I/'regional_path_states.csv',dtype={'adcode':str});n=len(c);idx=c.adcode.to_numpy();assert n==369 and c.adcode.is_unique
def state(s):return p[p.state_id.eq(s)].set_index('adcode').loc[idx]
s=state('single_00');t=state('tandem_00')
y=np.column_stack([s.csi_yield_kwh_kwp,s.candidate_yield_kwh_kwp,t.candidate_yield_kwh_kwp])
d=np.array([np.median(c.csi_yield_kwh_per_m2/c.csi_yield_kwh_per_kwp*1000),s.density_W_m2.iloc[0],t.density_W_m2.iloc[0]])
sync=[]
for j,k in enumerate(['csi','perovskite','tandem']):
 e=float(np.max(np.abs(y[:,j]-c[k+'_yield_kwh_per_kwp'])));assert e<1e-9;sync.append(dict(technology=k,max_yield_error=e))
u=c.utilization_low.to_numpy()
_,cost=capex_and_lcoe({k:1400 for k in TECHS},CENTRAL_LEARNING_RATES,CENTRAL_CAPEX_FLOORS_USD_W,CENTRAL_BREAKTHROUGH_YEAR,CENTRAL_POST_BREAKTHROUGH_LIFETIME_YR,return_capex=True)
ev=evaluate(c,y,d,cost);cap=ev['initial_cap'];packing=ev['packing']
dr=perovskite_durability(2035,2035,21.5);life=np.array([25.,21.5,25.]);deg=np.array([.005,dr.degradation_rate,.012]);burn=np.array([.01,dr.burn_in_loss,.04])
reg=json.loads((I/'previous_analysis_register.json').read_text(encoding='utf-8'))
for a,b in [(cap,reg['system_capex_usd_kwp']),(d,reg['capacity_density_w_m2_aperture']),(deg,reg['baseline_degradation_rate']),(burn,reg['baseline_burn_in_loss'])]:assert np.allclose(a,b,rtol=0,atol=1e-10)
names=['csi','single_junction','tandem'];techs={1:'single',2:'tandem'}
lives=np.arange(15.,25.001,.25);cuts=np.arange(0.,100.001,.5)
def candidate(j,yy,L,x,price,fee,z,rf=1.,sal=False):
 ef,cf,_=lifecycle(L,deg[j],burn[j],replace_factor=rf,salvage=sal)
 v=yy*u*ef*price-1000*x-cap[j]*(cf-1)
 return v if z==0 else v*d[j]*packing/1000-fee
def target(j,z,price,fee):
 e=evaluate(c,y,d,cost,price_cap=price,price_area=price,site_cost=fee)
 v=e['npv_cap' if z==0 else 'npv_area'];ix=[k for k in range(3) if k!=j]
 vv=np.column_stack([np.zeros(n),v[:,ix]])
 return vv.max(axis=1),np.array(['no_build']+[names[k] for k in ix])[vv.argmax(axis=1)]
def invert(j,yy,L,price,fee,z,rf=1.,sal=False):
 tar,ch=target(j,z,price,fee);unit=1. if z==0 else d[j]*packing/1000
 return (candidate(j,yy,L,0,price,fee,z,rf,sal)-tar)/(1000*unit),tar,ch
def count(b,x):return int((b>=x-1e-12).sum())
front=[];th=[];grid=[];counts=[];paired=[];paths=[];controls=[];replacement=[];maxinv=0.;maxbase=0.
for j in [1,2]:
 tech=techs[j];end=state(tech+'_10').candidate_yield_kwh_kwp.to_numpy()
 for z,context in enumerate(['capacity','site_area']):
  price=[.04,.08][z];fee=[0.,25.][z];bounds={}
  for response,yy in [('baseline',y[:,j]),('target',end)]:
   for L in lives:
    b,tar,ch=invert(j,yy,L,price,fee,z);bounds[response,float(L)]=b
    maxinv=max(maxinv,float(np.max(np.abs(candidate(j,yy,L,b,price,fee,z)-tar))))
    cov=(b[:,None]>=cap[j]/1000*(1-cuts[None,:]/100)-1e-12).sum(axis=0)/n*100;assert np.all(np.diff(cov)>=0)
    front.append(pd.DataFrame(dict(response_state=response,candidate=names[j],context=context,lifetime_years=L,adcode=idx,city=c.city,province=c.province,parity_initial_cost_usd_wp=b,nonnegative_cost_feasible=b>=-1e-12,fixed_target_npv=tar,fixed_target_technology=ch,npv_unit='USD/kWp' if z==0 else 'USD/m2 site')))
    grid.append(pd.DataFrame(dict(response_state=response,candidate=names[j],context=context,lifetime_years=L,cost_cut_pct=cuts,initial_system_cost_usd_wp=cap[j]/1000*(1-cuts/100),coverage_pct=cov)))
    for frac in [.5,1.]:
     rank=math.ceil(frac*n);order=np.argsort(-b,kind='stable');i=order[rank-1];v=b[i];assert count(b,v)>=rank and count(b,v+1e-8)<rank
     th.append(dict(response_state=response,candidate=names[j],context=context,lifetime_years=L,minimum_coverage_pct=frac*100,required_regions=rank,initial_system_cost_usd_wp=v,cost_cut_pct=100*(1-v/(cap[j]/1000)),feasible_at_nonnegative_cost=bool(v>=-1e-12),controlling_adcode=idx[i],controlling_city=c.city.iloc[i],controlling_province=c.province.iloc[i]))
   bb=bounds[response,float(life[j])];nn=count(bb,cap[j]/1000)
   counts.append(dict(candidate=names[j],context=context,response_state=response,regions=nn,coverage_pct=nn/n*100,initial_cost_usd_wp=cap[j]/1000,lifetime_years=life[j],max_coverage_at_zero_initial_cost_pct=count(bb,0)/n*100))
   for p0 in [.04,.08]:
    for fee0 in ([0.] if z==0 else [0.,25.]):
     bb,_,_=invert(j,yy,life[j],p0,fee0,z)
     controls.append(dict(response_state=response,candidate=names[j],context=context,electricity_value_usd_kwh=p0,site_charge_usd_m2=fee0,regions=count(bb,cap[j]/1000),cost50_usd_wp=float(np.sort(bb)[n-185]),cost100_usd_wp=float(bb.min())))
   for rf,sal,label in [(1.,False,'Full replacement/no salvage'),(.5,False,'Half replacement/no salvage'),(1.,True,'Full replacement/pro-rata salvage')]:
    for L in [15.,18.,21.5,24.99,25.]:
     bb,_,_=invert(j,yy,L,price,fee,z,rf,sal)
     replacement.append(dict(response_state=response,candidate=names[j],context=context,service_life=L,replacement_rule=label,regions_at_current_cost=count(bb,cap[j]/1000),cost50_usd_wp=float(np.sort(bb)[n-185]),cost100_usd_wp=float(bb.min())))
  a=bounds['baseline',float(life[j])];b=bounds['target',float(life[j])]
  v0=candidate(j,y[:,j],life[j],cap[j]/1000,price,fee,z);v1=candidate(j,end,life[j],cap[j]/1000,price,fee,z);tar,_=target(j,z,price,fee)
  maxbase=max(maxbase,float(np.max(np.abs(v0-ev['npv_cap' if z==0 else 'npv_area'][:,j]))))
  paired.append(pd.DataFrame(dict(candidate=names[j],context=context,adcode=idx,city=c.city,province=c.province,baseline_npv=v0,target_npv=v1,npv_change=v1-v0,npv_unit='USD/kWp' if z==0 else 'USD/m2 site',fixed_rival_target_npv=tar,baseline_cost_boundary_usd_wp=a,target_cost_boundary_usd_wp=b,boundary_change_usd_wp=b-a,baseline_at_parity=a>=cap[j]/1000-1e-12,target_at_parity=b>=cap[j]/1000-1e-12)))
  for k in range(11):
   sid=tech+'_'+str(k).zfill(2);bb,_,_=invert(j,state(sid).candidate_yield_kwh_kwp.to_numpy(),life[j],price,fee,z)
   paths.append(dict(candidate=names[j],context=context,state_id=sid,progress=k/10,regions=count(bb,cap[j]/1000),coverage_pct=count(bb,cap[j]/1000)/n*100,cost50_usd_wp=float(np.sort(bb)[n-185]),cost100_usd_wp=float(bb.min())))
assert maxinv<1e-8 and maxbase<1e-8
for name,rows in [('common_start_frontiers',pd.concat(front,ignore_index=True)),('coverage_thresholds',th),('national_coverage_grid',pd.concat(grid,ignore_index=True)),('baseline_target_counts',counts),('paired_region_economic_changes',pd.concat(paired,ignore_index=True)),('economic_path_summary',paths),('matched_financial_controls',controls),('replacement_boundary_sensitivity',replacement),('physical_baseline_sync',sync)]:save('Figure4_'+name,rows)
save('Figure4_derived_cost_paths',pd.DataFrame({'year':YEARS,**{names[j]+'_USD_Wp':cost[k] for j,k in enumerate(TECHS)}}))
js('Figure4_numerical_checks.json',dict(status='PASS',regions=n,frontier_rows=sum(len(x) for x in front),coverage_grid_rows=sum(len(x) for x in grid),threshold_rows=len(th),paired_rows=sum(len(x) for x in paired),max_inverse_NPV_residual=maxinv,max_baseline_NPV_residual=maxbase,physical_sync=sync,fixed_rivals=True,negative_thresholds_preserved=True))
js('Figure4_analysis_register.json',dict(date='2026-10-08',capex2035_usd_kwp=cap.tolist(),density_W_m2=d.tolist(),baseline_lifetime=life.tolist(),degradation=deg.tolist(),burn_in=burn.tolist(),prices=[.04,.08],site_charge=25.,packing=packing,discount_rate=.05,horizon=25,counts=counts,scope='Independent candidate path response intervention against fixed common-baseline rivals; cost/lifetime scan independent of retention.'))
print(pd.DataFrame(counts).to_string(index=False),flush=True)
print('PASS; max inverse NPV residual',maxinv,flush=True)
