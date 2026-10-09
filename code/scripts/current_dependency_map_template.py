"""The study's established geographic renderer; function body preserved exactly."""
import numpy as np
import matplotlib
from shapely import make_valid,transform
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
