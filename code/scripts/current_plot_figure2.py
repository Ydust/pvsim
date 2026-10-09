"""Reference-led article figures using the complete archived 369-region model outputs."""
from pathlib import Path
import sys, json, hashlib, math
sys.dont_write_bytecode = True
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, ListedColormap, BoundaryNorm, LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle, ConnectionPatch
import cartopy.crs as ccrs
from cartopy.mpl.ticker import LongitudeFormatter, LatitudeFormatter
from scipy.stats import pearsonr, spearmanr, gaussian_kde
from shapely import make_valid, transform
import data_helpers as b
from audit_panel_alignment import require_matplotlib_panel_alignment

if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
HERE=Path(__file__).resolve().parent
QA=HERE/'qa'; SD=HERE/'Source_Data'
QA.mkdir(exist_ok=True); SD.mkdir(exist_ok=True)
N=b.N; A=b.A; SUB=b.SUB
city=b.city.copy(); LOOKUP=city.set_index('adcode')
SJ='#d97732'; T='#347fac'; CSI='#727b82'; NONE='#e1e4e6'; BLACK='#22272b'
THERMAL='#ce9636'; SPECTRAL='#347fac'; IAM='#8c729a'
TECHS=['no_build','csi','single_junction','tandem']
TECH_NAMES=['No build','c-Si','Single junction','Tandem']
TECH_COLORS=[NONE,CSI,SJ,T]
DATA=ccrs.PlateCarree()
plt.rcParams.update({
 'font.family':'sans-serif','font.sans-serif':['Arial','DejaVu Sans'],
 'font.size':7.2,'axes.labelsize':7.2,'axes.titlesize':7.5,
 'xtick.labelsize':6.7,'ytick.labelsize':6.7,'legend.fontsize':6.8,
 'axes.linewidth':.55,'axes.edgecolor':'#687078','axes.facecolor':'white',
 'axes.spines.top':True,'axes.spines.right':True,
 'text.color':BLACK,'axes.labelcolor':BLACK,'xtick.color':BLACK,'ytick.color':BLACK,
 'xtick.major.width':.5,'ytick.major.width':.5,'xtick.major.size':2.7,'ytick.major.size':2.7,
 'pdf.fonttype':42,'svg.fonttype':'none','axes.unicode_minus':False,
 'legend.frameon':False,'figure.facecolor':'white','savefig.facecolor':'white'})
REPORT={'version':15,'backend':'Python','regions':369,'excluded_regions':0,'figures':{}}

def panel(ax, letter, title='', offset=6):
    ax.set_label(letter)
    ax.annotate(letter,(0,1),xycoords='axes fraction',xytext=(-13,offset),textcoords='offset points',
                ha='left',va='bottom',fontsize=8.5,fontweight='bold',annotation_clip=False)
    if title: ax.set_title(title,loc='left',pad=offset,fontsize=7.5)

def source(frame, name):
    original=pd.read_csv(SD/f'{name}.csv')
    pd.testing.assert_frame_equal(frame.reset_index(drop=True),original,check_dtype=False,check_exact=False,rtol=1e-12,atol=1e-12)

def export(fig,n,axes,rows,cols,notes=None):
    out=HERE/f'Figure_{n}'; out.mkdir(exist_ok=True)
    fig.canvas.draw()
    require_matplotlib_panel_alignment(fig,axes=axes,panel_ids={a:a.get_label() for a in axes},
      row_groups=rows,column_groups=cols,tolerance_pt=1.5,gutter_tolerance_pt=1.5,
      require_panel_labels=True,strict=True,json_out=QA/f'Figure_{n}.alignment.json',
      overlay_svg=QA/f'Figure_{n}.alignment.svg')
    fig.savefig(out/f'Figure_{n}.pdf',dpi=600)
    fig.savefig(out/f'Figure_{n}.svg',dpi=600)
    fig.savefig(out/f'Figure_{n}.png',dpi=300)
    fig.savefig(out/f'Figure_{n}.tiff',dpi=600,pil_kwargs={'compression':'tiff_lzw'})
    REPORT['figures'].setdefault(str(n),{}).update(dimensions_mm=(fig.get_size_inches()*25.4).tolist(),layout_notes=notes or [])
    plt.close(fig); print(f'Figure {n} exported and panel alignment passed',flush=True)

