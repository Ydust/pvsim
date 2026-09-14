from pathlib import Path
import pandas as pd, numpy as np, json, hashlib, platform
Q=Path(__file__).parent; R=Q.parent/'public_field_search_round2_20260910/raw'; O=Q/'Source_Data'; O.mkdir(exist_ok=True)
w=pd.read_csv(R/'irradiance_and_cell_temp.csv',parse_dates=['Time'])
summ=[]; qc=[]; allpairs=[]
for cell in ['p1','p2','p4']:
 d=pd.read_csv(R/f'outdoor_mpp_d1_{cell}.csv',parse_dates=['Time']); n=len(d)
 d=d.merge(w,on='Time',how='left',validate='one_to_one',indicator=True)
 joined=int((d['_merge']=='both').sum())
 # Relative metric only: multiplicative power/area units cancel within device.
 valid=np.isfinite(d[['Irradiance','Tcell_back','Vmax','Imax','Pmax']]).all(axis=1)&(d.Irradiance>=50)&(d.Irradiance<=1200)&(d.Pmax>0)&(d.Vmax>0)&(d.Imax>0)
 x=d.loc[valid].copy(); x['response']=x.Pmax/x.Irradiance
 x['date']=x.Time.dt.strftime('%Y-%m-%d');x['year']=x.Time.dt.year;x['month']=x.Time.dt.month
 qc.append(dict(cell=cell,raw=n,exact_weather_matches=joined,retained=len(x),dates=x.date.nunique()))
 # Same calendar month (March) in successive years, all shared conditions retained.
 x=x[x.month==3].copy()
 for gw,tw in [(50,5),(100,5),(100,10)]:
  x['gb']=np.floor(x.Irradiance/gw).astype(int)*gw;x['tb']=np.floor(x.Tcell_back/tw).astype(int)*tw
  a=x.groupby(['year','date','gb','tb']).response.agg(['median','size']).reset_index();a=a[a['size']>=4]
  b=a.groupby(['year','gb','tb'])['median'].agg(['median','size']).reset_index();b=b[b['size']>=3]
  p=b[b.year==2022].merge(b[b.year==2023],on=['gb','tb'],suffixes=('_2022','_2023'))
  p['ratio_2023_2022']=p.median_2023/p.median_2022;p['cell']=cell;p['G_bin_width']=gw;p['T_bin_width']=tw
  allpairs.append(p)
  for label,lo,hi in [('low',50,200),('high',600,1000),('all',50,1200)]:
   z=p[(p.gb>=lo)&(p.gb+gw<=hi)]
   v=z.ratio_2023_2022
   summ.append(dict(cell=cell,G_bin_width=gw,T_bin_width=tw,band=label,shared_bins=len(z),median_ratio=float(v.median()) if len(z) else None,q25=float(v.quantile(.25)) if len(z) else None,q75=float(v.quantile(.75)) if len(z) else None))
  a['cell']=cell;a.to_csv(O/f'{cell}_daily_bins_G{gw}_T{tw}.csv',index=False)
pd.concat(allpairs).to_csv(O/'matched_bins.csv',index=False)
pd.DataFrame(summ).to_csv(O/'response_summary.csv',index=False)
pd.DataFrame(qc).to_csv(O/'quality_counts.csv',index=False)
(Q/'results.json').write_text(json.dumps({'quality':qc,'summary':summ,'software':{'python':platform.python_version(),'pandas':pd.__version__,'numpy':np.__version__}},indent=2),encoding='utf-8')
print(pd.DataFrame(summ).to_string(index=False));print(qc)
