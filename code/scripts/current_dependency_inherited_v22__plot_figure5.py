"""Regional decision transitions and paired economic margins; original maps."""
from pathlib import Path
from types import SimpleNamespace
import sys,json
sys.dont_write_bytecode=True
O=Path(__file__).resolve().parent;sys.path.insert(0,str(O/'code'))
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap,BoundaryNorm
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.collections import LineCollection
import cartopy.crs as ccrs
from shapely.geometry import shape,box
from shapely import make_valid,transform,union_all
from pyproj import Transformer
from map_template import draw_original_map
sys.path.insert(0,'C:/Users/yuanq/.agents/skills/nature-figure/scripts')
from audit_panel_alignment import require_matplotlib_panel_alignment
width_mm=183;Q=O/'qa';SD=O/'Source_Data';BLACK='#26323b';GRAY='#77848e';SJ='#d47735';T='#347fac';GAP='#e1e4e6'
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial','DejaVu Sans'],'font.size':7.2,'axes.labelsize':7.0,'axes.titlesize':7.5,'xtick.labelsize':6.5,'ytick.labelsize':6.5,'legend.fontsize':6.2,'axes.linewidth':.55,'axes.edgecolor':GRAY,'text.color':BLACK,'axes.labelcolor':BLACK,'xtick.color':BLACK,'ytick.color':BLACK,'pdf.fonttype':42,'svg.fonttype':'none','axes.unicode_minus':False,'legend.frameon':False,'figure.facecolor':'white','savefig.facecolor':'white','xtick.major.width':.5,'ytick.major.width':.5})
data=pd.read_csv(SD/'Figure5_displayed_region_pairs.csv',dtype={'adcode':str})
city=pd.read_csv(O/'inputs/Figure1_region_values.csv',dtype={'adcode':str});geo=json.loads((O/'inputs/geography/prefecture_boundaries.geojson').read_text(encoding='utf-8'));context=json.loads((O/'inputs/geography/map_context.geojson').read_text(encoding='utf-8'))
DATA=ccrs.PlateCarree();PROJ=ccrs.LambertConformal(central_longitude=105,central_latitude=35,standard_parallels=(25,47));projector=Transformer.from_crs('EPSG:4326',PROJ.proj4_init,always_xy=True)
geoms=[(str(f['properties']['adcode']),make_valid(shape(f['geometry']))) for f in geo['features']]
b=SimpleNamespace(city=city,DATA=DATA,PROJ=PROJ,projector=projector,box=box,geoms=geoms,projected=[(code,make_valid(transform(g,projector.transform,interleaved=False))) for code,g in geoms],taiwan=[make_valid(shape(f['geometry'])) for f in context['features'] if f['properties']['role']=='taiwan_geographic_context'],maritime=[make_valid(shape(f['geometry'])) for f in context['features'] if f['properties']['role']=='south_china_sea_maritime_line'],outline=union_all([g for code,g in geoms]))
def panel(ax,letter,title):
 ax.set_label(letter);ax.annotate(letter,(0,1),xycoords='axes fraction',xytext=(-13,6),textcoords='offset points',fontsize=8.5,fontweight='bold',ha='left',va='bottom',annotation_clip=False)
 ax.set_title(title,loc='left',pad=6,fontsize=7.5)
