"""论文(系统侧姊妹篇)主图流水线：技术分辨的屋顶光储充配网友好性。

主张：晶硅→钙钛矿换板子, 因"中午更满"的发电形状, 同装机下加重配网负担;
该差异可分解为温度+光谱两机制(接 C 论文), 且随气候变化, 普通降额模型看不见。

本轮: GridFig1(技术形状差·8760h) + GridFig3(双机制分解·头条)。
运行: $env:PYTHONIOENCODING="utf-8"; python -m scripts.grid_paper
输出: outputs/paper_grid/*.png, *.csv
"""

import sys
import os

import numpy as np
import pandas as pd
from dataclasses import replace

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from pvsim import viz
from pvsim.viz import plt, color, LABEL_EN
from pvsim import weather as wx
from pvsim.system import SystemConfig, simulate_rooftop
from pvsim.materials import get_technology
from pvsim import load as ld
from pvsim import ev as evmod, tariff as tf, ems, grid as gd
from pvsim import powerflow as pf
from pvsim.storage import Battery
from pvsim.cities import CITIES as CITY_LIST

OUT = "outputs/paper_grid"
CSI, PERO = get_technology("c-Si-modern"), get_technology("perovskite")
# 跨气候代表城市 (key, lat, lon, alt, 英文名, 类型)
CITIES = [
    ("lhasa", 29.65, 91.14, 3650, "Lhasa", "plateau"),
    ("harbin", 45.75, 126.63, 150, "Harbin", "cold"),
    ("shanghai", 31.23, 121.47, 10, "Shanghai", "temperate"),
    ("guangzhou", 23.13, 113.26, 20, "Guangzhou", "hot"),
    ("haikou", 20.04, 110.32, 15, "Haikou", "tropical"),
]
BASE_CFG = SystemConfig(n_modules=20, thermal_u0=20.0, thermal_u1=3.0)


def load_city(key, lat, lon, alt):
    raw = wx.from_pvgis_tmy(lat, lon, altitude=alt, name=key).tz_convert("Asia/Shanghai")
    loc = wx.get_location(lat, lon, tz="Asia/Shanghai", altitude=alt, name=key)
    return raw, loc


def per_kwp(tech, raw, loc, apply_temp=True, apply_spec=True):
    """单朝南阵列, 每 kWp 交流出力 (W/kWp)。temp/spec 开关用于反事实分解。"""
    cfg = replace(BASE_CFG, apply_temperature=apply_temp, apply_spectral=apply_spec)
    r = simulate_rooftop(tech, raw, loc, cfg, [(abs(loc.latitude), 180.0, 20)])
    return (r["ac_power"] / r["kwp"]).to_numpy(float), r["ac_power"].index


def reverse_energy(pk_w_per_kwp, load_kw, kwp, dt=1.0):
    """同装机系统(无电池)年倒送电量 kWh。pk: W/kWp; load: kW。"""
    power_kw = pk_w_per_kwp * kwp / 1000.0
    return float(np.clip(power_kw - load_kw, 0, None).sum() * dt)


