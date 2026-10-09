"""Policy decisions: regional baseline, paired flows, fiscal allocation and outcomes."""
from pathlib import Path
from types import SimpleNamespace
import sys,json
sys.dont_write_bytecode=True
O=Path(__file__).resolve().parent;Q=O/'qa';SD=O/'Source_Data'
POLICY_MAP_SUPPORT='--policy-map-support' in sys.argv
map_shift=0.
sys.path.insert(0,str(O/'code'))
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch,Rectangle,PathPatch
from matplotlib.path import Path as MPath
from matplotlib.lines import Line2D
from matplotlib.colors import ListedColormap,BoundaryNorm
import matplotlib.patheffects as pe
import cartopy.crs as ccrs
from shapely.geometry import shape,box
from shapely import make_valid,transform,union_all
from pyproj import Transformer
from map_template import draw_original_map
sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_panel_alignment import require_matplotlib_panel_alignment

width_mm=183; height_mm=195
BLACK='#26323b';GRAY='#6e7d86';NET='#394B8C'
COL={'entry':'#009E73','switch':'#CC79A7','paid_unchanged':'#B8C1CA','unfunded_unchanged':'#E5E7EB'}
LABEL={'entry':'Project entry','switch':'Technology switch','paid_unchanged':'Supported unchanged','unfunded_unchanged':'Unfunded unchanged'}
POLCOL={'General':'#0072B2','New technology':'#D55E00'}
NAMES=['no_build','csi','single_junction','tandem'];DISPLAY={'no_build':'No build','csi':'c-Si','single_junction':'SJ','tandem':'Tandem'}
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial','DejaVu Sans'],'font.size':7.0,'axes.labelsize':6.8,'axes.titlesize':7.2,'xtick.labelsize':6.2,'ytick.labelsize':6.2,'legend.fontsize':6.3,'axes.linewidth':.55,'axes.edgecolor':GRAY,'text.color':BLACK,'axes.labelcolor':BLACK,'xtick.color':BLACK,'ytick.color':BLACK,'pdf.fonttype':42,'svg.fonttype':'none','axes.unicode_minus':False,'legend.frameon':False,'figure.facecolor':'white','savefig.facecolor':'white','xtick.major.width':.5,'ytick.major.width':.5})
df=pd.read_csv(SD/'Figure5_policy_all369_paired_choices.csv',dtype={'adcode':str})
sm=pd.read_csv(SD/'Figure5_policy_response_summary.csv')
matrix=pd.read_csv(SD/'Figure5_policy_transition_matrices.csv')
curves=pd.read_csv(SD/'Figure5_policy_rate_curves.csv')
city=pd.read_csv(O/'inputs/Figure1_region_values.csv',dtype={'adcode':str})
fig=plt.figure(figsize=(width_mm/25.4,height_mm/25.4))
fig.text(.025,.975,'a',fontsize=8.5,fontweight='bold',va='top')

fig.text(.535,.975,'b',fontsize=8.5,fontweight='bold',va='top')
fig.text(.115,.975,'Regional choices' if POLICY_MAP_SUPPORT else 'Baseline choices and support',fontsize=7.3,va='top')
fig.text(.625,.975,'Response-improvement gaps',fontsize=7.3,va='top')


# Reuse the established map renderer without changing its projection or body.
geo=json.loads((O/'inputs/geography/prefecture_boundaries.geojson').read_text(encoding='utf-8'))
ctx=json.loads((O/'inputs/geography/map_context.geojson').read_text(encoding='utf-8'))
DATA=ccrs.PlateCarree();PROJ=ccrs.LambertConformal(central_longitude=105,central_latitude=35,standard_parallels=(25,47))
projector=Transformer.from_crs('EPSG:4326',PROJ.proj4_init,always_xy=True)
geoms=[(str(f['properties']['adcode']),make_valid(shape(f['geometry']))) for f in geo['features']]
bundle=SimpleNamespace(city=city,DATA=DATA,PROJ=PROJ,projector=projector,box=box,geoms=geoms,
 projected=[(code,make_valid(transform(g,projector.transform,interleaved=False))) for code,g in geoms],
 taiwan=[make_valid(shape(f['geometry'])) for f in ctx['features'] if f['properties']['role']=='taiwan_geographic_context'],
 maritime=[make_valid(shape(f['geometry'])) for f in ctx['features'] if f['properties']['role']=='south_china_sea_maritime_line'],outline=union_all([g for code,g in geoms]))
