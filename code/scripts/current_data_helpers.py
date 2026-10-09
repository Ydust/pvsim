"""Render the independently versioned five-figure preview from archived results."""
from pathlib import Path
import sys, json, hashlib, math
sys.dont_write_bytecode = True
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, ListedColormap, BoundaryNorm, LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import cartopy.crs as ccrs
from shapely.geometry import shape, box
from shapely import make_valid, transform, union_all
from pyproj import Transformer

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent.parent
SUB = HERE / 'archived_context'
N = HERE / 'inputs/geography'
A = SUB / '05_Reproducibility/regional_pathways'
SKILL = HERE
sys.path.insert(0, str(SKILL))
from audit_panel_alignment import require_matplotlib_panel_alignment

QA = HERE / 'qa'
SD = HERE / 'Source_Data'
QA.mkdir(exist_ok=True)
SD.mkdir(exist_ok=True)
HASHES = {}
REPORT = {'n_regions':369, 'excluded_regions':0, 'backend':'Python', 'figures':{}}
BLACK = '#26323b'
GRAY = '#77848e'
LIGHT = '#d4d9dd'
SJ = '#d47735'
T = '#347fac'
THERMAL = '#c78c24'
SPECTRAL = '#345b86'
IAM = '#7f9382'
CHOICE_NAMES = ['No build', 'c-Si', 'Single junction', 'Tandem']
CHOICE_COLORS = [LIGHT, GRAY, SJ, T]
width_mm = 183

plt.rcParams.update({
 'font.family':'sans-serif', 'font.sans-serif':['DejaVu Sans','Arial'],
 'font.size':7.6, 'axes.labelsize':7.6, 'axes.titlesize':8.5,
 'xtick.labelsize':7.2, 'ytick.labelsize':7.2, 'legend.fontsize':7.2,
 'axes.linewidth':.6, 'axes.edgecolor':GRAY, 'axes.spines.top':False,
 'axes.spines.right':False, 'lines.linewidth':1.0, 'legend.frameon':False,
 'pdf.fonttype':42, 'svg.fonttype':'none', 'axes.unicode_minus':False,
 'savefig.facecolor':'white', 'figure.facecolor':'white',
 'xtick.major.width':.6, 'ytick.major.width':.6, 'text.color':BLACK,
 'axes.labelcolor':BLACK, 'xtick.color':BLACK, 'ytick.color':BLACK,
})

