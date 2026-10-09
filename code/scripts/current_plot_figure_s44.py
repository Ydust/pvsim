"""Complete matched response thresholds and paired changes; no new model inputs."""
from pathlib import Path
import sys,json
sys.dont_write_bytecode=True
O=Path(__file__).resolve().parent;Q=O/'qa';SD=O/'Source_Data';F=O/'Figure_S44'
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator,ScalarFormatter
sys.path.insert(0,str(O))
from audit_panel_alignment import require_matplotlib_panel_alignment
BLACK='#26323b';PURPLE='#883f81';GRAY='#77848e'
width_mm=183
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial','DejaVu Sans'],'font.size':7.2,'axes.labelsize':7.2,'axes.titlesize':7.5,'xtick.labelsize':6.5,'ytick.labelsize':6.5,'legend.fontsize':6.5,'axes.linewidth':.6,'axes.edgecolor':GRAY,'text.color':BLACK,'axes.labelcolor':BLACK,'xtick.color':BLACK,'ytick.color':BLACK,'pdf.fonttype':42,'svg.fonttype':'none','axes.unicode_minus':False,'legend.frameon':False,'figure.facecolor':'white','savefig.facecolor':'white','xtick.major.width':.5,'ytick.major.width':.5})
def main():
 F.mkdir(exist_ok=True)
 t=pd.read_csv(SD/'Figure4_coverage_thresholds.csv')
 keys=['candidate','context','minimum_coverage_pct','lifetime_years']
 paired=t.pivot(index=keys,columns='response_state',values='initial_system_cost_usd_wp').reset_index()
 paired['target_minus_baseline_usd_wp']=paired.target-paired.baseline
 assert len(t)==656 and len(paired)==328 and not paired.isna().any().any()
 paired.to_csv(SD/'FigureS44_full_comparison_and_changes.csv',index=False,encoding='utf-8-sig')
 fig=plt.figure(figsize=(width_mm/25.4,232/25.4));axes=[];traces=[]
 for k in range(8):
  differential=k>=4;case=k%4;ti,z=divmod(case,2);row=k//2
  candidate=['single_junction','tandem'][ti];context=['capacity','site_area'][z]
  left=[.105,.60][z];bottom=[.765,.54,.315,.09][row];w=.33;h=.15
  ax=fig.add_axes([left,bottom,w,h]);ax.set_label('abcdefgh'[k]);axes.append(ax)
  ep=fig.add_axes([left+w+.008,bottom,.022,h]);ep.set_label(f'endpoint-{k}')
  title=f"{['Single junction','Tandem'][ti]} · {['capacity','site area'][z]}"
  if differential:title='Δ · '+title
  ax.annotate('abcdefgh'[k],(0,1),xycoords='axes fraction',xytext=(-14,9),textcoords='offset points',fontweight='bold',fontsize=8.5,va='bottom',annotation_clip=False)
  ax.set_title(title,loc='left',pad=9)
  g=paired[paired.candidate.eq(candidate)&paired.context.eq(context)]
  all_y=[]
  for frac,ls in [(50.,'-'),(100.,'--')]:
   q=g[g.minimum_coverage_pct.eq(frac)].sort_values('lifetime_years')
   x=q.lifetime_years.to_numpy();assert len(x)==41
   series=[('difference',PURPLE,q.target_minus_baseline_usd_wp.to_numpy())] if differential else [('baseline',BLACK,q.baseline.to_numpy()),('target',PURPLE,q.target.to_numpy())]
   for response,col,y in series:
    all_y.extend(y)
    ax.plot(x[:-1],y[:-1],color=col,lw=1 if response!='target' else .75,ls=ls,drawstyle='steps-mid')
    ep.plot([24.91,25.09],[y[-1],y[-1]],color=col,lw=1 if response!='target' else .75,ls=ls,solid_capstyle='butt',dash_capstyle='butt')
    traces.append({'panel':'abcdefgh'[k],'candidate':candidate,'context':context,'coverage_pct':frac,'response':response,'years':x.tolist(),'values_usd_wp':y.tolist()})
  lo,hi=min(all_y),max(all_y);span=hi-lo
  if differential:
   # Panel-specific linear scales resolve the actual paired changes without offsets.
   pad=max(span*.15,hi*.025,1e-5);yl=(lo-pad,hi+pad)
  else:
   pad=(hi-min(lo,0))*.05;yl=(min(lo,0)-pad,hi+pad)
  ax.set(xlim=(14.875,24.875),ylim=yl,xticks=[15,18,21.5,24],xlabel='Service life (years)',ylabel='Change (USD/Wp)' if differential else 'Cost threshold (USD/Wp)')
  ax.yaxis.set_major_locator(MaxNLocator(nbins=3))
  fmt=ScalarFormatter(useOffset=False);fmt.set_scientific(False);ax.yaxis.set_major_formatter(fmt)
  ep.set(xlim=(24.875,25.125),ylim=yl,yticks=[],xticks=[25],xticklabels=['25*']);ep.tick_params(axis='x',length=0,pad=3)
  if yl[0]<0<yl[1]:
   ax.axhline(0,color=GRAY,lw=.45,zorder=0);ep.axhline(0,color=GRAY,lw=.45,zorder=0)
 handles=[Line2D([],[],color=BLACK,lw=1,label='Baseline'),Line2D([],[],color=PURPLE,lw=.75,label='Target'),Line2D([],[],color=BLACK,lw=1,label='≥50% regions'),Line2D([],[],color=BLACK,lw=1,ls='--',label='100% regions')]
 fig.legend(handles=handles,loc='upper center',bbox_to_anchor=(.52,.994),ncol=4,columnspacing=1.8,handlelength=2.1)
 fig.canvas.draw()
 require_matplotlib_panel_alignment(fig,axes=axes,panel_ids={a:a.get_label() for a in axes},row_groups=[['a','b'],['c','d'],['e','f'],['g','h']],column_groups=[['a','c','e','g'],['b','d','f','h']],exclude_axes=[a for a in fig.axes if a not in axes],tolerance_pt=1.5,gutter_tolerance_pt=1.5,require_panel_labels=True,strict=True,json_out=Q/'Figure_S44.alignment.json',overlay_svg=Q/'Figure_S44.alignment.svg')
 fig.savefig(F/'Figure_S44.pdf',dpi=600)
 fig.savefig(F/'Figure_S44.svg',dpi=600)
 fig.savefig(F/'Figure_S44.png',dpi=300)
 fig.savefig(F/'Figure_S44.tiff',dpi=600,pil_kwargs={'compression':'tiff_lzw'})
 plt.close(fig)
 (Q/'FigureS44_v54_plot_traces.json').write_text(json.dumps(traces,indent=2),encoding='utf-8')
 caption='Full response comparison and paired changes in initial-cost thresholds. a–d, Baseline and target thresholds for single-junction capacity, single-junction site area, tandem capacity and tandem site area, respectively. e–h, Target-minus-baseline changes for the same four comparisons, using panel-specific linear scales. Solid/dashed lines require at least 50%/all of 369 regions. Thresholds match or exceed the NPV of both fixed rivals and no build, including ties. Only candidate operating response changes between paired states. All 656 absolute values and 328 paired differences are retained, including negative absolute thresholds that remain infeasible at nonnegative initial cost. Separate 25* strips preserve the project-end replacement discontinuity. Positive differences permit higher initial cost at the same coverage but do not establish absolute feasibility or actual adoption.'
 (F/'Figure_S44_caption_en.txt').write_text(caption,encoding='utf-8')
 reg=json.loads((O/'caption_registry.json').read_text(encoding='utf-8'));reg['si']['S44']='Figure S44. '+caption
 (O/'caption_registry.json').write_text(json.dumps(reg,ensure_ascii=False,indent=2),encoding='utf-8')
 (Q/'FigureS44_v54_contract.json').write_text(json.dumps({'backend':'Python','archetype':'quantitative grid','question':'How far do the operating-response endpoint thresholds shift from baseline for each constraint and candidate?','absolute_panels':['a','b','c','d'],'paired_difference_panels':['e','f','g','h'],'source':'Figure4_coverage_thresholds.csv','absolute_values':656,'paired_differences':328,'exclusions':0,'new_external_inputs':0,'dimensions_mm':[183,232]},indent=2),encoding='utf-8')
 print('S44: 656 absolute thresholds and 328 exact paired differences, all retained.',flush=True)
if __name__=='__main__':main()
