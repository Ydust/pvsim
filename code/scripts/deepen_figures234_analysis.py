"""Common-estimator perturbations and cost/durability counterfactuals.

No new empirical validation, device fitting or probabilistic scenario weights.
All scientific outputs are versioned; existing primary results are untouched.
"""
from pathlib import Path
import json, hashlib
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scripts import build_prefecture_area_model_outputs as b
from scripts.mechanism_shapley import shapley_components

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/figures234_submission_20260907'
QA=ROOT/'.work/figures234_submission_20260907'
def read(p):return pd.read_csv(ROOT/p,dtype={'adcode':str,'province_code':str})
def save(d,n):d.to_csv(OUT/(n+'.csv'),index=False,encoding='utf-8-sig')

def spatial_operator(a):
    cache=QA/'spatial_operator.npy'
    if cache.exists():return np.load(cache)
    grid=read(b.GRID);sp=b._spatial_index(grid,a)
    ix,aw=b._cell_index(grid,b.load_boundaries())
    ghi,_=b._baseline_residual_field(grid.ghi_ann.to_numpy(),a.ghi_kwh_m2.to_numpy(),sp)
    gf=np.column_stack([np.ones(len(grid)),ghi/1000,grid.lat/40,grid.lon/110])
    af=np.column_stack([np.ones(len(a)),ghi[sp['anchor_grid_indices']]/1000,a.lat/40,a.lon/110])
    rr=[];cc=[];vv=[];fallback=[]
    for i,code in enumerate(a.adcode):
        ids=ix[code]
        if len(ids):rr.extend([i]*len(ids));cc.extend(ids);vv.extend(aw[code]/sum(aw[code]))
        else:fallback.append(i)
    agg=csr_matrix((vv,(rr,cc)),shape=(len(a),len(grid)))
    nei=sp['neighbours'];w=sp['weights']/sp['weights'].sum(axis=1)[:,None]
    local=csr_matrix((w.ravel(),(np.repeat(np.arange(len(grid)),nei.shape[1]),nei.ravel())),shape=(len(grid),len(a)))
    aa=(agg@local).toarray();pinv=np.linalg.pinv(af)
    op=(agg@gf)@pinv+aa-aa@af@pinv
    for i in fallback:op[i]=0;op[i,i]=1
    raw=read(b.ANCHOR_MECHANISMS).set_index('adcode').loc[a.adcode]
    y=raw.perovskite_yield_t1_s1_i1_kwh_per_kwp.to_numpy()
    direct=b._aggregate(b._trend_residual_field_only(y,af,gf,sp),a,ix,aw,y)
    assert np.allclose(op@y,direct,atol=1e-9,rtol=0)
    np.save(cache,op)
    print('Common spatial operator verified',flush=True)
    return op