a=df[df.context.eq('capacity')&df.policy.eq('General')].set_index('adcode')
b=df[df.context.eq('site_area')&df.policy.eq('General')].set_index('adcode').loc[a.index]
pairs=[('csi','csi'),('single_junction','csi'),('csi','tandem'),('single_junction','tandem'),('no_build','csi')]
paircol=['#1F5AA6','#E6B34A','#B46D9A','#42B3A3','#D8DDE3']
joint=pd.DataFrame({'capacity_choice':a.before_choice,'site_area_choice':b.before_choice})
joint['map_class']=[pairs.index(p) for p in zip(joint.capacity_choice,joint.site_area_choice)]
joint.reset_index().to_csv(SD/'Figure5_policy_baseline_joint_map.csv',index=False,encoding='utf-8-sig')
cmap=ListedColormap(paircol);norm=BoundaryNorm(np.arange(-.5,5.5),5)
# Original a: original geographic layout, paired-choice key and support symbols.
# Original a: original geographic layout, paired-choice key and support symbols.
map_ax,_,map_record=draw_original_map(fig,[.005,.636+map_shift,.48,.292],joint.map_class,norm,cmap,'a','',lambda ax,k,t:None,bundle)
map_ax.set_label('a_map')
map_record['quantitative_colormap_and_norm']='Five joint categorical classes and v40 palette unchanged; original baseline-policy symbols restored in v42.'
map_record['palette_hex']=paircol
map_record['main_axes_position']=list(map_ax.get_position().bounds)
map_record['policy_symbols_rendered']=True
fig.text(.275,.610+map_shift,'Equal capacity / Equal site area',fontsize=6.3,ha='center',va='center')
key_positions=[(.075,.585),(.300,.585),(.075,.558),(.300,.558),(.075,.531)]
key_names={'csi':'c-Si','single_junction':'SJ','tandem':'Tandem','no_build':'No build'}
for ((cap,site),(x,y),colour) in zip(pairs,key_positions,paircol):
 y+=map_shift
 fig.add_artist(Rectangle((x,y-.0045),.024,.009,transform=fig.transFigure,facecolor=colour,edgecolor='none'))
 fig.text(x+.034,y,key_names[cap]+' / '+key_names[site],fontsize=6.3,ha='left',va='center')

# Derive 30% choices from the same current baseline and General grant basis.
cap=a.copy();v=cap[['baseline_'+k+'_npv_usd' for k in ['csi','single_junction','tandem']]].to_numpy()
grant20=cap[['offered_'+k+'_grant_usd' for k in ['csi','single_junction','tandem']]].to_numpy()
choice_names=np.array(['no_build','csi','single_junction','tandem'])
ch30=choice_names[np.c_[np.zeros(len(cap)),v+grant20*1.5].argmax(axis=1)]
cap['after_choice30']=ch30
cap['support_class']=np.select([cap.before_choice.ne('no_build'),cap.after_choice.ne('no_build'),cap.after_choice30.ne('no_build')],['Initially viable','At 20%','Added at 30%'],default='Beyond 30%')
assert cap.before_choice.eq('no_build').sum()==68
assert cap.support_class.eq('At 20%').sum()==50 and cap.support_class.eq('Added at 30%').sum()==14 and cap.support_class.eq('Beyond 30%').sum()==4
scan=curves[curves.context.eq('capacity')&curves.policy.eq('General')&np.isclose(curves.support_rate,.3)].iloc[0]
assert cap.after_choice30.ne('no_build').sum()==scan.after_built
overlay=[];handles=[]
for state,marker,color,label in [('At 20%','o','#26323b','By 20%'),('Added at 30%','^','#26323b','Above 20–30%'),('Beyond 30%','x','#B2182B','Beyond 30%')]:
 z=cap[cap.support_class.eq(state)]
 projected=PROJ.transform_points(DATA,z.lon.to_numpy(),z.lat.to_numpy())
 lim=map_record['main_projected_limits']
 assert np.all((projected[:,0]>lim[0])&(projected[:,0]<lim[1])&(projected[:,1]>lim[2])&(projected[:,1]<lim[3]))
 if marker=='x':map_ax.scatter(z.lon,z.lat,transform=DATA,marker=marker,s=13,c=color,linewidths=.8,zorder=15,path_effects=[pe.Stroke(linewidth=1.8,foreground='white'),pe.Normal()])
 else:map_ax.scatter(z.lon,z.lat,transform=DATA,marker=marker,s=10 if marker=='^' else 11,facecolors='white',edgecolors=color,linewidths=.8,zorder=15)
 handles.append(Line2D([],[],marker=marker,ls='',mfc='white' if marker!='x' else 'none',mec=color,color=color,markersize=3.2,label=f'{label} ({len(z)})'))
 for code,row in z.iterrows():overlay.append(dict(adcode=code,lat=row.lat,lon=row.lon,support_class=state,marker=marker,
  before_choice=row.before_choice,after_choice20=row.after_choice,after_choice30=row.after_choice30))
