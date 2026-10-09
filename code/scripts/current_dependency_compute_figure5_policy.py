"""Same-baseline policy accounting, retaining every region and unchanged transfer."""
from pathlib import Path
import sys,json,hashlib
sys.dont_write_bytecode=True
O=Path(__file__).resolve().parents[1]; SD=O/'Source_Data'; Q=O/'qa'
sys.path.insert(0,str(O/'code'))
import numpy as np,pandas as pd
from scripts.finance import evaluate,lifecycle
from scripts.cost_paths import capex_and_lcoe,TECHS
from pvsim.economic_priors import CENTRAL_LEARNING_RATES,CENTRAL_CAPEX_FLOORS_USD_W,CENTRAL_BREAKTHROUGH_YEAR,CENTRAL_POST_BREAKTHROUGH_LIFETIME_YR
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for k,v in json.loads((O/'inputs/frozen_dependency_hashes.json').read_text()).items():assert sha(O/k)==v
c=pd.read_csv(O/'inputs/Figure1_region_values.csv',dtype={'adcode':str}).sort_values('adcode').reset_index(drop=True)
states=pd.read_csv(O/'inputs/regional_path_states.csv',dtype={'adcode':str})
def state(s):return states[states.state_id.eq(s)].set_index('adcode').loc[c.adcode]
s=state('single_00'); t=state('tandem_00')
y=np.c_[s.csi_yield_kwh_kwp,s.candidate_yield_kwh_kwp,t.candidate_yield_kwh_kwp]
reg=json.loads((Q/'Figure4_analysis_register.json').read_text())
contract=json.loads((O/'figure5_contract.json').read_text()); PC=contract['policy']
_,cost=capex_and_lcoe({k:1400 for k in TECHS},CENTRAL_LEARNING_RATES,CENTRAL_CAPEX_FLOORS_USD_W,CENTRAL_BREAKTHROUGH_YEAR,CENTRAL_POST_BREAKTHROUGH_LIFETIME_YR,return_capex=True)
ev=evaluate(c,y,np.array(reg['density_W_m2']),cost)
assert np.allclose(ev['initial_cap'],reg['capex2035_usd_kwp'],rtol=0,atol=1e-9)
names=np.array(['no_build','csi','single_junction','tandem'])
POL=[('General',np.array(PC['General_eligible'])),('New technology',np.array(PC['New_technology_eligible']))]
def winner(n):return np.c_[np.zeros(len(n)),n].argmax(axis=1)
def select(n,w):return np.c_[np.zeros(len(n)),n][np.arange(len(n)),w]

def result(e,ct,policy,elig,rate):
    area=ct=='site_area'; scale=10000 if area else 1000
    v=e['npv_area' if area else 'npv_cap']*scale
    install=e['initial_cap']*(e['density']*e['packing']/1000 if area else 1)*scale
    grant=install*rate*elig
    before=winner(v);after=winner(v+grant)
    paid=np.r_[0.,grant][after]
    entry=(before==0)&(after>0);sw=(before>0)&(after>0)&(before!=after)
    same=(before==after)&(paid>0);unfunded=(before==after)&(paid==0)
    labels=np.select([entry,sw,same,unfunded],['entry','switch','paid_unchanged','unfunded_unchanged'],default='INVALID')
    assert not np.any(labels=='INVALID')
    assert np.all(select(v,after)+paid>=select(v,before)-1e-7)
    energy=e['delivered_pv_kwh_kwp']*(e['density']*e['packing']/1000 if area else 1)*scale
    undisc=e['annual_delivered']*np.array([lifecycle(reg['baseline_lifetime'][j],reg['degradation'][j],reg['burn_in'][j])[2] for j in range(3)])
    undisc=undisc*(e['density']*e['packing']/1000 if area else 1)*scale
    delta=select(energy,after)-select(energy,before)
    delta_raw=select(undisc,after)-select(undisc,before)
    assert np.allclose(delta[same|unfunded],0,rtol=0,atol=1e-8)
    record=dict(context=ct,policy=policy,support_rate=rate,baseline_built=int((before>0).sum()),after_built=int((after>0).sum()),
        entry=int(entry.sum()),switch=int(sw.sum()),paid_unchanged=int(same.sum()),unfunded_unchanged=int(unfunded.sum()),
        direct_support_usd=float(paid.sum()),admin_usd=float(paid.sum()*PC['administration_fraction']),
        total_public_usd=float(paid.sum()*(1+PC['administration_fraction'])),
        net_discounted_generation_kwh=float(delta.sum()),net_generation_kwh=float(delta_raw.sum()))
    for label,mask in [('entry',entry),('switch',sw),('paid_unchanged',same),('unfunded_unchanged',unfunded)]:
        record[label+'_direct_support_usd']=float(paid[mask].sum())
        record[label+'_public_usd']=float(paid[mask].sum()*(1+PC['administration_fraction']))
        record[label+'_discounted_generation_kwh']=float(delta[mask].sum())
    for j,n in enumerate(names):record['before_'+n]=int((before==j).sum());record['after_'+n]=int((after==j).sum())
    assert sum(record[k] for k in ['entry','switch','paid_unchanged','unfunded_unchanged'])==369
    assert np.isclose(record['total_public_usd'],sum(record[k+'_public_usd'] for k in ['entry','switch','paid_unchanged']),rtol=0,atol=1e-6)
    frame=c[['adcode','city','province','lat','lon','ghi_kwh_m2']].copy()
    frame=frame.assign(context=ct,policy=policy,support_rate=rate,before_choice=names[before],after_choice=names[after],
        response_class=labels,direct_support_usd=paid,admin_usd=paid*PC['administration_fraction'],public_cost_usd=paid*(1+PC['administration_fraction']),
        baseline_selected_npv_usd=select(v,before),supported_selected_npv_usd=select(v,after)+paid,
        discounted_generation_change_kwh=delta,generation_change_kwh=delta_raw)
    for j,name in enumerate(names[1:]):
        frame['baseline_'+name+'_npv_usd']=v[:,j];frame['offered_'+name+'_grant_usd']=grant[j];frame['supported_'+name+'_npv_usd']=v[:,j]+grant[j]
    frame['selected_choice_near_tie']=np.diff(np.sort(np.c_[np.zeros(369),v+grant],axis=1),axis=1)[:,-1]<1e-7
    return record,frame

