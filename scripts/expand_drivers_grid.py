"""给新图 2 的 (a)(b) 加密数据点: 在中国 bbox 内撒一批 PVGIS 采样点, 对每点跑温度/光谱分解。

这些点只用于展示机制关系, 不是 ERA5 0.1° 陆地格点。
输出缓存 outputs/advantage_drivers_grid.csv (province=grid_*; 含 lat/lon/thermal/spectral/tcell/airmass)。
海洋/无效点 PVGIS 会失败, 自动跳过。重跑会复用缓存。
运行: python -m scripts.expand_drivers_grid
"""

import os
import sys
import numpy as np
import pandas as pd
import pvlib

from pvsim.materials import CSI_MODERN, PEROVSKITE
from pvsim import weather as wx
from pvsim.system import SystemConfig, simulate

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CACHE = "outputs/advantage_drivers_grid.csv"


def _fill_cached_metadata(rec):
    rec = dict(rec)
    name = str(rec.get("province", ""))
    parts = name.split("_")
    if len(parts) == 3 and parts[0] == "grid":
        if "lat" not in rec or pd.isna(rec.get("lat")):
            rec["lat"] = float(parts[1])
        if "lon" not in rec or pd.isna(rec.get("lon")):
            rec["lon"] = float(parts[2])
    if rec.get("band") == "grid":
        rec["band"] = "pvgis_bbox_sample"
    return rec


def _adv(w, **kw):
    cfg = SystemConfig(n_modules=20, **kw)
    rc = simulate(CSI_MODERN, w, cfg, npts=40)
    rp = simulate(PEROVSKITE, w, cfg, npts=40)
    return (rp["specific_yield"]/rc["specific_yield"]-1)*100, rc


def decompose(lat, lon, alt, name):
    w = wx.from_pvgis_tmy(lat, lon, altitude=alt, name=name)
    full, rc = _adv(w)
    no_spec, _ = _adv(w, apply_spectral=False)
    no_spec_no_iam, _ = _adv(w, apply_spectral=False, apply_iam=False)
    ts = rc["timeseries"]; poa = ts["poa_global"].to_numpy(); tc = ts["tcell"].to_numpy()
    am = pvlib.atmosphere.get_relative_airmass(w["solar_zenith"].to_numpy(float))
    am = np.where(np.isfinite(am), am, 40.0); m = poa > 50
    return {"province": name, "band": "pvgis_bbox_sample", "lat": lat, "lon": lon,
            "full": full, "thermal": no_spec_no_iam, "spectral": full-no_spec,
            "iam": no_spec-no_spec_no_iam,
            "tcell": float(np.average(tc[m], weights=poa[m])),
            "airmass": float(np.average(np.clip(am, 1, 10)[m], weights=poa[m]))}


def main():
    done = {}
    if os.path.exists(CACHE):
        for r in pd.read_csv(CACHE, encoding="utf-8-sig").to_dict("records"):
            rec = _fill_cached_metadata(r)
            done[rec["province"]] = rec      # 全部转 dict, 避免与新点(dict)混型
    lats = np.arange(23, 49, 2.0)
    lons = np.arange(80, 125, 2.5)
    rows = list(done.values())
    n_new, n_fail = 0, 0
    for la in lats:
        for lo in lons:
            name = f"grid_{la:.1f}_{lo:.1f}"      # 细一档, .1f 命名不撞旧整数名
            if name in done:
                continue
            try:
                rec = decompose(float(la), float(lo), 500.0, name)
                rows.append(rec); done[name] = rec; n_new += 1
                if n_new % 25 == 0:              # 增量存盘, 防崩溃白算
                    pd.DataFrame(rows).to_csv(CACHE, index=False, encoding="utf-8-sig")
                    print(f"  {n_new} 个新点完成 (已存盘)...")
            except Exception:
                n_fail += 1
    pd.DataFrame(rows).to_csv(CACHE, index=False, encoding="utf-8-sig")
    print(f"完成: 缓存共 {len(rows)} 个网格点 (本次新增 {n_new}, 跳过/失败 {n_fail})。")


if __name__ == "__main__":
    main()