# ----------------------------------------------------------------------
def fig1_shape(raw, loc):
    """技术形状差: 全年逐时 (钙钛矿−晶硅) 每 kWp 出力热图 + 平均日内曲线。"""
    csi, idx = per_kwp(CSI, raw, loc)
    pero, _ = per_kwp(PERO, raw, loc)
    diff = pd.Series(pero - csi, index=idx)
    df = pd.DataFrame({"v": diff.to_numpy(), "doy": idx.dayofyear, "h": idx.hour})
    grid = df.pivot_table(index="doy", columns="h", values="v", aggfunc="mean")

    fig, (ax, axr) = plt.subplots(1, 2, figsize=(13, 5),
                                  gridspec_kw={"width_ratios": [2.3, 1]})
    vmax = np.nanpercentile(np.abs(grid.to_numpy()), 99)
    im = ax.imshow(grid.to_numpy(), aspect="auto", origin="lower",
                   extent=[0, 24, 1, 366], cmap="RdBu_r", vmin=-vmax, vmax=vmax)
    ax.set(xlabel="Hour of day (local)", ylabel="Day of year",
           title="Perovskite − c-Si AC output (same kWp)")
    ax.set_xticks(range(0, 25, 6))
    cb = fig.colorbar(im, ax=ax); cb.set_label("W per kWp")

    csi_h = pd.Series(csi, index=idx).groupby(idx.hour).mean()
    pero_h = pd.Series(pero, index=idx).groupby(idx.hour).mean()
    axr.plot(csi_h.index, csi_h.to_numpy(), color=color("c-Si-modern"), lw=2, label="c-Si")
    axr.plot(pero_h.index, pero_h.to_numpy(), color=color("perovskite"), lw=2, label="Perovskite")
    axr.fill_between(csi_h.index, csi_h.to_numpy(), pero_h.to_numpy(),
                     where=(pero_h.to_numpy() >= csi_h.to_numpy()),
                     color=color("perovskite"), alpha=0.15)
    axr.set(xlabel="Hour of day", ylabel="Mean AC output (W per kWp)",
            title="Average diurnal shape", xlim=(4, 21))
    axr.legend(frameon=False)
    fig.suptitle("Fig.1  Same nameplate, fuller midday: the technology shape difference",
                 fontweight="bold")
    fig.tight_layout()
    viz.save(fig, f"{OUT}/GridFig1_shape.png")
    # 量化: 中午(11-14)平均差
    mid = (idx.hour >= 11) & (idx.hour <= 14)
    print(f"  Fig1: 中午 钙钛矿−晶硅 = {diff[mid].mean():+.0f} W/kWp "
          f"(晶硅 {csi[mid].mean():.0f}, 钙钛矿 {pero[mid].mean():.0f})")


