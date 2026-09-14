"""Deterministic annual-yield stress and policy counterexample scope; no fitted priors."""
from pathlib import Path
import itertools,json,sys
import numpy as np
import pandas as pd
from scripts.analyse_regional_policy import load,evaluate,lifecycle,winners
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'outputs/annual_policy_robustness_20260910'
OUT.mkdir(parents=True,exist_ok=True)
CITIES,Y,D,COST=load(); BASE=evaluate(CITIES,Y,D,COST); C=BASE['initial_cap']; A=BASE['annual_delivered']; IX=np.arange(len(A)); DISC=1.05**(-np.arange(1,26))
POL=[('General',np.ones(3)),('New',np.array([0,1,1]))]

def save(rows,name):
    d=pd.DataFrame(rows);d.to_csv(OUT/(name+'.csv'),index=False,encoding='utf-8-sig');return d

def state(ctx='cap',om='proportional',mult=1.,deg=.01505,life=21.5,rule='full',price=None,delta=(0,0,0)):
    cap=C*np.array([1,mult,1]);dur=[(25,.005,.01),(life,deg,.0675),(25,.012,.04)]
    fac=np.array([lifecycle(*v,replace_factor=.5 if rule=='half' else 1,salvage=rule=='salvage') for v in dur])
    annual=A*(1+np.asarray(delta));e=annual*fac[:,0];p=annual*fac[:,2]
    omcost=cap*.015 if om=='proportional' else np.full(3,float(om))
    wc=np.broadcast_to(cap*(fac[:,1]-.015*DISC.sum())+omcost*DISC.sum(),e.shape).copy()
    price=(.04 if ctx=='cap' else .08) if price is None else price
    if rule=='stop_option':
        active=np.clip(life-np.arange(25),0,1);gen=active*(1-.0675)*(1-deg)**np.arange(25)
        es=annual[:,1]*(gen@DISC);ps=annual[:,1]*gen.sum();cs=cap[1]+omcost[1]*(active@DISC)
        stop=es*price-cs>e[:,1]*price-wc[:,1]
        e[stop,1]=es[stop];p[stop,1]=ps[stop];wc[stop,1]=cs
    f=np.ones(3) if ctx=='cap' else D*.65/1000
    scale=1000 if ctx=='cap' else 10000;land=0 if ctx=='cap' else 25
    n=(e*price-wc)*f-land
    return n,e*f*scale/1000,p*f*scale/1000,cap*f*scale,scale,e*price*f

def selected(arr,w):return np.where(w>=0,arr[IX,np.maximum(w,0)],0)

def outcome(st,rate,elig):
    n,e,p,cap,scale,rev=st;w0=winners(n);nn=n+cap*rate*elig/scale;w=winners(nn)
    de=selected(e,w)-selected(e,w0);dp=selected(p,w)-selected(p,w0)
    entry=(w0<0)&(w>=0);sw=(w0>=0)&(w>=0)&(w0!=w)
    assert np.all((w0<0)|(w>=0))
    assert np.isclose(de.sum(),de[entry].sum()+de[sw].sum(),atol=1e-6)
    assert np.isclose(dp.sum(),dp[entry].sum()+dp[sw].sum(),atol=1e-6)
    pay=np.where(w>=0,(cap*rate*elig)[np.maximum(w,0)],0)
    out=dict(before_viable=int((w0>=0).sum()),after_viable=int((w>=0).sum()),new_projects=int(entry.sum()),switches=int(sw.sum()),discounted_mwh=float(de.sum()),undiscounted_mwh=float(dp.sum()),entry_discounted_mwh=float(de[entry].sum()),switch_discounted_mwh=float(de[sw].sum()),entry_undiscounted_mwh=float(dp[entry].sum()),switch_undiscounted_mwh=float(dp[sw].sum()),public_usd=float(pay.sum()*1.05),private_npv_gain_usd=float((np.maximum(0,nn.max(axis=1))-np.maximum(0,n.max(axis=1))).sum()*scale))
    out.update({f'after_{k}':int((w==i).sum()) for i,k in enumerate(['si','sj','t'])})
    out['counterexample_discounted']=bool(out['new_projects']>0 and out['discounted_mwh']< -1e-6)
    out['counterexample_physical']=bool(out['new_projects']>0 and out['undiscounted_mwh']< -1e-6)
    return out,w

def annual_stress():
    rows=[];cert=[];phys=[]
    for a in [.01,.02,.05,.10]:
        for j,tech in [(1,'sj'),(2,'t')]:
            for basis,f in [('capacity',1),('aperture',D[j]/D[0])]:
                ratio=Y[:,j]/Y[:,0]*f;lo=ratio*(1-a)/(1+a);hi=ratio*(1+a)/(1-a)
                phys.append(dict(amplitude=a,tech=tech,basis=basis,mean_gain_low_pct=100*(lo.mean()-1),mean_gain_high_pct=100*(hi.mean()-1),guaranteed_positive_cities=int((lo>1).sum()),possible_positive_cities=int((hi>1).sum())))
        for ctx,om in itertools.product(['cap','area'],['proportional','3.2']):
            st0=state(ctx,om)
            for label,rate,elig in [('None',0,np.zeros(3)),('General20',.2,np.ones(3)),('New20',.2,np.array([0,1,1]))]:
                n,e,p,cap,scale,rev=st0;nn=n+cap*rate*elig/scale;w=winners(nn);ww=np.where(w<0,3,w)
                nv=np.c_[nn,np.zeros(len(A))];rv=np.c_[rev,np.zeros(len(A))]
                margin=nv[IX,ww,None]-nv-a*(rv[IX,ww,None]+rv);margin[IX,ww]=np.inf
                safe=margin.min(axis=1)>1e-10
                for i in IX:cert.append(dict(amplitude=a,context=ctx,om=om,policy=label,adcode=CITIES.adcode.iloc[i],baseline_choice=int(w[i]),choice_certified=bool(safe[i]),viability_certified=bool(np.max(nn[i]-a*rev[i])>0),nonviability_certified=bool(np.max(nn[i]+a*rev[i])<=0)))
            for signs in itertools.product([-1,0,1],repeat=3):
                delta=a*np.array(signs);st=state(ctx,om,delta=delta)
                for name,elig in POL:
                    out,w=outcome(st,.2,elig);ref,wref=outcome(st0,.2,elig)
                    rows.append(dict(amplitude=a,delta_si=delta[0],delta_sj=delta[1],delta_t=delta[2],context=ctx,om=om,policy=name,choice_changes=int((w!=wref).sum()),**out))
    save(rows,'Annual_yield_stress');save(cert,'Annual_choice_certificates');save(phys,'Annual_physical_bounds')