fig.legend(handles=handles,loc='center',bbox_to_anchor=(.275,.941),ncol=3,fontsize=6,frameon=False,columnspacing=.9,title='General support · Capacity',title_fontsize=6)
pd.DataFrame(overlay).to_csv(SD/'Figure5_restored_a_support_symbols.csv',index=False,encoding='utf-8-sig')

if POLICY_MAP_SUPPORT:
 from matplotlib.transforms import Bbox
 stem='Figure_S_Baseline_policy_thresholds';dest=O/stem
 for artist in list(fig.texts):
  if artist.get_position()[0]>.51:artist.remove()
 fig.canvas.draw()
 bounds=Bbox.from_bounds(0,height_mm/25.4*.5,width_mm/25.4*.51,height_mm/25.4*.5)
 for ext,dpi in [('pdf',600),('svg',600),('png',300),('tiff',600)]:
  opts={'pil_kwargs':{'compression':'tiff_lzw'}} if ext=='tiff' else {}
  fig.savefig(dest/(stem+'.'+ext),dpi=dpi,bbox_inches=bounds,pad_inches=0,**opts)
 (dest/(stem+'_caption_en.txt')).write_text('Baseline regional technology choices and General-support thresholds. Colours identify the same capacity/site-area baseline choice pairs as main Figure5a. Symbols classify the68 initially nonviable fixed-capacity opportunities:50 viable by20% support,14 additionally viable at30%, and4 not viable at30%. General support applies to all technologies and covers initial system CAPEX. This is a baseline policy counterfactual; no operating-response endpoint is applied. All original region values and coordinates are retained.\n',encoding='utf-8')
 (Q/'Figure5_v41_support_map_checks.json').write_text(json.dumps({'status':'PASS','original_map_renderer_preserved':True,'map':map_record,'symbol_count':68,'support_classes':[50,14,4]},ensure_ascii=False,indent=2),encoding='utf-8')
 plt.close(fig)
 print('Exported original policy-threshold map as a companion support figure.')
 raise SystemExit(0)


# Remaining gap and paired change: distinct absolute and difference axes.
gaps=pd.read_csv(SD/'Figure5_path_gap_comparison.csv',dtype={'adcode':str})
paired=pd.read_csv(SD/'Figure5_paired_gap_changes.csv',dtype={'adcode':str})
groups=[('single_junction','capacity','SJ\nCapacity'),('single_junction','site_area','SJ\nSite area'),
        ('tandem','capacity','Tandem\nCapacity'),('tandem','site_area','Tandem\nSite area')]
gapcolors={'lower':'#0072B2','unchanged':'#969FA7','higher':'#D55E00'}
bg=fig.add_gridspec(1,2);b_axes=[]
for i,rect in enumerate([[.625,.592,.13,.312],[.85,.592,.13,.312]]):
 ax=fig.add_axes(rect);ax.set_subplotspec(bg[0,i]);ax.set_position(rect);ax.set_label('b'+str(i+1));b_axes.append(ax)
 ax.spines[['top','right','left']].set_visible(False);ax.tick_params(axis='y',length=0,pad=5)
 ax.set_ylim(-.55,3.55)