summary=[];details=[];curves=[]
for ct in ['capacity','site_area']:
    for pol,elig in POL:
        rr,ff=result(ev,ct,pol,elig,PC['reference_rate']);summary.append(rr);details.append(ff)
        for rate in np.linspace(0,.3,301):curves.append(result(ev,ct,pol,elig,float(rate))[0])
df=pd.concat(details,ignore_index=True);sm=pd.DataFrame(summary)
df.to_csv(SD/'Figure5_policy_all369_paired_choices.csv',index=False,encoding='utf-8-sig')
sm.to_csv(SD/'Figure5_policy_response_summary.csv',index=False,encoding='utf-8-sig')
pd.DataFrame(curves).to_csv(SD/'Figure5_policy_rate_curves.csv',index=False,encoding='utf-8-sig')
trans=[]
for (ct,pol),g in df.groupby(['context','policy'],sort=False):
    for before in names:
        for after in names:
            cell=g[g.before_choice.eq(before)&g.after_choice.eq(after)]
            cls='empty' if cell.empty else cell.response_class.iloc[0]
            assert cell.empty or cell.response_class.nunique()==1
            trans.append(dict(context=ct,policy=pol,support_rate=PC['reference_rate'],before_choice=before,after_choice=after,
                regions=len(cell),response_class=cls,direct_support_usd=float(cell.direct_support_usd.sum()),public_cost_usd=float(cell.public_cost_usd.sum())))
pd.DataFrame(trans).to_csv(SD/'Figure5_policy_transition_matrices.csv',index=False,encoding='utf-8-sig')
baseline=[]
for ct in ['capacity','site_area']:
    area=ct=='site_area';scale=10000 if area else 1000;v=ev['npv_area' if area else 'npv_cap']
    for j,name in enumerate(names[1:]):
        z=c[['adcode','city','province']].copy();z=z.assign(context=ct,technology=name,npv_per_resource=v[:,j],resource_unit='USD/m2 site' if area else 'USD/kWp',npv_per_opportunity=v[:,j]*scale,opportunity_scale=scale,baseline_choice=names[winner(v)])
        baseline.append(z)
pd.concat(baseline).to_csv(SD/'Figure5_policy_baseline_all_technology_NPV.csv',index=False,encoding='utf-8-sig')
# Independently reconstruct the three baseline NPVs from the registered lifecycle.
fac=np.array([lifecycle(reg['baseline_lifetime'][j],reg['degradation'][j],reg['burn_in'][j]) for j in range(3)])
energy=y*c.utilization_low.to_numpy()[:,None]*fac[:,0]
cash=energy*.04-np.array(reg['capex2035_usd_kwp'])*fac[:,1]
area_cash=(energy*.08-np.array(reg['capex2035_usd_kwp'])*fac[:,1])*(np.array(reg['density_W_m2'])*reg['packing']/1000)-reg['site_charge']
maxerr=max(np.max(np.abs(cash-ev['npv_cap'])),np.max(np.abs(area_cash-ev['npv_area'])))
assert maxerr<1e-8
previous=pd.read_csv(SD/'Figure5_all_four_case_region_decisions.csv',dtype={'adcode':str});numeric=[]
for ct in ['capacity','site_area']:
    src=previous[previous.context.eq(ct)&previous.candidate.eq('single_junction')].set_index('adcode').loc[c.adcode]
    vals=ev['npv_area' if ct=='site_area' else 'npv_cap']
    assert np.array_equal(names[winner(vals)],src.baseline_choice)
    err=float(np.max(np.abs(vals[:,1]-src.baseline_npv.to_numpy())));assert err<1e-8
    numeric.append(dict(context=ct,baseline_vs_Figure4_max_abs_NPV_residual=err))