def physical():
    a=read(b.ANCHOR_SUMMARY).sort_values('adcode').reset_index(drop=True)
    primary=read('outputs/unified_method_20260906/city_results.csv').set_index('adcode').loc[a.adcode].reset_index()
    central=read('outputs/figure2_science_20260906/consistent_area_mechanisms.csv').set_index('adcode').loc[a.adcode].reset_index()
    anchors=read(b.ANCHOR_MECHANISMS).set_index('adcode').loc[a.adcode]
    op=spatial_operator(a);allrows=[];summary=[]
    par=read('outputs/figure2_science_20260906/parameter_attribution.csv')
    for (gamma,scale),g in par.groupby(['gamma_target','spectral_scale']):
        g=g.set_index('adcode').loc[a.adcode];states={}
        d=primary[['adcode','city','province','ghi_quartile']].copy()
        d['gamma_pct_c']=gamma;d['spectral_scale']=scale
        for k in range(8):
            suf=f't{k&1}_s{(k>>1)&1}_i{(k>>2)&1}'
            si=anchors[f'csi_yield_{suf}_kwh_per_kwp'].to_numpy()
            pv=si*(1+g[f'advantage_{suf}_pct'].to_numpy()/100)
            sy=op@si;py=op@pv
            assert min(sy.min(),py.min())>0
            states[k]=100*(py/sy-1);d[f'advantage_{suf}_pct']=states[k]
        terms=shapley_components(states)
        for key,col in [('temperature','thermal_pp'),('spectral','spectral_pp'),('iam','iam_pp')]:d[col]=terms[key]
        d['electrical_pp']=states[0];d['total_pct']=states[7]
        assert np.allclose(d[['thermal_pp','spectral_pp','iam_pp','electrical_pp']].sum(axis=1),d.total_pct,atol=1e-10)
        d['largest_climate_term']=d[['thermal_pp','spectral_pp','iam_pp']].idxmax(axis=1).str.replace('_pp','')
        allrows.append(d)
        for col in ['thermal_pp','spectral_pp','iam_pp','electrical_pp','total_pct']:
            summary.append(dict(gamma_pct_c=gamma,spectral_scale=scale,component=col,mean=d[col].mean(),minimum=d[col].min(),maximum=d[col].max(),q1_q4_pp=d.loc[d.ghi_quartile=='Q1',col].mean()-d.loc[d.ghi_quartile=='Q4',col].mean(),negative_cities=int((d[col]<0).sum())))
    full=pd.concat(allrows,ignore_index=True)
    base=full[(full.gamma_pct_c==-.15)&(full.spectral_scale==1)]
    assert np.max(np.abs(base.total_pct.to_numpy()-primary.single_capacity_pct))<1e-9
    save(full,'Figure2_parameter_city_states');save(pd.DataFrame(summary),'Figure2_parameter_summary')
    stab=[]
    for code,g in full.groupby('adcode'):
        z=g[(g.gamma_pct_c==-.15)&(g.spectral_scale==1)].iloc[0]
        stab.append(dict(adcode=code,city=z.city,province=z.province,central_largest=z.largest_climate_term,distinct_largest_terms=g.largest_climate_term.nunique(),central_label_retained_cases=int((g.largest_climate_term==z.largest_climate_term).sum()),cases=len(g),minimum_total_pct=g.total_pct.min(),minimum_thermal_pp=g.thermal_pp.min(),maximum_thermal_pp=g.thermal_pp.max()))
    save(pd.DataFrame(stab),'Figure2_city_mechanism_stability')
    scan=read('outputs/figure1_science_20260906/parameter_scan.csv');records=[];baseline=[]
    for (tech,gamma,response,scale),g in scan.groupby(['tech','gamma_target_pct_per_c','response_parameter','efficiency_ratio_scale']):
        g=g.set_index('adcode').loc[a.adcode]
        sy=op@g.csi_yield_kwh_per_kwp.to_numpy();py=op@g.yield_kwh_per_kwp.to_numpy()
        density=(1+g.area_advantage_pct.to_numpy()/100)/(1+g.capacity_advantage_pct.to_numpy()/100)
        assert np.ptp(density)<1e-12
        cp=100*(py/sy-1);ar=100*(py/sy*density[0]-1)
        d=primary[['adcode','city','province','ghi_quartile']].copy()
        d['technology']=tech;d['gamma_pct_c']=gamma;d['response_parameter']=response;d['density_scale']=scale
        d['capacity_advantage_pct']=cp;d['area_advantage_pct']=ar
        d['candidate_yield_kwh_kwp']=py;d['csi_yield_kwh_kwp']=sy;d['density_ratio']=density[0]
        records.append(d)
        isbase=scale==1 and ((tech=='single' and gamma==-.15 and response==1) or (tech=='tandem' and gamma==-.3 and response==1.68))
        if isbase:
            err=np.max(np.abs(cp-primary[f'{tech}_capacity_pct']))
            assert err<.01,err
            baseline.append(dict(technology=tech,max_baseline_difference_pp=err,reason='Retained hourly numerical discretization; no offset correction'))
    ds=pd.concat(records,ignore_index=True);assert len(ds)==337*54
    save(ds,'Figure3_parameter_city_results');save(pd.DataFrame(baseline),'Figure3_baseline_reconciliation')
    ss=[]
    for key,g in ds.groupby(['technology','gamma_pct_c','response_parameter','density_scale']):
        r=dict(zip(['technology','gamma_pct_c','response_parameter','density_scale'],key));r['cities']=len(g)
        for metric in ['capacity','area']:
            x=g[f'{metric}_advantage_pct'];r.update({f'{metric}_mean_pct':x.mean(),f'{metric}_minimum_pct':x.min(),f'{metric}_maximum_pct':x.max(),f'{metric}_positive_cities':int((x>0).sum())})
        ss.append(r)
    save(pd.DataFrame(ss),'Figure3_parameter_summary')
    print('Physical perturbations reconciled and exported',flush=True)