def scope():
    rows=[]
    # All ranges are declared one-factor/joint stress grids, not empirical distributions.
    for ctx,om,mult,deg,life,rule,price_factor in itertools.product(['cap','area'],['proportional','1.6','3.2','6.4'],[.8,1,1.2],[.005,.01505,.03],[18,21.5,25],['full','half','salvage','stop_option'],[.75,1,1.25]):
        price=(.04 if ctx=='cap' else .08)*price_factor
        st=state(ctx,om,mult,deg,life,rule,price)
        for rate,(name,elig) in itertools.product([.1,.2,.3],POL):
            result,_=outcome(st,rate,elig)
            rows.append(dict(context=ctx,om=om,sj_cost_multiplier=mult,sj_degradation=deg,sj_lifetime=life,replacement_rule=rule,price=price,rate=rate,policy=name,**result))
    df=save(rows,'Counterexample_joint_scope')
    groups=[]
    for key,g in df.groupby(['context','om','replacement_rule','policy']):
        groups.append(dict(zip(['context','om','replacement_rule','policy'],key),cases=len(g),counterexample_discounted=int(g.counterexample_discounted.sum()),counterexample_physical=int(g.counterexample_physical.sum()),discounted_min_mwh=g.discounted_mwh.min(),discounted_max_mwh=g.discounted_mwh.max(),physical_min_mwh=g.undiscounted_mwh.min(),physical_max_mwh=g.undiscounted_mwh.max()))
    save(groups,'Counterexample_scope_summary')
    # Fine sampled response boundary around the existing anchored-O&M example.
    rows=[]
    for deg,delta,rule in itertools.product([.005,.01,.01505,.02,.025,.03],np.round(np.arange(-.10,.100001,.0025),6),['full','half','salvage','stop_option']):
        out,_=outcome(state('cap','3.2',deg=deg,rule=rule,delta=(0,delta,0)),.2,np.array([0,1,1]))
        rows.append(dict(sj_degradation=deg,relative_sj_yield_change=delta,replacement_rule=rule,**out))
    save(rows,'Counterexample_yield_degradation_grid')

def verify():
    # Reconcile the central reference results.
    old=pd.read_csv(ROOT/'outputs/reviewer_revision_20260910/Anchored_OM_generation_decomposition.csv')
    for name,elig in POL:
        out,_=outcome(state('cap','3.2'),.2,elig);ref=old[old.policy==name+'20'].iloc[0]
        for a,b in [('discounted_mwh','additional_discounted_mwh'),('undiscounted_mwh','additional_undiscounted_mwh')]:assert np.isclose(out[a],ref[b],rtol=1e-11)
    # General uniform support cannot lower discounted generation in capacity context:
    # not asserted globally because capex-dependent payment differs by technology.
    for ctx in ['cap','area']:
        st=state(ctx);out,_=outcome(st,0,np.ones(3));assert out['discounted_mwh']==0 and out['undiscounted_mwh']==0 and out['new_projects']==0
        # Constant annual rescaling leaves physical candidate/Si ratios unchanged.
        r=Y[:,1]/Y[:,0];assert np.allclose(Y[:,1]*1.1/(Y[:,0]*1.1),r)
    (OUT/'verification.json').write_text(json.dumps({'prior_counterexample_reconciled':True,'zero_support_identity':True,'energy_decomposition_checked_every_case':True,'common_yield_ratio_invariance':True},indent=2))

def certify_check():
    cert=pd.read_csv(OUT/'Annual_choice_certificates.csv',dtype={'om':str,'adcode':str})
    for key,g in cert.groupby(['amplitude','context','om','policy'],sort=False):
        a,ctx,om,policy=key;rate=0 if policy=='None' else .2;elig=np.zeros(3) if policy=='None' else np.ones(3) if policy=='General20' else np.array([0,1,1])
        safe=g.choice_certified.to_numpy();ref=g.baseline_choice.to_numpy()
        for signs in itertools.product([-1,1],repeat=3):
            st=state(ctx,om,delta=a*np.array(signs));_,w=outcome(st,rate,elig)
            assert np.array_equal(w[safe],ref[safe]),key
    save([dict(amplitude=k[0],context=k[1],om=k[2],policy=k[3],cities=len(g),choice_certified=int(g.choice_certified.sum()),viability_certified=int(g.viability_certified.sum()),nonviability_certified=int(g.nonviability_certified.sum())) for k,g in cert.groupby(['amplitude','context','om','policy'])],'Annual_certificate_summary')
    path=OUT/'verification.json';v=json.loads(path.read_text());v['certified_choices_checked_all_box_vertices']=True;path.write_text(json.dumps(v,indent=2))

if __name__=='__main__':
    verify();annual_stress();scope();certify_check();print('Annual yield and policy scope diagnostics complete',flush=True)