def track(path):
    path = Path(path)
    HASHES[str(path.relative_to(HERE))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return path

def csv(path, **kwargs):
    return pd.read_csv(track(path), **kwargs)

def source(frame, name):
    frame.to_csv(SD / (name + '.csv'), index=False, encoding='utf-8-sig')

def panel(ax, letter, title, color=BLACK):
    ax.set_label(letter)
    ax.annotate(letter,(0,1),xycoords='axes fraction',xytext=(-14,12),
                textcoords='offset points',fontweight='bold',fontsize=9,
                va='bottom',annotation_clip=False)
    ax.set_title(title,loc='left',fontweight='normal',color=color,pad=12)

def footer(fig, text, y=.015):
    fig.text(.5,y,text,ha='center',va='bottom',fontsize=7.0,color='#586772')

def export(fig, number, axes, rows=None, cols=None, excluded=None):
    out = HERE / f'Figure_{number}'
    out.mkdir(exist_ok=True)
    fig.canvas.draw()
    require_matplotlib_panel_alignment(
        fig, axes=axes, panel_ids={ax:ax.get_label() for ax in axes},
        row_groups=rows, column_groups=cols, exclude_axes=excluded or [],
        json_out=QA/f'Figure_{number}.alignment.json',
        overlay_svg=QA/f'Figure_{number}.alignment.svg',
        tolerance_pt=1.5,gutter_tolerance_pt=1.5,require_panel_labels=True,strict=True,
    )
    fig.savefig(out / f'Figure_{number}.pdf',dpi=600)
    fig.savefig(out / f'Figure_{number}.svg',dpi=600)
    fig.savefig(out / f'Figure_{number}.png',dpi=300)
    fig.savefig(out / f'Figure_{number}.tiff',dpi=600,pil_kwargs={'compression':'tiff_lzw'})
    REPORT['figures'].setdefault(str(number),{})['dimensions_mm'] = (fig.get_size_inches()*25.4).tolist()
    plt.close(fig)
    print(f'Figure {number}: four formats exported; alignment passed',flush=True)

city = pd.read_csv(HERE/'Source_Data/Figure1_region_values.csv', dtype={'adcode':str})
assert len(city)==369 and city.adcode.is_unique
assert city[['single_capacity_pct','tandem_area_pct','ghi_kwh_m2','tair_mean']].notna().all().all()
geo = json.loads(track(N/'prefecture_boundaries.geojson').read_text(encoding='utf-8'))
context = json.loads(track(N/'map_context.geojson').read_text(encoding='utf-8'))
DATA = ccrs.PlateCarree()
PROJ = ccrs.LambertConformal(central_longitude=105,central_latitude=35,standard_parallels=(25,47))
projector = Transformer.from_crs('EPSG:4326',PROJ.proj4_init,always_xy=True)
geoms = [(str(f['properties']['adcode']),make_valid(shape(f['geometry']))) for f in geo['features']]
assert len(geoms)==369 and set(c for c,g in geoms)==set(city.adcode)
projected = [(code,make_valid(transform(g,projector.transform,interleaved=False))) for code,g in geoms]
taiwan = [make_valid(shape(f['geometry'])) for f in context['features'] if f['properties']['role']=='taiwan_geographic_context']
maritime = [make_valid(shape(f['geometry'])) for f in context['features'] if f['properties']['role']=='south_china_sea_maritime_line']
outline = union_all([g for code,g in geoms])

def map_panel(fig, rect, values, cmap, norm, letter, title, titlecolor=BLACK):
    assert set(values.index)==set(city.adcode) and len(values)==369
    ax = fig.add_axes(rect,projection=PROJ)
    ax.set_extent([73,135,17,54],crs=DATA)
    ax.spines['geo'].set_visible(False)
    lim = box(*[ax.get_xlim()[0],ax.get_ylim()[0],ax.get_xlim()[1],ax.get_ylim()[1]])
    for code,g in projected:
        art=ax.add_geometries([g.intersection(lim)],crs=PROJ,
            facecolor=cmap(norm(values.loc[code])),edgecolor='white',linewidth=.12,zorder=2)
        art.set_rasterized(True)
    for g in taiwan:
        ax.add_geometries([g],crs=DATA,facecolor='#eceeef',edgecolor='#b3bcc2',linewidth=.3,zorder=1)
    ins=ax.inset_axes([.80,.035,.19,.33],projection=DATA)
    ins.set_extent([105,125,3,25],crs=DATA)
    ins.set_facecolor('white')
    slimit=box(105,3,125,25)
    for code,g in geoms:
        sg=g.intersection(slimit)
        if not sg.is_empty:
            ins.add_geometries([sg],crs=DATA,facecolor=cmap(norm(values.loc[code])),edgecolor='white',linewidth=.10,zorder=2)
    ins.add_geometries([outline.intersection(slimit)],crs=DATA,facecolor='none',edgecolor='#68777f',linewidth=.3,zorder=3)
    for g in taiwan:
        ins.add_geometries([g.intersection(slimit)],crs=DATA,facecolor='#eceeef',edgecolor='#8b969b',linewidth=.25,zorder=2)
    for g in maritime:
        ins.add_geometries([g.intersection(slimit)],crs=DATA,facecolor='none',edgecolor='#68777f',linewidth=.45,zorder=4)
    ins.spines['geo'].set_linewidth(.4)
    ins.spines['geo'].set_edgecolor('#8b969b')
    panel(ax,letter,title,titlecolor)
    return ax, matplotlib.cm.ScalarMappable(norm=norm,cmap=cmap)

