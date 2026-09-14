from pathlib import Path
import sys,json
root=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path.cwd()
sys.path.insert(0,str(root))
from scripts.analyse_regional_policy import load,evaluate,winners
q=Path(__file__).resolve().parent
c,y,d,k=load();a=evaluate(c,y,d,k);w=winners(a['npv_cap'])
out=c[['adcode','province','single_capacity_pct']].copy()
out['baseline_capacity_viable']=w>=0
out['baseline_best_npv_usd_per_kwp']=a['npv_cap'].max(axis=1)
out.to_csv(q/'Fig1_Fig5_baseline_city_link.csv',index=False,encoding='utf-8-sig')
s={label:{'n':int(mask.sum()),'mean_single_capacity_gain_pct':float(c.loc[mask,'single_capacity_pct'].mean())} for label,mask in [('nonviable',w<0),('viable',w>=0)]}
assert s['nonviable']['n']==79 and s['viable']['n']==258
s['interpretation']='Descriptive grouping under the baseline capacity scenario; not a causal effect of relative yield gain on viability.'
(q/'Fig1_Fig5_baseline_city_link.json').write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(s,ensure_ascii=False))