def draw_original_map(fig, rect, values, norm, cmap, letter, title, panel, b):
    assert len(values) == values.index.nunique() == 369
    assert set(values.index) == set(b.city.adcode)
    ax = fig.add_axes(rect, projection=b.PROJ)
    ax.set_extent([73, 135, 17, 54], crs=b.DATA)
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    # Preserve the original equal geographic aspect without moving any other
    # panel. Fit to the existing height, right-align within the map rectangle.
    width = rect[3] * fig.get_figheight()/fig.get_figwidth() * (x1-x0)/(y1-y0)
    assert width <= rect[2] + 1e-9
    ax.set_position([rect[0]+rect[2]-width, rect[1], width, rect[3]])
    ax.set_aspect('equal')
    ax.spines['geo'].set_visible(False)
    projected = dict(b.projected)
    visible_codes = set()

    def layers(a, inset=False):
        limits = b.box(a.get_xlim()[0], a.get_ylim()[0], a.get_xlim()[1], a.get_ylim()[1])
        crs = b.DATA if inset else b.PROJ

        def clip(g):
            return make_valid(g if inset else transform(g, b.projector.transform, interleaved=False)).intersection(limits)

        for code, g in b.geoms:
            z = g.intersection(limits) if inset else projected[code].intersection(limits)
            if not z.is_empty:
                visible_codes.add(code)
                a.add_geometries([z], crs=crs, facecolor=cmap(norm(values.loc[code])),
                                 edgecolor='white', linewidth=.06 if inset else .10, zorder=2)
        if inset:
            a.add_geometries([clip(b.outline)], crs=crs, facecolor='none',
                             edgecolor='#455154', linewidth=.25, zorder=4)
        for g in b.taiwan:
            a.add_geometries([clip(g)], crs=crs, facecolor='#eeeeee',
                             edgecolor='#697172' if inset else 'none',
                             linewidth=.32 if inset else 0, zorder=3)
        if inset:
            for g in b.maritime:
                a.add_geometries([clip(g)], crs=crs, facecolor='none',
                                 edgecolor='#455154', linewidth=.4, zorder=4)

    layers(ax)
    ins = ax.inset_axes([.785, .006, .212, .37], projection=b.DATA)
    ins.set_extent([105, 125, 3, 25], crs=b.DATA)
    ins.set_facecolor('white')
    layers(ins, True)
    ins.spines['geo'].set_linewidth(.4)
    ins.spines['geo'].set_edgecolor('#7d8588')
    ins.text(.5, -.08, 'South China Sea', transform=ins.transAxes, ha='center', va='top',
             fontsize=6, color='#51595c', fontfamily='DejaVu Sans')
    assert visible_codes == set(values.index)
    p = b.PROJ.transform_points(b.DATA, b.city.lon.to_numpy(), b.city.lat.to_numpy())
    assert np.isfinite(p).all()
    main = (p[:,0]>x0)&(p[:,0]<x1)&(p[:,1]>y0)&(p[:,1]<y1)
    inset = b.city.lon.between(105,125).to_numpy() & b.city.lat.between(3,25).to_numpy()
    assert (main | inset).all()
    panel(ax, letter, title)
    record = {'panel':letter,'regions':369,'visible_region_polygons':len(visible_codes),
              'main_region_centres':int(main.sum()),'inset_only_region_codes':b.city.loc[~main,'adcode'].tolist(),
              'main_extent':[73,135,17,54],'main_projection':'LambertConformal 105/35; 25/47',
              'main_projected_limits':[x0,x1,y0,y1],
              'inset_projection':'PlateCarree','inset_extent':[105,125,3,25],
              'inset_axes_fraction':[.785,.006,.212,.37],
              'main_frame':False,'province_overlay_layers':0,'graticule_layers':0,'river_layers':0,
              'coordinate_edits':False,'value_edits':False,'aspect':'equal',
              'city_boundary_color':'white','city_boundary_width_pt':.10,
              'inset_boundary_width_pt':.06,'width_figure_fraction':width,
              'quantitative_colormap_and_norm':'Unchanged from preview v3'}
    return ax, matplotlib.cm.ScalarMappable(norm=norm,cmap=cmap), record


