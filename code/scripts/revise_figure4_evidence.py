"""Economic calculations using a common city-mean estimand.

A harmonic yield is an exact computational identity for mean city LCOE when costs and
durability are shared; it is not a new spatial weighting assumption.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from pvsim.economic_priors import (TECH_CSI, TECH_PEROVSKITE, TECH_TANDEM,
    CENTRAL_LEARNING_RATES, CENTRAL_CAPEX_FLOORS_USD_W,
    CENTRAL_BREAKTHROUGH_YEAR, CENTRAL_POST_BREAKTHROUGH_LIFETIME_YR,
    sample_crossover_inputs)
from scripts.fig_substitution_validation import capex_and_lcoe, YEARS

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'outputs/unified_method_20260906'
OUT = ROOT/'outputs/figure4_policy_20260906'
QA = ROOT/'.work/figure4_policy_20260906'
TECH = {TECH_CSI: ('csi', 'c-Si'), TECH_PEROVSKITE: ('perovskite', 'perovskite'), TECH_TANDEM: ('tandem', 'tandem')}

def cross(lcoe):
    ix = np.flatnonzero(lcoe[TECH_PEROVSKITE] <= lcoe[TECH_CSI])
    return int(YEARS[ix[0]]) if len(ix) else 2051

def main():
    OUT.mkdir(exist_ok=True, parents=True); QA.mkdir(exist_ok=True, parents=True)
    d = pd.read_csv(BASE/'city_results.csv', dtype={'adcode': str})
    assert len(d) == d.adcode.nunique() == 337
    y = {tech: float(1/np.mean(1/d[f'{prefix}_yield_kwh_per_kwp'])) for tech,(prefix,_) in TECH.items()}
    central = capex_and_lcoe(y, CENTRAL_LEARNING_RATES, CENTRAL_CAPEX_FLOORS_USD_W, CENTRAL_BREAKTHROUGH_YEAR, CENTRAL_POST_BREAKTHROUGH_LIFETIME_YR)
    l = pd.read_csv(BASE/'prefecture_area_weighted_lcoe.csv')
    rows=[]; errors={}
    for tech,(_,code) in TECH.items():
        g=l[l.code==code].groupby('year').lcoe_cents_per_kwh
        mean=g.mean().reindex(YEARS)
        errors[code] = float(np.max(np.abs(mean-central[tech])))
        assert np.allclose(mean, central[tech], rtol=1e-12, atol=1e-12)
        for year in YEARS[YEARS>=2027]:
            rows.append(dict(year=int(year),code=code,mean=float(g.mean()[year]),p10=float(g.quantile(.1)[year]),p90=float(g.quantile(.9)[year]),n=337))
    pd.DataFrame(rows).to_csv(OUT/'Figure4a_city_mean_lcoe.csv',index=False)
    # Preserve the original active-parameter priors and random stream.
    rng=np.random.default_rng(42); draws=[]; inputs=[]
    for i in range(10000):
        lr, floor, bt, life = sample_crossover_inputs(rng)
        draws.append(cross(capex_and_lcoe(y, lr, floor, bt, life)))
        inputs.append(dict(draw=i+1,csi_learning_rate=lr[TECH_CSI],single_learning_rate=lr[TECH_PEROVSKITE],csi_floor_usd_w=floor[TECH_CSI],single_floor_usd_w=floor[TECH_PEROVSKITE],durability_endpoint_year=bt,endpoint_lifetime_years=life))
        if (i+1)%2500 == 0: print(f'{i+1}/10000 scenarios',flush=True)
    draws=np.asarray(draws); inp=pd.DataFrame(inputs)
    inp['first_crossover_year']=pd.array([int(v) if v<=2050 else None for v in draws],dtype='Int64')
    inp['right_censored_by_2050']=draws>2050
    inp.to_csv(OUT/'Figure4c_scenario_draws.csv',index=False)
    dist=pd.DataFrame({'year':np.arange(2025,2051)})
    dist['draws']=[int((draws==t).sum()) for t in dist.year]
    dist['share_pct']=dist.draws/len(draws)*100
    dist['cumulative_share_pct']=dist.share_pct.cumsum()
    dist.to_csv(OUT/'Figure4c_cumulative_scenarios.csv',index=False)
    conv=[]
    for n in [1000,2500,5000,10000]:
        sub=draws[:n]
        vals=np.quantile(sub,[.1,.5,.9],method='inverted_cdf')
        conv.append(dict(draws=n,p10=int(vals[0]),p50=int(vals[1]),p90=int(vals[2]) if vals[2]<=2050 else '>2050',not_crossed_by_2050_pct=float((sub>2050).mean()*100)))
    pd.DataFrame(conv).to_csv(OUT/'Figure4c_prefix_stability.csv',index=False)
    e=pd.read_csv(BASE/'fig4_tandem_area_economics_summary.csv')
    e.to_csv(OUT/'Figure4b_area_cost_boundary.csv',index=False)
    summary=dict(central_crossover_year=cross(central),mc_draws=len(draws),mc_seed=42,
        p10=int(np.quantile(draws,.1,method='inverted_cdf')),p50=int(np.quantile(draws,.5,method='inverted_cdf')),
        p90=int(np.quantile(draws,.9,method='inverted_cdf')),not_crossed_by_2050_pct=float((draws>2050).mean()*100),
        estimand='Unweighted mean LCOE across the same 337 cities in panels a and c',
        harmonic_identity_max_error=errors,harmonic_yields=y,
        incremental_area_cost='One-time additional USD per square metre of module-aperture area, common to both technologies; excludes recurring O&M',
        external_validation=False,regional_roi_computed=False)
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