def fig3_decompose():
    """头条: 同装机年倒送电量的(钙钛矿−晶硅)差, 分解为温度+光谱+交互。"""
    KWP = 6.0
    rows = []
    for key, lat, lon, alt, en, kind in CITIES:
        raw, loc = load_city(key, lat, lon, alt)
        # 固定负荷(不随气候, 隔离技术效应); 居民、无空调耦合
        load = ld.load_profile(raw.index, daily_kwh=14.0, kind="residential",
                               seasonal=True).to_numpy()

        def D(temp, spec):   # 钙钛矿−晶硅 的年倒送差(同装机)
            c, idx = per_kwp(CSI, raw, loc, temp, spec)
            p, _ = per_kwp(PERO, raw, loc, temp, spec)
            return (reverse_energy(p, load, KWP) - reverse_energy(c, load, KWP))

        d00, d10, d01, d11 = D(False, False), D(True, False), D(False, True), D(True, True)
        temp_c = d10 - d00
        spec_c = d01 - d00
        inter = d11 - d10 - d01 + d00
        rows.append(dict(city=en, kind=kind, total=d11, temp=temp_c,
                         spec=spec_c, inter=inter, base=d00))
        print(f"  Fig3 {en:10s}: 总+{d11:6.0f} kWh/yr = 温度 {temp_c:+.0f} + 光谱 {spec_c:+.0f} "
              f"+ 交互 {inter:+.0f} (基线 {d00:+.0f})")
    df = pd.DataFrame(rows)
    df.to_csv(f"{OUT}/decomposition.csv", index=False, encoding="utf-8-sig")

    order = df.sort_values("total")
    x = np.arange(len(order))
    fig, ax = plt.subplots(figsize=(9.2, 5.4))
    b0 = order["base"].to_numpy()
    bt = b0 + order["temp"].to_numpy()
    bs = bt + order["spec"].to_numpy()
    ax.bar(x, order["base"], color="#9FE1CB", label="Low-light / IV (intrinsic)")
    ax.bar(x, order["temp"], bottom=b0, color="#D14520", label="Temperature mechanism")
    ax.bar(x, order["spec"], bottom=bt, color="#378ADD", label="Spectrum mechanism")
    ax.bar(x, order["inter"], bottom=bs, color="#B4B2A9", label="Interaction")
    ax.plot(x, order["total"], "k_", ms=18, mew=2.5, label="Total")
    ax.axhline(0, color="gray", lw=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{r.city}\n({r.kind})" for r in order.itertuples()], fontsize=9)
    ax.set(ylabel="Extra annual reverse-power energy,\nperovskite − c-Si (kWh/yr, 6 kWp)",
           title="Fig.3  Perovskite's extra grid burden = temperature + spectrum")
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    viz.save(fig, f"{OUT}/GridFig3_decomposition.png")
    # 温度占比(热区应更高)
    for r in order.itertuples():
        if r.total > 1:
            print(f"    {r.city}: 温度占比 {r.temp/r.total*100:.0f}%")


def fig3_scatter():
    """头条(重做): 双机制随物理量连续变化, 露 8760h × 5气候带点云。
    温度分量 ~ 电池温度(正相关), 光谱分量 ~ 大气质量(负相关), 接 C 论文双机制。"""
    import pvlib
    from pvsim.weather import make_weather
    from pvsim.system import simulate
    keys = [("harbin", 45.75, 126.63, 150), ("lhasa", 29.65, 91.14, 3650),
            ("shanghai", 31.23, 121.47, 10), ("guangzhou", 23.13, 113.26, 20),
            ("haikou", 20.04, 110.32, 15)]
    cmap = plt.get_cmap("turbo")
    cols = [cmap(i / (len(keys) - 1)) for i in range(len(keys))]
    pts = []
    for ci, (key, lat, lon, alt) in enumerate(keys):
        raw, loc = load_city(key, lat, lon, alt)
        w = make_weather(raw.index, loc, raw["ghi"], raw["dni"], raw["dhi"],
                         raw["temp_air"], raw["wind_speed"],
                         surface_tilt=abs(lat), surface_azimuth=180.0)
        poa = w["poa_global"].to_numpy()
        am = pvlib.atmosphere.get_relative_airmass(w["solar_zenith"].to_numpy())
        tcell = simulate(CSI, w, replace(BASE_CFG, n_modules=20),
                         npts=80)["timeseries"]["tcell"].to_numpy()

        def pk(temp, spec, tech):
            cfg = replace(BASE_CFG, n_modules=20, apply_temperature=temp, apply_spectral=spec)
            r = simulate(tech, w, cfg, npts=80)
            return r["timeseries"]["ac_power"].to_numpy() / r["kwp"]

        d00 = pk(False, False, PERO) - pk(False, False, CSI)
        d10 = pk(True, False, PERO) - pk(True, False, CSI)
        d01 = pk(False, True, PERO) - pk(False, True, CSI)
        tempc, specc = d10 - d00, d01 - d00
        day = (poa > 50) & np.isfinite(am) & (am < 8)
        pts.append((tcell[day], tempc[day], am[day], specc[day], ci, key.capitalize()))

    T = np.concatenate([p[0] for p in pts]); TC = np.concatenate([p[1] for p in pts])
    AM = np.concatenate([p[2] for p in pts]); SC = np.concatenate([p[3] for p in pts])
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5.2))
    for p in pts:
        a1.scatter(p[0], p[1], s=3, alpha=0.10, color=cols[p[4]], label=p[5], edgecolors="none")
        a2.scatter(p[2], p[3], s=3, alpha=0.10, color=cols[p[4]], edgecolors="none")
    rT = np.corrcoef(T, TC)[0, 1]; zt = np.polyfit(T, TC, 1)
    xt = np.linspace(T.min(), T.max(), 50)
    a1.plot(xt, np.polyval(zt, xt), "k--", lw=1.6)
    a1.axhline(0, color="gray", lw=0.5); a1.axvline(25, color="gray", lw=0.5, ls=":")
    rA = np.corrcoef(AM, SC)[0, 1]; za = np.polyfit(AM, SC, 1)
    xa = np.linspace(1, 6, 50)
    a2.plot(xa, np.polyval(za, xa), "k--", lw=1.6)
    a2.axhline(0, color="gray", lw=0.5)
    a1.set(xlabel="Cell temperature (°C)",
           ylabel="Temperature-mechanism advantage (W per kWp)",
           title=f"(A) Temperature mechanism   r = {rT:+.2f}  (n = {len(T):,} h)")
    a2.set(xlabel="Air mass (1 = sun overhead)",
           ylabel="Spectrum-mechanism advantage (W per kWp)",
           title=f"(B) Spectrum mechanism   r = {rA:+.2f}", xlim=(1, 6))
    leg = a1.legend(markerscale=4, fontsize=8, frameon=False, loc="upper left")
    for lh in leg.legend_handles:
        lh.set_alpha(1)
    fig.suptitle("Fig.3  Two independent mechanisms, resolved over 8760 h × 5 climates",
                 fontweight="bold")
    fig.tight_layout(); viz.save(fig, f"{OUT}/GridFig3_decomposition.png")
    print(f"  Fig3: 温度分量~电池温度 r={rT:+.2f}; 光谱分量~大气质量 r={rA:+.2f}; "
          f"共 {len(T):,} 个白天小时点")