fig=plt.figure(figsize=(width_mm/25.4,165/25.4));axes=[];records=[];h=183*.50*(39/62)/165
for j,(tech,ct,col,pale,title) in enumerate([('single_junction','capacity',SJ,'#e8b78e','Single junction · capacity · 0.04 USD/kWh'),('tandem','site_area',T,'#a5c5da','Tandem · site area · 0.08 USD/kWh')]):
 q=data[data.candidate.eq(tech)&data.context.eq(ct)].sort_values('baseline_rank');assert len(q)==369
 bottom=[.57,.12][j]
 levels=['remaining_gap','retained','new','lost'];colours=[GAP,pale,col,'#8c729a']
 values=q.set_index('adcode').transition_class.map({v:k for k,v in enumerate(levels)})
 cmap=ListedColormap(colours);norm=BoundaryNorm(np.arange(-.5,4.5),4)
 a,_,record=draw_original_map(fig,[.055,bottom,.50,h],values,norm,cmap,'ac'[j],title,panel,b)
 record['quantitative_colormap_and_norm']='Categorical economic transition classes; projection/layer renderer unchanged';records.append(record);axes.append(a)
 ns=q.transition_class.value_counts();handles=[Patch(facecolor=pale,label=f'Retained: {int(ns.get("retained",0))}'),Patch(facecolor=col,label=f'New: {int(ns.get("new",0))}'),Patch(facecolor=GAP,label=f'Below parity: {int(ns.get("remaining_gap",0))}')]
 if ns.get('lost',0):handles.append(Patch(facecolor=colours[3],label=f'Lost: {int(ns["lost"])}'))
 fig.legend(handles=handles,loc='upper center',bbox_to_anchor=(.31,bottom-.026),ncol=3,handlelength=1.05,columnspacing=1.0,handletextpad=.35,fontsize=6.3)
 a=fig.add_axes([.685,bottom,.28,h]);axes.append(a);panel(a,'bd'[j],'Paired regional economic margins')
 x=q.baseline_rank.to_numpy();y0=q.baseline_margin_pct.to_numpy();y1=q.target_margin_pct.to_numpy()
 assert (x==np.arange(1,370)).all()
 segments=np.stack([np.c_[x,y0],np.c_[x,y1]],axis=1)
 a.add_collection(LineCollection(segments,colors=col,linewidths=.4,alpha=.32,rasterized=True,zorder=2))
 a.plot(x,y0,color=GRAY,lw=.85,zorder=3,label='Baseline')
 a.scatter(x,y1,s=1.8,color=col,lw=0,alpha=.85,rasterized=True,zorder=4,label='Path target')
 newly=q.transition_class.eq('new').to_numpy();a.scatter(x[newly],y1[newly],s=5.5,color=col,edgecolors='white',linewidths=.2,rasterized=True,zorder=5)
 a.axhline(0,color=BLACK,lw=.7,ls='--',zorder=1)
 a.set(xlim=(0,370),ylim=(-45,15),xticks=[1,185,369],yticks=[-40,-20,0,10],xlabel='Regions ranked by baseline margin',ylabel='NPV margin / initial\nsystem expenditure (%)')
 a.spines[['top','right']].set_visible(False)
 # Both candidate cases share a common normalized margin scale and all369 ranks.
 a.legend(loc='lower right',fontsize=6.1,handlelength=1.25,labelspacing=.6)
fig.text(.5,.030,'Independent candidate improvements; fixed baseline rivals, costs and lifetimes; all 369 regions',ha='center',fontsize=6.1,color=GRAY)
fig.canvas.draw()
require_matplotlib_panel_alignment(fig,axes=axes,panel_ids={a:a.get_label() for a in axes},row_groups=[['a','b'],['c','d']],column_groups=[['a','c'],['b','d']],exclude_axes=[a for a in fig.axes if a not in axes],tolerance_pt=1.5,gutter_tolerance_pt=1.5,require_panel_labels=True,strict=True,json_out=Q/'Figure_5.alignment.json',overlay_svg=Q/'Figure_5.alignment.svg')
fig.savefig(O/'Figure_5/Figure_5.pdf',dpi=600)
fig.savefig(O/'Figure_5/Figure_5.svg',dpi=600)
fig.savefig(O/'Figure_5/Figure_5.png',dpi=300)
fig.savefig(O/'Figure_5/Figure_5.tiff',dpi=600,pil_kwargs={'compression':'tiff_lzw'})
plt.close(fig)
(Q/'Figure5_map_template_checks.json').write_text(json.dumps(dict(status='PASS',maps=records,renderer_body_preserved=True,projection_and_geographic_layers_unchanged=True),ensure_ascii=False,indent=2),encoding='utf-8')
caption='Regional decision consequences of baseline-anchored operating improvements. a,c, All 369 study units under the single-junction capacity case and tandem site-area case. Pale technology colours denote retained competitiveness, saturated colours newly competitive regions, and grey regions remaining below economic parity at the respective path endpoint. Parity compares the candidate NPV with the maximum NPV of its two fixed common-baseline rivals and no build, including ties. Below parity is a model-result category, not missing data or necessarily negative candidate NPV. Neither displayed case loses an initially competitive region, although some regional margins decline. b,d, Baseline and endpoint NPV margins for the same 369 regions, ranked once by baseline margin; endpoint observations retain the same region order. Vertical segments connect matched regions. Margin is candidate NPV minus the identical fixed rival/no-build target, divided by baseline initial system expenditure and multiplied by 100. The common site charge is excluded from the denominator. Zero marks economic parity; both panels use the same normalized scale. Only the candidate operating response changes from the common physical baseline to its Figure 3 parameter-scenario endpoint. Rivals, cost, lifetime, retention and financial rules remain fixed as in Figure 4. Capacity uses 0.04 USD/kWh; site area uses 0.08 USD/kWh and a 25 USD/m² site charge. Costs and durability are the inherited conditional 2035 author scenarios. The two cases are independent interventions under different financial settings; their region counts do not define a common national allocation. All four candidate/context combinations are retained in Source Data. These are conditional competitiveness results, not observed device development, adoption forecasts or policy optima. The original geographic template and South China Sea inset are retained.'
(O/'Figure_5/Figure_5_caption_en.txt').write_text(caption,encoding='utf-8')
print('Figure5 exported with original maps, all369 paired ranks and alignment PASS.',flush=True)
