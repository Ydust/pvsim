"""Deterministic electrical, coverage and economic diagnostics.

Run from project root. Structural alternatives are not empirical probabilities.
"""
from pathlib import Path
import sys,json,itertools,time
from concurrent.futures import ProcessPoolExecutor,as_completed
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/reviewer_revision_20260910'
OUT.mkdir(parents=True,exist_ok=True)
def save(d,n): pd.DataFrame(d).to_csv(OUT/(n+'.csv'),index=False,encoding='utf-8-sig')

def reference_check():
    import pvsim.spectral as sp
    rows=[]; errors=[]
    old=sp.TANDEM_TOP_EG_REF
    for gap in [1.60,1.68,1.75]:
        sp.TANDEM_TOP_EG_REF=gap; sp._tandem_reference_subcell_yields.cache_clear()
        wl,E=sp.reference_am15g(); tr,br=sp._tandem_subcell_weights(wl,E,25)
        # q/(hc) converts the wavelength-weighted integral to A/m2.
        c=1.602176634e-19/(6.62607015e-34*299792458)*1e-9
        at=min(tr,br)/tr;ab=min(tr,br)/br
        rows.append(dict(gap_eV=gap,top_reference_A_m2=tr*c,bottom_reference_A_m2=br*c,top_bottom_ratio=tr/br,top_collection_scale=at,bottom_collection_scale=ab,matched_current_A_m2=min(tr,br)*c))
        for z,t in itertools.product([0,20,40,60,80],[-10,25,60,80]):
            w,s=sp.generate_spectrum(z);top,bot=sp._tandem_subcell_weights(w,s,t)
            G=sp._broadband(s,w);Gref=sp._broadband(E,wl)
            legacy=sp.tandem_current_matching_factor(w,s,t)
            matched=min(at*top,ab*bot)/min(at*tr,ab*br)*Gref/G
            raw=min(top,bot)/min(tr,br)*Gref/G
            assert abs(legacy-matched)<1e-12
            errors.append(dict(gap_eV=gap,zenith_deg=z,temperature_C=t,legacy_factor=legacy,explicit_matched_factor=matched,raw_ratio_factor=raw))
    sp.TANDEM_TOP_EG_REF=old;sp._tandem_reference_subcell_yields.cache_clear()
    save(rows,'Tandem_reference_currents');save(errors,'Tandem_structural_factors')

def raw_table(gap):
    import pvsim.spectral as sp
    old=sp.TANDEM_TOP_EG_REF;sp.TANDEM_TOP_EG_REF=gap
    try:
        w,e=sp.reference_am15g();tr,br=sp._tandem_subcell_weights(w,e,25);gref=sp._broadband(e,w)
        zs=np.linspace(0,88,13);ts=np.linspace(-10,80,10);v=np.zeros((len(ts),len(zs)))
        for j,z in enumerate(zs):
            wl,E=sp.generate_spectrum(z);g=sp._broadband(E,wl)
            for i,t in enumerate(ts):v[i,j]=min(sp._tandem_subcell_weights(wl,E,t))/min(tr,br)*gref/g
        return zs,ts,v
    finally:sp.TANDEM_TOP_EG_REF=old

def city_scan(a):
    import pvsim.system as sy
    import pvsim.spectral as sp
    from pvsim import weather as wx
    from pvsim.materials import CSI_MODERN
    from scripts.strengthen_figure1_science import gamma_tech
    dest=OUT/'shards'/f'{a.adcode}.csv'
    if dest.exists():return
    w=wx.from_pvgis_tmy(a.lat,a.lon,altitude=a.altitude_m,name=a.cache_key,allow_download=False)
    original=sy.spectral_factor_from_zenith;cfg=sy.SystemConfig()
    si=sy.simulate(CSI_MODERN,w,cfg,npts=60)['specific_yield'];r=[]
    for gap in [1.60,1.68,1.75]:
        z,t,v=raw_table(gap)
        def sf(tech,zen,tcell_C=None):
            return sp._bilinear_lookup(zen,tcell_C,z,t,v) if tech.name=='tandem' else original(tech,zen,tcell_C=tcell_C)
        try:
            sy.spectral_factor_from_zenith=sf
            for gamma in [-.4,-.3,-.2]:
                y=sy.simulate(gamma_tech('tandem',gamma),w,cfg,npts=60)['specific_yield']
                r.append(dict(adcode=str(a.adcode),gamma=gamma,gap=gap,yield_kwh_kwp=y,csi_kwh_kwp=si))
        finally:sy.spectral_factor_from_zenith=original
    dest.parent.mkdir(exist_ok=True);pd.DataFrame(r).to_csv(dest,index=False)

