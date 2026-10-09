"""Reconstruct matched regional states and audit all boundary claims."""
from pathlib import Path
import sys,json,hashlib,math
sys.dont_write_bytecode=True
import numpy as np,pandas as pd
O=Path(__file__).resolve().parents[1];W=O.parents[1]
P=O.parent;R=P
def csv(d,name):pd.DataFrame(d).to_csv(O/'results'/f'{name}.csv',index=False,encoding='utf-8-sig')
def js(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
states=pd.read_csv(O/'inputs/path_states.csv');raw=pd.read_csv(O/'results/anchor_path_yields.csv',dtype={'adcode':str})
c=pd.read_csv(O/'inputs/original_city_metadata.csv',dtype={'adcode':str,'province_code':str}).sort_values('adcode').reset_index(drop=True)
codes=c.adcode.to_numpy();op=np.load(O/'inputs/spatial_operator.npy')
assert op.shape==(369,369) and len(c)==369
assert np.max(np.abs(op.sum(1)-1))<1e-10
assert len(raw)==369*26 and not raw.duplicated(['adcode','state_id']).any()
rows=[];ref0=None
for state in states.to_dict('records'):
    z=raw[raw.state_id.eq(state['state_id'])].set_index('adcode').loc[codes]
    assert len(z)==369
    sy=op@z.csi_yield_kwh_kwp.to_numpy();yy=op@z.yield_kwh_kwp.to_numpy()
    if ref0 is None:ref0=sy.copy()
    assert np.array_equal(sy,ref0)
    d=c[['adcode','city','province','lat','lon','ghi_kwh_m2','tair_mean','ghi_quartile']].copy()
    for k,v in state.items():d[k]=v
    d['candidate_yield_kwh_kwp']=yy;d['csi_yield_kwh_kwp']=sy
    d['capacity_gain_pct']=100*(yy/sy-1);d['area_gain_pct']=100*(yy/sy*state['density_ratio']-1)
    d['area_yield_kwh_m2']=yy*state['density_W_m2']/1000
    d['required_density_gain_pct']=100*(1/(yy/sy*state['density_ratio'])-1)
    rows.append(d)
city=pd.concat(rows,ignore_index=True);csv(city,'regional_path_states')
assert np.max(np.abs(100*((1+city.capacity_gain_pct/100)*city.density_ratio-1)-city.area_gain_pct))<1e-10
summary=[];bounds=[];curves=[];worst=[]
for sid,z in city.groupby('state_id',sort=False):
    gain=z.capacity_gain_pct.to_numpy();area=z.area_gain_pct.to_numpy()
    s=z.iloc[0];summary.append(dict(state_id=sid,technology=s.technology,branch=s.branch,progress=s.progress,gamma_actual_pct_C=s.gamma_actual_pct_C,top_bandgap_eV=s.top_bandgap_eV,
     n=369,mean_gain_pct=gain.mean(),p10_gain_pct=np.quantile(gain,.1),p90_gain_pct=np.quantile(gain,.9),min_gain_pct=gain.min(),max_gain_pct=gain.max(),
     mean_area_gain_pct=area.mean(),min_area_gain_pct=area.min(),capacity_parity_regions=int((gain>=0).sum()),area_parity_regions=int((area>=0).sum()),density_ratio=s.density_ratio))
    if s.technology=='single':
        z=z.sort_values(['required_density_gain_pct','adcode']);v=z.required_density_gain_pct.to_numpy()
        for rank,(_,r) in enumerate(z.iterrows(),1):
            curves.append(dict(state_id=sid,progress=s.progress,adcode=r.adcode,city=r.city,coverage_pct=rank/369*100,required_density_gain_pct=r.required_density_gain_pct))
        for fraction in [.5,.9,.95,.99,1]:
            rank=math.ceil(369*fraction);r=z.iloc[rank-1];req=r.required_density_gain_pct
            assert (v<=req).sum()>=rank and (v<req).sum()<rank
            bounds.append(dict(state_id=sid,progress=s.progress,gamma_actual_pct_C=s.gamma_actual_pct_C,coverage_pct=fraction*100,required_regions=rank,
              required_density_gain_pct=req,controller_adcode=r.adcode,controller_city=r.city,controller_province=r.province,controller_latitude=r.lat,controller_tair_mean_C=r.tair_mean))
        for _,r in z.tail(10).iterrows():worst.append(dict(state_id=sid,progress=s.progress,adcode=r.adcode,city=r.city,province=r.province,latitude=r.lat,tair_mean_C=r.tair_mean,required_density_gain_pct=r.required_density_gain_pct))
csv(summary,'path_summary');csv(bounds,'single_coverage_thresholds');csv(curves,'single_coverage_curves');csv(worst,'single_limiting_regions_top10')
summary=pd.DataFrame(summary);bounds=pd.DataFrame(bounds)

# Same-unit changes; no inference from unmatched distributions.
paired=[]
for name in ['single','tandem']:
    start=city[city.state_id.eq(name+'_00')].set_index('adcode').loc[codes]
    for i in range(11):
        end=city[city.state_id.eq(f'{name}_{i:02}')].set_index('adcode').loc[codes]
        d=start[['city','province','ghi_kwh_m2','tair_mean','capacity_gain_pct','area_gain_pct','required_density_gain_pct']].reset_index().rename(columns={
          'capacity_gain_pct':'start_gain_pct','area_gain_pct':'start_area_gain_pct','required_density_gain_pct':'start_required_density_gain_pct'})
        d['technology']=name;d['step']=i;d['progress']=i/10;d['target_gain_pct']=end.capacity_gain_pct.to_numpy();d['change_pp']=d.target_gain_pct-d.start_gain_pct
        d['target_area_gain_pct']=end.area_gain_pct.to_numpy();d['target_required_density_gain_pct']=end.required_density_gain_pct.to_numpy()
        d['target_at_parity']=d.target_gain_pct.ge(0);paired.append(d)
paired=pd.concat(paired,ignore_index=True);csv(paired,'paired_path_changes')
t=paired[paired.technology.eq('tandem')&paired.step.eq(10)].copy().set_index('adcode').loc[codes]
for branch in ['thermal_only','bandgap_only']:
    t[branch+'_gain_pct']=city[city.state_id.eq(f'tandem_{branch}_10')].set_index('adcode').loc[codes].capacity_gain_pct
t['thermal_change_pp']=t.thermal_only_gain_pct-t.start_gain_pct;t['bandgap_change_pp']=t.bandgap_only_gain_pct-t.start_gain_pct
t['interaction_pp']=t.target_gain_pct-t.thermal_only_gain_pct-t.bandgap_only_gain_pct+t.start_gain_pct
csv(t.reset_index(),'tandem_endpoint_decomposition')

# Regional zero-state reconciliation, exact to archived60 scan; report legacy45 differences.
primary=pd.read_csv(R/'figure_workflow/input/city_results.csv',dtype={'adcode':str}).set_index('adcode').loc[codes]
scan=pd.read_csv(R/'outputs/results/joint_all_ERA5/parameter_city_results.csv',dtype={'adcode':str})
recon=[]
for name,field,gamma,response in [('single','single_capacity_pct',-.15,1.),('tandem','tandem_capacity_pct',-.3,1.68)]:
    new=city[city.state_id.eq(name+'_00')].set_index('adcode').loc[codes]
    old=scan[scan.technology.eq(name)&scan.gamma_pct_c.eq(gamma)&scan.response_parameter.eq(response)&scan.density_scale.eq(1)].set_index('adcode').loc[codes]
    assert np.max(np.abs(new.capacity_gain_pct-old.capacity_advantage_pct))<1e-10
    for code in codes:recon.append(dict(adcode=code,city=new.loc[code,'city'],technology=name,uniform60_gain_pct=new.loc[code,'capacity_gain_pct'],archived_scan60_gain_pct=old.loc[code,'capacity_advantage_pct'],legacy_primary_gain_pct=primary.loc[code,field],scan_residual_pp=new.loc[code,'capacity_gain_pct']-old.loc[code,'capacity_advantage_pct'],legacy_residual_pp=new.loc[code,'capacity_gain_pct']-primary.loc[code,field]))
csv(recon,'baseline_reconciliation')
oldtarget=scan[scan.technology.eq('tandem')&scan.gamma_pct_c.eq(-.2)&scan.response_parameter.eq(1.75)&scan.density_scale.eq(1)].set_index('adcode').loc[codes]
assert np.max(np.abs(t.target_gain_pct-oldtarget.capacity_advantage_pct))<1e-10

# Check the reversal under every province-removal subset, recalculating the ranks.
leave=[]
s0=city[city.state_id.eq('single_00')].set_index('adcode').loc[codes];s1=city[city.state_id.eq('single_10')].set_index('adcode').loc[codes]
for province in sorted(c.province.unique()):
    mask=s0.province.ne(province)
    for q in [.5,.95,1.]:
        rank=math.ceil(mask.sum()*q)-1
        x0=np.sort(s0.loc[mask,'required_density_gain_pct'])[rank];x1=np.sort(s1.loc[mask,'required_density_gain_pct'])[rank]
        leave.append(dict(removed_province=province,retained_units=int(mask.sum()),coverage_pct=100*q,start_density_gain_pct=x0,target_density_gain_pct=x1,change_pp=x1-x0))
csv(leave,'leave_province_thresholds')
endpoint={}
for name in ['single','tandem']:
    z=paired[paired.technology.eq(name)&paired.step.eq(10)]
    endpoint[name]=dict(mean_change_pp=float(z.change_pp.mean()),min_change_pp=float(z.change_pp.min()),max_change_pp=float(z.change_pp.max()),improving_regions=int(z.change_pp.gt(0).sum()),declining_regions=int(z.change_pp.lt(0).sum()))
mechanism={k:float(t[k].mean()) for k in ['thermal_change_pp','bandgap_change_pp','interaction_pp']}
residual=t[t.target_gain_pct.lt(0)].reset_index();csv(residual,'tandem_residual_regions')
recon=pd.DataFrame(recon)
results={'study_units':369,'path_states':26,'annual_anchor_state_simulations':len(raw),'hourly_records_per_anchor':8760,'regional_state_records':len(city),
 'anchors':'Exact primary-model parameter settings; all60 numerical zero states. No empirical device-development claim.',
 'baseline_reconciliation':{'max_scan60_residual_pp':float(recon.scan_residual_pp.abs().max()),'max_legacy_primary_residual_pp':float(recon.legacy_residual_pp.abs().max()),'by_technology':recon.groupby('technology').legacy_residual_pp.agg(lambda z:float(z.abs().max())).to_dict()},
 'single_thresholds':bounds[bounds.progress.isin([0,1])].to_dict('records'),
 'single_majority_decreases_all_intervals':bool(np.all(np.diff(bounds[bounds.coverage_pct.eq(50)].sort_values('progress').required_density_gain_pct)<0)),
 'single_full_coverage_increases_all_intervals':bool(np.all(np.diff(bounds[bounds.coverage_pct.eq(100)].sort_values('progress').required_density_gain_pct)>0)),
 'tandem_baseline':summary[summary.state_id.eq('tandem_00')].iloc[0].to_dict(),'tandem_endpoint':summary[summary.state_id.eq('tandem_10')].iloc[0].to_dict(),
 'paired_endpoint_changes':endpoint,'tandem_mean_response_decomposition_pp':mechanism,
 'leave_province_counts':pd.DataFrame(leave).groupby('coverage_pct').change_pp.agg(lambda z:{'decrease':int((z<0).sum()),'increase':int((z>0).sum()),'n':len(z)}).to_dict(),
 'excluded_regions':0,'economic_conclusions_recomputed':False,
 'boundary':'A baseline-anchored continuous parameter scenario. Reference-current normalization/voltage/rated efficiency remain prescribed. Density thresholds are fixed-response inverse requirements, not full-device efficiency improvements.'}
js(O/'results/key_findings.json',results)

# Upstream inputs are checked by the portable manifest before execution.
print("All 369 regional path states, compensation thresholds and paired changes recomputed.")
