from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[2]));sys.stdout.reconfigure(encoding='utf-8')
import numpy as np,pandas as pd
from scripts.analyse_regional_policy import load,evaluate,winners
Q=Path(__file__).resolve().parent;S=Q/'deliverables/Source_Data'
c,y,d,k=load();ix=np.arange(len(c));rows=[]
specs=[('Central',{}),('Discount3%',{'r':.03}),('Discount8%',{'r':.08}),('Investment85%',{'cap_multiplier':.85}),('Investment115%',{'cap_multiplier':1.15}),('SingleLife18',{'single_life':18.}),('SingleLife25',{'single_life':25.}),('HalfReplacement',{'replacement_factor':.5}),('ResidualValue',{'salvage':True}),('LowElectricity',{'price_cap':.03,'price_area':.06}),('HighElectricity',{'price_cap':.05,'price_area':.10})]
for case,kw in specs:
 e=evaluate(c,y,d,k,**kw)
 for ctx,scale in [('cap',1000),('area',10000)]:
  p=e['npv_'+ctx]*scale;w=winners(p);b=np.maximum(0,p.max(axis=1));cost=e['initial_cap']*(1 if ctx=='cap' else d*.65/1000)*scale
  energy=e['delivered_pv_kwh_kwp']*(scale if ctx=='cap' else d*.65/1000*scale)/1000;eb=np.where(w>=0,energy[ix,np.maximum(w,0)],0)
  for share in [.1,.2,.3]:
   g=np.broadcast_to(cost*share,p.shape).copy();vg=winners(p+g)
   t=np.zeros_like(p);mask=(vg>=0)&(vg!=w);t[ix[mask],vg[mask]]=np.maximum(0,b[mask]-p[ix[mask],vg[mask]])+1
   assert (t<=g+1e-5).all()
   nt=g.copy();nt[:,0]=0
   for policy,a in [('General',g),('New technology',nt),('Matched gap',t)]:
    v=winners(p+a);gain=np.maximum(0,(p+a).max(axis=1))-b;paid=np.where(v>=0,a[ix,np.maximum(v,0)],0)
    ea=np.where(v>=0,energy[ix,np.maximum(v,0)],0)
    if policy=='Matched gap':assert np.array_equal(v,vg)
    for admin in [0,.05,.10]:
     rows.append(dict(case=case,context=ctx,strategy=policy,share=share,admin_fraction=admin,before_viable=int((w>=0).sum()),after_viable=int((v>=0).sum()),after_si=int((v==0).sum()),after_sj=int((v==1).sum()),after_t=int((v==2).sum()),direct_support_usd=paid.sum(),total_public_usd=paid.sum()*(1+admin),private_gain_usd=gain.sum(),additional_discounted_mwh=(ea-eb).sum()))
r=pd.DataFrame(rows);r.to_csv(S/'Figure5_policy_sensitivity.csv',index=False)
(S/'Sensitivity_definitions.json').write_text(json.dumps(dict(specs),indent=2),encoding='utf-8')
print('Sensitivity records',len(r));print(r.query("share==.2 and context=='cap' and admin_fraction==.05 and strategy=='General'")[['case','after_viable','after_si','after_sj','after_t']].to_string(index=False))