def en_label(tech):
    return "Perovskite" if tech.name == "perovskite" else "c-Si"


def pv_at_kwp(tech, raw, loc, kwp=6.0):
    pk, idx = per_kwp(tech, raw, loc)
    return pd.Series(pk * kwp / 1000.0, index=idx).rename("pv_kw")


def system_inputs(raw):
    """共用的负荷 + 充电桩(车队)。"""
    load = ld.load_profile(raw.index, daily_kwh=12.0, kind="residential",
                           temp_air=raw["temp_air"], hvac_kw_per_degC=0.18,
                           daily_variation=0.12, seed=2)
    sess = evmod.fleet_sessions("home", 1, len(raw) // 24 + 1, 0.7, seed=1)
    ev_agg = evmod.daily_ev_aggregate(raw.index, sess, allow_v2g=False)
    return load, sess, ev_agg


# ----------------------------------------------------------------------
def fig2_costgrid(raw, loc):
    """最省钱≠配网友好: (A)成本-倒送 取舍前沿(两技术) (B)变压器夜间反弹历时。"""
    KWP = 6.0
    cfgF = gd.FeederConfig()
    load, sess, ev_agg = system_inputs(raw)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5))

    # Panel A: 扫描倒送上限, 记录 年电费 vs 最大倒送(单户)
    exp_levels = [6.0, 4.0, 3.0, 2.5, 2.0, 1.5]
    for tech in (CSI, PERO):
        pv = pv_at_kwp(tech, raw, loc, KWP)
        bills, revs = [], []
        for el in exp_levels:
            try:
                r = ems.dispatch_optimal(pv, load, Battery(10, 5), ev_agg,
                                         tf.Tariff(), ems.GridConfig(export_limit_kw=el))
            except RuntimeError:
                continue
            bills.append(r["summary"]["annual_bill_yuan"])
            revs.append(r["summary"]["max_export_kw"])
        a1.plot(revs, bills, "o-", color=color(tech.name), label=en_label(tech), lw=2)
    a1.set(xlabel="Max reverse power per house (kW)",
           ylabel="Annual electricity bill (yuan)",
           title="(A) Cost vs grid stress (sweep export limit)")
    a1.annotate("cost-optimal\n(loose limit)", xy=(0, 0), xytext=(0.55, 0.9),
                textcoords="axes fraction", fontsize=8, color="#888")
    a1.legend(frameon=False)

    # Panel B: 变压器负载历时, 最省钱 vs 配网友好(限进线)
    pv = pv_at_kwp(PERO, raw, loc, KWP)
    n = len(pv); pct = np.arange(n) / n * 100
    for label, gc, c in [("Cost-optimal (uncoordinated)", ems.GridConfig(), "#D14520"),
                         ("Grid-friendly (import-capped 5kW)",
                          ems.GridConfig(import_limit_kw=5.0), "#1D9E75")]:
        try:
            r = ems.dispatch_optimal(pv, load, Battery(10, 5), ev_agg, tf.Tariff(), gc)
        except RuntimeError:
            continue
        g = gd.evaluate(r["timeseries"], KWP, cfgF, apply_voltvar=False)
        tl = np.sort(g["timeseries"]["transformer_loading"].to_numpy())[::-1] * 100
        a2.plot(pct, tl, color=c, lw=2, label=label)
        print(f"  Fig2 {label}: 变压器峰值 {tl[0]:.0f}%")
    a2.axhline(100, color="gray", ls=":", lw=1.2, label="Transformer rating")
    a2.set(xlabel="% of hours exceeding", ylabel="Transformer loading (%)",
           xlim=(0, 12), title="(B) Cost-optimal charging rebounds at night (Perovskite)")
    a2.legend(frameon=False, fontsize=8)
    fig.suptitle("Fig.2  The cost-optimal operating point is not the grid-friendly one",
                 fontweight="bold")
    fig.tight_layout(); viz.save(fig, f"{OUT}/GridFig2_costgrid.png")


