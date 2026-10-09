"""Fresh, matched 2^3 factorial rerun at60 MPP samples for all3 technologies."""
from pathlib import Path
import os,sys,json,hashlib,time,argparse
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'factorial'
P=ROOT
sys.path.insert(0,str(OUT/'code'))
import numpy as np,pandas as pd
from concurrent.futures import ProcessPoolExecutor,as_completed
from pvsim import system as sy,weather as wx,spectral as sp
from pvsim.materials import CSI_MODERN,PEROVSKITE,TANDEM_2T
from pvsim.module import module_stc_power
from scripts.exact_vector import array_dc_power
from scripts.mechanism_shapley import config_for_mask,shapley_components
SD=OUT/'Source_Data';QA=OUT/'qa';SH=OUT/'calculation/shards'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return pd.read_csv(p,dtype={'adcode':str})
def js(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
def save(d,n):pd.DataFrame(d).to_csv(SD/(n+'.csv'),index=False,encoding='utf-8-sig')
def initialize():
    global TRACE
    sy.array_dc_power=array_dc_power
    TRACE=read(OUT/'inputs/PVGIS_369城市_数值与元数据精确出处.csv').set_index('adcode')
    assert sp.TANDEM_TOP_EG_REF==1.68 and abs(sp.TANDEM_BOTTOM_DEG_DT+.0002677*1.121)<1e-15
def weather(a):
    z=TRACE.loc[a['adcode']];path=P/z.cache_file
    assert sha(path)==z.cache_sha256
    raw=pd.read_csv(path,index_col=0,parse_dates=True)
    if raw.index.tz is None:raw.index=raw.index.tz_localize('UTC')
    assert len(raw)==8760 and raw.index.is_unique
    assert abs(a['lat']-z.used_latitude)<1e-9 and abs(a['lon']-z.used_longitude)<1e-9 and abs(a['altitude_m']-z.used_altitude_m)<1e-9
    loc=wx.get_location(a['lat'],a['lon'],altitude=a['altitude_m'],name=a['city'])
    return wx.make_weather(raw.index,loc,raw.ghi,raw.dni,raw.dhi,raw.temp_air,raw.wind_speed,irradiance_time_offset_h=float(z.irradiance_time_offset_h))
def compute(a):
    st=time.monotonic();w=weather(a);rows=[]
    for k in range(8):
        cfg=sy.SystemConfig(**config_for_mask(k));row=dict(adcode=a['adcode'],mask=k,offset_h=.5,mpp_samples=60)
        for name,tech in [('csi',CSI_MODERN),('single',PEROVSKITE),('tandem',TANDEM_2T)]:
            row[name+'_yield_kwh_kwp']=sy.simulate(tech,w,cfg,npts=60)['specific_yield']
        rows.append(row)
    d=pd.DataFrame(rows);dest=SH/(a['adcode']+'.csv');tmp=dest.with_suffix('.tmp')
    d.to_csv(tmp,index=False,encoding='utf-8-sig');tmp.replace(dest)
    return a['adcode'],time.monotonic()-st
def pilot(anchors):
    initialize();old=read(OUT/'inputs/common_start_anchor_yields.csv');checks=[]
    for a in anchors:
        code,_=compute(a);d=read(SH/(code+'.csv')).set_index('mask').loc[7]
        for name in ['single','tandem']:
            z=old[old.adcode.eq(code)&old.state_id.eq(name+'_00')].iloc[0]
            err=max(abs(d[name+'_yield_kwh_kwp']-z.yield_kwh_kwp),abs(d.csi_yield_kwh_kwp-z.csi_yield_kwh_kwp))
            assert err<1e-8,(code,name,err)
            checks.append(dict(adcode=code,technology=name,max_yield_error_kwh_kwp=err))
        print('Pilot full-state match',code,flush=True)
    pd.DataFrame(checks).to_csv(QA/'pilot_baseline_equivalence.csv',index=False,encoding='utf-8-sig')
    js(QA/'pilot_validation.json',dict(status='PASS',anchors=len(anchors),max_yield_error_kwh_kwp=max(z['max_yield_error_kwh_kwp'] for z in checks)))
def combine():
    legacy=read(OUT/'inputs/legacy_figure1_regions.csv').sort_values('adcode').reset_index(drop=True)
    codes=legacy.adcode.to_list();assert len(codes)==len(set(codes))==369
    common=read(OUT/'inputs/common_start_regional_states.csv');op=np.load(OUT/'inputs/spatial_operator.npy')
    assert op.shape==(369,369) and np.max(abs(op.sum(1)-1))<1e-10
    city=legacy.copy();densities={}
    density0=module_stc_power(CSI_MODERN)/(CSI_MODERN.area_cm2*CSI_MODERN.cells_in_series)*1e4
    for name in ['single','tandem']:
        z=common[common.state_id.eq(name+'_00')].set_index('adcode').loc[codes]
        ref=z.csi_yield_kwh_kwp.to_numpy();yy=z.candidate_yield_kwh_kwp.to_numpy();den=z.density_W_m2.to_numpy()
        city['csi_yield_kwh_per_kwp']=ref;city['csi_yield_kwh_per_m2']=ref*density0/1000
        prefix='perovskite' if name=='single' else name
        city[prefix+'_yield_kwh_per_kwp']=yy;city[prefix+'_yield_kwh_per_m2']=yy*den/1000
        city[name+'_capacity_pct']=z.capacity_gain_pct.to_numpy();city[name+'_area_pct']=z.area_gain_pct.to_numpy()
        densities[name]=float(z.density_ratio.iloc[0]);assert np.ptp(z.density_ratio)<1e-12
    save(city,'Figure1_region_values')
    baseline_changes=[]
    for name in ['single','tandem']:
        for field in ['capacity','area']:
            key=f'{name}_{field}_pct';delta=city[key]-legacy[key]
            baseline_changes.append(dict(metric=key,old_mean_pct=legacy[key].mean(),new_mean_pct=city[key].mean(),max_abs_change_pp=abs(delta).max(),changed_parity_classifications=int((city[key].ge(0)!=legacy[key].ge(0)).sum())))
    save(baseline_changes,'Figure1_baseline_change_summary')
    raw=pd.concat([read(SH/(c+'.csv')) for c in codes],ignore_index=True)
    assert len(raw)==369*8 and not raw.duplicated(['adcode','mask']).any()
    raw.to_csv(OUT/'calculation/anchor_factorial_yields.csv',index=False,encoding='utf-8-sig')
    meta=city[['adcode','city','province','ghi_quartile','temperature_quartile','ghi_kwh_m2','tcell_weighted_c']]
    components=[];allstates=[];identities=[];summaries=[];contrasts=[];strata=[];errors={};closure=[]
    fields=['electrical_pp','thermal_pp','spectral_pp','iam_pp','total_pct']
    for name in ['single','tandem']:
        d=meta.copy();values={}
        for k in range(8):
            z=raw[raw['mask'].eq(k)].set_index('adcode').loc[codes]
            ref=op@z.csi_yield_kwh_kwp.to_numpy();yy=op@z[name+'_yield_kwh_kwp'].to_numpy()
            assert min(ref.min(),yy.min())>0
            values[k]=100*(yy/ref-1)
            allstates.append(meta.assign(technology=name,mask=k,temperature_on=bool(k&1),spectrum_on=bool(k&2),iam_on=bool(k&4),candidate_yield_kwh_kwp=yy,matched_csi_yield_kwh_kwp=ref,gain_capacity_pct=values[k]))
        d['technology']=name;d['electrical_pp']=values[0]
        effects=shapley_components(values)
        for key,col in [('temperature','thermal_pp'),('spectral','spectral_pp'),('iam','iam_pp')]:d[col]=effects[key]
        d['total_pct']=values[7];closure.append(float(np.max(abs(d[fields[:-1]].sum(axis=1)-d.total_pct))))
        errors[name]=float(np.max(abs(values[7]-city[name+'_capacity_pct'])))
        assert errors[name]<1e-9 and closure[-1]<1e-10,(errors,closure)
        components.append(d)
        for term in fields:
            z=d[term];summaries.append(dict(technology=name,term=term,n=369,mean=z.mean(),p10=z.quantile(.1),median=z.median(),p90=z.quantile(.9),minimum=z.min(),maximum=z.max()))
            q=d.groupby('ghi_quartile',observed=True)[term].mean();contrasts.append(dict(technology=name,term=term,q1_q4_pp=q.loc['Q1']-q.loc['Q4']))
        dr=densities[name];area=100*(dr-1)+dr*values[7]
        assert np.max(abs(area-city[name+'_area_pct']))<1e-10
        identities.append(meta.assign(technology=name,density_ratio=dr,capacity_gain_pct=values[7],density_contribution_pp=100*(dr-1),operating_contribution_pp=dr*values[7],area_gain_pct=area))
        phase=d.groupby(['temperature_quartile','ghi_quartile'],observed=True).total_pct.agg(['mean','size']).reset_index();phase['technology']=name;strata.append(phase)
    allstates=pd.concat(allstates,ignore_index=True);controlled=[];stratum_contrasts=[]
    for (name,k,q),d in allstates.groupby(['technology','mask','ghi_quartile'],observed=True):
        z=d.gain_capacity_pct;controlled.append(dict(technology=name,mask=k,ghi_quartile=q,n=len(z),mean_ghi_mwh_m2=d.ghi_kwh_m2.mean()/1000,mean_gain_pct=z.mean(),p10=z.quantile(.1),p90=z.quantile(.9)))
    for (name,temp),d in allstates[allstates['mask'].eq(7)].groupby(['technology','temperature_quartile'],observed=True):
        q=d.groupby('ghi_quartile',observed=True).gain_capacity_pct.mean()
        stratum_contrasts.append(dict(technology=name,temperature_stratum=temp,contrast_pp=q.loc['Q1']-q.loc['Q4']))
    for d,n in [(allstates,'all_states'),(pd.concat(components),'components'),(summaries,'component_summaries'),(pd.concat(identities),'area_identity'),(controlled,'response_summaries'),(pd.concat(strata),'temperature_strata'),(contrasts,'ghi_contrasts'),(stratum_contrasts,'stratum_contrasts')]:save(d,'Figure2_dual_path_'+n)
    provenance=json.loads((QA/'runtime_fingerprint.json').read_text())
    report=dict(status='PASS',regions=369,excluded_regions=0,anchor_switch_states=len(raw),annual_technology_anchor_runs=len(raw)*3,matched_region_technology_states=len(allstates),technology_component_rows=738,
      baseline_reconciliation_max_pp=errors,attribution_closure_max_pp=max(closure),irradiance_time_offset_h=.5,tandem_bottom_gap_slope_ev_K=sp.TANDEM_BOTTOM_DEG_DT,
      comparison='Annual AC gain over matched c-Si in every switch state; same spatial operator before ratio',
      native_numerical_grids='All technologies and switch states use60 MPP samples; STC400 samples; full7 matches common-start Fig3',
      spectral_off='Reference spectrum; tandem temperature-driven subcell-current mismatch retained if temperature is on',thermal_off='25C for candidate and c-Si',
      attribution='All-off electrical baseline plus3-factor Shapley effects, including allocated interactions',area_identity='100*(fixed density ratio-1)+density ratio*specific-yield gain in percent',
      uncertainty='Spatial P10–P90, not confidence intervals',runtime_fingerprint=provenance['fingerprint'],source_sha256=provenance['files'])
    js(QA/'Figure2_dual_path_calculation.json',report)
    js(QA/'factorial_shard_manifest.json',{p.name:sha(p) for p in SH.glob('*.csv')})
    print(json.dumps({k:v for k,v in report.items() if k!='source_sha256'},ensure_ascii=False,indent=2),flush=True)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--pilot',action='store_true');ap.add_argument('--workers',type=int,default=6);args=ap.parse_args()
    initialize()
    files=list((OUT/'code/pvsim').glob('*.py'))+list((OUT/'code/scripts').glob('*.py'))+list((OUT/'inputs').glob('*'))+[Path(__file__)]
    hashes={str(p.relative_to(ROOT)):sha(p) for p in sorted(files) if p.is_file()}
    trace=read(OUT/'inputs/PVGIS_369城市_数值与元数据精确出处.csv')
    for z in trace.to_dict('records'):
        p=P/z['cache_file'];assert sha(p)==z['cache_sha256'];hashes[str(p.relative_to(ROOT))]=z['cache_sha256']
    fp=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest();mark=QA/'runtime_fingerprint.json'
    if mark.exists():assert json.loads(mark.read_text())['fingerprint']==fp,'Changed numerical inputs/code require a fresh version.'
    else:js(mark,dict(fingerprint=fp,files=hashes))
    anchors=read(OUT/'inputs/anchor_metadata.csv').sort_values('adcode').to_dict('records');assert len(anchors)==369
    if args.pilot:pilot([a for a in anchors if a['adcode'] in ['110000','310000','540100','650100']])
    else:
        assert (QA/'pilot_validation.json').exists()
        with ProcessPoolExecutor(max_workers=args.workers,initializer=initialize) as ex:
            futures=[ex.submit(compute,a) for a in anchors]
            for i,f in enumerate(as_completed(futures),1):
                code,sec=f.result()
                if i%20==0 or i==369:print(f'{i}/369 complete; last {code}, {sec:.2f}s',flush=True)
        combine()