# Compare selections to the earlier original-policy computation, not its old full-precision NPVs.
old=pd.read_csv(O/'sources/policy/inherited_policy_summary.csv')
matches=[]
for row in summary:
    oldctx='area' if row['context']=='site_area' else 'capacity'
    z=old[old.context.eq(oldctx)&old.strategy.eq(row['policy'])&np.isclose(old.share,PC['reference_rate'])].iloc[0]
    same=int(z.new_viable)==row['entry'] and int(z.material_switches)==row['switch']
    matches.append(dict(context=row['context'],policy=row['policy'],entry_count_same=same,old_entry=int(z.new_viable),new_entry=row['entry'],old_switch=int(z.material_switches),new_switch=row['switch'],old_public_usd=float(z.total_public_usd),new_public_usd=row['total_public_usd']))
    assert same
pd.DataFrame(matches).to_csv(SD/'Figure5_policy_previous_count_reconciliation.csv',index=False,encoding='utf-8-sig')
controls=[]
settings=[('Primary',{}),('Common price0.04',dict(price_cap=.04,price_area=.04)),('Common price0.08',dict(price_cap=.08,price_area=.08)),('No site fee',dict(site_cost=0)),('Half replacement',dict(replacement_factor=.5)),('Pro-rata salvage',dict(salvage=True))]
for lab,kwargs in settings:
    ex=evaluate(c,y,np.array(reg['density_W_m2']),cost,**kwargs)
    for ct in ['capacity','site_area']:
        for pol,elig in POL:
            row,_=result(ex,ct,pol,elig,PC['reference_rate']);controls.append(dict(control=lab,**row))
pd.DataFrame(controls).to_csv(SD/'Figure5_policy_financial_controls.csv',index=False,encoding='utf-8-sig')
defs=[('entry','before=no_build and after is a built technology','Choice effect, not observed adoption'),('switch','both built and technology differs','Choice effect under a fixed baseline'),('paid_unchanged','same built choice; positive selected grant','A transfer with no change in the modelled discrete choice; no claim about all real behavioural effects'),('unfunded_unchanged','same choice; zero selected grant, including no build','Retained in all369 totals; not a funded unchanged project'),('grant','rate*initial system CAPEX*eligibility of selected technology','Site fee, O&M, replacement are excluded'),('public_cost','direct grant*(1+0.05)','Administration is an inherited author allowance, not an observed programme cost'),('tie_rule','maximum over no_build,csi,single_junction,tandem; first occurrence wins','No build at NPV=0; near ties separately flagged'),('sample','369 standardized opportunities separately per context','No exclusions, sampling uncertainty or national siting inventory')]
pd.DataFrame(defs,columns=['quantity','definition','scope']).to_csv(SD/'Figure5_policy_derived_definitions.csv',index=False,encoding='utf-8-sig')
par=[('support_rate',.2,'fraction','Inherited author scenario','sources/policy/inherited_cell_15.py and inherited_policy_summary.csv, share=0.2'),('administration_fraction',.05,'fraction','Inherited author allowance','sources/policy/inherited_cell_15.py, admin_usd=0.05*direct_support_usd'),('General eligibility','1,1,1','cSi,SJ,T','Policy scenario','sources/policy/inherited_cell_13.py, policy_result'),('New technology eligibility','0,1,1','cSi,SJ,T','Policy scenario','sources/policy/inherited_cell_13.py, grant[0]=0'),('capacity_scale',1000,'kWp/opportunity','Inherited standardized opportunity','sources/policy/inherited_cell_11.py, scale=1000'),('site_scale',10000,'m2/opportunity','Inherited standardized opportunity','sources/policy/inherited_cell_11.py, site=25*10000 and scale=density*packing*10'),('rate_scan','0..0.3,301 states','fraction','Inherited author scan','sources/policy/inherited_cell_15.py, np.linspace(0,0.3,301)')]
pd.DataFrame(par,columns=['parameter','value','unit','identity','numeric_locator']).to_csv(SD/'Figure5_policy_parameter_identities.csv',index=False,encoding='utf-8-sig')
out=dict(status='PASS',all_regions=369,paired_details=len(df),transition_cells=len(trans),policy_rate_summaries=len(curves),same_physical_baseline=True,no_operating_endpoint_applied=True,no_new_external_numeric_inputs=True,baseline_NPV_recalculation_max_abs_residual=float(maxerr),baseline_Figure4_reconciliation=numeric,previous_count_reconciliation=matches,all_opportunities_partitioned=True,public_cost_and_energy_decompositions_verified=True,zero_rate_identity_verified=all(z['entry']==z['switch']==z['paid_unchanged']==0 and z['unfunded_unchanged']==369 and z['total_public_usd']==0 for z in curves if z['support_rate']==0),selected_near_ties=int(df.selected_choice_near_tie.sum()),summary=summary)
(Q/'Figure5_policy_numerical_checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(sm[['context','policy','entry','switch','paid_unchanged','unfunded_unchanged','total_public_usd']].to_string(index=False),flush=True)
print('PASS: same-baseline policy and complete transfer decomposition.',flush=True)
