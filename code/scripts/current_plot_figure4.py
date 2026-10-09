"""Figure4: primary cost/lifetime boundaries and baseline regional gaps."""
from pathlib import Path
import sys,json
sys.dont_write_bytecode=True
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch,Rectangle
from audit_panel_alignment import require_matplotlib_panel_alignment
O=Path(__file__).resolve().parent;Q=O/'qa';S=O/'Source_Data'
SJ='#d97732';T='#347fac';CSI='#667582';NEAR='#8652a1';BLACK='#26323b';GRAY='#77848e'
width_mm=183
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial','DejaVu Sans'],'font.size':7.2,'axes.labelsize':7.2,'axes.titlesize':7.8,'xtick.labelsize':6.7,'ytick.labelsize':6.7,'legend.fontsize':6.5,'axes.linewidth':.6,'axes.edgecolor':GRAY,'axes.spines.top':False,'axes.spines.right':False,'text.color':BLACK,'axes.labelcolor':BLACK,'xtick.color':BLACK,'ytick.color':BLACK,'pdf.fonttype':42,'svg.fonttype':'none','axes.unicode_minus':False,'legend.frameon':False,'figure.facecolor':'white','savefig.facecolor':'white','xtick.major.width':.5,'ytick.major.width':.5,'hatch.linewidth':.35})
R=json.loads((Q/'Figure4_analysis_register.json').read_text());zones=pd.read_csv(S/'Figure4_regional_choice_zones.csv');th=pd.read_csv(S/'Figure4_coverage_thresholds.csv')
CM=ListedColormap(['#ffffff','#d1d9de','#f6d9bc','#c5e0ed','#f4f4f4']);TRACES=[]
def panel(a,letter,title):
 a.set_label(letter);a.annotate(letter,(0,1),xycoords='axes fraction',xytext=(-14,10),textcoords='offset points',fontweight='bold',fontsize=8.5,va='bottom',annotation_clip=False);a.set_title(title,loc='left',pad=10)
def hatch(a,x,y,categories):
 dy=float(np.median(np.diff(y)))
 for k,xx in enumerate(x):
  mask=categories[:,k]==4;starts=np.flatnonzero(mask&~np.r_[False,mask[:-1]]);ends=np.flatnonzero(mask&~np.r_[mask[1:],False])
  for start,end in zip(starts,ends):a.add_patch(Rectangle((xx-.125,y[start]-dy/2),.25,y[end]-y[start]+dy,facecolor='none',edgecolor='#b6b6b6',lw=0,hatch='///',zorder=1.2,rasterized=True))
def phase(fig,rect,j,ct,letter,destination):
 candidate=['csi','single_junction','tandem'][j];a=fig.add_axes(rect);panel(a,letter,['Single junction','Tandem'][j-1]+' · '+('capacity' if ct=='capacity' else 'site area'))
 q=zones[zones.candidate.eq(candidate)&zones.context.eq(ct)&zones.response_state.eq('baseline')]
 field=q.pivot(index='lifetime_years',columns='initial_system_cost_usd_wp',values='majority_category').sort_index().sort_index(axis=1);assert field.shape==(41,201)
 L=field.index.to_numpy();costs=field.columns.to_numpy();v=field.to_numpy();C0=R['capex2035_usd_kwp'][j]/1000;L0=R['baseline_lifetime'][j]
 a.pcolormesh(L[:-1],costs,v[:-1].T,cmap=CM,vmin=-.5,vmax=4.5,shading='nearest',rasterized=True);hatch(a,L[:-1],costs,v[:-1].T)
 left,bottom,w,h=rect;ep=fig.add_axes([left+w+.008,bottom,.023,h]);ep.set_label('endpoint-'+destination+'-'+letter)
 dy=float(np.median(np.diff(costs)));edges=np.r_[costs-dy/2,costs[-1]+dy/2]
 ep.pcolormesh([24.875,25.125],edges,v[-1][:,None],cmap=CM,vmin=-.5,vmax=4.5,shading='flat',rasterized=True);hatch(ep,np.array([25.]),costs,v[-1][:,None])
 ep.set(xlim=(24.875,25.125),ylim=(0,C0*1.02),yticks=[],xticks=[25],xticklabels=['25*']);ep.tick_params(axis='x',length=0,pad=3)
 curves=[]
 for pct,ls in [(50.,'-'),(100.,'--')]:
  t=th[th.candidate.eq(candidate)&th.context.eq(ct)&th.response_state.eq('baseline')&th.minimum_coverage_pct.eq(pct)].sort_values('lifetime_years');values=t.initial_system_cost_usd_wp.to_numpy();assert np.array_equal(L,t.lifetime_years.to_numpy())
  valid=(values[:-1]>=0)&(values[:-1]<=C0*1.02);a.plot(L[:-1],np.where(valid,values[:-1],np.nan),color=BLACK,lw=1.15,ls=ls,drawstyle='steps-mid')
  if 0<=values[-1]<=C0*1.02:ep.plot([24.91,25.09],[values[-1]]*2,color=BLACK,lw=1.15,ls=ls,solid_capstyle='butt',dash_capstyle='butt')
  curves.append(dict(coverage_pct=pct,years=L.tolist(),values_usd_wp=values.tolist()))
 (ep if L0==25 else a).scatter(L0,C0,s=25,marker='D',color=[SJ,T][j-1],edgecolor='white',linewidth=.7,clip_on=False,zorder=6)
 a.set(xlim=(14.875,24.875),ylim=(0,C0*1.02),xticks=[15,18,21.5,24],yticks=[0,.1,.2,.3] if j==1 else [0,.2,.4,.6],xlabel='Service life (years)',ylabel='Initial system cost (USD/Wp)')
 TRACES.append(dict(destination=destination,panel=letter,candidate=candidate,context=ct,lifetimes=L.tolist(),costs_usd_wp=costs.tolist(),majority_category=v.tolist(),curves=curves,baseline_marker=[L0,C0]));return a