def geography(fig,rect,values,norm,cmap,letter,title,framed=False):
    # Geographic rendering is the study's original template, independently of
    # the new surrounding evidence-panel arrangement and quantitative scales.
    ax,sm,record=draw_original_map(fig,rect,values,norm,cmap,letter,title,panel,b)
    REPORT.setdefault('map_template',[]).append(record)
    return ax,sm

def supplementary_distributions():
    fig=plt.figure(figsize=(183/25.4,95/25.4));axes=[];stats=[]
    for j,(field,col,limits,label,title) in enumerate([
      ('single_capacity_pct',SJ,(0,6.5),'Single junction · capacity','Single junction · equal capacity'),
      ('tandem_area_pct',T,(26.8,28.9),'Tandem · aperture','Tandem · equal aperture area')]):
        left=[.08,.60][j]
        a=fig.add_axes([left,.44,.36,.43]);panel(a,'ab'[j],title)
        grouped=[city.loc[city.ghi_quartile.eq(q),field].to_numpy() for q in ['Q1','Q2','Q3','Q4']]
        v=a.violinplot(grouped,positions=np.arange(1,5),widths=.72,showmeans=False,showmedians=False,showextrema=False,bw_method=.3)
        for body in v['bodies']:body.set(facecolor=col,edgecolor=col,alpha=.22,linewidth=.65)
        for k,z in enumerate(grouped,1):
            jitter=(np.arange(len(z))%17-8)/100
            a.scatter(k+jitter,z,s=2.1,color=col,alpha=.19,linewidths=0,rasterized=True)
            p10,med,p90=np.quantile(z,[.1,.5,.9])
            a.hlines([p10,p90],k-.21,k+.21,color=col,lw=.8,ls='--')
            a.hlines(med,k-.26,k+.26,color=BLACK,lw=.95)
            a.plot(k,z.mean(),'o',color='white',markeredgecolor=col,mew=.8,ms=3,zorder=6)
            stats.append({'technology':label,'ghi_quartile':f'Q{k}','n':len(z),'minimum':z.min(),'p10':p10,'median':med,'p90':p90,'maximum':z.max(),'mean':z.mean()})
        a.set(xlim=(.4,4.6),ylim=limits,xticks=range(1,5),xticklabels=['Q1','Q2','Q3','Q4'],ylabel='Yield gain (%)')
        a.grid(axis='y',color='#eceeef',lw=.45);a.set_axisbelow(True);axes.append(a)
        tab=fig.add_axes([left,.085,.36,.26]);tab.axis('off');tab.set(xlim=(0,1),ylim=(0,1))
        for k in range(4):tab.text((k+.5)/4,.90,f'Q{k+1}',ha='center',va='center',fontsize=6.3)
        for row,key in enumerate(['n','mean','median','p10','p90']):
            y=.74-row*.15
            tab.text(-.025,y,{'n':'n','mean':'Mean','median':'Median','p10':'P10','p90':'P90'}[key],ha='right',va='center',fontsize=6.3)
            for k,z in enumerate(stats[j*4:j*4+4]):
                value=str(z[key]) if key=='n' else f'{z[key]:.2f}'
                tab.text((k+.5)/4,y,value,ha='center',va='center',fontsize=6.3)
        for y in [.98,.82,.065]:tab.plot([0,1],[y,y],transform=tab.transAxes,color='#c9ced2',lw=.4)
    fig.legend(handles=[Line2D([],[],marker='o',markerfacecolor='white',markeredgecolor=BLACK,ms=3,ls='none',label='Mean'),
                        Line2D([],[],color=BLACK,lw=.95,label='Median'),
                        Line2D([],[],color=CSI,lw=.8,ls='--',label='Spatial P10–P90')],
               loc='lower center',bbox_to_anchor=(.52,.015),ncol=3,fontsize=6.5,handlelength=1.8,columnspacing=2)
    name='Figure_S_Fig1_distributions';out=HERE/name;out.mkdir(exist_ok=True)
    fig.canvas.draw()
    require_matplotlib_panel_alignment(fig,axes=axes,panel_ids={a:a.get_label() for a in axes},
      row_groups=[['a','b']],column_groups=[],tolerance_pt=1.5,gutter_tolerance_pt=1.5,
      require_panel_labels=True,strict=True,json_out=QA/f'{name}.alignment.json',overlay_svg=QA/f'{name}.alignment.svg')
    fig.savefig(out/f'{name}.pdf',dpi=600);fig.savefig(out/f'{name}.svg',dpi=600)
    fig.savefig(out/f'{name}.png',dpi=300);fig.savefig(out/f'{name}.tiff',dpi=600,pil_kwargs={'compression':'tiff_lzw'})
    plt.close(fig)
    caption='Regional yield-gain distributions by GHI quartile. a, Single-junction gains at equal installed capacity. b, Tandem gains at equal aperture area. All 369 modelling regions are retained (Q1: 93; Q2–Q4: 92 each). Violin widths are kernel densities with bandwidth factor 0.3; dots show every regional value with deterministic display-only horizontal jitter. Open circles, black lines and coloured dashed marks show mean, median and spatial P10–P90. Tables give n and the corresponding statistics in percent. Spatial percentiles are not confidence intervals. Values and quartile definitions are identical to the main Figure1 source data.'
    (out/f'{name}_caption.txt').write_text(caption,encoding='utf-8')
    source(pd.DataFrame(stats),'Figure1_quartile_statistics')
    REPORT['supplementary_figures']={name:{'n':369,'dimensions_mm':[183,95],'numbering':'Provisional descriptive name; not inserted into formal SI','statistics_recomputed':True}}
    print('Companion SI distributions exported and alignment passed',flush=True)


