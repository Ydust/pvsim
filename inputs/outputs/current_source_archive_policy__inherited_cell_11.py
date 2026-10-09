from pathlib import Path
from functools import lru_cache
import itertools,json,math
import numpy as np
import pandas as pd

ROOT=Path.cwd()
if not (ROOT/'input').is_dir():ROOT=ROOT.parent
OUT=ROOT/'output';OUT.mkdir(exist_ok=True)
settings=json.loads((ROOT/'input/analysis_settings.json').read_text())
city=pd.read_csv(ROOT/'input/city_physical_yields.csv',dtype={'adcode':str,'province_code':str})
register=pd.read_csv(ROOT/'input/Original_parameter_register.csv').set_index('Input').Value
reg=lambda key:float(register.loc[key])
TECHS=['csi','sj','tandem'];OLDTECHS=['csi','perovskite','tandem'];N=len(city);H=settings['horizon_years'];BASE=settings['commissioning_year'];FX=settings['fx_cny_per_usd'];R=settings['discount_rate']
Y=city[[k+'_yield_kwh_per_kwp' for k in OLDTECHS]].to_numpy()
YA=city[[k+'_yield_kwh_per_m2' for k in OLDTECHS]].to_numpy()
DENSITY=np.array([reg(k+' STC density') for k in OLDTECHS])
assert N==369 and np.allclose(1000*YA/Y,DENSITY)
baseline_utilization=pd.read_csv(ROOT/'input/baseline_utilization.csv',dtype={'province_code':str}).set_index('province_code').utilization_low
u_old=city.province_code.map(baseline_utilization).to_numpy()
assert np.isfinite(u_old).all() and city.adcode.is_unique
util=pd.read_csv(ROOT/'input/annual_pv_utilization.csv',dtype={'province_code':str})
u_new=city.province_code.map(util[(util.year==2025)&(util.province_code!='00')].groupby('province_code').pv_utilization_pct.min()/100).to_numpy()
assert np.isfinite(u_new).all()
costs=pd.read_csv(ROOT/'input/Published_cost_scenarios.csv')
mask=np.ones(len(costs),bool)
for key,value in settings['cost_reference'].items():mask &= costs[key].eq(value)
cost=costs.loc[mask].iloc[0]
old_capex=np.array([reg(k+' capex_usd_kwp') for k in OLDTECHS])
old_lives=np.array([reg(k+' life_y') for k in OLDTECHS])
old_deg=np.array([reg(k+' degradation_fraction_y') for k in OLDTECHS])
old_burn=np.array([reg(k+' burn_in_fraction') for k in OLDTECHS])
new_lives=np.array(settings['updated_intervals'],float)
new_deg=np.r_[old_deg[0],1-.8**(1/new_lives[1:])]
new_module=np.array([cost.csi_module_cny_w*1000,cost.sj_module_cny_m2*1000/DENSITY[1],cost.tandem_module_cny_m2*1000/DENSITY[2]])/FX
new_capex=new_module+cost.nonmodule_cny_w*1000/FX

def profile(**kw):
    return dict(capital=False,om=False,site=False,interval=False,degradation=False,price=False,itemized=False,flexible=False,residual=False,burn_removed=False,trapezoid=False,util_updated=False,**kw)

def make_profile(**kw):
    p=profile();p.update(kw);return p

@lru_cache(None)
def paths_for(k,ls,lt,flexible):
    lives=(25.,ls,lt)
    def walk(material,start,prefix):
        end=min(float(H),start+lives[material]);path=prefix+((material,start,end),)
        if end>=H-1e-9:yield path
        elif flexible:
            yield path+((-1,end,float(H)),)
            for nxt in range(3):yield from walk(nxt,end,path)
        else:yield from walk(material,end,path)
    return tuple(walk(k,0.,()))

def energy_factor(path,deg,burn,trapezoid):
    e=np.zeros((3,H+1));active=np.zeros((3,H+1))
    for k,start,end in path:
        if k<0:continue
        age=0
        while start+age<end-1e-9:
            a=start+age;b=min(a+1,end)
            retention=(1-burn[k])*(1-deg[k])**age
            if trapezoid:retention*=1-deg[k]/2
            for year in range(max(1,int(np.floor(a))+1),min(H,int(np.ceil(b)))+1):
                overlap=max(0.,min(b,year)-max(a,year-1))
                e[k,year]+=overlap*retention;active[k,year]+=overlap
            age+=1
    return e,active