def economics():
    from pvsim.economic_priors import TECH_CSI as SI,TECH_PEROVSKITE as PV,CENTRAL_LEARNING_RATES as LR,CENTRAL_CAPEX_FLOORS_USD_W as FL,CENTRAL_BREAKTHROUGH_YEAR as BY,CENTRAL_POST_BREAKTHROUGH_LIFETIME_YR as LF
    from pvsim.economics import discounted_lcoe,perovskite_durability,MODERN_CSI_DURABILITY as sd
    from scripts.fig_substitution_validation import capex_and_lcoe,YEARS
    p=read('outputs/unified_method_20260906/city_results.csv')
    from scripts.revise_figure4_evidence import TECH
    y={tech:float(1/np.mean(1/p[f'{prefix}_yield_kwh_per_kwp'])) for tech,(prefix,_) in TECH.items()}
    lc,cost=capex_and_lcoe(y,LR,FL,BY,LF,return_capex=True);fixed=perovskite_durability(2025,BY,LF)
    rows=[]
    for learning,durable,name in [(0,0,'Neither'),(1,0,'Cost only'),(0,1,'Durability only'),(1,1,'Both')]:
        for i,yr in enumerate(YEARS):
            dur=perovskite_durability(yr,BY,LF) if durable else fixed
            cp=cost[PV][i if learning else 0]
            coeff=discounted_lcoe(cp,1,dur.lifetime_years,dur.degradation_rate,dur.burn_in_loss)*100
            ref=discounted_lcoe(cost[SI][i],1,sd.lifetime_years,sd.degradation_rate,sd.burn_in_loss)*100
            x=coeff/p.perovskite_yield_kwh_per_kwp.to_numpy();z=ref/p.csi_yield_kwh_per_kwp.to_numpy()
            if name=='Both':assert abs(x.mean()-lc[PV][i])<1e-10
            d=p[['adcode','city','province']].copy();d['case']=name;d['year']=int(yr);d['single_lcoe_cents_kwh']=x;d['csi_lcoe_cents_kwh']=z;d['lcoe_ratio']=x/z
            d['single_capex_usd_w']=cp;d['single_lifetime_years']=dur.lifetime_years;d['single_degradation_rate']=dur.degradation_rate;d['single_burn_in_loss']=dur.burn_in_loss
            rows.append(d)
    d=pd.concat(rows,ignore_index=True);save(d,'Figure4_cost_durability_city_cases')
    sm=[]
    for (case,yr),g in d.groupby(['case','year']):
        sm.append(dict(case=case,year=yr,cities=len(g),single_mean_lcoe_cents=g.single_lcoe_cents_kwh.mean(),csi_mean_lcoe_cents=g.csi_lcoe_cents_kwh.mean(),ratio_of_mean_lcoes=g.single_lcoe_cents_kwh.mean()/g.csi_lcoe_cents_kwh.mean(),city_ratio_p10=g.lcoe_ratio.quantile(.1),city_ratio_p90=g.lcoe_ratio.quantile(.9),cities_at_or_below_parity=int((g.lcoe_ratio<=1).sum())))
    sm=pd.DataFrame(sm);save(sm,'Figure4_cost_durability_summary')
    print(sm[sm.year==2035].to_string(index=False),flush=True)

if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True);QA.mkdir(parents=True,exist_ok=True)
    physical();economics()
    (QA/'input_hashes.json').write_text(json.dumps({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'outputs/figure1_science_20260906/parameter_scan.csv',ROOT/'outputs/figure2_science_20260906/parameter_attribution.csv',ROOT/'outputs/unified_method_20260906/city_results.csv']},indent=2))
