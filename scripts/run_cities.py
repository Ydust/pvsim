"""中国代表城市运行测试：用 PVGIS 真实气象(TMY)对比晶硅 vs 钙钛矿。

含: 年比发电量/性能比、钙钛矿优势随温度变化、以及逐城 LCOE(含多年衰减)。
运行: python -m scripts.run_cities   (首次联网拉取, 之后用 data/tmy_cache 缓存)
输出: outputs/cities_comparison.csv, outputs/figures/11_cities.png, 12_cities_lcoe.png
"""

import sys

import numpy as np
import pandas as pd

from pvsim import viz
from pvsim.viz import plt, color
from pvsim.materials import CSI_EARLY, PEROVSKITE
from pvsim.cities import CITIES
from pvsim import weather as wx
from pvsim.system import SystemConfig, simulate
from pvsim.lcoe import lcoe

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PERO_SCENARIO = "代表性"   # 钙钛矿衰减情景


def run_one(city):
    w = wx.from_pvgis_tmy(city.lat, city.lon, altitude=city.alt, name=city.key)
    cfg = SystemConfig(n_modules=20)
    res = {t.name: simulate(t, w, cfg, npts=90) for t in (CSI_EARLY, PEROVSKITE)}

    # 辐照加权平均电池温度
    ts = res["c-Si"]["timeseries"]
    poa = ts["poa_global"].to_numpy(); tcell = ts["tcell"].to_numpy()
    m = poa > 50
    tcell_w = float(np.average(tcell[m], weights=poa[m])) if m.any() else float("nan")

    rc, rp = res["c-Si"], res["perovskite"]
    lc = lcoe(CSI_EARLY, rc["kwp"], rc["energy_ac_kwh"])
    lp = lcoe(PEROVSKITE, rp["kwp"], rp["energy_ac_kwh"], PERO_SCENARIO)

    return {
        "城市": city.name, "纬度": city.lat, "海拔m": city.alt,
        "年均气温": round(float(w["temp_air"].mean()), 1),
        "加权电池温": round(tcell_w, 1),
        "年GHI": round(float(w["ghi"].sum() / 1000.0), 0),
        "晶硅比发电": round(rc["specific_yield"], 0),
        "钙钛矿比发电": round(rp["specific_yield"], 0),
        "钙钛矿优势%": round((rp["specific_yield"] / rc["specific_yield"] - 1) * 100, 1),
        "晶硅PR": round(rc["performance_ratio"], 3),
        "钙钛矿PR": round(rp["performance_ratio"], 3),
        "晶硅LCOE分": round(lc["lcoe"] * 100, 2),
        "钙钛矿LCOE分": round(lp["lcoe"] * 100, 2),
        "LCOE比(钙/晶)": round(lp["lcoe"] / lc["lcoe"], 2),
    }


def fig_yield(df):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    x = np.arange(len(df)); bw = 0.4
    ax1.bar(x - bw / 2, df["晶硅比发电"], bw, color=color("c-Si"), label="早期晶硅")
    ax1.bar(x + bw / 2, df["钙钛矿比发电"], bw, color=color("perovskite"), label="钙钛矿")
    ax1.set_xticks(x); ax1.set_xticklabels(df["城市"], rotation=30, ha="right")
    ax1.set_ylabel("年比发电量 (kWh/kWp)")
    ax1.set_title("各城市年发电量 (真实气象 TMY)"); ax1.legend()
    for i, v in enumerate(df["钙钛矿优势%"]):
        ax1.annotate(f"+{v:.0f}%", (x[i], max(df['晶硅比发电'][i], df['钙钛矿比发电'][i])),
                     ha="center", va="bottom", fontsize=8, color=color("perovskite"))

    ax2.scatter(df["加权电池温"], df["钙钛矿优势%"], s=80, color=color("perovskite"), zorder=3)
    for _, r in df.iterrows():
        ax2.annotate(r["城市"], (r["加权电池温"], r["钙钛矿优势%"]),
                     textcoords="offset points", xytext=(5, 4), fontsize=9)
    z = np.polyfit(df["加权电池温"], df["钙钛矿优势%"], 1)
    xx = np.linspace(df["加权电池温"].min(), df["加权电池温"].max(), 50)
    ax2.plot(xx, np.polyval(z, xx), "--", color="gray",
             label=f"趋势: 每升1°C优势 +{z[0]:.2f}%")
    ax2.set_xlabel("辐照加权平均电池温度 (°C)")
    ax2.set_ylabel("钙钛矿比发电优势 (%)")
    ax2.set_title("钙钛矿优势随运行温度上升而增大"); ax2.legend()
    fig.suptitle("中国代表城市运行测试：发电量与温度效应", fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    viz.save(fig, "outputs/figures/11_cities.png")


def fig_lcoe(df):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    x = np.arange(len(df)); bw = 0.4
    ax1.bar(x - bw / 2, df["晶硅LCOE分"], bw, color=color("c-Si"), label="早期晶硅")
    ax1.bar(x + bw / 2, df["钙钛矿LCOE分"], bw, color=color("perovskite"), label="钙钛矿(代表情景)")
    ax1.set_xticks(x); ax1.set_xticklabels(df["城市"], rotation=30, ha="right")
    ax1.set_ylabel("LCOE (分/kWh)")
    ax1.set_title("各城市度电成本 LCOE (含多年衰减)"); ax1.legend()

    # LCOE 比值随温度: 越接近1说明钙钛矿越接近晶硅
    ax2.scatter(df["加权电池温"], df["LCOE比(钙/晶)"], s=80, color=color("perovskite"), zorder=3)
    for _, r in df.iterrows():
        ax2.annotate(r["城市"], (r["加权电池温"], r["LCOE比(钙/晶)"]),
                     textcoords="offset points", xytext=(5, 4), fontsize=9)
    ax2.axhline(1.0, ls=":", color="gray", label="与晶硅持平线")
    ax2.set_xlabel("辐照加权平均电池温度 (°C)")
    ax2.set_ylabel("LCOE 比值 (钙钛矿 / 晶硅)")
    ax2.set_title("高温城市钙钛矿 LCOE 更接近晶硅"); ax2.legend()
    fig.suptitle("中国代表城市运行测试：度电成本对比", fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    viz.save(fig, "outputs/figures/12_cities_lcoe.png")


def main():
    viz.setup()
    rows = []
    for c in CITIES:
        print(f"  {c.name} ({c.note}) ...", flush=True)
        rows.append(run_one(c))
    df = pd.DataFrame(rows).sort_values("加权电池温").reset_index(drop=True)
    df.to_csv("outputs/cities_comparison.csv", index=False, encoding="utf-8-sig")
    print("\n" + df.to_string(index=False))
    fig_yield(df)
    fig_lcoe(df)
    print("\n已保存 outputs/cities_comparison.csv 及 figures/11_cities.png, 12_cities_lcoe.png")


if __name__ == "__main__":
    main()
