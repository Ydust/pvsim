from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[2]));sys.dont_write_bytecode=True
import numpy as np,pandas as pd
from scripts.analyse_regional_policy import load,evaluate,lifecycle,winners
from pvsim.economics import MODERN_CSI_DURABILITY,TANDEM_DURABILITY,perovskite_durability
Q=Path(__file__).resolve().parent;O=Q/'deliverables/Source_Data';O.mkdir(parents=True,exist_ok=True)
c,y,d,k=load();base=evaluate(c,y,d,k);dur=[MODERN_CSI_DURABILITY,perovskite_durability(2035,2035,21.5),TANDEM_DURABILITY]
central=[dict(life=v.lifetime_years,deg=v.degradation_rate,burn=v.burn_in_loss) for v in dur]
specs=[('Central',{})]
for name,vals in [('om',[.01,.02]),('sj_deg',[.007,.03]),('t_deg',[.005,.02]),('sj_burn',[0,.10]),('t_burn',[0,.10]),('t_life',[18.,21.5]),('si_deg',[.007,.01]),('packing',[.5,.8]),('site',[0.,50.])]:
 for val in vals:specs.append((f'{name}={val}',{name:val}))
rows=[];detail=[];ix=np.arange(len(c))
for case,kw in specs:
 ds=[x.copy() for x in central]
 for tech,j in [('si',0),('sj',1),('t',2)]:
  for field in ['life','deg','burn']:
   if tech+'_'+field in kw:ds[j][field]=kw[tech+'_'+field]
 factors=np.array([lifecycle(**x) for x in ds]);om=kw.get('om',.015)
 factors[:,1]+=(om-.015)*np.sum(1.05**(-np.arange(1,26)))
 energy=y*c.utilization_low.to_numpy()[:,None]*factors[:,0]
 cap=base['initial_cap'];whole=cap*factors[:,1];packing=kw.get('packing',.65);site=kw.get('site',25.)
 for ctx,scale,price,f,land in [('cap',1000.,.04,np.ones(3),0),('area',10000.,.08,d*packing/1000,site)]:
  p=(energy*price*f-whole*f-land)*scale;construction=cap*f*scale;en=energy*f*scale/1000
  if case=='Central':assert np.allclose(p,base['npv_'+ctx]*scale)
  w=winners(p);b=np.maximum(0,p.max(axis=1));eb=np.where(w>=0,en[ix,np.maximum(w,0)],0)
  for share in [0.,.1,.2,.3]:
   general=np.broadcast_to(construction*share,p.shape).copy();nt=general.copy();nt[:,0]=0
   vg=winners(p+general);gap=np.zeros_like(p);changed=(vg>=0)&(vg!=w)
   gap[ix[changed],vg[changed]]=np.maximum(0,b[changed]-p[ix[changed],vg[changed]])+1
   assert (gap<=general+1e-5).all()
   for policy,tr in [('General',general),('New technology',nt),('Matched gap',gap)]:
    v=winners(p+tr);paid=np.where(v>=0,tr[ix,np.maximum(v,0)],0);after=np.maximum(0,(p+tr).max(axis=1))
    ea=np.where(v>=0,en[ix,np.maximum(v,0)],0)
    if policy=='Matched gap':assert np.array_equal(v,vg)
    assert (after>=b-1e-7).all()
    rows.append(dict(case=case,context=ctx,strategy=policy,share=share,before_viable=int((w>=0).sum()),after_viable=int((v>=0).sum()),after_si=int((v==0).sum()),after_sj=int((v==1).sum()),after_t=int((v==2).sum()),total_public_usd=float(paid.sum()*1.05),private_gain_usd=float((after-b).sum()),additional_discounted_mwh=float((ea-eb).sum())))
  for j,tech in enumerate(['Si','SJ','T']):
   detail.append(pd.DataFrame(dict(case=case,context=ctx,adcode=c.adcode,technology=tech,npv_usd=p[:,j],discounted_mwh=en[:,j],construction_usd=construction[j])))
r=pd.DataFrame(rows);r.to_csv(O/'Parameter_stress_policy_summary.csv',index=False,encoding='utf-8-sig')
pd.concat(detail).to_csv(O/'Parameter_stress_city_technology.csv',index=False,encoding='utf-8-sig')
(O/'Parameter_stress_definitions.json').write_text(json.dumps({'central_durability':central,'specs':dict(specs),'scope':'One-at-a-time deterministic accounting stress; fixed hourly yield; not a probability or independent device validation; O&M independent of replacement; lifetime perturbation does not change burn-in or annual degradation.','checks':{'baseline_reproduced':True,'gap_portfolios_reproduced':True,'cases':len(specs),'summary_rows':len(r)}},indent=2),encoding='utf8')
print(r.query("share==.2 and strategy=='General'")[['case','context','after_si','after_sj','after_t','after_viable']].to_string(index=False))
