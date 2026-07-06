"""全国光伏"生命周期"动画：真实增长(2010-2024) + 外推退役 + 累计碳减排。

- 2010-2024: 真实投产年驱动装机增长(红=当年新增)。
- 2024 后: 冻结新增, 按寿命外推**退役潮**(晶硅25年为基准; 叠钙钛矿15年作对比虚线)。
- 全程: 在运机组发电替代电网 → **累计减排 CO2**逐年累积。
外推假设(图上标注): 电网排放因子0.58 tCO2/MWh, 年利用1300 kWh/kWp, 寿命 晶硅25/钙钛矿15年。
运行: python -m scripts.anim_pv_lifecycle   输出: outputs/animations/pv_lifecycle.gif (+ _peak.png)
"""

import os
import sys
import json

import numpy as np
import matplotlib.animation as animation

from pvsim import viz
from pvsim.viz import plt

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

GEO = r"C:/Users/yuanq/new/geojson"
ADM = "CHN_adm_shp__0__CHN_adm_shp.geojson"
SOLAR = "China_Solar_Power_Plants_GEM_202406__0__China_Solar_Power_Plants_GEM_202406.geojson"
OUT = "outputs/animations/pv_lifecycle.gif"
Y0, Y1, LAST_INSTALL = 2010, 2050, 2024
LIFE_CSI, LIFE_PERO = 25, 15
GRID_EF = 0.58            # tCO2/MWh
YIELD = 1300.0           # kWh/kWp/yr  -> 每GW年发电 1300 GWh
MT_PER_GW = YIELD * 1e3 * GRID_EF / 1e6   # Mt CO2 / (GW·yr) = 1300e3 MWh × 0.58 t/MWh /1e6
ASPECT = 1.0 / np.cos(np.radians(36))


def load(fn):
    with open(os.path.join(GEO, fn), encoding="utf-8-sig") as f:
        return json.load(f)


def num(x):
    try:
        return float(x)
    except Exception:
        return 0.0


