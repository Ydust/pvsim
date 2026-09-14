"""Matched-project NPV screening, with explicit non-empirical financial scenarios."""

from pvsim.labels import label as _text_label
from pathlib import Path
import json,itertools
import numpy as np
import pandas as pd
from scripts.fig_substitution_validation import capex_and_lcoe,YEARS
from pvsim.economic_priors import CENTRAL_LEARNING_RATES,CENTRAL_CAPEX_FLOORS_USD_W,CENTRAL_BREAKTHROUGH_YEAR,CENTRAL_POST_BREAKTHROUGH_LIFETIME_YR
from pvsim.economics import perovskite_durability,MODERN_CSI_DURABILITY,TANDEM_DURABILITY

ROOT=Path(__file__).resolve().parents[1];O=ROOT/'outputs/figure5_regional_20260906';Q=ROOT/'.work/figure5_regional_20260906'
CODES=['csi','perovskite','tandem'];NAMES=['c-Si','Single junction','2T tandem'];TECHS=[_text_label('tech_csi'),_text_label('tech_perovskite'),_text_label('tech_tandem')]

def load():
    city=pd.read_csv(ROOT/'outputs/unified_method_20260906/city_results.csv',dtype={'adcode':str})
    use=pd.read_csv(ROOT/'data/source_tables/nea_pv_utilization_rate_2024.csv')
    g=use.groupby('province').pv_utilization_rate_pct_2024.agg(['min','max'])/100
    city=city.join(g,on='province').rename(columns={'min':'utilization_low','max':'utilization_high'})
    assert len(city)==city.adcode.nunique()==337
    assert city[['utilization_low','utilization_high']].notna().all().all()
    y=np.column_stack([city[f'{k}_yield_kwh_per_kwp'] for k in CODES])
    density=np.array([np.median(city[f'{k}_yield_kwh_per_m2']/city[f'{k}_yield_kwh_per_kwp']*1000) for k in CODES])
    _,cost=capex_and_lcoe({k:1400 for k in TECHS},CENTRAL_LEARNING_RATES,CENTRAL_CAPEX_FLOORS_USD_W,CENTRAL_BREAKTHROUGH_YEAR,CENTRAL_POST_BREAKTHROUGH_LIFETIME_YR,return_capex=True)
    return city,y,density,cost

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

def winners(npv):
    idx=np.argmax(npv,axis=1);best=np.max(npv,axis=1)
    return np.where(best>0,idx,-1)

