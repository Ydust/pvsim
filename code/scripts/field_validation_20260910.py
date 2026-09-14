from pathlib import Path
import sys,json,hashlib,os,argparse
ap=argparse.ArgumentParser();ap.add_argument('--project-root',type=Path,default=Path.cwd());ap.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
args=ap.parse_args();ROOT=args.project_root.resolve();Q=args.output.resolve();Q.mkdir(parents=True,exist_ok=True);os.chdir(ROOT)
sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True
import numpy as np,pandas as pd
from pvsim.cell import operating_point
from pvsim.materials import PEROVSKITE,CSI_MODERN
from pvsim.city_catalog import load_city_catalog
from pvsim.weather import from_pvgis_tmy
from pvsim.temperature import cell_temperature
from scripts.jaramillo_montoya_outdoor_validation import audit_raw_files,build_paired_data
S=Q/'Source_Data';S.mkdir(exist_ok=True)
audit=audit_raw_files();pairs=build_paired_data();assert len(pairs)==4205
pairs['row_id']=np.arange(len(pairs))
raw=pairs.psm_pmax_w/pairs.silicon_pmax_w
pairs['raw_power_ratio']=raw
pred=[]
for r in pairs.itertuples():
    pp=operating_point(PEROVSKITE,r.irradiance_w_m2,r.Panel_temperature_1).pmp
    sp=operating_point(CSI_MODERN,r.irradiance_w_m2,r.Panel_temperature_2).pmp
    pred.append(pp/sp)