def aggregate():
    from scripts.deepen_figures234_analysis import spatial_operator,read
    from scripts import build_prefecture_area_model_outputs as b
    a=read(b.ANCHOR_SUMMARY).sort_values('adcode').reset_index(drop=True);op=spatial_operator(a)
    old=read('outputs/figures234_submission_20260907/Figure3_parameter_city_results.csv')
    raw=pd.concat([pd.read_csv(x,dtype={'adcode':str}) for x in (OUT/'shards').glob('*.csv')]);assert len(raw)==3033
    records=[];summary=[]
    for (gamma,gap),g in raw.groupby(['gamma','gap']):
        g=g.set_index('adcode').loc[a.adcode];py=op@g.yield_kwh_kwp;sy=op@g.csi_kwh_kwp
        ref=old[(old.technology=='tandem')&(old.gamma_pct_c==gamma)&(old.response_parameter==gap)&(old.density_scale==1)].set_index('adcode').loc[a.adcode]
        cp=100*(py/sy-1);ar=100*(py/sy*ref.density_ratio.to_numpy()-1)
        d=a[['adcode','city','province']].copy();d['gamma']=gamma;d['gap']=gap;d['raw_capacity_pct']=cp;d['matched_capacity_pct']=ref.capacity_advantage_pct.to_numpy();d['raw_area_pct']=ar;d['raw_yield_kwh_kwp']=py
        records.append(d);summary.append(dict(gamma=gamma,gap=gap,matched_positive=int((d.matched_capacity_pct>0).sum()),raw_positive=int((cp>0).sum()),raw_area_positive=int((ar>0).sum()),raw_area_min=float(min(ar)),raw_mean=float(np.mean(cp)),matched_mean=float(d.matched_capacity_pct.mean()),classification_changed=int(((cp>0)!=(d.matched_capacity_pct.to_numpy()>0)).sum())))
    save(pd.concat(records),'Tandem_raw_ratio_city');save(summary,'Tandem_raw_ratio_summary')

def coverage():
    from scripts.deepen_figures234_analysis import read,spatial_operator
    from scripts import build_prefecture_area_model_outputs as b
    a=read(b.ANCHOR_SUMMARY).sort_values('adcode').reset_index(drop=True);op=spatial_operator(a)
    scan=read('outputs/figure1_science_20260906/parameter_scan.csv');rows=[];tail=[]
    for (gamma,s),g in scan[(scan.tech=='single')&(scan.efficiency_ratio_scale==1)].groupby(['gamma_target_pct_per_c','response_parameter']):
        g=g.set_index('adcode').loc[a.adcode];yr=g.yield_kwh_per_kwp.to_numpy();si=g.csi_yield_kwh_per_kwp.to_numpy()
        density=float(((1+g.area_advantage_pct/100)/(1+g.capacity_advantage_pct/100)).median())
        for scheme,ratio in [('Primary',op@yr/(op@si)),('City anchor',yr/si)]:
            req=100*(1/(density*ratio)-1)
            for remove in ['None',*sorted(a.province_code.unique())]:
                mask=np.ones(len(a),bool) if remove=='None' else a.province_code.to_numpy()!=remove
                vals=np.sort(req[mask]);n=len(vals)
                for q in [.5,.9,.95,.99,1.]:rows.append(dict(gamma=gamma,spectral_scale=s,spatial=scheme,left_out_province=remove,coverage=q,n=n,threshold_density_increase_pct=float(vals[int(np.ceil(q*n))-1])))
            for i in np.argsort(req)[-10:]:tail.append(dict(gamma=gamma,spectral_scale=s,spatial=scheme,adcode=a.adcode.iloc[i],city=a.city.iloc[i],province=a.province.iloc[i],threshold=req[i],annual_temperature_C=a.tair_mean.iloc[i]))
    save(rows,'Coverage_tail_diagnostics');save(tail,'Coverage_tail_cities')

