"""Numeric source verification and financial assumption identities for Figure4."""
from pathlib import Path
import sys,json,hashlib,shutil,zipfile,xml.etree.ElementTree as ET,ast
sys.dont_write_bytecode=True
O=Path(__file__).resolve().parents[1];R=O.parents[1];sys.path.insert(0,str(O/'code'))
import numpy as np,pandas as pd
from scripts.finance import lifecycle,evaluate
from scripts.cost_paths import capex_and_lcoe,TECHS
from pvsim.economic_priors import CENTRAL_LEARNING_RATES,CENTRAL_CAPEX_FLOORS_USD_W,CENTRAL_BREAKTHROUGH_YEAR,CENTRAL_POST_BREAKTHROUGH_LIFETIME_YR
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,x):pd.DataFrame(x).to_csv(O/'Source_Data'/(n+'.csv'),index=False,encoding='utf-8-sig')
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
doc=O/'sources/NEA/nea_2024_renewable_monitoring_result.docx'
r=ET.fromstring(zipfile.ZipFile(doc).read('word/document.xml'));table=r.findall('.//w:tbl',ns)[3]
orig={}
for tr in table.findall('w:tr',ns)[1:]:
 q=[''.join(t.text or '' for t in tc.findall('.//w:t',ns)).strip() for tc in tr.findall('w:tc',ns)]
 if len(q)==3:orig[q[0]]=(float(q[1].strip('%')),float(q[2].strip('%')))
assert len(orig)==33
u33=pd.read_csv(O/'sources/nea_pv_utilization_rate_2024.csv');checks=[]
for q in u33.itertuples():
 assert orig[q.reporting_region]==(q.pv_utilization_rate_pct_2023,q.pv_utilization_rate_pct_2024)
 checks.append(dict(region=q.reporting_region,used_percent=q.pv_utilization_rate_pct_2024,original_percent=orig[q.reporting_region][1],source_file=str(doc.relative_to(O)).replace('\\','/'),source_sha256=sha(doc),numeric_locator='Printed Table4; original DOCX table index3; '+q.reporting_region+' row,2024 column',source_url=q.source_url,conversion='divide by100; for provinces with multiple reporting regions take minimum as declared model scenario'))
c=pd.read_csv(O/'inputs/Figure1_region_values.csv',dtype={'adcode':str}).sort_values('adcode').reset_index(drop=True)
use=u33.groupby('province').pv_utilization_rate_pct_2024.min()/100
assert np.allclose(c.province.map(use).to_numpy(),c.utilization_low.to_numpy(),rtol=0,atol=1e-15)
save('Figure4_official_utilization_numeric_locations',checks)
save('Figure4_all369_utilization_mapping',c[['adcode','city','province','utilization_low']].assign(aggregation='2024 reporting-region minimum in province'))
external=pd.read_csv(O/'sources/physical_provenance/external_numeric_source_index.csv').fillna('')
for k,q in external.iterrows():
 src=R/'deliverables/Main_figures_preview_20261008_v15'/q.source_file;assert sha(src)==q.source_sha256
 dst=O/'sources/physical_originals'/q.source_file;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
 external.loc[k,'source_file']=str(dst.relative_to(O)).replace('\\','/')
save('Figure4_inherited_external_numeric_source_index',external)
reg=json.loads((O/'qa/Figure4_analysis_register.json').read_text(encoding='utf-8'))
params=[]
def add(key,value,unit,file,needle,identity):
 hits=[i+1 for i,t in enumerate((O/file).read_text(encoding='utf-8').splitlines()) if needle in t];assert hits,(file,needle)
 params.append(dict(parameter=key,value=json.dumps(value,ensure_ascii=False),unit=unit,identity=identity,numeric_locator=file+':'+','.join(map(str,hits))+'; '+needle,code_sha256=sha(O/file),external_observation_claim=False))