def fig4_geography():
    """全国(12省会)技术配网负担: 随运行温度的梯度 + 空间分布。"""
    KWP = 6.0
    rows = []
    for c in CITY_LIST:
        raw, loc = load_city(c.key, c.lat, c.lon, c.alt)
        load = ld.load_profile(raw.index, daily_kwh=14.0, kind="residential",
                               seasonal=True).to_numpy()
        cs, idx = per_kwp(CSI, raw, loc); pe, _ = per_kwp(PERO, raw, loc)
        burden = reverse_energy(pe, load, KWP) - reverse_energy(cs, load, KWP)
        ghi = raw["ghi"].to_numpy(); ta = raw["temp_air"].to_numpy()
        optemp = float((ghi * ta).sum() / ghi.sum()) if ghi.sum() > 0 else float("nan")
        rows.append(dict(en=c.key.capitalize(), lat=c.lat, lon=c.lon,
                         burden=burden, optemp=optemp))
        print(f"  Fig4 {c.key:10s}: 负担 +{burden:.0f} kWh/yr, 辐照加权气温 {optemp:.1f}°C")
    df = pd.DataFrame(rows)
    df.to_csv(f"{OUT}/geography.csv", index=False, encoding="utf-8-sig")

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5.2))
    a1.scatter(df["optemp"], df["burden"], s=70, color=color("perovskite"), zorder=3)
    z = np.polyfit(df["optemp"], df["burden"], 1)
    xx = np.linspace(df["optemp"].min(), df["optemp"].max(), 50)
    a1.plot(xx, np.polyval(z, xx), "--", color="#888",
            label=f"slope {z[0]:.0f} kWh/yr per °C")
    for r in df.itertuples():
        a1.annotate(r.en, (r.optemp, r.burden), textcoords="offset points",
                    xytext=(4, 3), fontsize=8)
    a1.set(xlabel="Irradiance-weighted air temperature (°C)",
           ylabel="Extra reverse energy, Perovskite − c-Si (kWh/yr)",
           title="(A) Grid burden rises with operating temperature")
    a1.legend(frameon=False)

    sc = a2.scatter(df["lon"], df["lat"], c=df["burden"], s=df["burden"] / 2.5,
                    cmap="YlOrRd", edgecolor="k", linewidth=0.5, zorder=3)
    for r in df.itertuples():
        a2.annotate(r.en, (r.lon, r.lat), textcoords="offset points",
                    xytext=(4, 3), fontsize=7)
    a2.set(xlabel="Longitude (°E)", ylabel="Latitude (°N)",
           title="(B) Spatial pattern (hot south = highest burden)")
    cb = fig.colorbar(sc, ax=a2); cb.set_label("Extra reverse energy (kWh/yr)")
    fig.suptitle("Fig.4  The technology grid burden is geographic — largest where it is hot",
                 fontweight="bold")
    fig.tight_layout(); viz.save(fig, f"{OUT}/GridFig4_geography.png")


