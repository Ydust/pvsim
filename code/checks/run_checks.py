from pathlib import Path
import os,sys,json,hashlib,shutil,subprocess,time
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reproduced';OUT.mkdir(exist_ok=True)
began=time.time()
for item in json.loads((ROOT/'input_manifest.json').read_text(encoding='utf-8')):
 assert hashlib.sha256((ROOT/item['path']).read_bytes()).hexdigest()==item['sha256'],item['path']
shutil.copy2(ROOT/'inputs/electrical_hourly_inputs.npz',OUT/'electrical_hourly_inputs.npz')
env={**os.environ,'PVSIM_ROOT':str(ROOT),'PVSIM_CHECK_DIR':str(OUT),'PYTHONDONTWRITEBYTECODE':'1','PYTHONIOENCODING':'utf-8'}
for script in ['analysis.py','electrical.py']:
 subprocess.run([sys.executable,str(ROOT/'checks'/script)],cwd=ROOT,env=env,check=True)
records=[]
for expected in sorted((ROOT/'expected').glob('*.csv')):
 a=pd.read_csv(expected);b=pd.read_csv(OUT/'data'/expected.name)
 assert a.shape==b.shape and a.columns.tolist()==b.columns.tolist(),expected.name
 for col in a.columns:
  if pd.api.types.is_numeric_dtype(a[col]):
   np.testing.assert_allclose(a[col].to_numpy(float),b[col].to_numpy(float),rtol=1e-9,atol=1e-7,equal_nan=True,err_msg=expected.name+':'+col)
  else:assert a[col].fillna('').equals(b[col].fillna('')),(expected.name,col)
 records.append({'file':expected.name,'rows':len(a),'all_values_match':True})
report={'passed':True,'runtime_seconds':round(time.time()-began,2),'rtol':1e-9,'atol':1e-7,'verified_tables':records,
 'scope':'Central economic endpoints and added checks from supplied processed inputs; raw-weather acquisition and full historical figure regeneration not tested.'}
(OUT/'verification_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
