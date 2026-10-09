"""Retained financial equations with unsupported empirical calibration removed."""
import numpy as np
from scripts.cost_paths import YEARS, TECHS
from pvsim.economic_priors import CENTRAL_BREAKTHROUGH_YEAR,CENTRAL_POST_BREAKTHROUGH_LIFETIME_YR
from pvsim.economics import MODERN_CSI_DURABILITY,TANDEM_DURABILITY,perovskite_durability

def lifecycle(life,deg,burn,r=.05,horizon=25,replace_factor=1.,salvage=False):
    """Exact integration of piecewise annual-age retention over calendar-year bins.

    Replacement is paid at its exact fractional year. Calendar-year revenue
    is paid at each year end. This recovers the old discount model exactly
    for a 25-year non-replaced device, without rounding service lifetimes.
    """
    generation=np.zeros(horizon);replace_times=np.arange(life,horizon-1e-9,life)
    start_times=np.r_[0.,replace_times]
    for start in start_times:
        end=min(start+life,horizon)
        age=0
        while start+age<end-1e-10:
            a=start+age;b=min(a+1,end)
            for year in range(max(1,int(np.floor(a))+1),min(horizon,int(np.ceil(b)))+1):
                overlap=max(0.,min(b,year)-max(a,year-1))
                generation[year-1]+=overlap*(1-burn)*(1-deg)**age
            age+=1
    disc=(1+r)**(-np.arange(1,horizon+1))
    energy_factor=float(generation@disc)
    om_factor=float(.015*disc.sum())
    replacement_factor=float(np.sum((1+r)**(-replace_times))*replace_factor)
    salvage_credit=0.
    if salvage and len(replace_times):
        remaining=(replace_times[-1]+life-horizon)/life
        salvage_credit=replace_factor*remaining*(1+r)**(-horizon)
    return energy_factor,1+om_factor+replacement_factor-salvage_credit,float(generation.sum())

def evaluate(city,y,density,cost,year=2035,r=.05,price_cap=.04,price_area=.08,site_cost=25.,packing=.65,util_high=False,no_curtail=False,single_life=None,cap_multiplier=1.,single_cost_multiplier=1.,tandem_cost_multiplier=1.,replacement_factor=1.,salvage=False):
    dur=[MODERN_CSI_DURABILITY,perovskite_durability(year,CENTRAL_BREAKTHROUGH_YEAR,CENTRAL_POST_BREAKTHROUGH_LIFETIME_YR),TANDEM_DURABILITY]
    life=[v.lifetime_years for v in dur]
    if single_life is not None:
        dur[1]=perovskite_durability(2035,2035,single_life)
        life[1]=dur[1].lifetime_years
    factors=np.array([lifecycle(life[i],dur[i].degradation_rate,dur[i].burn_in_loss,r,replace_factor=replacement_factor,salvage=salvage) for i in range(3)])
    cap=np.array([cost[k][np.where(YEARS==year)[0][0]] for k in TECHS])*1000*cap_multiplier
    cap[1]*=single_cost_multiplier;cap[2]*=tandem_cost_multiplier
    u=np.ones(len(city)) if no_curtail else city['utilization_high' if util_high else 'utilization_low'].to_numpy()
    e=y*u[:,None]*factors[:,0]
    whole_cost=cap*factors[:,1]
    npv_cap=e*price_cap-whole_cost
    npv_area=e*price_area*(density*packing/1000)-whole_cost*(density*packing/1000)-site_cost
    initial_area=cap*density*packing/1000+site_cost
    return dict(npv_cap=npv_cap,npv_area=npv_area,delivered_pv_kwh_kwp=e,discounted_cost_kwp=whole_cost,
        full_horizon_cost_usd_kwh=whole_cost/e,initial_cap=cap,initial_area=initial_area,
        npv_cap_per_initial=npv_cap/cap,npv_area_per_initial=npv_area/initial_area,
        annual_delivered=y*u[:,None],density=density,packing=packing)
