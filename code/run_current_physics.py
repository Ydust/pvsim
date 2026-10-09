"""Current hourly model: source hashes, four-anchor pilot, or full 369-region rerun."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--full',action='store_true');p.add_argument('--workers',type=int,default=4);args=p.parse_args()
 manifest=json.loads((ROOT/'environment/current_physics_manifest.json').read_text());work=ROOT/'environment/.runtime/current_physics'
 if work.exists():shutil.rmtree(work)
 work.mkdir(parents=True)
 for row in manifest['entries']:
  data=(ROOT/row['source']).read_bytes()
  assert hashlib.sha256(data).hexdigest()==row['sha256'],row['source']
  target=work/row['runtime'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
 for x in ['paths/results','paths/qa','factorial/Source_Data','factorial/qa','factorial/calculation/shards']:(work/x).mkdir(parents=True,exist_ok=True)
 env={**os.environ,'PYTHONIOENCODING':'utf-8','PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1','MPLBACKEND':'Agg'}
 def run(script,*a):subprocess.run([sys.executable,str(work/script),*a],cwd=work,env=env,check=True)
 run('paths/code/run_paths.py','--pilot');run('factorial/code/compute_factorial.py','--pilot')
 if args.full:
  run('paths/code/run_paths.py','--workers',str(args.workers));run('paths/code/analyse_paths.py');run('factorial/code/compute_factorial.py','--workers',str(args.workers))
 else:run('paths/code/analyse_paths.py')
 for branch in ['paths','factorial']:
  for f in (work/branch/'qa').glob('*.json'):shutil.copy2(f,ROOT/'outputs'/('current_physics_'+branch+'_'+f.name))
 print('Hourly pilot verified at four anchors; full rerun completed.' if args.full else 'Four-anchor hourly pilot and stored all-region path reconstruction passed; use --full for every anchor.')
if __name__=='__main__':main()