b1,b2=b_axes
b1.set(xlim=(-4,110),xticks=[0,50,100],xlabel='Required CAPEX\nreduction (%)')
b2.set(xlim=(-4,1),xticks=[-4,-2,0,1],xlabel='Change in requirement\n(percentage points)')
b1.set_yticks([3,2,1,0],[label for tech,ct,label in groups],fontsize=6.2);b2.set_yticks([])
b1.set_title('Path endpoint',fontsize=6.7,pad=10)
b2.set_title('Endpoint − baseline',fontsize=6.7,pad=10)
b1.axvline(100,color='#c6cdd1',lw=.5,ls=':',zorder=0)
for ax in b_axes:ax.axvline(0,color='#8a969f',lw=.55,ls=':',zorder=1)
geometry=[];gap_summary=[]
for iy,(tech,ct,label) in enumerate(groups):
 z=paired[paired.candidate.eq(tech)&paired.context.eq(ct)].sort_values('adcode').reset_index(drop=True)
 assert len(z)==369 and z.adcode.nunique()==369
 endpoint=gaps[gaps.candidate.eq(tech)&gaps.context.eq(ct)&gaps.response_state.eq('endpoint')].set_index('adcode').loc[z.adcode]
 assert np.allclose(endpoint.required_upfront_cut_pct,z.endpoint,rtol=0,atol=1e-10)
 yy=3-iy;jitter=np.array([(int(code)*.618033988749895)%1-.5 for code in z.adcode])*.24
 direction=np.where(z.change_pp < -1e-9,'lower',np.where(z.change_pp>1e-9,'higher','unchanged'))
 for ax,metric,xx in [(b1,'endpoint_gap_pct',z.endpoint.to_numpy()),(b2,'paired_change_pp',z.change_pp.to_numpy())]:
  assert xx.min()>=ax.get_xlim()[0] and xx.max()<=ax.get_xlim()[1]
  for cls in gapcolors:
   mask=direction==cls
   ax.scatter(xx[mask],yy+jitter[mask],s=3,color=gapcolors[cls],edgecolors='none',alpha=.67,zorder=3)
  lo,med,hi=np.quantile(xx,[.25,.5,.75]);line_y=yy+.28
  ax.plot([lo,hi],[line_y,line_y],color=BLACK,lw=1.4,zorder=4)
  ax.plot([med,med],[line_y-.045,line_y+.045],color=BLACK,lw=.8,zorder=4)
  for code,x,y0,cls in zip(z.adcode,xx,yy+jitter,direction):
   geometry.append(dict(adcode=code,candidate=tech,context=ct,metric=metric,plot_x=x,plot_y=y0,direction=cls))
 gap_summary.append(dict(candidate=tech,context=ct,regions=369,lower=int((direction=='lower').sum()),unchanged=int((direction=='unchanged').sum()),higher=int((direction=='higher').sum()),
  median_baseline_gap_pct=float(z.baseline.median()),median_endpoint_gap_pct=float(z.endpoint.median()),
  paired_change_min_pp=float(z.change_pp.min()),paired_change_median_pp=float(z.change_pp.median()),paired_change_max_pp=float(z.change_pp.max())))
fig.legend([Line2D([],[],marker='o',ls='none',color=gapcolors[k],ms=3.2,markeredgewidth=0) for k in gapcolors],
 ['Lower gap','Unchanged','Higher gap'],loc='center',bbox_to_anchor=(.79,.953),ncol=3,fontsize=6.1,columnspacing=.8,handlelength=.7,handletextpad=.45)
pd.DataFrame(geometry).to_csv(SD/'Figure5_v32_gap_display.csv',index=False,encoding='utf-8-sig')
pd.DataFrame(gap_summary).to_csv(SD/'Figure5_v32_gap_summary.csv',index=False,encoding='utf-8-sig')

# Policy choices as four conservative Sankeys, all sharing one region-width scale.
fig.text(.535,.490,'d',fontsize=8.5,fontweight='bold',va='baseline')
fig.text(.625,.490,'Policy-induced choices',fontsize=7.3,va='baseline')
flowcol={'entry':COL['entry'],'switch':COL['switch'],'paid_unchanged':COL['paid_unchanged'],'unfunded_unchanged':COL['unfunded_unchanged']}
fig.legend([Patch(facecolor=flowcol[k],edgecolor='#cad1d5',linewidth=.3) for k in flowcol],
 ['Project entry','Technology switch','Supported unchanged','Still no build'],loc='center',bbox_to_anchor=(.772,.461),ncol=2,fontsize=6.2,columnspacing=1.2,handlelength=1.2,handletextpad=.5)