def figure1():
    # Main evidence: location of modeled gains and their association with GHI.
    # The same empirical quartile evidence is retained in the companion SI.
    height=150;fig=plt.figure(figsize=(183/25.4,height/25.4));axes=[]
    width=.345;lefts=[.05,.595]
    probe=fig.add_axes([0,0,1,1],projection=b.PROJ);probe.set_extent([73,135,17,54],crs=DATA)
    aspect=np.ptp(probe.get_xlim())/np.ptp(probe.get_ylim());probe.remove()
    h=183*width/aspect/height
    points=None
    for j,(field,col,cmap,limits,heading) in enumerate([
      ('single_capacity_pct',SJ,plt.get_cmap('YlOrBr'),(0,6.5),'Single junction · equal installed capacity'),
      ('tandem_area_pct',T,plt.get_cmap('Blues'),(26.8,28.9),'Tandem · equal aperture area')]):
        y=[.60,.14][j];letters=['ab','cd'][j]
        fig.text(lefts[0],[.975,.485][j],heading,color=col,fontsize=8.5,fontweight='bold',va='center')
        vals=city.set_index('adcode')[field]
        ax,sm=geography(fig,[lefts[0],y,width,h],vals,Normalize(*limits),cmap,letters[0],'Regional gains');axes.append(ax)
        cbax=fig.add_axes([.10,y-.045,.24,.01])
        cb=fig.colorbar(sm,cax=cbax,orientation='horizontal',ticks=[0,3,6] if j==0 else [27,28,28.8])
        cb.set_label('Yield gain (%)',labelpad=2,fontsize=6.7);cb.ax.tick_params(labelsize=6.4,pad=1.5,length=2)
        a=fig.add_axes([lefts[1],y,width,h]);panel(a,letters[1],'GHI association')
        points=a.scatter(city.ghi_kwh_m2/1000,city[field],c=city.tair_mean,cmap='Purples',norm=Normalize(-2,27),s=5,linewidths=0,alpha=.85,rasterized=True)
        x=np.linspace(city.ghi_kwh_m2.min()/1000,city.ghi_kwh_m2.max()/1000,100)
        a.plot(x,np.polyval(np.polyfit(city.ghi_kwh_m2/1000,city[field],1),x),color='#777f86',lw=.7,ls='--')
        a.set(xlim=(.9,2.4),ylim=limits,xticks=[1,1.5,2],xlabel='GHI (MWh/m²/year)',ylabel='Yield gain (%)');axes.append(a)
    cbax=fig.add_axes([lefts[1],.048,width,.01])
    cb=fig.colorbar(points,cax=cbax,orientation='horizontal',ticks=[0,10,20])
    cb.set_label('Mean air temperature (°C)',fontsize=6.7,labelpad=2);cb.ax.tick_params(labelsize=6.4,pad=1.5,length=2)
    export(fig,1,axes,[['a','b'],['c','d']],[['a','c'],['b','d']],
      ['Two technology rows with equal-width map and association panels. Original map aspect fixes the common rendered plot height; colorbars are ancillary axes. Quartile distributions retained in companion SI.'])
    source(city,'Figure1_region_values')
    REPORT['figures']['1'].update(n=369,quartile_counts=city.groupby('ghi_quartile').size().to_dict(),
      correlations={k:{'pearson':float(pearsonr(city.ghi_kwh_m2,city[k]).statistic),'spearman':float(spearmanr(city.ghi_kwh_m2,city[k]).statistic)} for k in ['single_capacity_pct','tandem_area_pct']},
      panel_order=['SJ map','SJ GHI association','Tandem map','Tandem GHI association'],
      supplementary_distributions='Figure_S_Fig1_distributions',scatter_marker_area_pt2=5)
    supplementary_distributions()