def main():
    O.mkdir(parents=True,exist_ok=True);Q.mkdir(parents=True,exist_ok=True)
    city,y,density,cost=load();a=evaluate(city,y,density,cost)
    # Regression checks for an unreplaced 25-year device and zero-price rejection.
    from pvsim.economics import discounted_energy,discounted_cost_multiplier
    e,f,_=lifecycle(25,.005,.01)
    assert np.isclose(e,discounted_energy(1,25,.005,.01))
    assert np.isclose(f,discounted_cost_multiplier(25))
    assert (winners(evaluate(city,y,density,cost,price_cap=0)['npv_cap'])==-1).all()
    records=city.copy()
    for name in ['npv_cap','npv_area','npv_cap_per_initial','npv_area_per_initial','full_horizon_cost_usd_kwh','delivered_pv_kwh_kwp','annual_delivered']:
        for j,k in enumerate(CODES):records[f'{k}_{name}']=a[name][:,j]
    for name in ['cap','area']:
        records[f'{name}_winner_index']=winners(a['npv_'+name])
        records[f'{name}_winner']=[NAMES[i] if i>=0 else 'None viable' for i in records[f'{name}_winner_index']]
        sorted_values=np.sort(a['npv_'+name],axis=1)
        records[f'{name}_margin_best_second']=sorted_values[:,-1]-sorted_values[:,-2]
    records['paired_class']=records.cap_winner+' / '+records.area_winner
    # Electricity-value thresholds for NPV switching at fixed usable site area.
    pv_area=a['delivered_pv_kwh_kwp']*density*.65/1000
    cost_area=a['discounted_cost_kwp']*density*.65/1000+25
    for j in range(3):
        for k in range(j+1,3):
            denominator=pv_area[:,k]-pv_area[:,j]
            records[f'area_price_switch_{CODES[j]}_{CODES[k]}']=(cost_area[k]-cost_area[j])/denominator
    records.to_csv(O/'Figure5_city_decisions.csv',index=False,encoding='utf-8-sig')
    # Predeclared stress cases, not a probability distribution or fitted ensemble.
    specs=[('Central',{})]
    for field,values in [('price_cap',[.03,.05]),('price_area',[.06,.10]),('r',[.03,.08]),
        ('year',[2030,2040]),('single_life',[18.,25.]),('cap_multiplier',[.85,1.15]),
        ('single_cost_multiplier',[.8,1.2]),('tandem_cost_multiplier',[.8,1.2]),
        ('packing',[.5,.8]),('site_cost',[0.,50.]),('replacement_factor',[.5]),
        ('salvage',[True]),('util_high',[True]),('no_curtail',[True])]:
        for value in values:specs.append((f'{field}={value}',{field:value}))
    specs += [('Joint downside',dict(price_cap=.03,price_area=.06,r=.08,cap_multiplier=1.15,single_life=18.,site_cost=50.)),
        ('Joint upside',dict(price_cap=.05,price_area=.10,r=.03,cap_multiplier=.85,single_life=25.,site_cost=0.))]
    stress=[]
    for label,kwargs in specs:
        ev=evaluate(city,y,density,cost,**kwargs)
        ca=winners(ev['npv_cap']);ar=winners(ev['npv_area'])
        for i,row in city.iterrows():
            stress.append(dict(adcode=row.adcode,scenario=label,cap_winner_index=int(ca[i]),area_winner_index=int(ar[i]),
                cap_same=bool(ca[i]==records.cap_winner_index.iloc[i]),area_same=bool(ar[i]==records.area_winner_index.iloc[i]),
                paired_same=bool(ca[i]==records.cap_winner_index.iloc[i] and ar[i]==records.area_winner_index.iloc[i]),
                **{f'{tech}_npv_{context}':float(ev['npv_'+context][i,j]) for j,tech in enumerate(CODES) for context in ['cap','area']}))
    stress=pd.DataFrame(stress);stress.to_csv(O/'Figure5_scenario_classifications.csv',index=False)
    agree=stress.groupby('adcode')[['cap_same','area_same','paired_same']].mean()
    records=records.join(agree,on='adcode')
    records.to_csv(O/'Figure5_city_decisions.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame([dict(scenario=n,**{k:str(v) for k,v in kw.items()}) for n,kw in specs]).fillna('').to_csv(O/'Figure5_scenario_definitions.csv',index=False)
    stats=[]
    for name,gp in records.groupby('paired_class'):
        vals={'paired_class':name,'cities':len(gp)}
        for col in ['ghi_kwh_m2','tair_mean','utilization_low','cap_same','area_same','paired_same','cap_margin_best_second','area_margin_best_second']:
            vals[col+'_median']=float(gp[col].median());vals[col+'_p10']=float(gp[col].quantile(.1));vals[col+'_p90']=float(gp[col].quantile(.9))
        stats.append(vals)
    pd.DataFrame(stats).to_csv(O/'Figure5_class_profiles.csv',index=False)
    factorial=[]
    for price in [.04,.08]:
        ev=evaluate(city,y,density,cost,price_cap=price,price_area=price)
        for context in ['cap','area']:
            win=winners(ev['npv_'+context])
            for i in [-1,0,1,2]:factorial.append(dict(value_usd_kwh=price,context=context,technology='None viable' if i==-1 else NAMES[i],cities=int((win==i).sum())))
    pd.DataFrame(factorial).to_csv(O/'Figure5_price_constraint_factorial.csv',index=False)
    # Province-level utilization can reverse rankings only through delivered energy
    # and revenue, not through a technology-specific physical correction.
    none=evaluate(city,y,density,cost,no_curtail=True)
    utilization_changed=int(np.sum((winners(none['npv_cap'])!=records.cap_winner_index)|(winners(none['npv_area'])!=records.area_winner_index)))
    counts=records.groupby(['cap_winner','area_winner']).size().reset_index(name='cities')
    counts.to_csv(O/'Figure5_paired_classes.csv',index=False)
    print(counts.to_string(index=False));print('density',density)
    print(records.groupby('paired_class')[['ghi_kwh_m2','tair_mean','utilization_low']].median().to_string())
    print(records.groupby('paired_class').city.apply(lambda s:', '.join(s.head(12))).to_string())
    report={'n':337,'density_w_m2':density.tolist(),'counts':counts.to_dict('records'),
        'input_assumptions':'See declared analysis contract; these are conditional scenarios, not project investment forecasts.',
        'lifecycle_regression_checks_pass':True,'stress_scenarios':len(specs),
        'paired_choices_changed_without_regional_utilization_proxy':utilization_changed,
        'all_scenarios_same_pair_cities':int((records.paired_same==1).sum()),
        'city_agreement_median':float(records.paired_same.median()),
        'fig1_to_fig5_correlation_relative_gain_vs_csi_absolute_yield':float(city.single_capacity_pct.corr(city.csi_yield_kwh_per_kwp)),
        'relative_gain_mean_in_nonviable_grid_cities':float(records.loc[records.cap_winner_index==-1,'single_capacity_pct'].mean()),
        'relative_gain_mean_in_viable_grid_cities':float(records.loc[records.cap_winner_index>=0,'single_capacity_pct'].mean())}
    (O/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':main()