def fig5_mitigation(raw, loc, cityname):
    """缓解: 过压时数随电池容量下降; 钙钛矿需更大电池才达到同等友好。"""
    KWP = 6.0
    cfgF = gd.FeederConfig()
    load, sess, ev_agg = system_inputs(raw)
    sizes = [0, 2, 4, 6, 8, 10, 12, 15]
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    req = {}
    for tech in (CSI, PERO):
        pv = pv_at_kwp(tech, raw, loc, KWP)
        pref = ems.pv_surplus_preference(pv, load, tf.Tariff())
        ev_s = evmod.flexible_demand(raw.index, sess, pref)
        ov = []
        for b in sizes:
            bat = Battery(max(b, 0.01), max(2.0, b * 0.5))
            r = ems.dispatch(pv, load, ev_s, bat, tf.Tariff(),
                             ems.GridConfig(), "self_consumption")
            g = gd.evaluate(r["timeseries"], KWP, cfgF, apply_voltvar=False)
            ov.append(g["metrics"]["overvoltage_hours"])
        ax.plot(sizes, ov, "o-", color=color(tech.name), lw=2, label=en_label(tech))
        # 达到 ≤ 起点20% 所需电池(粗略友好门槛)
        thr = 0.2 * ov[0]
        below = [s for s, o in zip(sizes, ov) if o <= thr]
        req[en_label(tech)] = below[0] if below else float("nan")
        print(f"  Fig5 {en_label(tech)}: 过压 {ov[0]}→{ov[-1]} h; 降到20%需电池≈{req[en_label(tech)]} kWh")
    ax.set(xlabel="Battery size (kWh)", ylabel="Annual over-voltage hours",
           title=f"Fig.5  Perovskite needs a larger battery for the same grid-friendliness\n({cityname})")
    ax.legend(frameon=False)
    fig.tight_layout(); viz.save(fig, f"{OUT}/GridFig5_mitigation.png")