def structural_policy():
    from scripts.analyse_regional_policy import load,evaluate,winners
    c,y,d,cost=load();ix=np.arange(len(c));raw=pd.read_csv(OUT/'Tandem_raw_ratio_city.csv',dtype={'adcode':str});records=[]
    for family in ['reference_matched','unscaled_ratio']:
        yy=y.copy()
        if family=='unscaled_ratio':
            g=raw[(raw.gamma==-.3)&(raw.gap==1.68)].set_index('adcode').loc[c.adcode]
            yy[:,2]=yy[:,0]*(1+g.raw_capacity_pct.to_numpy()/100)
        a=evaluate(c,yy,d,cost)
        for ctx,f,scale in [('cap',np.ones(3),1000),('area',d*.65/1000,10000)]:
            n=a['npv_'+ctx];e=a['delivered_pv_kwh_kwp']*f;w0=winners(n);eb=np.where(w0>=0,e[ix,np.maximum(w0,0)]*scale,0)
            for pol,s,elig in [('No subsidy',0,[0,0,0]),('General20',.2,[1,1,1]),('New20',.2,[0,1,1]),('New30',.3,[0,1,1])]:
                tr=a['initial_cap']*f*s*np.array(elig);w=winners(n+tr);ea=np.where(w>=0,e[ix,np.maximum(w,0)]*scale,0)
                paid=np.where(w>=0,tr[np.maximum(w,0)]*scale,0)
                records.append(dict(family=family,context=ctx,policy=pol,viable=int((w>=0).sum()),si=int((w==0).sum()),sj=int((w==1).sum()),t=int((w==2).sum()),public_usd=float(paid.sum()*1.05),additional_discounted_mwh=float((ea-eb).sum()/1000)))
    save(records,'Structural_response_policy')