def legends(fig):
 fig.legend(handles=[Line2D([],[],color=BLACK,lw=1.15,label='≥50% regions'),Line2D([],[],color=BLACK,lw=1.15,ls='--',label='100% regions'),Line2D([],[],marker='D',color=GRAY,ls='none',ms=3.5,label='Reference')],loc='upper center',bbox_to_anchor=(.52,.995),ncol=3,columnspacing=2,handlelength=2.1,title='Baseline response',title_fontsize=6.8)
 fig.legend(handles=[Patch(facecolor=CM(1),edgecolor='none',label='c-Si'),Patch(facecolor=CM(2),edgecolor='none',label='Single junction'),Patch(facecolor=CM(3),edgecolor='none',label='Tandem'),Line2D([],[],marker='s',ms=4.5,mfc=CM(4),mec='#b6b6b6',mew=.6,ls='none',label='Mixed')],loc='upper center',bbox_to_anchor=(.52,.928),ncol=4,columnspacing=1.5,handlelength=1.5)
def save(fig,name,axes,rows,cols):
 fig.canvas.draw();require_matplotlib_panel_alignment(fig,axes=axes,panel_ids={a:a.get_label() for a in axes},row_groups=rows,column_groups=cols,exclude_axes=[a for a in fig.axes if a not in axes],tolerance_pt=1.5,gutter_tolerance_pt=1.5,require_panel_labels=True,strict=True,json_out=Q/(name+'.alignment.json'),overlay_svg=Q/(name+'.alignment.svg'))
 fig.savefig(O/name/(name+'.pdf'),dpi=600)
 fig.savefig(O/name/(name+'.svg'),dpi=600)
 fig.savefig(O/name/(name+'.png'),dpi=300)
 fig.savefig(O/name/(name+'.tiff'),dpi=600,pil_kwargs={'compression':'tiff_lzw'});plt.close(fig)
def main():
 fig=plt.figure(figsize=(width_mm/25.4,155/25.4));axes=[];legends(fig)
 axes.append(phase(fig,[.095,.54,.342,.285],1,'capacity','a','main'))
 axes.append(phase(fig,[.59,.54,.342,.285],2,'site_area','b','main'))
 cols={'substitution-favorable':SJ,'tandem-favorable':T,'c-Si-dominant':CSI,'near-transition':NEAR,'entry-limited':CSI};labels={'substitution-favorable':'Substitution-favorable','tandem-favorable':'Tandem-favorable','c-Si-dominant':'c-Si-dominant','near-transition':'Near-transition','entry-limited':'Entry-limited'}
 fig.legend(handles=[Line2D([],[],marker='x' if k=='entry-limited' else 'o',ms=3.5,ls='none',color=cols[k],label=labels[k]) for k in cols],loc='upper center',bbox_to_anchor=(.52,.466),ncol=3,columnspacing=1.6,handlelength=1)
 for z,ct in enumerate(['capacity','site_area']):
  letter=['c','d'][z];a=fig.add_axes([[.095,.59][z],.095,.342,.25]);panel(a,letter,'Regional gaps · '+('capacity' if z==0 else 'site area'))
  d=pd.read_csv(S/('Figure4'+letter+'_regional_gaps.csv'),dtype={'adcode':str});assert len(d)==369 and d.cumulative_share_pct.iloc[-1]==100
  a.axvspan(0,5,color=NEAR,alpha=.06);a.axvline(5,color=NEAR,lw=.75,ls=':')
  for k,col in cols.items():
   q=d[d.classification.eq(k)]
   if len(q):a.scatter(q.minimum_cost_cut_pct,q.cumulative_share_pct,s=7,marker='x' if k=='entry-limited' else 'o',color=col,lw=.55 if k=='entry-limited' else 0,alpha=.8)
  a.set(xlim=(-.4,45 if z==0 else 14),ylim=(-1.5,102),yticks=[0,50,100],xlabel='Required upfront cost reduction (%)',ylabel='Cumulative share of regions (%)');a.grid(axis='y',color='#e7eaed',lw=.45);a.set_axisbelow(True);axes.append(a)
 save(fig,'Figure_4',axes,[['a','b'],['c','d']],[['a','c'],['b','d']])
def supplement():
 fig=plt.figure(figsize=(width_mm/25.4,85/25.4));legends(fig)
 axes=[phase(fig,[.095,.125,.342,.53],1,'site_area','a','S45'),phase(fig,[.59,.125,.342,.53],2,'capacity','b','S45')]
 save(fig,'Figure_S45',axes,[['a','b']],[])
if __name__=='__main__':
 main();supplement();(Q/'Figure4_v55_phase_traces.json').write_text(json.dumps(TRACES,ensure_ascii=False,indent=2),encoding='utf-8');print('Main Figure4 and cross-context Figure S45 exported.')