def fig6_hosting():
    """真潮流·头条: 接入容量(峰值限, 技术几乎无差) vs 弃光(能量限, 钙钛矿惩罚随热飙升)。"""
    fd = pf.build_lv_feeder(n_houses=20, span_m=400.0, s_rated_kva=250.0)
    K_FIX = 6.0
    keys = [("harbin", 45.75, 126.63, 150, "Harbin", "cold"),
            ("lhasa", 29.65, 91.14, 3650, "Lhasa", "plateau"),
            ("urumqi", 43.83, 87.62, 900, "Urumqi", "arid"),
            ("shanghai", 31.23, 121.47, 10, "Shanghai", "temperate"),
            ("chengdu", 30.67, 104.07, 500, "Chengdu", "cloudy"),
            ("guangzhou", 23.13, 113.26, 20, "Guangzhou", "hot"),
            ("haikou", 20.04, 110.32, 15, "Haikou", "tropical")]
    rows = []
    for key, lat, lon, alt, en, kind in keys:
        raw, loc = load_city(key, lat, lon, alt)
        load = ld.load_profile(raw.index, daily_kwh=14.0, kind="residential",
                               seasonal=True).to_numpy()
        ghi = raw["ghi"].to_numpy(); ta = raw["temp_air"].to_numpy()
        optemp = float((ghi * ta).sum() / ghi.sum())
        rec = {"en": en, "kind": kind, "optemp": optemp}
        for tech, tag in ((CSI, "csi"), (PERO, "pero")):
            r = simulate_rooftop(tech, raw, loc, BASE_CFG, [(abs(lat), 180.0, 20)])
            pk = (r["ac_power"] / r["kwp"]).to_numpy()
            rec[f"hc_{tag}"] = pf.hosting_capacity(fd, pk, load, v_limit=1.05)["kwp_per_house"]
            rec[f"cur_{tag}"] = pf.annual_curtailment(fd, pk, load, K_FIX, v_limit=1.05)["curtail_kwh"]
        rec["hc_ratio"] = rec["hc_pero"] / rec["hc_csi"]
        rec["cur_penalty"] = (rec["cur_pero"] / max(rec["cur_csi"], 1e-9) - 1) * 100
        rows.append(rec)
        print(f"  Fig6 {en:10s}: 接入容量比 {rec['hc_ratio']:.3f}, 弃光惩罚 {rec['cur_penalty']:+.0f}%",
              flush=True)
    df = pd.DataFrame(rows).sort_values("optemp")
    df.to_csv(f"{OUT}/hosting.csv", index=False, encoding="utf-8-sig")

    x = np.arange(len(df)); w = 0.38
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13.5, 5.2))
    a1.bar(x - w / 2, df["hc_csi"], w, color=color("c-Si-modern"), label="c-Si")
    a1.bar(x + w / 2, df["hc_pero"], w, color=color("perovskite"), label="Perovskite")
    a1.set_xticks(x); a1.set_xticklabels(df["en"], rotation=30, ha="right")
    a1.set(ylabel="Hosting capacity (kWp per house)",
           title="(A) Hosting capacity (peak-limited): technology barely matters")
    a1.legend(frameon=False)
    for xi, r in zip(x, df.itertuples()):
        a1.annotate(f"{r.hc_ratio:.2f}", (xi, max(r.hc_csi, r.hc_pero)),
                    ha="center", va="bottom", fontsize=7, color="#555")

    a2.scatter(df["optemp"], df["cur_penalty"], s=80, color=color("perovskite"), zorder=3)
    z = np.polyfit(df["optemp"], df["cur_penalty"], 1)
    xx = np.linspace(df["optemp"].min(), df["optemp"].max(), 50)
    a2.plot(xx, np.polyval(z, xx), "--", color="#888",
            label=f"+{z[0]:.0f}% per °C")
    for r in df.itertuples():
        a2.annotate(r.en, (r.optemp, r.cur_penalty), textcoords="offset points",
                    xytext=(4, 3), fontsize=8)
    a2.axhline(0, color="gray", lw=0.6)
    a2.set(xlabel="Irradiance-weighted air temperature (°C)",
           ylabel="Extra curtailment of perovskite vs c-Si (%)",
           title="(B) Curtailment (energy-limited): perovskite penalty soars with heat")
    a2.legend(frameon=False)
    fig.suptitle("Fig.  Real power flow: technology is invisible to hosting capacity "
                 "but dominates curtailment", fontweight="bold")
    fig.tight_layout(); viz.save(fig, f"{OUT}/GridFig6_hosting.png")


def main():
    viz.setup_en()
    os.makedirs(OUT, exist_ok=True)
    figs = set(sys.argv[1:]) or {"1", "2", "3", "4", "5", "6"}
    if {"1", "2", "5"} & figs:
        raw_sh, loc_sh = load_city("shanghai", 31.23, 121.47, 10)
    if "1" in figs:
        print("GridFig1 技术形状差 ...", flush=True); fig1_shape(raw_sh, loc_sh)
    if "3" in figs:
        print("GridFig3 双机制连续散点 ...", flush=True); fig3_scatter()
    if "2" in figs:
        print("GridFig2 最省钱≠配网友好 ...", flush=True); fig2_costgrid(raw_sh, loc_sh)
    if "4" in figs:
        print("GridFig4 全国地理 ...", flush=True); fig4_geography()
    if "5" in figs:
        print("GridFig5 缓解决策 ...", flush=True)
        raw_g, loc_g = load_city("guangzhou", 23.13, 113.26, 20)
        fig5_mitigation(raw_g, loc_g, "Guangzhou")
    if "6" in figs:
        print("GridFig6 真潮流·接入容量vs弃光 ...", flush=True)
        fig6_hosting()
    print(f"\n完成。图/表在 {OUT}/")


if __name__ == "__main__":
    main()