def economics():
    from scripts.analyse_regional_policy import load,evaluate,lifecycle,winners
    c,y,d,cost=load();base=evaluate(c,y,d,cost);C=base['initial_cap'];annual=base['annual_delivered'];ix=np.arange(len(c));disc=1.05**(-np.arange(1,26))
    dur=[(25,.005,.01),(21.5,.01505,.0675),(25,.012,.04)]
    rows=[];margins=[];details=[];info=[]
    # Joint scenarios use fixed endpoints rather than fitted priors.
    specs=list(itertools.product([.8,1,1.2],[.005,.012,.02],['full','half','salvage','stop_option']))
    for mult,td,rule in specs:
        cap=C*np.array([1,mult,mult]);df=[dur[0],dur[1],(25,td,.04)]
        fac=np.array([lifecycle(*v,replace_factor=.5 if rule=='half' else 1,salvage=rule=='salvage') for v in df])
        en=annual*fac[:,0];physical=annual*fac[:,2];whole=cap*fac[:,1]
        for ctx,f,price,land,scale in [('cap',np.ones(3),.04,0,1000),('area',d*.65/1000,.08,25,10000)]:
            e=en.copy();ep=physical.copy();wc=np.broadcast_to(whole,e.shape).copy()
            # Alternative early retirement pays O&M only while operating; no salvage.
            if rule=='stop_option':
                life,deg,burn=dur[1];gen=np.zeros(25);active=np.zeros(25)
                for k in range(25):active[k]=max(0,min(1,life-k));gen[k]=active[k]*(1-burn)*(1-deg)**k
                es=annual[:,1]*(gen@disc);ps=annual[:,1]*gen.sum();cs=cap[1]*(1+.015*(active@disc))
                stop=es*price-cs>e[:,1]*price-wc[:,1]
                e[stop,1]=es[stop];ep[stop,1]=ps[stop];wc[stop,1]=cs
            n=(e*price-wc)*f-land;w0=winners(n)
            eb=np.where(w0>=0,(e*f)[ix,np.maximum(w0,0)]*scale,0);pb=np.where(w0>=0,(ep*f)[ix,np.maximum(w0,0)]*scale,0)
            for policy,rate,elig in [('None',0,[0,0,0]),('General20',.2,[1,1,1]),('New20',.2,[0,1,1]),('New30',.3,[0,1,1])]:
                tr=cap*rate*np.array(elig)*f;nn=n+tr;w=winners(nn)
                ea=np.where(w>=0,(e*f)[ix,np.maximum(w,0)]*scale,0);pa=np.where(w>=0,(ep*f)[ix,np.maximum(w,0)]*scale,0)
                paid=np.where(w>=0,tr[np.maximum(w,0)]*scale,0)
                new=(w0<0)&(w>=0);switch=(w0>=0)&(w>=0)&(w!=w0)
                vals=dict(cost_multiplier=mult,tandem_degradation=td,replacement_rule=rule,context=ctx,policy=policy,viable=int((w>=0).sum()),si=int((w==0).sum()),sj=int((w==1).sum()),t=int((w==2).sum()),public_usd=float(paid.sum()*1.05),new_projects=int(new.sum()),additional_discounted_mwh=float((ea-eb).sum()/1000),additional_undiscounted_mwh=float((pa-pb).sum()/1000),entry_discounted_mwh=float((ea-eb)[new].sum()/1000),switch_discounted_mwh=float((ea-eb)[switch].sum()/1000))
                assert abs(vals['entry_discounted_mwh']+vals['switch_discounted_mwh']-vals['additional_discounted_mwh'])<1e-7
                rows.append(vals)
                if rule!='stop_option':
                    yh=y[:,0,None]*np.mean(y/y[:,0,None],axis=0)[None,:]
                    eh=yh*c.utilization_low.to_numpy()[:,None]*fac[:,0]
                    nh=(eh*price-wc)*f-land+tr;wh=winners(nh)
                    true_chosen=np.where(wh>=0,nn[ix,np.maximum(wh,0)],0)*scale
                    optimal=np.maximum(0,nn.max(axis=1))*scale
                    loss=float((optimal-true_chosen).sum())
                    assert loss>=-1e-6
                    info.append(dict(cost_multiplier=mult,tandem_degradation=td,replacement_rule=rule,context=ctx,policy=policy,decision_changes=int((w!=wh).sum()),npv_loss_usd=loss,npv_loss_pct=100*loss/optimal.sum()))
                if mult==1 and td==.012 and rule=='full':
                    # Minimum absolute independent fractional yield perturbation (L-infinity)
                    # on all technologies needed to change current winner, allowing no-build.
                    rev=e*price*f;rv=np.c_[rev,np.zeros(len(c))];nv=np.c_[nn,np.zeros(len(c))];ww=np.where(w<0,3,w)
                    gap=nv[ix,ww,None]-nv;den=rv[ix,ww,None]+rv
                    bound=np.divide(gap,den,out=np.full_like(gap,np.inf),where=den>0);bound[ix,ww]=np.inf
                    tol=bound.min(axis=1);competitor=bound.argmin(axis=1)
                    for k in ix:margins.append(dict(adcode=c.adcode.iloc[k],context=ctx,policy=policy,winner=int(w[k]),challenger=int(competitor[k]),yield_perturbation_radius=float(tol[k]),npv_margin=float(gap[k,competitor[k]]*scale)))
    save(rows,'Joint_economic_policy');save(margins,'Decision_yield_flip_margins');save(info,'Regional_information_value')
    # Existing anchored O&M counterexample, independently recomputed with physical totals.
    fac=np.array([lifecycle(*v) for v in dur]);en=annual*fac[:,0];phys=annual*fac[:,2];wc=C*(fac[:,1]-.015*disc.sum())+3.2*disc.sum();n=en*.04-wc;w0=winners(n)
    for name,elig in [('General20',np.ones(3)),('New20',np.array([0,1,1]))]:
        w=winners(n+C*.2*elig);eb=np.where(w0>=0,en[ix,np.maximum(w0,0)],0);ea=np.where(w>=0,en[ix,np.maximum(w,0)],0);pb=np.where(w0>=0,phys[ix,np.maximum(w0,0)],0);pa=np.where(w>=0,phys[ix,np.maximum(w,0)],0)
        new=(w0<0)&(w>=0);sw=(w0>=0)&(w>=0)&(w!=w0)
        details.append(dict(policy=name,before_viable=int((w0>=0).sum()),after_viable=int((w>=0).sum()),additional_discounted_mwh=float((ea-eb).sum()),additional_undiscounted_mwh=float((pa-pb).sum()),entry_discounted_mwh=float((ea-eb)[new].sum()),switch_discounted_mwh=float((ea-eb)[sw].sum())))
    save(details,'Anchored_OM_generation_decomposition')

if __name__=='__main__':
    mode=sys.argv[1] if len(sys.argv)>1 else 'quick'
    if mode=='quick':reference_check();coverage();economics();print('Quick diagnostics complete',flush=True)
    elif mode=='aggregate':aggregate();structural_policy()
    elif mode=='scan':
        from pvsim.city_catalog import load_city_catalog
        anchors=load_city_catalog()
        with ProcessPoolExecutor(max_workers=4) as pool:
            jobs=[pool.submit(city_scan,a) for a in anchors]
            for i,f in enumerate(as_completed(jobs),1):
                f.result()
                if i%10==0:print(f'Raw-current structural scan {i}/337',flush=True)
        aggregate();print('Full structural scan complete',flush=True)