for xx,title in [(.6425,'General · 20%'),(.8875,'New technology · 20%')]:
 fig.text(xx,.435,title,fontsize=6.7,ha='center',va='center')
for yy,label in [(.3535,'Capacity'),(.1575,'Site area')]:
 fig.text(.515,yy,label,fontsize=6.3,ha='center',va='center',rotation=90)
cg=fig.add_gridspec(2,2);c_axes=[];band_records=[];node_records=[]
node_order=['no_build','csi','single_junction','tandem']
names={'no_build':'No build','csi':'c-Si','single_junction':'SJ','tandem':'Tandem'}
region_scale=.70/369;node_gap=.075
for ri,ct in enumerate(['capacity','site_area']):
 for ci,pol in enumerate(['General','New technology']):
  rect=[.535+ci*.245,.281-ri*.196,.215,.145]
  ax=fig.add_axes(rect);ax.set_subplotspec(cg[ri,ci]);ax.set_position(rect);ax.set_label(f'd{ri}{ci}');c_axes.append(ax)
  ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
  z=matrix[matrix.context.eq(ct)&matrix.policy.eq(pol)].copy();assert len(z)==16 and z.regions.sum()==369
  node_bounds={};cursors={}
  for side,field,x in [('without','before_choice',.29),('with','after_choice',.71)]:
   amounts=z.groupby(field).regions.sum().reindex(node_order,fill_value=0)
   positive=int(amounts.gt(0).sum());margin=(1-.70-node_gap*(positive-1))/2;cursor=1-margin
   for tech in node_order:
    n=int(amounts[tech]);rendered=n>0
    top=cursor if rendered else np.nan;bottom_y=cursor-n*region_scale if rendered else np.nan
    if rendered:
     node_bounds[(side,tech)]=(bottom_y,top);cursors[(side,tech)]=top
     ax.add_patch(Rectangle((x,bottom_y),.025,top-bottom_y,facecolor='#536875',edgecolor='none',zorder=4))
     tx=x-.015 if side=='without' else x+.04
     ax.text(tx,(top+bottom_y)/2,names[tech]+'\n'+str(n),fontsize=6,ha='right' if side=='without' else 'left',va='center',linespacing=1.05)
     cursor=bottom_y-node_gap
    node_records.append(dict(context=ct,policy=pol,side=side,technology=tech,regions=n,rendered=rendered,bottom=bottom_y,top=top,region_scale=region_scale))
  for before in node_order:
   for after in node_order:
    row=z[z.before_choice.eq(before)&z.after_choice.eq(after)].iloc[0];n=int(row.regions);cls=row.response_class
    rec=dict(context=ct,policy=pol,support_rate=.2,before_choice=before,after_choice=after,regions=n,response_class=cls,rendered=n>0,region_scale=region_scale)
    if n:
     st=cursors[('without',before)];sb=st-n*region_scale;tt=cursors[('with',after)];tb=tt-n*region_scale
     cursors[('without',before)]=sb;cursors[('with',after)]=tb
     xl,xr=.315,.71;xm=(xl+xr)/2
     path=MPath([(xl,sb),(xm,sb),(xm,tb),(xr,tb),(xr,tt),(xm,tt),(xm,st),(xl,st),(xl,sb)],
      [MPath.MOVETO,MPath.CURVE4,MPath.CURVE4,MPath.CURVE4,MPath.LINETO,MPath.CURVE4,MPath.CURVE4,MPath.CURVE4,MPath.CLOSEPOLY])
     ax.add_patch(PathPatch(path,facecolor=flowcol[cls],edgecolor='white',linewidth=.25,alpha=.9,zorder=2))
     if cls in ['entry','switch']:
      tlabel=.10 if cls=='entry' else .50
      label_x=(1-tlabel)**3*xl+3*(1-tlabel)**2*tlabel*xm+3*(1-tlabel)*tlabel**2*xm+tlabel**3*xr
      label_y=(st+sb)/2+(3*tlabel**2-2*tlabel**3)*((tt+tb-st-sb)/2)
      ax.text(label_x,label_y,str(n),fontsize=6,ha='center',va='center',zorder=5)
     rec.update(source_bottom=sb,source_top=st,target_bottom=tb,target_top=tt)
    else:rec.update(source_bottom=np.nan,source_top=np.nan,target_bottom=np.nan,target_top=np.nan)
    band_records.append(rec)
  for key,(bottom_y,top) in node_bounds.items():assert np.isclose(cursors[key],bottom_y,rtol=0,atol=1e-12)