for key,value,unit,file,needle,identity in [
 ('discount',.05,'fraction','code/scripts/finance.py','def lifecycle','Author scenario'),
 ('O&M',.015,'baseline CAPEX/year','code/scripts/finance.py','om_factor=','Author scenario'),
 ('horizon',25,'years','code/scripts/finance.py','def lifecycle','Author scenario'),
 ('capacity_price',.04,'USD/kWh','code/scripts/finance.py','def evaluate','Author scenario'),
 ('site_price',.08,'USD/kWh','code/scripts/finance.py','def evaluate','Author scenario'),
 ('site_charge',25.,'USD/m2 site','code/scripts/finance.py','def evaluate','Author scenario'),
 ('packing',.65,'aperture/site area','code/scripts/finance.py','def evaluate','Author scenario'),
 ('csi_durability',[25.,.005,.01],'years;degradation;burn-in','code/pvsim/economics.py','MODERN_CSI_DURABILITY =','Author scenario'),
 ('tandem_durability',[25.,.012,.04],'years;degradation;burn-in','code/pvsim/economics.py','TANDEM_DURABILITY =','Author scenario'),
 ('SJ_life_endpoint',21.5,'years','code/pvsim/economic_priors.py','POST_BREAKTHROUGH_LIFETIME_RANGE_YR =','Derived author midpoint of18 and25'),
 ('SJ_interpolation_endpoints',[15.,25.,.03,.007,.10,.05],'years;fractions','code/pvsim/economics.py','PEROVSKITE_','Author interpolation definition'),
 ('SJ_retention',[reg['degradation'][1],reg['burn_in'][1]],'fractions','code/pvsim/economics.py','endpoint_fraction =','Derived at21.5yr, not external observations'),
 ('initial_CAPEX_seeds',[.65,.95,1.13],'USD/Wp','code/pvsim/economic_priors.py','INITIAL_SYSTEM_CAPEX_USD_W =','Author scenario'),
 ('effective_learning_seeds',[1500.,12.,4.],'GW','code/pvsim/economic_priors.py','INITIAL_GLOBAL_DEPLOYMENT_GW =','Author effective seeds, not observed installations'),
 ('learning_rates',[.18,.27,.30],'fraction/doubling','code/pvsim/economic_priors.py','LEARNING_RATE_PRIORS =','Author scenario'),
 ('CAPEX_floor_bounds',[[.35,.45],[.32,.45],[.42,.58]],'USD/Wp','code/pvsim/economic_priors.py','CAPEX_FLOOR_PRIORS_USD_W =','Author scenario; central values are midpoints'),
 ('cost_annual_lower_bound',.88,'remaining fraction','code/scripts/cost_paths.py','cap[k]*0.88','Author regularization'),
 ('rest_of_world_multiplier',1.4,'factor','code/scripts/cost_paths.py','ROW=0.4','Author scenario'),
 ('cost_time_grid',[2025,2050,1],'years','code/scripts/cost_paths.py','YEARS=np.arange','Author time grid'),
 ('deployment_schedule','cSi:linspace80to30+linspace0to20;SJ:min(4a+5,100);T:max(0,min(3a-12,80))','GW/year','code/scripts/cost_paths.py','def global_new_schedule','Author exogenous schedule'),
 ('derived2035_CAPEX',reg['capex2035_usd_kwp'],'USD/kWp','code/scripts/cost_paths.py','def capex_and_lcoe','Recomputed model output'),
 ('scan_lifetime',[15.,25.,.25],'years:min/max/step','code/compute_figure4.py','lives=np.arange','Author scan'),
 ('scan_cost_reduction',[0.,100.,.5],'percent:min/max/step','code/compute_figure4.py','cuts=np.arange','Author scan'),
 ('candidate_path_states',[0.,1.,.1],'progress:min/max/step','code/compute_figure4.py','range(11)','Inherited Figure3 author parameter scenario'),
 ('parity_tolerance',1e-12,'USD/Wp','code/compute_figure4.py','def count','Numerical tolerance'),
 ('replacement_factor',1.,'baseline system expenditure','code/scripts/finance.py','replace_factor=1.','Author full replacement rule'),
 ('salvage',False,'boolean','code/scripts/finance.py','salvage=False','Author no salvage rule'),
 ('replacement_sensitivity',[.5,1.],'factor','code/compute_figure4.py','Half replacement','Author robustness scenario'),
 ('matched_prices',[.04,.08],'USD/kWh','code/compute_figure4.py','for p0 in','Author matched controls'),
 ('matched_site_charges',[0.,25.],'USD/m2 site','code/compute_figure4.py','for fee0 in','Author matched controls')]:add(key,value,unit,file,needle,identity)
