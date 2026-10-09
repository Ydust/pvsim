"""Common-start Figure3 candidate; all369 units, baseline-anchored parameter paths."""
from pathlib import Path
import sys,json,math
sys.dont_write_bytecode=True
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from scipy.stats import gaussian_kde
O=Path(__file__).resolve().parent;QA=O/'qa';SD=O/'inputs'
sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_panel_alignment import require_matplotlib_panel_alignment
SJ='#d97732';T='#347fac';CSI='#727b82';BLACK='#22272b'
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial','DejaVu Sans'],
 'font.size':7.2,'axes.labelsize':7.2,'axes.titlesize':7.5,'xtick.labelsize':6.7,'ytick.labelsize':6.7,
 'axes.linewidth':.55,'axes.edgecolor':'#687078','text.color':BLACK,'axes.labelcolor':BLACK,
 'xtick.color':BLACK,'ytick.color':BLACK,'xtick.major.width':.5,'ytick.major.width':.5,'xtick.major.size':2.7,'ytick.major.size':2.7,
 'pdf.fonttype':42,'svg.fonttype':'none','axes.unicode_minus':False,'legend.frameon':False,'figure.facecolor':'white','savefig.facecolor':'white'})
def panel(ax,letter,title,offset=6):
    ax.set_label(letter)
    ax.annotate(letter,(0,1),xycoords='axes fraction',xytext=(-13,offset),textcoords='offset points',ha='left',va='bottom',fontsize=8.5,fontweight='bold',annotation_clip=False)
    ax.set_title(title,loc='left',pad=offset,fontsize=7.5)
def source(d,name):
    original=pd.read_csv(O/'Source_Data'/(name+'.csv'),dtype={'adcode':str})
    pd.testing.assert_frame_equal(d.reset_index(drop=True),original,check_dtype=False,check_exact=False,rtol=1e-12,atol=1e-12)
def export(fig,name,axes,rows):
    fig.canvas.draw()
    require_matplotlib_panel_alignment(fig,axes=axes,panel_ids={a:a.get_label() for a in axes},row_groups=rows,column_groups=[],tolerance_pt=1.5,gutter_tolerance_pt=1.5,require_panel_labels=False,strict=True,json_out=QA/(name+'.alignment.json'),overlay_svg=QA/(name+'.alignment.svg'))
    fig.savefig(O/'Figure_3'/('Figure_3'+'.pdf'),dpi=600)
    fig.savefig(O/'Figure_3'/('Figure_3'+'.svg'),dpi=600)
    fig.savefig(O/'Figure_3'/('Figure_3'+'.png'),dpi=300)
    fig.savefig(O/'Figure_3'/('Figure_3'+'.tiff'),dpi=600,pil_kwargs={'compression':'tiff_lzw'})
    plt.close(fig)
allstates=pd.read_csv(SD/'regional_path_states.csv',dtype={'adcode':str})
summary=pd.read_csv(SD/'path_summary.csv')
city=allstates[allstates.state_id.eq('single_00')][['adcode','city','ghi_kwh_m2']].copy()
for tech in ['single','tandem']:
    z=allstates[allstates.state_id.eq(tech+'_00')].set_index('adcode')
    city[tech+'_capacity_pct']=city.adcode.map(z.capacity_gain_pct)
