"""稳健性蒙卡: 多样化住户(随机朝向+负荷)下, 钙钛矿弃光惩罚是否稳健。

排除"20户同质同步"假象。先验证线性化潮流≈精确潮流, 再对每个馈线实现随机分配
住户朝向/负荷, 用向量化线性潮流算全年弃光, 给出惩罚的 P10–P90 分布。
运行: $env:PYTHONIOENCODING="utf-8"; python -m scripts.grid_robustness
输出: outputs/paper_grid/GridFig7_robustness.png, robustness.csv
"""

import sys
import os

import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from pvsim import viz
from pvsim.viz import plt, color
from pvsim import weather as wx, powerflow as pf
from pvsim.system import SystemConfig, simulate_rooftop
from pvsim.materials import get_technology
from pvsim import load as ld

OUT = "outputs/paper_grid"
CSI, PERO = get_technology("c-Si-modern"), get_technology("perovskite")
CFG = SystemConfig(n_modules=20, thermal_u0=20.0, thermal_u1=3.0)
AZIMUTHS = [120.0, 150.0, 180.0, 210.0, 240.0]      # ESE..S..WSW
AZ_W = np.array([0.1, 0.2, 0.4, 0.2, 0.1])           # 多数朝南
K_FIX = 6.0
VLIM, VSLACK = 1.05, 1.02
N_MC = 40
CITIES = [("shanghai", 31.23, 121.47, 10, "Shanghai"),
          ("haikou", 20.04, 110.32, 15, "Haikou")]


def az_profiles(tech, raw, loc, lat):
    """各朝向每 kWp 出力 (W/kWp) 字典。"""
    out = {}
    for az in AZIMUTHS:
        r = simulate_rooftop(tech, raw, loc, CFG, [(abs(lat), az, 20)])
        out[az] = (r["ac_power"] / r["kwp"]).to_numpy()
    return out


def curtail_total(fd, Rc, Xc, gen_house, load_house):
    """给定每户发电/负荷矩阵(house×T, kW), 算全年弃光(kWh, 全馈线)。"""
    nh = gen_house.shape[0]
    net = gen_house - load_house                     # kW/户, 倒送为正
    P = np.zeros((fd.n_bus, gen_house.shape[1]))
    P[1:nh + 1, :] = -net * 1000.0 / 3.0             # 注入→每相负的负荷 W
    v = pf.fast_voltage_pu(fd, P, np.zeros_like(P), VSLACK, Rc, Xc)
    vmax = v.max(axis=0)
    frac = np.clip((vmax - VLIM) / np.maximum(vmax - VSLACK, 1e-6), 0, 1)
    export_h = np.clip(net, 0, None).sum(axis=0)     # 全馈线倒送 kW
    return float((frac * export_h).sum())


def main():
    viz.setup_en()
    os.makedirs(OUT, exist_ok=True)
    vf = pf.validate_fast()
    print("线性化 vs 精确潮流: 末端 %.4f vs %.4f pu, 全网最大差 %.4f pu"
          % (vf["v_end_linear"], vf["v_end_exact"], vf["max_abs_diff_pu"]))

    fd = pf.build_lv_feeder(n_houses=20, span_m=400.0, s_rated_kva=250.0)
    Rc, Xc = pf.build_sensitivity(fd)
    rng = np.random.default_rng(7)
    rows = []
    dist = {}
    for key, lat, lon, alt, en in CITIES:
        raw = wx.from_pvgis_tmy(lat, lon, altitude=alt, name=key).tz_convert("Asia/Shanghai")
        loc = wx.get_location(lat, lon, tz="Asia/Shanghai", altitude=alt, name=en)
        load_shape = ld.load_profile(raw.index, daily_kwh=14.0, kind="residential",
                                     seasonal=True).to_numpy()
        prof = {"csi": az_profiles(CSI, raw, loc, lat),
                "pero": az_profiles(PERO, raw, loc, lat)}
        T = len(load_shape)

        # 同质朝南基线(对照)
        base = {}
        for tag in ("csi", "pero"):
            gen = np.tile(K_FIX * prof[tag][180.0] / 1000.0, (20, 1))
            ld_h = np.tile(load_shape, (20, 1))
            base[tag] = curtail_total(fd, Rc, Xc, gen, ld_h)
        base_pen = (base["pero"] / base["csi"] - 1) * 100

        # 蒙卡: 随机朝向+负荷
        pens = []
        for _ in range(N_MC):
            az_idx = rng.choice(len(AZIMUTHS), size=20, p=AZ_W)
            scale = rng.uniform(0.6, 1.5, size=20)
            ld_h = load_shape[None, :] * scale[:, None]
            cur = {}
            for tag in ("csi", "pero"):
                gen = np.stack([K_FIX * prof[tag][AZIMUTHS[i]] / 1000.0 for i in az_idx])
                cur[tag] = curtail_total(fd, Rc, Xc, gen, ld_h)
            pens.append((cur["pero"] / max(cur["csi"], 1e-9) - 1) * 100)
        pens = np.array(pens)
        dist[en] = pens
        p10, p50, p90 = np.percentile(pens, [10, 50, 90])
        rows.append(dict(city=en, base_identical=base_pen, p10=p10, p50=p50, p90=p90))
        print(f"  {en}: 同质基线 {base_pen:+.0f}% | 多样化 P10/中位/P90 = "
              f"{p10:+.0f}/{p50:+.0f}/{p90:+.0f}%  (n={N_MC})")

    pd.DataFrame(rows).to_csv(f"{OUT}/robustness.csv", index=False, encoding="utf-8-sig")

    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    for i, (en, pens) in enumerate(dist.items()):
        xj = i + (rng.uniform(-0.12, 0.12, len(pens)))
        ax.scatter(xj, pens, s=22, alpha=0.5, color=color("perovskite"), edgecolors="none")
        p10, p50, p90 = np.percentile(pens, [10, 50, 90])
        ax.plot([i, i], [p10, p90], color="k", lw=2, zorder=3)
        ax.plot(i, p50, "o", color="k", ms=8, zorder=4)
        bp = next(r["base_identical"] for r in rows if r["city"] == en)
        ax.plot(i, bp, "D", color="#378ADD", ms=9, zorder=4,
                label="Identical-south baseline" if i == 0 else None)
        ax.annotate(f"median {p50:+.0f}%", (i, p50), xytext=(12, 0),
                    textcoords="offset points", fontsize=9, va="center")
    ax.axhline(0, color="gray", lw=0.8)
    ax.set_xticks(range(len(dist))); ax.set_xticklabels(list(dist.keys()))
    ax.set(ylabel="Extra curtailment of perovskite vs c-Si (%)",
           title=f"Fig.7  Curtailment penalty is robust to household diversity "
                 f"(n={N_MC} feeders each)")
    ax.legend(frameon=False, loc="upper left")
    ax.set_ylim(bottom=0)
    fig.tight_layout(); viz.save(fig, f"{OUT}/GridFig7_robustness.png")
    print(f"\n完成。图/表在 {OUT}/")


if __name__ == "__main__":
    main()
