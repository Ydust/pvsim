"""Spatial and sensitivity analyses for Figure 1.

Resampling envelopes describe
geographic-composition sensitivity, not independent-device confidence limits.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import replace
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from scipy.stats import pearsonr, spearmanr

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/figure1_science_20260906"
CACHE = ROOT / "data/pvgis_multiyear_2019_2023"
SEED = 20260906
N_BOOT = 10000
MAIN_METRICS = ["single_capacity_pct", "tandem_area_pct"]
SOURCE_URL = "https://re.jrc.ec.europa.eu/api/v5_3/seriescalc"


def save(frame, name):
    OUT.mkdir(parents=True, exist_ok=True)
    frame.to_csv(OUT / f"{name}.csv", index=False, encoding="utf-8-sig")


def data():
    d = pd.read_csv(ROOT / "outputs/prefecture_area_weighted_physics_summary.csv", dtype={"adcode": str, "province_code": str})
    a = pd.read_csv(ROOT / "outputs/city_physics_summary.csv", dtype={"adcode": str, "province_code": str})
    for f in (d, a):
        f.sort_values("adcode", inplace=True)
        f.reset_index(drop=True, inplace=True)
        assert len(f) == 337 and f.adcode.nunique() == 337
        for t, label in [("perovskite", "single"), ("tandem", "tandem")]:
            for unit, suffix in [("kwp", "capacity"), ("m2", "area")]:
                denominator = f[f"csi_yield_kwh_per_{unit}"]
                assert np.isfinite(denominator).all() and (denominator > 0).all()
                f[f"{label}_{suffix}_pct"] = 100 * (f[f"{t}_yield_kwh_per_{unit}"] / denominator - 1)
                f[f"{label}_delta_kwh_per_{unit}"] = f[f"{t}_yield_kwh_per_{unit}"] - denominator
        f["ghi_quartile"] = pd.qcut(f.ghi_kwh_m2, 4, labels=["Q1", "Q2", "Q3", "Q4"]).astype(str)
        f["tandem_density_ratio"] = (f.tandem_yield_kwh_per_m2 / f.tandem_yield_kwh_per_kwp) / (f.csi_yield_kwh_per_m2 / f.csi_yield_kwh_per_kwp)
        f["tandem_stc_gain_pp"] = 100 * (f.tandem_density_ratio - 1)
        f["tandem_operating_correction_pp"] = f.tandem_density_ratio * f.tandem_capacity_pct
        assert np.allclose(f.tandem_stc_gain_pp + f.tandem_operating_correction_pp, f.tandem_area_pct, atol=1e-10)
    assert d.adcode.tolist() == a.adcode.tolist()
    return d, a


def grouped_bootstrap(d, block_codes, label, draws=N_BOOT):
    groups, inv = np.unique(np.asarray(block_codes, str), return_inverse=True)
    rng = np.random.default_rng(SEED)
    weights = rng.multinomial(len(groups), np.full(len(groups), 1 / len(groups)), size=draws)
    q = d.ghi_quartile.to_numpy()
    allrows, summaries = [], []
    for metric in MAIN_METRICS:
        y = d[metric].to_numpy(float)
        counts = np.bincount(inv, minlength=len(groups))
        sums = np.bincount(inv, weights=y, minlength=len(groups))
        means = (weights @ sums) / (weights @ counts)
        qm = []
        for quartile in ("Q1", "Q4"):
            mask = q == quartile
            n = np.bincount(inv[mask], minlength=len(groups))
            s = np.bincount(inv[mask], weights=y[mask], minlength=len(groups))
            den = weights @ n
            qm.append(np.divide(weights @ s, den, out=np.full(draws, np.nan), where=den > 0))
        diff = qm[0] - qm[1]
        valid = np.isfinite(diff)
        assert valid.sum() >= draws * .98
        summaries.append(dict(scheme=label, metric=metric, blocks=len(groups), draws=draws,
            valid_draws=int(valid.sum()), observed_mean=float(y.mean()),
            mean_low=float(np.quantile(means, .025)), mean_high=float(np.quantile(means, .975)),
            q1_mean=float(y[q == "Q1"].mean()), q4_mean=float(y[q == "Q4"].mean()),
            effect_pp=float(y[q == "Q1"].mean() - y[q == "Q4"].mean()),
            effect_low=float(np.quantile(diff[valid], .025)), effect_high=float(np.quantile(diff[valid], .975)),
            positive_draw_fraction=float((diff[valid] > 0).mean()),
            interval_definition="central 95% geographic-block resampling envelope; fixed national quartiles; not device or climate uncertainty"))
        allrows.append(pd.DataFrame(dict(scheme=label, metric=metric, draw=np.arange(1, draws + 1), mean_pct=means, effect_pp=diff)))
    return pd.DataFrame(summaries), pd.concat(allrows, ignore_index=True)


def basic_analysis():
    d, a = data()
    save(d, "city_results")
    qrows = []
    for layer, f in [("Prefecture area", d), ("City anchor", a)]:
        for q, g in f.groupby("ghi_quartile", sort=True):
            for metric in ["single_capacity_pct", "tandem_area_pct", "single_area_pct", "tandem_capacity_pct"]:
                qrows.append(dict(layer=layer, quartile=q, metric=metric, n=len(g), ghi_min=g.ghi_kwh_m2.min(), ghi_max=g.ghi_kwh_m2.max(),
                    mean=g[metric].mean(), median=g[metric].median(), p10=g[metric].quantile(.1), p90=g[metric].quantile(.9),
                    minimum=g[metric].min(), maximum=g[metric].max()))
    save(pd.DataFrame(qrows), "quartile_summary")
    summaries, samples = [], []
    schemes = [("Province", d.province_code.to_numpy())]
    for width in (5, 10):
        blocks = (np.floor(d.anchor_lat / width).astype(int).astype(str) + "_" + np.floor(d.anchor_lon / width).astype(int).astype(str)).to_numpy()
        schemes.append((f"{width}-degree blocks", blocks))
    for label, blocks in schemes:
        s, b = grouped_bootstrap(d, blocks, label)
        summaries.append(s); samples.append(b)
    summary = pd.concat(summaries, ignore_index=True)
    save(summary, "block_effect_summary")
    save(pd.concat(samples, ignore_index=True), "block_effect_draws")
    loo = []
    for p in sorted(d.province_code.unique()):
        g = d[d.province_code != p]
        for metric in MAIN_METRICS:
            loo.append(dict(left_out_province=p, metric=metric, n=len(g), effect_pp=g.loc[g.ghi_quartile == "Q1", metric].mean() - g.loc[g.ghi_quartile == "Q4", metric].mean(),
                pearson_r=pearsonr(g.ghi_kwh_m2, g[metric]).statistic))
    save(pd.DataFrame(loo), "leave_province_effects")
    negative = d[d.single_capacity_pct < 0].merge(a[["adcode", "single_capacity_pct"]].rename(columns={"single_capacity_pct":"anchor_advantage_pct"}), on="adcode", validate="one_to_one")
    save(negative, "negative_prefectures")
    decomp = []
    for q, g in [("All", d), *list(d.groupby("ghi_quartile", sort=True))]:
        decomp.append(dict(group=q, n=len(g), stc_gain_pp=g.tandem_stc_gain_pp.mean(), operating_correction_pp=g.tandem_operating_correction_pp.mean(), total_area_advantage_pct=g.tandem_area_pct.mean()))
    save(pd.DataFrame(decomp), "tandem_decomposition")
    rows = []
    for q, g in d.groupby("ghi_quartile", sort=True):
        for tech in ("single", "tandem"):
            rows.append(dict(quartile=q, tech=tech, n=len(g), capacity_advantage_pct=g[f"{tech}_capacity_pct"].mean(), area_advantage_pct=g[f"{tech}_area_pct"].mean(),
                extra_kwh_per_kwp=g[f"{tech}_delta_kwh_per_kwp"].mean(), extra_kwh_per_m2=g[f"{tech}_delta_kwh_per_m2"].mean(), csi_kwh_per_kwp=g.csi_yield_kwh_per_kwp.mean()))
    save(pd.DataFrame(rows), "absolute_generation")
    print(summary.to_string(index=False), flush=True)


def spatial_validation():
    """Two explicit validation targets; no claim of independent field accuracy."""
    from scripts.build_prefecture_area_model_outputs import GRID, LON_SCALE
    d, a = data()
    grid = pd.read_csv(ROOT / GRID)
    xy = np.column_stack([a.lon * LON_SCALE, a.lat])
    _, near = cKDTree(np.column_stack([grid.lon * LON_SCALE, grid.lat])).query(xy)
    base = grid.adv.to_numpy()[near]
    # Training-only trend provides a leakage-free auxiliary spatial benchmark.
    features = np.column_stack([np.ones(len(a)), a.ghi_kwh_m2 / 1000, a.tair_mean / 20, a.altitude_m / 1000, a.lat / 40, a.lon / 110])
    rows = []
    for province in sorted(a.province_code.unique()):
        test = np.flatnonzero(a.province_code.to_numpy() == province)
        train = np.flatnonzero(a.province_code.to_numpy() != province)
        dist, nb = cKDTree(xy[train]).query(xy[test], k=8)
        nb = train[nb]
        w = 1 / np.maximum(dist, .02) ** 2
        for metric in MAIN_METRICS:
            y = a[metric].to_numpy(float)
            beta = np.linalg.lstsq(features[train], y[train], rcond=None)[0]
            residual = y - features @ beta
            predicted = features[test] @ beta + (w * residual[nb]).sum(axis=1) / w.sum(axis=1)
            for j, idx in enumerate(test):
                rows.append(dict(adcode=a.adcode.iloc[idx], province_code=province, metric=metric, scheme="Training-only climate trend + residual IDW", observed=y[idx], predicted=predicted[j], nearest_training_distance_deg=dist[j, 0]))
        y = a.single_capacity_pct.to_numpy(float)
        residual = y - base
        pred = base[test] + (w * residual[nb]).sum(axis=1) / w.sum(axis=1)
        for j, idx in enumerate(test):
            rows.append(dict(adcode=a.adcode.iloc[idx], province_code=province, metric="single_capacity_pct", scheme="Frozen physical baseline + held-out residual IDW", observed=y[idx], predicted=pred[j], nearest_training_distance_deg=dist[j, 0]))
    raw = pd.DataFrame(rows)
    raw["error_pp"] = raw.predicted - raw.observed
    save(raw, "spatial_validation_predictions")
    sums=[]
    for (scheme, metric), g in raw.groupby(["scheme", "metric"]):
        error=g.error_pp.to_numpy()
        sums.append(dict(scheme=scheme, metric=metric, n=len(g), held_out_provinces=g.province_code.nunique(), rmse_pp=np.sqrt(np.mean(error ** 2)), mae_pp=np.mean(np.abs(error)), bias_pp=np.mean(error), r2=1-np.sum(error**2)/np.sum((g.observed-g.observed.mean())**2), p90_absolute_error_pp=np.quantile(np.abs(error),.9),
            interpretation="Interpolation-to-model validation; frozen-baseline case is conditional on pre-existing provincial calibration; not independent field validation"))
    save(pd.DataFrame(sums), "spatial_validation_summary")
    print(pd.DataFrame(sums).to_string(index=False), flush=True)


@lru_cache(maxsize=16)
def gamma_tech(name, gamma):
    from pvsim.materials import PEROVSKITE, TANDEM_2T
    from scripts.silicon_baseline_sensitivity import _gamma_pmax
    tech = PEROVSKITE if name == "single" else TANDEM_2T
    if gamma == (-.15 if name == "single" else -.30):
        return tech
    low, high = .3, 2.2
    for _ in range(50):
        mid=(low+high)/2
        actual=_gamma_pmax(replace(tech,Ea_recomb=mid))
        if actual > gamma: low=mid
        else: high=mid
    result=replace(tech,Ea_recomb=(low+high)/2)
    assert abs(_gamma_pmax(result)-gamma)<1e-4
    return result


@lru_cache(maxsize=6)
def gap_table(gap):
    import pvsim.spectral as sp
    old=sp.TANDEM_TOP_EG_REF
    try:
        sp.TANDEM_TOP_EG_REF=gap
        sp._tandem_reference_subcell_yields.cache_clear()
        sp._tandem_sf_table.cache_clear()
        return tuple(x.copy() for x in sp._tandem_sf_table())
    finally:
        sp.TANDEM_TOP_EG_REF=old
        sp._tandem_reference_subcell_yields.cache_clear()
        sp._tandem_sf_table.cache_clear()


def scan_city(anchor):
    import pvsim.system as sy
    import pvsim.spectral as sp
    from pvsim import weather as wx
    from pvsim.materials import CSI_MODERN
    from pvsim.module import module_stc_power
    path=OUT / "parameter_shards" / f"{anchor.adcode}.csv"
    if path.exists(): return pd.read_csv(path, dtype={"adcode":str}).to_dict("records")
    w=wx.from_pvgis_tmy(anchor.lat,anchor.lon,altitude=anchor.altitude_m,name=anchor.cache_key,allow_download=False)
    cfg=sy.SystemConfig()
    csi=sy.simulate(CSI_MODERN,w,cfg,npts=60)
    csi_density=module_stc_power(CSI_MODERN)/(CSI_MODERN.cells_in_series*CSI_MODERN.area_cm2*1e-4)/1000
    original=sy.spectral_factor_from_zenith
    rows=[]
    for name,gammas,responses in [("single",[-.25,-.15,-.10],[.7,1,1.3]),("tandem",[-.4,-.3,-.2],[1.60,1.68,1.75])]:
        for gamma in gammas:
            tech=gamma_tech(name,gamma)
            density=module_stc_power(tech)/(tech.cells_in_series*tech.area_cm2*1e-4)/1000
            for response in responses:
                if name == "single":
                    def sf(t,z,tcell_C=None):
                        base=original(t,z,tcell_C=tcell_C)
                        return 1+response*(base-1) if t.name=="perovskite" else base
                else:
                    zg,tg,values=gap_table(response)
                    def sf(t,z,tcell_C=None):
                        return sp._bilinear_lookup(z,tcell_C,zg,tg,values) if t.name=="tandem" else original(t,z,tcell_C=tcell_C)
                try:
                    sy.spectral_factor_from_zenith=sf
                    result=sy.simulate(tech,w,cfg,npts=60)
                finally:
                    sy.spectral_factor_from_zenith=original
                ratio=result["specific_yield"]/csi["specific_yield"]
                for scale in [.9,1.,1.1]:
                    rows.append(dict(adcode=anchor.adcode,province_code=anchor.province_code,tech=name,gamma_target_pct_per_c=gamma,
                        response_parameter=response,response_parameter_name="Spectral deviation multiplier" if name=="single" else "Top-cell bandgap at 25 C (eV)",
                        efficiency_ratio_scale=scale,capacity_advantage_pct=100*(ratio-1),area_advantage_pct=100*(ratio*density/csi_density*scale-1),
                        yield_kwh_per_kwp=result["specific_yield"],csi_yield_kwh_per_kwp=csi["specific_yield"],ghi_kwh_m2=float(w.ghi.sum()/1000),
                        scan_definition="Full factorial over declared temperature-response, spectral-response and capacity-density scenarios; no empirical probability assigned"))
    path.parent.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(rows).to_csv(path,index=False,encoding="utf-8-sig")
    return rows


def parameter_scan(workers):
    from pvsim.city_catalog import load_city_catalog
    rows=[]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        jobs={pool.submit(scan_city,a):a.adcode for a in load_city_catalog()}
        for i,future in enumerate(as_completed(jobs),1):
            rows.extend(future.result())
            if i%10==0: print(f"Parameter scan {i}/337 cities",flush=True)
    f=pd.DataFrame(rows)
    assert len(f)==337*54
    save(f,"parameter_scan")
    d,a=data()
    f=f.merge(a[["adcode","ghi_quartile"]],on="adcode",validate="many_to_one")
    sums=[]
    keys=["tech","gamma_target_pct_per_c","response_parameter","efficiency_ratio_scale"]
    for key,g in f.groupby(keys,sort=True):
        for unit in ["capacity","area"]:
            y=g[f"{unit}_advantage_pct"]
            effect=y[g.ghi_quartile=="Q1"].mean()-y[g.ghi_quartile=="Q4"].mean()
            sums.append(dict(zip(keys,key),metric=unit,mean_pct=y.mean(),min_pct=y.min(),max_pct=y.max(),positive_cities=int((y>0).sum()),q1_q4_effect_pp=effect,pearson_r=pearsonr(g.ghi_kwh_m2,y).statistic))
    save(pd.DataFrame(sums),"parameter_scan_summary")
    # Exact baseline agreement is checked against the independent source file.
    baseline=f[(f.efficiency_ratio_scale==1)&(((f.tech=="single")&(f.gamma_target_pct_per_c==-.15)&(f.response_parameter==1))|((f.tech=="tandem")&(f.gamma_target_pct_per_c==-.3)&(f.response_parameter==1.68)))]
    checks=[]
    for tech,g in baseline.groupby("tech"):
        ref=a.set_index("adcode").loc[g.adcode,f"{tech}_capacity_pct"].to_numpy()
        err=np.abs(g.capacity_advantage_pct.to_numpy()-ref)
        checks.append(dict(tech=tech,max_advantage_error_pp=float(err.max())))
        assert err.max()<.01, (tech,err.max())
    save(pd.DataFrame(checks),"parameter_baseline_reconciliation")


def coverage():
    from pvsim.city_catalog import load_city_catalog
    d,a=data()
    codes=set(a.groupby("province_code",sort=True).first().adcode)
    medoids=pd.read_csv(ROOT / ".work/supplementary_video1/Supplementary_Video_1_coverage_city_selection.csv",dtype={"adcode":str})
    codes |= set(medoids.adcode) | set(d.loc[d.single_capacity_pct<0,"adcode"])
    rows=[]
    for anchor in load_city_catalog():
        if anchor.adcode in codes:
            rows.append(anchor)
    assert len({x.province_code for x in rows})==31
    frame=pd.DataFrame([dict(adcode=x.adcode,province_code=x.province_code,city=x.city_fullname,lat=x.lat,lon=x.lon,altitude_m=x.altitude_m,
        selection="union of one administrative-code-first anchor per province, 12 geographic/climate medoids, and six negative-area prefectures") for x in rows])
    save(frame,"multiyear_coverage")
    return rows


def download_one(anchor):
    import requests
    CACHE.mkdir(parents=True,exist_ok=True)
    path=CACHE / f"{anchor.adcode}.json.gz"
    params=dict(lat=anchor.lat,lon=anchor.lon,startyear=2019,endyear=2023,raddatabase="PVGIS-ERA5",components=1,angle=0,aspect=0,outputformat="json",usehorizon=1)
    if path.exists():
        raw=gzip.decompress(path.read_bytes())
        payload=json.loads(raw)
        if len(payload.get("outputs",{}).get("hourly",[]))!=43824: raise ValueError(f"Invalid cached hours: {anchor.adcode}")
        return dict(adcode=anchor.adcode,hours=43824,sha256=hashlib.sha256(raw).hexdigest(),source_url=payload.get("source_url",SOURCE_URL),retrieved_date="2026-09-06")
    for attempt in range(3):
        try:
            r=requests.get(SOURCE_URL,params=params,timeout=55)
            r.raise_for_status()
            payload=r.json()
            assert len(payload["outputs"]["hourly"])==43824
            payload["source_url"]=r.url
            raw=json.dumps(payload,separators=(",", ":")).encode()
            path.write_bytes(gzip.compress(raw))
            return dict(adcode=anchor.adcode,hours=43824,sha256=hashlib.sha256(raw).hexdigest(),source_url=r.url,retrieved_date="2026-09-06")
        except Exception:
            if attempt==2: raise
            time.sleep(2+attempt*2)


def fetch_weather(workers):
    rows=[]
    anchors=coverage()
    with ThreadPoolExecutor(max_workers=min(workers,3)) as pool:
        jobs={pool.submit(download_one,a):a.adcode for a in anchors}
        for i,f in enumerate(as_completed(jobs),1):
            rows.append(f.result())
            print(f"Downloaded {i}/{len(anchors)} locations",flush=True)
    save(pd.DataFrame(rows),"multiyear_data_sources")


def multiyear_city(anchor):
    from pvsim import weather as wx
    from pvsim.materials import CSI_MODERN,PEROVSKITE,TANDEM_2T
    from pvsim.system import SystemConfig,simulate
    from pvlib.location import Location
    path=OUT / "multiyear_shards" / f"{anchor.adcode}.csv"
    if path.exists(): return pd.read_csv(path,dtype={"adcode":str}).to_dict("records")
    payload=json.loads(gzip.decompress((CACHE/f"{anchor.adcode}.json.gz").read_bytes()))
    raw=pd.DataFrame(payload["outputs"]["hourly"])
    raw.index=pd.to_datetime(raw.time,format="%Y%m%d:%H%M",utc=True)
    assert raw.index.is_unique and (raw.index.to_series().diff().dropna()==pd.Timedelta(hours=1)).all()
    rows=[]
    for year,g in raw.groupby(raw.index.year):
        sine=np.sin(np.deg2rad(g.H_sun.to_numpy(float)))
        direct=g["Gb(i)"].to_numpy(float)
        assert not ((direct>0)&(sine<=0)).any()
        dni=np.divide(direct,sine,out=np.zeros_like(direct),where=sine>0)
        ghi=g["Gb(i)"]+g["Gd(i)"]+g["Gr(i)"]
        loc=Location(anchor.lat,anchor.lon,tz="Asia/Shanghai",altitude=anchor.altitude_m)
        w=wx.make_weather(g.index,loc,ghi,dni,g["Gd(i)"],g.T2m,g.WS10m)
        result={}
        for name,tech in [("csi",CSI_MODERN),("single",PEROVSKITE),("tandem",TANDEM_2T)]:
            r=simulate(tech,w,SystemConfig(),npts=60)
            area=20*tech.cells_in_series*tech.area_cm2*1e-4
            result[name]=(r["specific_yield"],r["energy_ac_kwh"]/area)
        rows.append(dict(adcode=anchor.adcode,province_code=anchor.province_code,year=year,hours=len(g),ghi_kwh_m2=ghi.sum()/1000,
            single_capacity_pct=100*(result["single"][0]/result["csi"][0]-1),tandem_area_pct=100*(result["tandem"][1]/result["csi"][1]-1),
            tandem_capacity_pct=100*(result["tandem"][0]/result["csi"][0]-1),single_area_pct=100*(result["single"][1]/result["csi"][1]-1),
            csi_kwh_per_kwp=result["csi"][0],single_kwh_per_kwp=result["single"][0],tandem_kwh_per_kwp=result["tandem"][0],
            source="PVGIS 5.3 ERA5 historical hourly reanalysis; not field generation measurements"))
    path.parent.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(rows).to_csv(path,index=False,encoding="utf-8-sig")
    return rows


def multiyear(workers):
    anchors=coverage(); rows=[]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        jobs={pool.submit(multiyear_city,a):a.adcode for a in anchors}
        for i,f in enumerate(as_completed(jobs),1):
            rows.extend(f.result())
            print(f"Historical simulation {i}/{len(anchors)} locations",flush=True)
    f=pd.DataFrame(rows)
    assert len(f)==len(anchors)*5
    d,a=data()
    f=f.merge(a[["adcode","ghi_quartile"]],on="adcode",validate="many_to_one")
    save(f,"multiyear_results")
    rows=[]
    for year,g in f.groupby("year"):
        for metric in MAIN_METRICS:
            y=g[metric]
            rows.append(dict(year=year,metric=metric,n=len(g),q1_n=int((g.ghi_quartile=="Q1").sum()),q4_n=int((g.ghi_quartile=="Q4").sum()),
                mean_pct=y.mean(),effect_pp=y[g.ghi_quartile=="Q1"].mean()-y[g.ghi_quartile=="Q4"].mean(),pearson_r=pearsonr(g.ghi_kwh_m2,y).statistic,positive_locations=int((y>0).sum()),
                interpretation="Purposefully selected coverage set; quartiles fixed from all 337 TMY anchors; not nationwide 337-city year-specific estimates"))
    save(pd.DataFrame(rows),"multiyear_summary")


if __name__=="__main__":
    if hasattr(sys.stdout,"reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
    p=argparse.ArgumentParser()
    p.add_argument("action",choices=["analyse","scan","fetch-weather","multiyear"])
    p.add_argument("--workers",type=int,default=4)
    args=p.parse_args()
    if args.action=="analyse": basic_analysis(); spatial_validation()
    elif args.action=="scan": parameter_scan(args.workers)
    elif args.action=="fetch-weather": fetch_weather(args.workers)
    else: multiyear(args.workers)
