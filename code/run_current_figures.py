"""Reproduce current 369-region figures from individually hash-checked inputs."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--figure',type=int,choices=range(1,6));parser.add_argument('--support',action='store_true');args=parser.parse_args()
 manifest=json.loads((ROOT/'environment/current_figures_manifest.json').read_text())
 work=ROOT/'environment/.runtime/current_figures'
 if work.exists():shutil.rmtree(work)
 work.mkdir(parents=True)
 for row in manifest['entries']:
  source=ROOT/row['source'];data=source.read_bytes()
  if hashlib.sha256(data).hexdigest()!=row['sha256']:raise ValueError('Input hash mismatch: '+row['source'])
  target=work/row['runtime'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
 for n in [1,2,3,4,5,'S45']:(work/('Figure_'+str(n))).mkdir(exist_ok=True)
 env={**os.environ,'PYTHONIOENCODING':'utf-8','PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1','MPLBACKEND':'Agg'}
 commands=['code/compute_figure4.py','code/compute_figure5.py','code/compute_figure5_policy.py','code/compute_choice_zones.py','compute_regional_gaps.py','compute_operating_impacts.py','compute_figure4_gaps.py','check_current_consistency.py']+['plot_figure'+str(n)+'.py' for n in ([args.figure] if args.figure else range(1,6))]
 if args.support:commands.extend(['plot_figure_s44.py','plot_SI_support.py'])
 for name in commands:subprocess.run([sys.executable,str(work/name)],cwd=work,env=env,check=True)
 for d in work.glob('Figure_*'):
  if d.is_dir():
   for f in d.iterdir():
    if f.is_file():shutil.copy2(f,ROOT/'outputs'/f.name)
 for f in (work/'qa').glob('*.json'):shutil.copy2(f,ROOT/'outputs'/('current_'+f.name))
 print('Current 369-region inputs verified; figures exported to outputs.')
 return 0
if __name__=='__main__':raise SystemExit(main())