save('Figure4_financial_parameter_identities',params)
# Independent NPV check: original economics inputs recover the old frontiers.
old=pd.read_csv(O/'inputs/previous_economic_physical_baseline.csv',dtype={'adcode':str}).set_index('adcode').loc[c.adcode]
yo=np.column_stack([old[k+'_yield_kwh_per_kwp'] for k in ['csi','perovskite','tandem']])
d=np.array(reg['density_W_m2']);cap=np.array(reg['capex2035_usd_kwp'])
_,cost=capex_and_lcoe({k:1400 for k in TECHS},CENTRAL_LEARNING_RATES,CENTRAL_CAPEX_FLOORS_USD_W,CENTRAL_BREAKTHROUGH_YEAR,CENTRAL_POST_BREAKTHROUGH_LIFETIME_YR,return_capex=True)
e=evaluate(c,yo,d,cost);oldfront=pd.read_csv(O/'inputs/previous_cost_lifetime_frontiers.csv',dtype={'adcode':str});errors=[]
for j,name in [(1,'single_junction'),(2,'tandem')]:
 for z,ct in enumerate(['capacity','site_area']):
  L=reg['baseline_lifetime'][j];ef,cf,_=lifecycle(L,reg['degradation'][j],reg['burn_in'][j]);unit=1. if z==0 else d[j]*reg['packing']/1000
  v=e['npv_cap' if z==0 else 'npv_area'];tar=np.c_[np.zeros(369),v[:,[k for k in range(3) if k!=j]]].max(axis=1)
  at0=yo[:,j]*c.utilization_low.to_numpy()*ef*reg['prices'][z]-cap[j]*(cf-1)
  if z:at0=at0*unit-25.
  b=(at0-tar)/(1000*unit)
  q=oldfront[oldfront.candidate.eq(name)&oldfront.context.eq(ct)&oldfront.scan.eq('isolated')&oldfront.lifetime_years.eq(L)].set_index('adcode').loc[c.adcode]
  err=float(np.max(np.abs(b-q.parity_initial_cost_usd_wp.to_numpy())));assert err<1e-12;errors.append(dict(candidate=name,context=ct,max_boundary_error_usd_wp=err))
# Non-replaced25yr cashflow has an independent closed form.
for dg,bi in zip(reg['degradation'],reg['burn_in']):
 ef,cf,_=lifecycle(25,dg,bi);tt=np.arange(1,26)
 assert abs(ef-np.sum((1-bi)*(1-dg)**(tt-1)/(1.05**tt)))<1e-12
 assert abs(cf-(1+.015*np.sum(1.05**(-tt))))<1e-12
(O/'qa/Figure4_provenance_checks.json').write_text(json.dumps(dict(status='PASS',original_NEATable4_rows=33,region_mappings=369,physical_external_numeric_artifacts=len(external),financial_parameter_identity_records=len(params),old_financial_regression=errors,closed_form_cashflow=True,external_inputs_no_new_unverified_numerals=True),ensure_ascii=False,indent=2),encoding='utf-8')
print('PASS: source33 rows,369 mappings,22 physical artifacts,financial identities and regression.',flush=True)
