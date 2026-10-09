def winners(v):return np.where(v.max(axis=1)>0,v.argmax(axis=1),-1)
def select(a,k):return np.where(k>=0,a[np.arange(len(k)),np.maximum(k,0)],0.)

def policy_result(ev,strategy,share):
    v=ev['npv'];before=winners(v);base=np.maximum(0,v.max(axis=1))
    grant=share*ev['capex'].copy()
    if strategy=='New technology':grant[0]=0
    after=winners(v+grant);paid=np.where(after>=0,grant[np.maximum(after,0)],0.)
    if strategy=='Matched gap':paid=np.where(after!=before,np.maximum(0,base-select(v,after)),0.)
    assert np.all(select(v,after)+paid>=base-1e-7)
    entry=(before<0)&(after>=0);sw=(before>=0)&(after>=0)&(before!=after)
    d=select(ev['discounted'],after)-select(ev['discounted'],before)
    raw=select(ev['raw'],after)-select(ev['raw'],before)
    row=dict(strategy=strategy,share=float(share),baseline_viable=int((before>=0).sum()),after_viable=int((after>=0).sum()),
             new_viable=int(entry.sum()),material_switches=int(sw.sum()),direct_public_usd=float(paid.sum()),
             net_discounted_generation_kwh=float(d.sum()),net_generation_kwh=float(raw.sum()),
             entry_discounted_generation_kwh=float(d[entry].sum()),switching_discounted_generation_kwh=float(d[sw].sum()))
    for j,k in enumerate(TECHS):row['before_'+k]=int((before==j).sum());row['after_'+k]=int((after==j).sum())
    assert np.isclose(d.sum(),d[entry].sum()+d[sw].sum(),atol=1e-7)
    return row,dict(before_choice=before,after_choice=after,grant_usd=paid,net_discounted_generation_kwh=d,net_generation_kwh=raw)