def figure2():
    components=pd.read_csv(SD/'Figure2_dual_path_components.csv',dtype={'adcode':str})
    stats=pd.read_csv(SD/'Figure2_dual_path_component_summaries.csv')
    identity=pd.read_csv(SD/'Figure2_dual_path_area_identity.csv',dtype={'adcode':str})
    states=pd.read_csv(SD/'Figure2_dual_path_all_states.csv',dtype={'adcode':str})
    means=pd.read_csv(SD/'Figure2_dual_path_response_summaries.csv')
    calc=json.loads((QA/'Figure2_dual_path_calculation.json').read_text(encoding='utf-8'))
    assert calc['status']=='PASS' and len(states)==5904 and len(components)==738
    fig=plt.figure(figsize=(183/25.4,145/25.4));axes=[]
    lefts=[.135,.655];width=.31;height=.285
    techs=[('single','Single junction',SJ,'o'),('tandem','2T tandem',T,'s')]
    a=fig.add_axes([lefts[0],.635,width,height]);panel(a,'a','Specific-yield contributions')
    terms=['electrical_pp','thermal_pp','spectral_pp','iam_pp','total_pct']
    for j,(tech,name,col,marker) in enumerate(techs):
        z=stats[stats.technology.eq(tech)].set_index('term').loc[terms]
        y=np.arange(5)[::-1]+(.15 if j==0 else -.15)
        a.barh(y,z['mean'],height=.24,color=col,alpha=.72,linewidth=0,zorder=2)
        a.hlines(y,z.p10,z.p90,color=col,lw=.85,zorder=4)
        a.plot(z['mean'],y,marker,ms=2.6,color='white',markeredgecolor=col,mew=.75,ls='none',zorder=5)
    a.axvline(0,color='#a3aab0',lw=.6,zorder=1)
    a.set(yticks=range(5),yticklabels=['Total','IAM','Spectral','Thermal','Electrical'],
          ylim=(-.55,4.55),xlim=(-2.5,6),xticks=[-2,0,2,4,6],xlabel='Specific-yield gain / contribution (pp)')
    a.tick_params(axis='y',length=0);a.spines[['right','top','left']].set_visible(False);axes.append(a)
    # Square rendered plot area in physical units; an inset does not alter
    # main-axis limits or the original IAM bars.
    parent=a
    inset_width=.34
    inset_height=inset_width*(width*183)/(height*145)
    ins=parent.inset_axes([.64,.36,inset_width,inset_height],zorder=6)
    ins.set_facecolor('white')
    zoom_rows=[]
    for j,(tech,name,col,marker) in enumerate(techs):
        z=stats[stats.technology.eq(tech)&stats.term.eq('iam_pp')].iloc[0]
        yy=1+(.15 if j==0 else -.15)
        ins.barh(yy,z['mean'],height=.20,color=col,alpha=.72,linewidth=0,zorder=2)
        ins.hlines(yy,z.p10,z.p90,color=col,lw=.85,zorder=4)
        ins.plot(z['mean'],yy,marker,ms=2.8,color='white',markeredgecolor=col,mew=.75,zorder=5)
        ins.text(.048 if j==0 else .025,1.39 if j==0 else .61,
                 f"{z['mean']:.3f}",ha='center',va='center',fontsize=6.0,color=col)
        zoom_rows.append({'technology':tech,'mean_pp':float(z['mean']),
                          'p10_pp':float(z.p10),'p90_pp':float(z.p90)})
    ins.axvline(0,color='#a3aab0',lw=.45,zorder=1)
    ins.set(xlim=(-.005,.085),ylim=(.5,1.5),yticks=[],xticks=[0,.04,.08])
    ins.set_xticklabels(['0.00','0.04','0.08'],fontsize=6.0)
    ins.set_xlabel('IAM contribution (pp)',fontsize=6.0,labelpad=2)
    ins.set_title('IAM · zoom',fontsize=6.1,pad=2)
    ins.tick_params(axis='x',length=2,pad=1.5)
    for spine in ins.spines.values():spine.set_visible(True);spine.set_linewidth(.6);spine.set_edgecolor('#7b848c')
    parent.add_patch(Rectangle((-.10,.64),.30,.72,fill=False,edgecolor='#7b848c',lw=.65,zorder=5))
    connector=ConnectionPatch(xyA=(.20,1.36),coordsA=parent.transData,
       xyB=(0,0),coordsB=ins.transAxes,color='#7b848c',lw=.6,zorder=5)
    fig.add_artist(connector)
    fig.canvas.draw()
    inset_rect=ins.get_window_extent()
    physical_mm=np.array([inset_rect.width,inset_rect.height])/fig.dpi*25.4
    assert abs(physical_mm[0]-physical_mm[1])<.01
    assert all(-.005<z['p10_pp']<=z['mean_pp']<=z['p90_pp']<.085 for z in zoom_rows)
    (QA/'Figure2_IAM_inset.json').write_text(json.dumps({
      'physical_dimensions_mm':physical_mm.tolist(),'x_limits_pp':[-.005,.085],
      'values':zoom_rows,'source':'New common-60 factorial component summaries; all eight states recomputed',
      'data_exclusions':0,'parent_xlim':[-2.5,6],
      'alignment_exemption':'Ancillary local-magnification axes, excluded from comparisons of the four main plot areas; square geometry checked separately.'},indent=2),encoding='utf-8')
    a=fig.add_axes([lefts[1],.635,width,height]);panel(a,'b','Aperture gain: density + operation')
    rows=[]
    for j,(tech,name,col,marker) in enumerate(techs):
        d=identity[identity.technology.eq(tech)]
        for k,(field,label) in enumerate([('density_contribution_pp','STC density'),('operating_contribution_pp','Density × operation'),('area_gain_pct','Total')]):
            z=d[field];y=2-k+(.15 if j==0 else -.15)
            a.barh(y,z.mean(),height=.24,color=col,alpha=.72,linewidth=0,zorder=2)
            a.hlines(y,z.quantile(.1),z.quantile(.9),color=col,lw=.85,zorder=4)
            a.plot(z.mean(),y,marker,ms=2.6,color='white',markeredgecolor=col,mew=.75,zorder=5)
            rows.append(dict(technology=tech,term=field,n=len(z),mean=z.mean(),p10=z.quantile(.1),median=z.median(),p90=z.quantile(.9)))
    a.axvline(0,color='#a3aab0',lw=.6,zorder=1)
    a.set(yticks=[0,1,2],yticklabels=['Total','Density × operation','STC density'],ylim=(-.55,2.55),
          xlim=(-15,35),xticks=[-10,0,10,20,30],xlabel='Aperture-area gain / contribution (pp)')
    a.tick_params(axis='y',length=0,labelsize=6.7);a.spines[['right','top','left']].set_visible(False);axes.append(a)
    source(pd.DataFrame(rows),'Figure2_dual_path_area_summaries')
    fig.legend(handles=[Line2D([],[],marker=m,ls='-',color=c,markerfacecolor='white',ms=3,lw=1.1,label=name)
      for tech,name,c,m in techs],loc='upper center',bbox_to_anchor=(.56,.997),ncol=2,fontsize=7,
      handlelength=1.7,columnspacing=2)
    state_specs=[(7,'Full model',BLACK,'o','-'),(6,'Temperature off',THERMAL,'s','--'),
                 (5,'Spectrum off',IAM,'^','-.'),(0,'All three off',CSI,'D',':')]
    plotted=[];yvalues=[]
    for j,(tech,name,col,marker) in enumerate(techs):
        a=fig.add_axes([lefts[j],.125,width,height]);panel(a,'cd'[j],name+' · matched controls')
        for mask,label,color,mark,linestyle in state_specs:
            d=states[states.technology.eq(tech)&states['mask'].eq(mask)].sort_values('adcode')
            assert len(d)==369
            a.scatter(d.ghi_kwh_m2/1000,d.gain_capacity_pct,s=2.1,color=color,alpha=.12,linewidths=0,rasterized=True,zorder=2)
            z=means[means.technology.eq(tech)&means['mask'].eq(mask)].sort_values('ghi_quartile')
            assert z.n.sum()==369
            a.plot(z.mean_ghi_mwh_m2,z.mean_gain_pct,color=color,marker=mark,ls=linestyle,ms=2.8,lw=1.0,zorder=4)
            plotted.append(dict(panel='cd'[j],technology=tech,mask=mask,display_name=label,regions=369))
            yvalues.extend(d.gain_capacity_pct)
        a.axhline(0,color='#a3aab0',lw=.6,zorder=1)
        a.set(xlim=(.9,2.4),ylim=(-2.5,6.5),xticks=[1,1.5,2],yticks=[-2,0,2,4,6],
              xlabel='GHI (MWh/m²/year)',ylabel='Specific-yield gain over c-Si (%)')
        a.spines[['top','right']].set_visible(False);axes.append(a)
    assert min(yvalues)>-2.5 and max(yvalues)<6.5
    fig.legend(handles=[Line2D([],[],color=c,marker=m,ls=l,ms=2.8,lw=1,label=name)
       for k,name,c,m,l in state_specs],loc='upper center',bbox_to_anchor=(.55,.49),ncol=4,fontsize=6.4,
       handlelength=1.6,columnspacing=1.35,handletextpad=.5)
    source(pd.DataFrame(plotted),'Figure2_displayed_states')
    export(fig,2,axes,[['a','b'],['c','d']],[['a','c'],['b','d']],
      ['Four complementary panels: matched specific-yield attribution, exact density/operation identity, and both technology controls. All raw displayed regional values retained; common lower-panel axis ranges. IAM inset is ancillary and its square physical geometry is checked separately.'])
    REPORT['figures']['2'].update(n=369,technologies=2,factorial_states_per_technology=8,
      baseline_reconciliation_max_pp=calc['baseline_reconciliation_max_pp'],
      spatial_summary='Mean and spatial P10–P90; no experimental CI',same_switch_reference=True,
      density_is_not_climate_effect=True,displayed_raw_values=2952)


def main():
    figure2()
    REPORT['input_sha256']=b.HASHES
    REPORT['scope']='Figure2 readability revision only; all existing numerical Source Data retained'
    (QA/'Figure2_v43_render_report.json').write_text(json.dumps(REPORT,indent=2,ensure_ascii=False),encoding='utf-8')

if __name__=='__main__':main()

# Final current caption export; plotting and numerical results are unchanged.
if __name__ == "__main__":
    from caption_registry import write_main_caption
    write_main_caption(2)