def main():
    viz.setup()
    geom = load(ADM)["features"][0]["geometry"]
    polys = [np.array(p[0]) for p in (geom["coordinates"] if geom["type"] == "MultiPolygon"
                                      else [geom["coordinates"]])]
    lons, lats, caps, syr = [], [], [], []
    for ft in load(SOLAR)["features"]:
        p = ft["properties"]
        if p.get("Status") != "operating":
            continue
        g = ft.get("geometry") or {}
        if g.get("type") != "Point":
            continue
        try:
            y = int(float(p.get("Start_year")))
        except Exception:
            continue
        lon, lat = g["coordinates"][:2]
        if not (70 < lon < 140 and 15 < lat < 55 and 1990 <= y <= LAST_INSTALL):
            continue
        lons.append(lon); lats.append(lat); caps.append(max(num(p.get("Capacity__MW_")), 0.1)); syr.append(y)
    lons, lats, caps, syr = map(np.array, (lons, lats, caps, syr))
    ret_csi = syr + LIFE_CSI    # 退役年(晶硅)

    years = list(range(Y0, Y1 + 1))
    inst, oper, retc, retp, co2 = [], [], [], [], []
    cum = 0.0
    for Y in years:
        i_gw = caps[syr <= Y].sum() / 1000
        rc = caps[syr + LIFE_CSI <= Y].sum() / 1000
        rp = caps[syr + LIFE_PERO <= Y].sum() / 1000
        o = i_gw - rc
        cum += o * MT_PER_GW
        inst.append(i_gw); oper.append(o); retc.append(rc); retp.append(rp); co2.append(cum)

    fig, ax = plt.subplots(figsize=(12, 9))
    ax_cap = fig.add_axes([0.63, 0.46, 0.25, 0.20])
    ax_co2 = fig.add_axes([0.63, 0.15, 0.25, 0.20])

    def update(idx):
        Y = years[idx]
        ax.clear()
        for ext in polys:
            ax.fill(ext[:, 0], ext[:, 1], facecolor="#eef1f4", edgecolor="#8a939b", lw=0.5, zorder=1)
        installed = syr <= Y
        retired = ret_csi <= Y
        operating = installed & ~retired
        new = (syr == Y) & (Y <= LAST_INSTALL)
        retiring = ret_csi == Y
        # 已退役: 灰色幽灵
        ax.scatter(lons[installed & retired], lats[installed & retired],
                   s=3, c="#b9bfc6", alpha=0.30, edgecolors="none", zorder=2)
        # 在运: 橙
        ax.scatter(lons[operating], lats[operating], s=2 + 1.3 * np.sqrt(caps[operating]),
                   c="#ff9a3c", alpha=0.55, edgecolors="none", zorder=3)
        # 当年新增: 红 / 当年退役: 深灰描边
        ax.scatter(lons[new], lats[new], s=6 + 2.2 * np.sqrt(caps[new]),
                   c="#d62728", alpha=0.9, edgecolors="white", linewidths=0.2, zorder=5)
        ax.scatter(lons[retiring], lats[retiring], s=6 + 2.0 * np.sqrt(caps[retiring]),
                   c="#555", alpha=0.8, edgecolors="black", linewidths=0.3, zorder=4)
        ax.set_aspect(ASPECT); ax.set_xlim(72, 136); ax.set_ylim(16, 54)
        ax.set_xlabel("经度 °E"); ax.set_ylabel("纬度 °N"); ax.grid(alpha=0.2)
        phase = "真实增长" if Y <= LAST_INSTALL else "外推·退役潮(冻结新增)"
        ax.set_title(f"中国光伏全生命周期 · {Y} 年   [{phase}]\n"
                     f"在运 {oper[idx]:.0f} GW · 累计装机 {inst[idx]:.0f} · 已退役 {retc[idx]:.0f} GW"
                     f"   |   累计减排 CO₂ {co2[idx]/1000:.2f} Gt", fontweight="bold", fontsize=12)

        ax_cap.clear()
        ax_cap.plot(years[:idx + 1], inst[:idx + 1], color="#333", lw=1.6, label="累计装机")
        ax_cap.plot(years[:idx + 1], oper[:idx + 1], color="#2ca02c", lw=1.6, label="在运")
        ax_cap.plot(years[:idx + 1], retc[:idx + 1], color="#8c564b", lw=1.6, label="退役(晶硅25yr)")
        ax_cap.plot(years[:idx + 1], retp[:idx + 1], color="#8c564b", lw=1.2, ls="--", label="退役(钙钛矿15yr)")
        ax_cap.axvline(LAST_INSTALL, color="gray", ls=":", lw=0.8)
        ax_cap.set_xlim(Y0, Y1); ax_cap.set_ylim(0, max(inst) * 1.08)
        ax_cap.set_title("装机 / 在运 / 退役 (GW)", fontsize=9)
        ax_cap.tick_params(labelsize=7); ax_cap.grid(alpha=0.3); ax_cap.legend(fontsize=6, loc="upper left")

        ax_co2.clear()
        ax_co2.fill_between(years[:idx + 1], 0, np.array(co2[:idx + 1]) / 1000, color="#1f9e57", alpha=0.5)
        ax_co2.plot(years[:idx + 1], np.array(co2[:idx + 1]) / 1000, color="#1f7a44", lw=1.6)
        ax_co2.set_xlim(Y0, Y1); ax_co2.set_ylim(0, max(co2) / 1000 * 1.08)
        ax_co2.set_title("累计减排 CO₂ (Gt)", fontsize=9)
        ax_co2.tick_params(labelsize=7); ax_co2.grid(alpha=0.3)
        ax_co2.text(Y0 + 0.5, max(co2) / 1000 * 0.82, f"{co2[idx]/1000:.2f} Gt",
                    color="#1f7a44", fontweight="bold", fontsize=10)
        return []

    anim = animation.FuncAnimation(fig, update, frames=len(years), interval=420, blit=False)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    anim.save(OUT, writer=animation.PillowWriter(fps=2.4))
    update(len(years) - 1)
    fig.savefig(OUT.replace(".gif", "_peak.png"), dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"已生成 {OUT}  ({len(years)} 帧)")
    print(f"  2024: 在运{oper[years.index(2024)]:.0f}GW 累计减排{co2[years.index(2024)]/1000:.2f}Gt")
    print(f"  2050: 在运{oper[-1]:.0f}GW 累计退役(晶硅){retc[-1]:.0f}GW 累计减排{co2[-1]/1000:.2f}Gt")


if __name__ == "__main__":
    main()