pairs['model_power_ratio']=pred
predictions=[];splits=[]
for session,g in pairs.groupby('session'):
    days=sorted(g.calendar_day.unique());cut=max(1,len(days)//2)
    plans=[('chronological',','.join(days[cut:]),g.calendar_day.isin(days[:cut]),g.calendar_day.isin(days[cut:]))]
    plans += [('leave_one_day_out',day,g.calendar_day.ne(day),g.calendar_day.eq(day)) for day in days]
    for mode,fold,trainmask,testmask in plans:
        train=g.loc[trainmask];test=g.loc[testmask].copy();high=train.irradiance_w_m2.between(900,1100)
        assert high.sum()>=20,(session,fold,high.sum())
        obsref=float(train.loc[high,'raw_power_ratio'].median());modref=float(train.loc[high,'model_power_ratio'].median())
        test['observed_normalized_ratio']=test.raw_power_ratio/obsref
        test['predicted_normalized_ratio']=test.model_power_ratio/modref
        test['log_error']=np.log(test.predicted_normalized_ratio/test.observed_normalized_ratio)
        test['log_error_constant']=np.log(1/test.observed_normalized_ratio)
        test['split']=mode;test['fold']=fold
        predictions.append(test)
        splits.append(dict(session=session,split=mode,fold=fold,train_days=';'.join(sorted(train.calendar_day.unique())),test_days=';'.join(sorted(test.calendar_day.unique())),train_n=len(train),test_n=len(test),reference_n=int(high.sum()),observed_reference=obsref,model_reference=modref))
out=pd.concat(predictions,ignore_index=True)
out.to_csv(S/'paired_holdout_predictions.csv',index=False)
out[(out['split']=='leave_one_day_out')&(out.session=='PSM50')].groupby('calendar_day').agg(n=('log_error','size'),log_bias=('log_error','mean'),mse=('log_error',lambda v:np.mean(v*v))).to_csv(S/'day_level_error_audit.csv')
pd.DataFrame(splits).to_csv(S/'holdout_split_register.csv',index=False)
rng=np.random.default_rng(20260910);summaries=[]
for (mode,session),g in out.groupby(['split','session']):
    for band,low,high in [('all',150,1201),('150–500',150,500),('500–900',500,900),('900–1200',900,1201)]:
        z=g[g.irradiance_w_m2.ge(low)&g.irradiance_w_m2.lt(high)]
        if z.empty:continue
        ds=z.groupby('calendar_day').agg(bias=('log_error','mean'),mse=('log_error',lambda v:np.mean(v*v)),mse_constant=('log_error_constant',lambda v:np.mean(v*v)),obs=('observed_normalized_ratio','median'),model=('predicted_normalized_ratio','median'))
        # Descriptive day-equal metrics; days are within-device temporal blocks, not independent devices.
        bs=ds.bias.to_numpy()[rng.integers(0,len(ds),(2000,len(ds)))].mean(axis=1)
        summaries.append(dict(split=mode,session=session,band=band,n=len(z),days=len(ds),day_equal_log_bias=ds.bias.mean(),log_bias_p025=np.quantile(bs,.025) if len(ds)>=3 else np.nan,log_bias_p975=np.quantile(bs,.975) if len(ds)>=3 else np.nan,day_equal_log_rmse=np.sqrt(ds.mse.mean()),constant_ratio_log_rmse=np.sqrt(ds.mse_constant.mean()),day_median_observed_ratio=ds.obs.median(),day_median_predicted_ratio=ds.model.median()))
pd.DataFrame(summaries).to_csv(S/'holdout_summary.csv',index=False)
print('Holdout complete',flush=True)
tandem=pd.read_csv('outputs/si_aydin_tandem_outdoor_pairs.csv');assert len(tandem)==377
domains={'single_junction':(pairs.irradiance_w_m2.to_numpy(),pairs.Panel_temperature_1.to_numpy()),'tandem_2T':(tandem.irradiance_suns.to_numpy()*1000,tandem.tandem_cell_temperature_c.to_numpy())}
grid=[(50,2.5),(100,5),(200,10)];histograms={};regs=[]
for tech,(gg,tt) in domains.items():
    for dg,dt in grid:
        keys=np.floor(gg/dg).astype(int)*1000+np.floor(tt/dt).astype(int)
        u,c=np.unique(keys,return_counts=True);histograms[(tech,dg,dt)]=(u,c)
        for k,n in zip(u,c):regs.append(dict(technology=tech,irradiance_bin_wm2=dg,temperature_bin_c=dt,key=int(k),n=int(n)))
pd.DataFrame(regs).to_csv(S/'observed_operating_domain_bins.csv',index=False)
coverage=[];cityhash=[]
for i,city in enumerate(load_city_catalog()):
    w=from_pvgis_tmy(city.lat,city.lon,altitude=city.altitude_m,name=city.cache_key,allow_download=False)
    gg=w.poa_global.to_numpy();tt=cell_temperature(gg,w.temp_air.to_numpy(),w.wind_speed.to_numpy(),model='faiman',u0=25,u1=6.84)
    day=gg>=20;weight=gg[day];temp=np.asarray(tt)[day];g=gg[day]
    assert len(w)==8760 and np.isfinite(temp).all()
    for tech,(fg,ft) in domains.items():
        rect=(g>=fg.min())&(g<=fg.max())&(temp>=ft.min())&(temp<=ft.max())
        coverage.append(dict(adcode=city.adcode,city=city.city,technology=tech,definition='bounding_rectangle',irradiance_bin_wm2=0,temperature_bin_c=0,min_observations=0,daylight_hours=int(day.sum()),fraction_hours=rect.mean(),fraction_poa=np.sum(weight[rect])/weight.sum()))
        for dg,dt in grid:
            keys=np.floor(g/dg).astype(int)*1000+np.floor(temp/dt).astype(int);u,c=histograms[(tech,dg,dt)]
            for n in [1,5,20]:
                ok=np.isin(keys,u[c>=n]);coverage.append(dict(adcode=city.adcode,city=city.city,technology=tech,definition='occupied_bins',irradiance_bin_wm2=dg,temperature_bin_c=dt,min_observations=n,daylight_hours=int(day.sum()),fraction_hours=ok.mean(),fraction_poa=np.sum(weight[ok])/weight.sum()))
    fp=Path('data/tmy_cache')/(city.cache_key+'.csv');cityhash.append(dict(adcode=city.adcode,file=str(fp),sha256=hashlib.sha256(fp.read_bytes()).hexdigest()))
    if (i+1)%50==0:print('Coverage',i+1,flush=True)
cov=pd.DataFrame(coverage);assert cov.adcode.nunique()==337 and len(cov)==6740
cov.to_csv(S/'city_operating_domain_overlap.csv',index=False)
cs=cov.groupby(['technology','definition','irradiance_bin_wm2','temperature_bin_c','min_observations']).agg(cities=('adcode','size'),median_poa=('fraction_poa','median'),min_poa=('fraction_poa','min'),max_poa=('fraction_poa','max'),median_hours=('fraction_hours','median')).reset_index()
cs.to_csv(S/'operating_domain_overlap_summary.csv',index=False)
pd.DataFrame(cityhash).to_csv(S/'weather_input_hashes.csv',index=False)
report={'raw_integrity':audit,'paired_rows':4205,'paired_days':15,'single_junction_devices':2,'single_junction_sites':1,'tandem_rows':377,'tandem_day_clusters':9,'tandem_sites':1,'national_city_anchors':337,'night_exclusion':'POA <20 W/m2','overlap_weight':'incident POA irradiation, not generated electricity','holdout':'Chronological first floor(n_days/2) training days; remaining days test. Leave-one-day-out sensitivity. High-reference normalization only in training, 900–1100 W/m2. No national parameters fitted.','uncertainty':'2000 day resamples within each device, seed 20260910; conditional temporal dispersion, not between-device/site uncertainty. No intervals with <3 days.','limitations':'Power ratio normalized to training high-irradiance reference is not STC specific yield or annual technology preference. Broadband transfer diagnostic lacks measured spectra and incidence angle. Domain overlap does not establish prediction accuracy, nationwide ranks or long-term durability.'}
(S/'analysis_protocol.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(cs[(cs.definition=='bounding_rectangle')|((cs.irradiance_bin_wm2==100)&(cs.min_observations==5))].to_string(index=False),flush=True)
print(pd.DataFrame(summaries).query("split=='chronological' and band=='all'").to_string(index=False),flush=True)