pd.DataFrame(band_records).to_csv(SD/'Figure5_v34_sankey_bands.csv',index=False,encoding='utf-8-sig')
pd.DataFrame(node_records).to_csv(SD/'Figure5_v34_sankey_nodes.csv',index=False,encoding='utf-8-sig')


# Case-specific waterfalls: show signed contributions and exact decision counts.
dg=fig.add_gridspec(1,2);bottom=[]
pathsm=pd.read_csv(SD/'Figure5_operating_path_summary.csv')
energydecomp=pd.read_csv(SD/'Figure5_operating_path_response_decomposition.csv')
effectcol={'entry':COL['entry'],'switch':COL['switch'],'unchanged':COL['paid_unchanged']}
fig.text(.025,.490,'c',fontsize=8.5,fontweight='bold',va='baseline')
fig.text(.115,.490,'Response-improvement outcomes',fontsize=7.3,va='baseline')
fig.legend([Patch(facecolor=effectcol[k],edgecolor='none') for k in effectcol]+[Patch(facecolor=NET,edgecolor='none')],
 ['Project entry','Technology switch','Unchanged choice','Net generation'],loc='center',bbox_to_anchor=(.28,.461),ncol=2,fontsize=6.2,columnspacing=1.2,handlelength=1.2,handletextpad=.5)
waterfall=[];count_display=[];zero_controls=[]
cases=[('single_junction','capacity','SJ / Capacity',[.10,.100,.16,.290],(-3,80),[0,20,40,60,80]),
       ('tandem','site_area','Tandem / Site area',[.31,.100,.16,.290],(-15,500),[0,100,200,300,400,500])]
for i,(tech,ct,title,rect,ylimit,yticks) in enumerate(cases):
 ax=fig.add_axes(rect);ax.set_subplotspec(dg[0,i]);ax.set_position(rect);ax.set_label('c'+str(i+1));bottom.append(ax)
 ax.spines[['top','right']].set_visible(False);ax.tick_params(axis='x',length=0,pad=4,labelsize=6)
 ax.set_title(title,fontsize=6.7,pad=7)
 r=pathsm[pathsm.candidate.eq(tech)&pathsm.context.eq(ct)].iloc[0]
 running=0.;ticks=[]
 for x,cls in enumerate(['entry','switch','unchanged']):
  z=energydecomp[energydecomp.candidate.eq(tech)&energydecomp.context.eq(ct)&energydecomp.response_class.eq(cls)].iloc[0]
  start=running
  for sign,value in [('positive',z.positive_generation_change_kwh/1e6),('negative',z.negative_generation_change_kwh/1e6)]:
   # No minimum display height: small adverse components retain their true magnitude.
   ax.bar(x,value,bottom=running,width=.64,color=effectcol[cls],edgecolor='none',zorder=3)
   waterfall.append(dict(candidate=tech,context=ct,response_class=cls,sign=sign,plot_x=x,bottom_gwh=running,contribution_gwh=value,top_gwh=running+value))
   running+=value
  if abs(z.net_discounted_generation_kwh)<1e-9:
   ax.scatter(x,start,s=13,facecolors='white',edgecolors=effectcol[cls],linewidths=.7,zorder=4)
  ax.plot([x+.32,x+.68],[running,running],color='#8a969f',lw=.55,zorder=2)
  net=z.net_discounted_generation_kwh/1e6
  # Numeric labels report class net contribution; signs make downward steps explicit.
  label='0' if net==0 else f'{net:+.1f}'
  ax.text(x,max(start,running)+(ylimit[1]-ylimit[0])*.035,label,fontsize=6,ha='center',va='bottom')
  ticks.append({'entry':'Entry','switch':'Switch','unchanged':'Same'}[cls])
 total=r.net_discounted_generation_kwh/1e6
 assert np.isclose(running,total,rtol=0,atol=1e-10)
 ax.bar(3,total,width=.64,color=NET,edgecolor='none',zorder=3)
 ax.text(3,total+(ylimit[1]-ylimit[0])*.035,f'{total:.1f}',fontsize=6,ha='center',va='bottom')
 waterfall.append(dict(candidate=tech,context=ct,response_class='net',sign='total',plot_x=3,bottom_gwh=0.,contribution_gwh=total,top_gwh=total))
 ticks.append('Net');ax.set(xlim=(-.6,3.6),ylim=ylimit,yticks=yticks,xticks=[0,1,2,3]);ax.set_xticklabels(ticks)
 ax.axhline(0,color='#8a969f',lw=.5,zorder=1)
 if i==0:ax.set_ylabel('Discounted generation change (GWh)',fontsize=6.5,labelpad=3)
