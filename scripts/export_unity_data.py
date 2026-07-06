"""导出 Unity 仿真所需的数据 (pvdata.json)。

作为 Unity 端的**单一数据源**：
    - 两套器件参数 (Unity 端 C# 实时算 I-V 用)
    - 光谱失配因子 SF 关于天顶角的查表 (C# 插值用)
    - 多年衰减曲线、叠层扫描、样例日序列 (面板展示/动画用)

运行: python -m scripts.export_unity_data
输出: unity/PvCompare/Assets/StreamingAssets/pvdata.json
"""

import sys
import json
import datetime as dt

import numpy as np

from pvsim.materials import CSI_EARLY, PEROVSKITE
from pvsim.cell import operating_point
from pvsim import spectral as sp
from pvsim import weather as wx
from pvsim import tandem as td
from pvsim.degradation import lifetime_energy, PEROVSKITE_SCENARIOS
from pvsim.cities import CITIES
from pvsim.viz import COLORS

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

OUT = "unity/PvCompare/Assets/StreamingAssets/pvdata.json"


def tech_dict(tech):
    ns = tech.cells_in_series
    op = operating_point(tech, 1000.0, 25.0, ns=ns, npts=400)
    s = tech.spectral
    return {
        "name": tech.name,
        "name_cn": tech.name_cn,
        "color": COLORS.get(tech.name, "#888888"),
        "area_cm2": tech.area_cm2,
        "cells_in_series": ns,
        # 单二极管参考参数 (C# 实时计算用)
        "I_L_ref": tech.I_L_ref,
        "I_o_ref": tech.I_o_ref,
        "R_s": tech.R_s,
        "R_sh_ref": tech.R_sh_ref,
        "n_ideality": tech.n_ideality,
        "alpha_sc": tech.alpha_sc,
        "EgRef": tech.EgRef,
        "Ea_recomb": tech.Ea_recomb,
        "noct": tech.noct,
        # 光谱响应形状
        "lambda_min": s.lambda_min,
        "lambda_gap": s.lambda_gap,
        "eqe_peak": s.eqe_peak,
        "edge_width": s.edge_width,
        "blue_rolloff": s.blue_rolloff,
        # 其他
        "bifaciality": tech.bifaciality,
        "lifetime_years": tech.lifetime_years,
        "capex_per_wp": tech.capex_per_wp,
        "hysteresis_index": tech.hysteresis_index,
        # STC 校核值 (C# 端可对照)
        "stc": {"isc": op.isc, "voc": op.voc, "pmp": op.pmp,
                "ff": op.ff, "eff": op.efficiency},
    }


def spectral_table(n=19):
    zen = np.linspace(0.0, 88.0, n)
    sf = {}
    for tech in (CSI_EARLY, PEROVSKITE):
        sf[tech.name] = [float(sp.spectral_factor_from_zenith(tech, z)) for z in zen]
    return {"zenith": zen.tolist(), "sf": sf}


def degradation_table(horizon=25):
    years = np.arange(1, horizon + 1)
    le_c = lifetime_energy(CSI_EARLY, 1.0, horizon_years=horizon)
    out = {"years": years.tolist(),
           "c-Si": le_c["retention"].tolist(),
           "perovskite": {}}
    for sc in PEROVSKITE_SCENARIOS:
        le = lifetime_energy(PEROVSKITE, 1.0, sc, horizon_years=horizon)
        out["perovskite"][sc] = {
            "retention": le["retention"].tolist(),
            "t80": le["t80_year"],
        }
    return out


def tandem_table():
    egs, effs, eg_opt, eff_opt = td.optimal_top_bandgap()
    t = td.tandem_perovskite_silicon()
    pero, csi = td.reference_single_junctions()
    return {
        "bandgap": egs.tolist(),
        "efficiency": effs.tolist(),
        "best_eg": float(eg_opt), "best_eff": float(eff_opt),
        "tandem_eff": t.efficiency,
        "single_csi_eff": csi.efficiency,
        "single_pero_eff": pero.efficiency,
        "current_mismatch": t.current_mismatch * 100,
        "voc": t.voc,
    }


def sample_day():
    loc = wx.get_location()
    day = wx.clear_sky_day("2023-06-21", loc, freq="30min", tmean=32.0)
    hours = (day.index.hour + day.index.minute / 60.0).tolist()
    return {
        "location": loc.name,
        "hour": hours,
        "poa": day["poa_global"].round(1).tolist(),
        "temp_air": day["temp_air"].round(2).tolist(),
        "zenith": day["solar_zenith"].round(2).tolist(),
        "azimuth": day["solar_azimuth"].round(2).tolist(),
        "aoi": day["aoi"].round(2).tolist(),
        "wind_speed": day["wind_speed"].round(2).tolist(),
    }


def _day_dict(w, tz="Asia/Shanghai", months=(5, 6, 7, 8)):
    """从一城真实TMY里挑指定季节中辐照最强的代表日, 转成播放用逐时日数据(仅白天)。"""
    wl = w.tz_convert(tz)
    dates = wl.index.normalize()
    daily = wl.groupby(dates)["poa_global"].sum()
    sel = daily[daily.index.month.isin(months)]
    best = (sel if len(sel) else daily).idxmax()
    day = wl[dates == best]
    day = day[day["poa_global"] > 5.0]              # 只留白天
    hours = (day.index.hour + day.index.minute / 60.0).tolist()
    return {
        "hour": hours,
        "poa": day["poa_global"].round(1).tolist(),
        "temp_air": day["temp_air"].round(2).tolist(),
        "zenith": day["solar_zenith"].round(2).tolist(),
        "azimuth": day["solar_azimuth"].round(2).tolist(),
        "aoi": day["aoi"].round(2).tolist(),
        "wind_speed": day["wind_speed"].round(2).tolist(),
    }


def cities_data():
    """每城代表日 (用于 Unity 城市下拉)。"""
    out = []
    for c in CITIES:
        w = wx.from_pvgis_tmy(c.lat, c.lon, altitude=c.alt, name=c.key)
        summer = _day_dict(w, months=(5, 6, 7, 8)); summer["location"] = c.name
        winter = _day_dict(w, months=(12, 1, 2)); winter["location"] = c.name
        out.append({"name": c.name, "note": c.note, "day": summer, "winter_day": winter})
        print(f"  城市日: {c.name} (夏{len(summer['hour'])}点/冬{len(winter['hour'])}点)")
    return out


def main():
    data = {
        "meta": {
            "generated": dt.datetime.now().isoformat(timespec="seconds"),
            "note": "晶硅 vs 钙钛矿 Unity 仿真数据 (由 pvsim 模型导出)",
            "g_ref": 1000.0, "t_ref": 25.0,
        },
        "technologies": {
            "c-Si": tech_dict(CSI_EARLY),
            "perovskite": tech_dict(PEROVSKITE),
        },
        "spectral_sf": spectral_table(),
        "degradation": degradation_table(),
        "tandem": tandem_table(),
        "sample_day": sample_day(),
        "cities": cities_data(),
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"已导出 {OUT}")
    print(f"  技术: {list(data['technologies'])}")
    print(f"  城市数: {len(data['cities'])} -> {[c['name'] for c in data['cities']]}")


if __name__ == "__main__":
    main()
