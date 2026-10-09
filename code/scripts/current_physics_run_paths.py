"""Annual hourly rerun on two baseline-anchored parameter paths, no yield offsets."""
from pathlib import Path
import sys, os, json, hashlib, time, argparse
from dataclasses import replace, asdict
from concurrent.futures import ProcessPoolExecutor, as_completed
sys.dont_write_bytecode=True
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
O=Path(__file__).resolve().parents[1];W=O.parents[1]
P=O.parent;R=P
sys.path.insert(0,str(O/'code'))
import numpy as np,pandas as pd
from pvsim import system as sy,spectral as sp,weather as wx
from pvsim.materials import CSI_MODERN,PEROVSKITE,TANDEM_2T
from pvsim.module import module_stc_power
from scripts.device_scenarios import _gamma_pmax
from scripts.exact_vector import array_dc_power

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def js(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def clear():
    sp._tandem_reference_subcell_yields.cache_clear();sp._tandem_sf_table.cache_clear();sp._tandem_reference_temperature_table.cache_clear()
def calibrated(base,target):
    low,high=.3,2.2
    for _ in range(50):
        mid=(low+high)/2
        if _gamma_pmax(replace(base,Ea_recomb=mid))>target:low=mid
        else:high=mid
    tech=replace(base,Ea_recomb=(low+high)/2)
    assert abs(_gamma_pmax(tech)-target)<1e-7
    return tech

def prepare_states():
    statefile=O/'inputs/path_states.csv'
    if statefile.exists():return pd.read_csv(statefile)
    records=[];tables={};density0=module_stc_power(CSI_MODERN)/(CSI_MODERN.area_cm2*CSI_MODERN.cells_in_series)*1e4
    gammas={n:_gamma_pmax(t) for n,t in [('single',PEROVSKITE),('tandem',TANDEM_2T)]}
    for name,base,label,target in [('single',PEROVSKITE,-.15,-.10),('tandem',TANDEM_2T,-.30,-.20)]:
        for i in range(11):
            lam=i/10
            goal=(1-lam)*gammas[name]+lam*target
            tech=base if i==0 else calibrated(base,goal)
            records.append(dict(state_id=f'{name}_{i:02}',technology=name,branch='main',step=i,progress=lam,
              gamma_nominal_pct_C=(1-lam)*label+lam*target,gamma_actual_pct_C=_gamma_pmax(tech),Ea_recomb_eV=tech.Ea_recomb,
              top_bandgap_eV=1.68+.07*lam if name=='tandem' else np.nan,spectral_scale=1.,module_stc_W=module_stc_power(tech),
              density_W_m2=module_stc_power(tech)/(tech.area_cm2*tech.cells_in_series)*1e4,
              density_ratio=module_stc_power(tech)/(tech.area_cm2*tech.cells_in_series)*1e4/density0))
    for i in [5,10]:
        main=next(x for x in records if x['state_id']==f'tandem_{i:02}')
        for branch in ['thermal_only','bandgap_only']:
            z=main.copy();z.update(state_id=f'tandem_{branch}_{i:02}',branch=branch)
            if branch=='thermal_only':z['top_bandgap_eV']=1.68
            else:z.update(Ea_recomb_eV=TANDEM_2T.Ea_recomb,gamma_actual_pct_C=gammas['tandem'],gamma_nominal_pct_C=-.30)
            records.append(z)
    states=pd.DataFrame(records)
    assert len(states)==26
    assert states.groupby('technology').density_ratio.agg(lambda a:np.ptp(a)).max()<1e-12
    states.to_csv(statefile,index=False,encoding='utf-8-sig')
    sp.TANDEM_BOTTOM_DEG_DT=-.0002677*1.121
    for eg in sorted(states.loc[states.technology.eq('tandem'),'top_bandgap_eV'].unique()):
        sp.TANDEM_TOP_EG_REF=float(eg);clear()
        z,t,v=sp._tandem_sf_table();key=f'{eg:.6f}';tables[key+'_zenith']=z;tables[key+'_temperature']=t;tables[key+'_values']=v
    sp.TANDEM_TOP_EG_REF=1.68;clear()
    np.savez_compressed(O/'inputs/tandem_spectral_tables.npz',**tables)
    temps=np.arange(15.,66.,5.);cal=[]
    from pvsim.cell import operating_point
    for z in records:
        base=PEROVSKITE if z['technology']=='single' else TANDEM_2T;tech=replace(base,Ea_recomb=z['Ea_recomb_eV'])
        for t in temps:cal.append(dict(state_id=z['state_id'],temperature_C=t,broadband_W_m2=1000,pmp_W=operating_point(tech,1000,float(t),ns=tech.cells_in_series).pmp))
    pd.DataFrame(cal).to_csv(O/'inputs/gamma_calibration_raw_points.csv',index=False,encoding='utf-8-sig')
    return states

def initialize():
    global STATES,TABLES,TRACE
    sy.array_dc_power=array_dc_power
    STATES=pd.read_csv(O/'inputs/path_states.csv').to_dict('records')
    TABLES=np.load(O/'inputs/tandem_spectral_tables.npz')
    TRACE=pd.read_csv(O/'inputs/PVGIS_369城市_数值与元数据精确出处.csv',dtype={'adcode':str}).set_index('adcode')

def weather_for(a):
    rec=TRACE.loc[a['adcode']];cache=P/rec.cache_file
    assert sha(cache)==rec.cache_sha256
    raw=pd.read_csv(cache,index_col=0,parse_dates=True)
    if raw.index.tz is None:raw.index=raw.index.tz_localize('UTC')
    assert len(raw)==8760 and abs(a['lat']-rec.used_latitude)<1e-9 and abs(a['lon']-rec.used_longitude)<1e-9
    assert abs(a['altitude_m']-rec.used_altitude_m)<1e-9
    loc=wx.get_location(a['lat'],a['lon'],altitude=a['altitude_m'],name=a['city'])
    return wx.make_weather(raw.index,loc,raw.ghi,raw.dni,raw.dhi,raw.temp_air,raw.wind_speed,irradiance_time_offset_h=float(rec.irradiance_time_offset_h))

def simulate_state(z,w,npts=60):
    tech=replace(PEROVSKITE if z['technology']=='single' else TANDEM_2T,Ea_recomb=z['Ea_recomb_eV'])
    orig=sy.spectral_factor_from_zenith
    if z['technology']=='tandem':
        key=f"{z['top_bandgap_eV']:.6f}"
        zg,tg,values=[TABLES[key+s] for s in ['_zenith','_temperature','_values']]
        def sf(t,zen,tcell_C=None):
            return sp._bilinear_lookup(zen,tcell_C,zg,tg,values) if t.name=='tandem' else orig(t,zen,tcell_C=tcell_C)
        sy.spectral_factor_from_zenith=sf
    try:return sy.simulate(tech,w,sy.SystemConfig(),npts=npts)['specific_yield']
    finally:sy.spectral_factor_from_zenith=orig

def run_anchor(a):
    dest=O/'results/anchor_shards'/f"{a['adcode']}.csv"
    if dest.exists():
        d=pd.read_csv(dest);assert len(d)==26
        return a['adcode'],0
    st=time.monotonic();w=weather_for(a);ref=sy.simulate(CSI_MODERN,w,sy.SystemConfig(),npts=60)['specific_yield'];rows=[]
    for z in STATES:
        yy=simulate_state(z,w)
        rows.append(dict(adcode=a['adcode'],city=a['city'],state_id=z['state_id'],yield_kwh_kwp=yy,csi_yield_kwh_kwp=ref))
    tmp=dest.with_suffix('.tmp');pd.DataFrame(rows).to_csv(tmp,index=False,encoding='utf-8-sig');tmp.replace(dest)
    return a['adcode'],time.monotonic()-st

def pilot(anchors):
    initialize();archive=pd.read_csv(R/'outputs/all_anchor_results.csv',dtype={'adcode':str});rows=[];precision=[]
    for a in anchors:
        w=weather_for(a);ref=sy.simulate(CSI_MODERN,w,sy.SystemConfig(),npts=60)['specific_yield']
        ref120=sy.simulate(CSI_MODERN,w,sy.SystemConfig(),npts=120)['specific_yield']
        for name,gamma,response in [('single',-.15,1),('tandem',-.3,1.68)]:
            z=next(x for x in STATES if x['state_id']==name+'_00');yy=simulate_state(z,w)
            old=archive[archive.adcode.eq(a['adcode'])&archive.technology.eq(name)&archive.gamma_pct_c.eq(gamma)&archive.response_parameter.eq(response)&archive.offset_h.eq(.5)&archive.bandgap_corrected.eq(name=='tandem')].iloc[0]
            err=max(abs(yy-old.yield_kwh_kwp),abs(ref-old.csi_yield_kwh_kwp));assert err<1e-7,(a['adcode'],name,err)
            rows.append(dict(adcode=a['adcode'],technology=name,uniform60_yield_kwh_kwp=yy,archive_scan60_yield_kwh_kwp=old.yield_kwh_kwp,max_abs_yield_error=err))
            for step in [0,10]:
                state=next(x for x in STATES if x['state_id']==f'{name}_{step:02}')
                v60=simulate_state(state,w);v120=simulate_state(state,w,120)
                precision.append(dict(adcode=a['adcode'],state_id=state['state_id'],gain60_pct=100*(v60/ref-1),gain120_pct=100*(v120/ref120-1),difference_pp=100*(v60/ref-v120/ref120)))
        run_anchor(a)
        print('Pilot passed',a['adcode'],flush=True)
    pd.DataFrame(rows).to_csv(O/'qa/pilot_baseline_equivalence.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame(precision).to_csv(O/'qa/pilot_solver_precision.csv',index=False,encoding='utf-8-sig')
    js(O/'qa/pilot_validation.json',dict(anchors=len(anchors),max_archive_scan_yield_error=max(x['max_abs_yield_error'] for x in rows),max_60_vs_120_gain_difference_pp=max(abs(x['difference_pp']) for x in precision),no_baseline_offsets=True))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--pilot',action='store_true');ap.add_argument('--workers',type=int,default=6);args=ap.parse_args()
    assert (O/'qa/input_validation.json').exists()
    prepare_states()
    files=list((O/'code/pvsim').glob('*.py'))+list((O/'code/scripts').glob('*.py'))+[Path(__file__),O/'inputs/path_states.csv',O/'inputs/tandem_spectral_tables.npz',O/'inputs/upstream_manifest.json']
    fp=hashlib.sha256(json.dumps({p.relative_to(O).as_posix():sha(p) for p in sorted(files)},sort_keys=True).encode()).hexdigest()
    mark=O/'qa/runtime_fingerprint.json'
    if mark.exists():assert json.loads(mark.read_text())['fingerprint']==fp,'Changed inputs/code require a new output version'
    else:js(mark,{'fingerprint':fp,'files':{p.relative_to(O).as_posix():sha(p) for p in sorted(files)}})
    (O/'results/anchor_shards').mkdir(exist_ok=True)
    anchors=pd.read_csv(O/'inputs/anchor_metadata.csv',dtype={'adcode':str}).sort_values('adcode').to_dict('records')
    if args.pilot:
        pilot([a for a in anchors if a['adcode'] in ['110000','310000','540100','650100']])
    else:
        assert (O/'qa/pilot_validation.json').exists(),'Run the baseline-equivalence pilot first'
        with ProcessPoolExecutor(max_workers=args.workers,initializer=initialize) as ex:
            futures=[ex.submit(run_anchor,a) for a in anchors]
            for i,f in enumerate(as_completed(futures),1):
                code,seconds=f.result()
                if i%10==0 or i==369:print(f'{i}/369 complete; last {code}, {seconds:.2f}s',flush=True)
        d=pd.concat([pd.read_csv(O/'results/anchor_shards'/f"{a['adcode']}.csv",dtype={'adcode':str}) for a in anchors],ignore_index=True)
        assert len(d)==369*26
        d.to_csv(O/'results/anchor_path_yields.csv',index=False,encoding='utf-8-sig')
        print('Completed',len(d),'anchor-state annual hourly calculations',flush=True)