for row in pathsm.itertuples():
 for cls in ['entry','switch','unchanged','exit']:
  count_display.append(dict(candidate=row.candidate,context=row.context,response_class=cls,regions=int(getattr(row,cls))))
for iy,(tech,ct,label) in enumerate([('single_junction','site_area','SJ / Site area'),('tandem','capacity','Tandem / Capacity')]):
 r=pathsm[pathsm.candidate.eq(tech)&pathsm.context.eq(ct)].iloc[0]
 assert r.entry==r.switch==r.exit==r.net_discounted_generation_kwh==0 and r.unchanged==369
 yy=.044-iy*.018
 zero_controls.append(dict(candidate=tech,context=ct,regions=369,entry=0,switch=0,unchanged=369,exit=0,net_generation_gwh=0.))
pd.DataFrame(waterfall).to_csv(SD/'Figure5_v33_waterfall_display.csv',index=False,encoding='utf-8-sig')
pd.DataFrame(count_display).to_csv(SD/'Figure5_v33_decision_counts.csv',index=False,encoding='utf-8-sig')
pd.DataFrame(zero_controls).to_csv(SD/'Figure5_v33_zero_controls.csv',index=False,encoding='utf-8-sig')


fig.canvas.draw()
comparable=b_axes+c_axes+bottom
require_matplotlib_panel_alignment(fig,axes=comparable,panel_ids={a:a.get_label() for a in comparable},
 row_groups=[['b1','b2'],['d00','d01'],['d10','d11'],['c1','c2']],column_groups=[['d00','d10'],['d01','d11']],exclude_axes=[a for a in fig.axes if a not in comparable],
 tolerance_pt=1.5,gutter_tolerance_pt=1.5,strict=True,json_out=Q/'Figure_5.alignment.json',overlay_svg=Q/'Figure_5.alignment.svg')
fig.savefig(O/'Figure_5/Figure_5.pdf',dpi=600)
fig.savefig(O/'Figure_5/Figure_5.svg',dpi=600)
fig.savefig(O/'Figure_5/Figure_5.png',dpi=300)
fig.savefig(O/'Figure_5/Figure_5.tiff',dpi=600,pil_kwargs={'compression':'tiff_lzw'})
plt.close(fig)
(Q/'Figure5_v42_map_checks.json').write_text(json.dumps({'status':'PASS','original_map_renderer_preserved':True,'map':map_record,'joint_choice_count':369},ensure_ascii=False,indent=2),encoding='utf-8')
caption='Decision effects of operating-response improvements and baseline support. a, Baseline choices under capacity and site-area constraints; symbols mark General-support thresholds for initially nonviable capacity opportunities. b, Candidate-specific initial-cost reductions required for parity against fixed rivals and no build at the response endpoint (left), and endpoint-minus-baseline changes (right). Dots show 369 regions per group; black intervals/ticks indicate interquartile ranges/medians, including zeros. c, Signed discounted-generation contributions from entry, technology switching and unchanged choices, followed by their net sum. Choices maximize NPV. b,c independently improve one candidate’s response while holding rivals, costs, density and durability fixed. d, Original-baseline choices before and after 20% support; band width denotes region count, with 369 paired choices per diagram. General supports all technologies; New technology supports single junction and tandem. d is a separate policy comparison. Portfolios contain standardized 1-MWp or 1-ha opportunities over 25 years. SJ, single junction.\n'
(O/'Figure_5/Figure_5_caption_en.txt').write_text(caption,encoding='utf-8')

print('Exported v44: original policy-threshold symbols restored to main a; b/c/d and all numerical values unchanged.')

# Final current caption export; plotting and numerical results are unchanged.
if __name__ == "__main__":
    from caption_registry import write_main_caption
    write_main_caption(5)
