from pathlib import Path
import json,sys
import numpy as np,pandas as pd,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
O=Path(__file__).resolve().parent;F=O/'Figure_SI_support';F.mkdir(exist_ok=True);sys.path.insert(0,str(O))
scope={'__file__':str(O/'plot_figure4.py'),'__name__':'standalone_support'};exec(compile((O/'plot_figure4.py').read_text(encoding='utf-8'),str(O/'plot_figure4.py'),'exec'),scope)
mapping=json.loads((O/'SI_support_mapping.json').read_text())
def save(fig,n):
 for ext in ['png','svg','pdf']:fig.savefig(F/f'Figure_S{n}.{ext}',dpi=300,bbox_inches='tight',pad_inches=.06)
 row=next(x for x in mapping if x['number']==n)
 from PIL import Image
 im=Image.open(F/f'Figure_S{n}.png');row['width_in']=min(im.width/300,5.7681);row['height_in']=row['width_in']*im.height/im.width;row['source_kind']='Standalone matplotlib replot from exact current numerical tables';plt.close(fig)
for n,j,ct in [(134,1,'site_area'),(135,2,'capacity')]:
 fig=plt.figure(figsize=(183/25.4,85/25.4));scope['legends'](fig);scope['phase'](fig,[.095,.125,.80,.53],j,ct,'a','standalone')
 # Independent figure number is displayed by SI; remove only composite letter.
 ax=fig.axes[0]
 for t in list(ax.texts):
  if t.get_text()=='a':t.remove()
 save(fig,n)
th=pd.read_csv(O/'Source_Data/Figure4_coverage_thresholds.csv')
paired=th.pivot(index=['candidate','context','minimum_coverage_pct','lifetime_years'],columns='response_state',values='initial_system_cost_usd_wp').reset_index()
for n,(candidate,ct) in enumerate([('single_junction','capacity'),('single_junction','site_area'),('tandem','capacity'),('tandem','site_area')],130):
 fig=plt.figure(figsize=(183/25.4,85/25.4));ax=fig.add_axes([.095,.18,.80,.53]);ep=fig.add_axes([.908,.18,.022,.53]);q=paired[paired.candidate.eq(candidate)&paired.context.eq(ct)];allvalues=q[['baseline','target']].to_numpy();low=float(allvalues.min());high=float(allvalues.max());span=max(high-low,.03);yl=(min(0,low-span*.06),high+span*.08)
 for pct,ls in [(50,'-'),(100,'--')]:
  z=q[q.minimum_coverage_pct.eq(pct)].sort_values('lifetime_years');x=z.lifetime_years.to_numpy()
  for state,color,width in [('baseline','#26323b',1.1),('target','#883f81',.85)]:
   v=z[state].to_numpy();ax.plot(x[:-1],v[:-1],color=color,lw=width,ls=ls,drawstyle='steps-mid');ep.plot([24.91,25.09],[v[-1]]*2,color=color,lw=width,ls=ls)
 ax.set(xlim=(14.875,24.875),ylim=yl,xticks=[15,18,21.5,24],xlabel='Service life (years)',ylabel='Initial system cost (USD/Wp)',title=('Single junction' if candidate=='single_junction' else 'Tandem')+' · '+('capacity' if ct=='capacity' else 'site area'))
 ep.set(xlim=(24.875,25.125),ylim=yl,yticks=[],xticks=[25],xticklabels=['25*']);ep.tick_params(axis='x',length=0,pad=3)
 if yl[0]<0<yl[1]:ax.axhline(0,color='#77848e',lw=.45);ep.axhline(0,color='#77848e',lw=.45)
 fig.legend(handles=[Line2D([],[],color='#26323b',lw=1.1,label='Baseline'),Line2D([],[],color='#883f81',lw=.85,label='Target'),Line2D([],[],color='#26323b',lw=1.1,label='≥50% regions'),Line2D([],[],color='#26323b',lw=1.1,ls='--',label='100% regions')],loc='upper center',bbox_to_anchor=(.52,.98),ncol=4,frameon=False)
 save(fig,n)
(O/'SI_support_mapping.json').write_text(json.dumps(mapping,indent=2),encoding='utf-8')
print('S130–S135 replotted with native vector/dashed-line rendering; all source values retained.')

s=pd.read_csv(O/'Source_Data/Figure4_gap_cutoff_sensitivity.csv')
colors={'substitution-favorable':'#d97732','tandem-favorable':'#347fac','near-transition':'#8652a1','c-Si-dominant':'#667582','entry-limited':'#a9b1b8'}
for n,ct in [(136,'capacity'),(137,'site_area')]:
 q=s[s.context.eq(ct)];tab=q.groupby(['cutoff_pct','classification']).size().unstack(fill_value=0)
 fig,ax=plt.subplots(figsize=(5.1,3.0));fig.subplots_adjust(left=.15,bottom=.18,right=.97,top=.72)
 for k in tab:ax.plot(tab.index,100*tab[k]/369,'o-',ms=4,lw=1.0,color=colors[k],label=k.replace('-',' ').capitalize())
 fig.legend(loc='upper center',ncol=3,fontsize=7,frameon=False)
 ax.set(xlabel='Near-transition cutoff (%)',ylabel='Share of regions (%)',xticks=[1,5,10],ylim=(0,60),title='Capacity constraint' if ct=='capacity' else 'Site-area constraint')
 save(fig,n)

(O/'SI_support_mapping.json').write_text(json.dumps(mapping,indent=2),encoding='utf-8')