baseline=allstates[allstates.state_id.isin(['single_00','tandem_00'])].rename(columns={'capacity_gain_pct':'specific_gain_pct'})
primary_summary=summary[summary.state_id.isin(['single_00','tandem_00'])]
def main_figure():
    fig=plt.figure(figsize=(183/25.4,145/25.4));axes=[]
    a=fig.add_axes([.10,.53,.36,.335]);panel(a,'a','Regional response and compensation')
    baseline=allstates[allstates.state_id.isin(['single_00','tandem_00'])].rename(columns={'capacity_gain_pct':'specific_gain_pct'})
    primary_summary=summary[summary.state_id.isin(['single_00','tandem_00'])]
    assert len(baseline)==738 and baseline.adcode.nunique()==369
    summaries=primary_summary.to_dict(orient='records')
    distribution_regions=[];distribution_curves=[];distribution_summary=[]
    for tech,y,col,name,field in [('single',1.18,SJ,'Single junction','single_capacity_pct'),('tandem',.02,T,'Tandem','tandem_capacity_pct')]:
        z=baseline[baseline.technology.eq(tech)].copy().sort_values('adcode')
        row=primary_summary[primary_summary.technology.eq(tech)].iloc[0]
        gain=z.specific_gain_pct.to_numpy();density=float(row.density_ratio)
        assert len(z)==369 and z.adcode.is_unique and np.ptp(z.density_ratio)<1e-12
        assert np.allclose(gain,city.set_index('adcode').loc[z.adcode,field],rtol=0,atol=1e-10)
        assert np.allclose((1+gain/100)*density,1+z.area_gain_pct.to_numpy()/100,rtol=0,atol=1e-12)
        target=100*(1/density-1) if tech=='single' else 0.
        mean=float(gain.mean());lo,hi=np.quantile(gain,[.1,.9])
        grid=np.linspace(gain.min(),gain.max(),600)
        kernel=gaussian_kde(gain,bw_method=.25);density_shape=kernel(grid)
        height=.44*density_shape/density_shape.max()
        # Curve height encodes shape, never a second physical measurement.
        a.fill_between(grid,y,y+height,color=col,alpha=.24,lw=0,zorder=2)
        a.plot(grid,y+height,color=col,lw=.85,zorder=3)
        a.hlines(y,gain.min(),gain.max(),color=col,lw=.55,zorder=2)
        a.plot(gain,np.full(len(gain),y-.045),ls='none',marker='|',ms=2.2,mew=.35,color=col,alpha=.24,zorder=2,rasterized=True)
        a.plot([lo,hi],[y,y],color=col,lw=2,zorder=4)
        a.plot(mean,y,'o',color=col,mec='white',mew=.5,ms=3.5,zorder=5)
        a.vlines(target,y-.065,y+.44,color=col,lw=.9,ls=(0,(2.5,1.5)),zorder=3)
        a.plot(target,y,marker='|',ms=5,color=col,mew=1,zorder=5)
        a.text(-1.75,y+.54,name,fontsize=6.8,fontweight='bold',color=col,ha='left',va='bottom')
        a.text(6.0,y+.54,f'Density {100*(density-1):+.2f}%',fontsize=6.0,color=CSI,ha='left',va='bottom')
        if tech=='single':
            bracket_y=y-.19
            a.plot([mean,target],[bracket_y,bracket_y],color=CSI,lw=.7,zorder=3)
            a.plot([mean,target],[bracket_y,bracket_y],ls='none',marker='|',ms=3.5,mew=.7,color=CSI,zorder=3)
            a.text((mean+target)/2,bracket_y-.075,f'{target-mean:.2f} pp',ha='center',va='top',fontsize=6.2,color=BLACK)
            a.text(target,y+.52,'Area parity',ha='center',va='bottom',fontsize=6,color=BLACK)
        else:
            a.text(.35,y+.12,'Capacity parity',ha='left',va='bottom',fontsize=6,color=BLACK)
            # Repeated observations in an explicitly scaled inset, not new data.
            ins=a.inset_axes([.49,.10,.45,.22])
            ins.set_label('tandem-detail')
            ins.fill_between(grid,0,height/.44*.7,color=col,alpha=.24,lw=0)
            ins.plot(grid,height/.44*.7,color=col,lw=.75)
            ins.plot(gain,np.full(len(gain),-.065),ls='none',marker='|',ms=1.8,mew=.3,color=col,alpha=.3,rasterized=True)
            ins.plot([lo,hi],[0,0],color=col,lw=1.7)
            ins.plot(mean,0,'o',color=col,mec='white',mew=.4,ms=3)
            ins.axvline(0,color=col,lw=.65,ls=(0,(2.5,1.5)))
            ins.plot([mean,0],[.93,.93],color=CSI,lw=.65)
            ins.plot([mean,0],[.93,.93],ls='none',marker='|',ms=3,mew=.65,color=CSI)
            ins.text(mean/2,1.08,f'{-mean:.2f} pp',ha='center',va='bottom',fontsize=6.0)
            ins.set(xlim=(-1.5,.2),ylim=(-.2,1.55),xticks=[-1.2,-.6,0],yticks=[])
            ins.tick_params(axis='x',labelsize=6.0,pad=1.5,length=2)
            ins.spines[['top','right','left']].set_visible(False)
            ins.set_title('Tandem detail',fontsize=6.0,loc='left',pad=2)
        z['target_specific_gain_pct']=target
        z['specific_gain_gap_pp']=target-z.specific_gain_pct
        z['target_constraint']='aperture parity at fixed baseline density' if tech=='single' else 'capacity parity'
        distribution_regions.append(z)
        distribution_curves.append(pd.DataFrame({'technology':tech,'specific_gain_pct':grid,'kde_density':density_shape,'peak_normalized_height':height/.44,'display_baseline_y':y}))
        distribution_summary.append(dict(technology=tech,n=369,density_ratio=density,density_difference_pct=100*(density-1),mean_specific_gain_pct=mean,p10_specific_gain_pct=lo,p90_specific_gain_pct=hi,min_specific_gain_pct=gain.min(),max_specific_gain_pct=gain.max(),target_specific_gain_pct=target,mean_gap_pp=target-mean,min_gap_pp=target-gain.max(),max_gap_pp=target-gain.min(),kde_bw_method=.25))
    a.set(xlim=(-2,15.5),ylim=(-.34,2.03),xticks=[0,5,10,15],yticks=[],xlabel='Specific-yield gain over c-Si (%)')
    a.spines[['left','right','top']].set_visible(False)
    axes.append(a)
    source(pd.concat(distribution_regions,ignore_index=True),'Figure3_reference_distribution_regions')
    source(pd.concat(distribution_curves,ignore_index=True),'Figure3_reference_density_curves')
    source(pd.DataFrame(distribution_summary),'Figure3_reference_distribution_summary')


    host=fig.add_axes([.59,.53,.36,.335]);panel(host,'b','Majority vs full-coverage thresholds')
    host.set_axis_off()
    colors={0:BLACK,5:'#d8a780',10:SJ};styles={0:'-',5:'--',10:':'}
    bounds=pd.read_csv(SD/'single_coverage_thresholds.csv')
    curves=pd.read_csv(SD/'single_coverage_curves.csv')
    facet_width=(.36-2*.020)/3
    baxes=[];threshold_records=[]
    for i,step in enumerate([0,5,10]):
        a=fig.add_axes([.59+i*(facet_width+.020),.53,facet_width,.335],sharey=baxes[0] if baxes else None)
        a.set_label(f'b{step}')
        z=curves[curves.state_id.eq(f'single_{step:02}')].sort_values('coverage_pct')
        assert len(z)==369 and z.adcode.nunique()==369
        v=z.required_density_gain_pct.to_numpy()
        a.step(np.r_[5,v,14.5],np.r_[0,z.coverage_pct,100],where='post',color=colors[step],ls=styles[step],lw=1.1,zorder=3)
        for q,marker in [(50,'o'),(100,'D')]:
            t=bounds[bounds.state_id.eq(f'single_{step:02}')&bounds.coverage_pct.eq(q)].iloc[0]
            y=t.required_regions/369*100
            a.axhline(q,color='#b7bec3',lw=.5,ls=(0,(2,3)),zorder=1)
            a.scatter(t.required_density_gain_pct,y,marker=marker,s=17,edgecolor='white',linewidth=.5,color=colors[step],zorder=5)
            a.annotate(f'{t.required_density_gain_pct:.2f}',(t.required_density_gain_pct,y),xytext=(-2,4),textcoords='offset points',ha='right',va='bottom',fontsize=6.0,color=colors[step])
            threshold_records.append(dict(progress=step/10,coverage_target_pct=q,required_regions=int(t.required_regions),actual_coverage_pct=y,required_density_gain_pct=t.required_density_gain_pct))
        a.set(xlim=(5,14.5),ylim=(0,112),xticks=[5,10,14],yticks=[0,25,50,75,100])
        a.tick_params(axis='x',labelsize=6.2)
        if i==0:a.set_ylabel('Regions at aperture parity (%)')
        else:a.tick_params(axis='y',left=False,labelleft=False)
        a.spines[['top','right']].set_visible(False)
        if i>0:a.spines['left'].set_visible(False)
        axes.append(a);baxes.append(a)
    fig.text(.77,.472,'SJ capacity-density increase (%)\n(relative to its baseline density)',ha='center',va='top',fontsize=7.2)
    pd.DataFrame(threshold_records).to_csv(QA/'Figure3b_displayed_thresholds.csv',index=False,encoding='utf-8-sig')
    changes=[]
    for q,marker in [(50,'o'),(100,'D')]:
        base=bounds[bounds.state_id.eq('single_00')&bounds.coverage_pct.eq(q)].iloc[0]
        target=bounds[bounds.state_id.eq('single_10')&bounds.coverage_pct.eq(q)].iloc[0]
        changes.append(dict(coverage_pct=q,baseline_pct=float(base.required_density_gain_pct),target_pct=float(target.required_density_gain_pct),change_pp=float(target.required_density_gain_pct-base.required_density_gain_pct),controller_baseline=str(base.controller_city),controller_target=str(target.controller_city)))
    fig.legend(handles=[Line2D([],[],marker=m,color=BLACK,ls='none',ms=3,label=f'{d["coverage_pct"]}%: {d["change_pp"]:+.2f} pp') for d,m in zip(changes,['o','D'])],title='Threshold change · target − baseline',title_fontsize=6.0,loc='center',bbox_to_anchor=(.77,.408),ncol=2,columnspacing=1.8,fontsize=6.0,handletextpad=.4)
    (QA/'Figure3b_threshold_changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2),encoding='utf-8')
    fig.canvas.draw()
    jsrows=[]
    for a in baxes:
        bbox=a.get_window_extent();jsrows.append(dict(id=a.get_label(),width_pt=bbox.width/fig.dpi*72,height_pt=bbox.height/fig.dpi*72,xlim=list(a.get_xlim()),ylim=list(a.get_ylim())))
    (QA/'Figure3b_facet_geometry.json').write_text(json.dumps(jsrows,indent=2),encoding='utf-8')
    fig.legend(handles=[Line2D([],[],color=CSI,marker='o',mec='white',ls='none',ms=3.5,label='Regional mean'),Line2D([],[],color=CSI,ls=(0,(2.5,1.5)),lw=.9,label='Parity requirement')],loc='upper left',bbox_to_anchor=(.075,.985),ncol=2,columnspacing=1.2,handlelength=1.4,fontsize=6.4)
    fig.legend(handles=[Line2D([],[],color=colors[k],ls=styles[k],lw=1.1,label=name) for k,name in [(0,'Baseline'),(5,'Intermediate'),(10,'Target')]],loc='upper left',bbox_to_anchor=(.575,.990),ncol=3,columnspacing=1.1,handlelength=1.5,fontsize=6.2)
    fig.legend(handles=[Line2D([],[],color=CSI,marker='o',ls='none',ms=3,label='≥50%'),Line2D([],[],color=CSI,marker='D',ls='none',ms=3,label='100%')],loc='upper left',bbox_to_anchor=(.575,.961),ncol=2,columnspacing=2,fontsize=6.2)
    a=fig.add_axes([.10,.105,.85,.22]);panel(a,'c','Tandem response and remaining deficit',offset=18)
    a.text(0,1.03,'γ: −0.30 → −0.20%/°C; Eg: 1.68 → 1.75 eV',transform=a.transAxes,fontsize=6.5,va='bottom')
    paired=pd.read_csv(SD/'paired_path_changes.csv',dtype={'adcode':str})
    paired=paired[paired.technology.eq('tandem')&paired.step.eq(10)].sort_values(['ghi_kwh_m2','adcode'])
    assert len(paired)==369
    xx=paired.ghi_kwh_m2.to_numpy()/1000
    a.vlines(xx,paired.start_gain_pct,paired.target_gain_pct,color='#d9dee2',lw=.35,zorder=1)
    a.scatter(xx,paired.start_gain_pct,s=4.5,color=CSI,alpha=.70,linewidths=0,rasterized=True,zorder=3)
    for yes in [True,False]:
        z=paired[paired.target_at_parity.eq(yes)]
        a.scatter(z.ghi_kwh_m2/1000,z.target_gain_pct,s=7,facecolors=T if yes else 'white',edgecolors=T,linewidths=.4,rasterized=True,zorder=4)
    a.axhline(0,color=BLACK,lw=.65,ls='--')
    assert xx.min()>1.05 and xx.max()<2.30
    a.set(xlim=(1.05,2.30),ylim=(-1.6,2.4),yticks=[-1,0,1,2],xticks=[1.1,1.3,1.5,1.7,1.9,2.1,2.3],xlabel='GHI (MWh/m²/year)',ylabel='Specific-yield gain over c-Si (%)')
    axes.append(a)
    counts=[int(paired.target_at_parity.sum()),int((~paired.target_at_parity).sum())]
    fig.legend(handles=[Line2D([],[],marker='o',color=CSI,ls='none',ms=3,label='Baseline (λ = 0)'),Line2D([],[],marker='o',color=T,ls='none',ms=3,label=f'Target ≥ parity: {counts[0]}'),Line2D([],[],marker='o',mfc='white',mec=T,color=T,ls='none',ms=3,label=f'Target below parity: {counts[1]}')],loc='upper center',bbox_to_anchor=(.52,.038),ncol=3,columnspacing=2,handlelength=.7,handletextpad=.4,fontsize=6.5)
    export(fig,'Figure_3',axes,[['b0','b5','b10']])


if __name__=='__main__':main_figure()

# Final current caption export; plotting and numerical results are unchanged.
if __name__ == "__main__":
    from caption_registry import write_main_caption
    write_main_caption(3)
