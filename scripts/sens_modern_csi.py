"""#1 敏感性: 把对照从'早期晶硅'换成'现代晶硅'(TOPCon/PERC), 看头条结论缩水多少.

现代晶硅目标: STC 组件效率 ~22%, γ_Pmax ~ -0.32 %/°C (TOPCon/PERC 代表).
自动标定 Ea_recomb(定 γ) 与 I_L_ref(定效率), 再重算:
  - 器件级: 效率/γ 四技对比 (含'单结钙钛矿 vs 现代晶硅'是否还更高效)
  - 系统级: perov / tandem 对 现代晶硅 的每 kWp 优势 (均值/范围/对辐照 r) vs 早期版
运行: python -m scripts.sens_modern_csi
"""

import sys
import numpy as np
import pandas as pd
from dataclasses import replace

from pvsim.materials import CSI_EARLY, PEROVSKITE, TANDEM_2T
from pvsim.cell import operating_point
from pvsim.module import module_pmp
from pvsim.provinces import PROVINCES
from pvsim import weather as wx
from pvsim.system import SystemConfig, simulate

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def gamma_pct(tech):
    p25 = module_pmp(tech, 800, 25, npts=60); p45 = module_pmp(tech, 800, 45, npts=60)
    return (p45/p25 - 1)/20*100


def stc_eff(tech):
    return operating_point(tech, 1000.0, 25.0, ns=tech.cells_in_series, npts=200).efficiency*100


def build_modern_csi(target_eff=22.0, target_gamma=-0.32):
    """从早期晶硅出发, 标定到现代 TOPCon/PERC 的效率与温度系数。"""
    # name 保持 "c-Si": 现代晶硅带隙/光谱响应同早期, 复用其光谱失配表 (spectral.py 按 name 查表)
    m = replace(CSI_EARLY, name="c-Si", name_cn="现代晶硅",
                I_L_ref=9.8,        # Jsc ~40 mA/cm² (vs 早期 33)
                I_o_ref=4.0e-10,    # 更高 Voc (更好钝化)
                R_s=0.0040, R_sh_ref=15.0, n_ideality=1.02,
                gamma_pmax_lit=target_gamma, degradation_rate=0.005, burn_in_loss=0.01)
    # 标定 Ea_recomb -> γ (γ 随 Ea 单调; 二分)
    lo, hi = 0.84, 1.10
    for _ in range(28):
        mid = (lo+hi)/2
        m = replace(m, Ea_recomb=mid)
        g = gamma_pct(m)
        if g < target_gamma:   # 太负 -> 降 Ea
            hi = mid
        else:
            lo = mid
    # 标定 I_L_ref -> 效率 (效率近似随 I_L 线性; 迭代几次)
    for _ in range(8):
        e = stc_eff(m)
        m = replace(m, I_L_ref=m.I_L_ref*target_eff/e)
    return m


def per_kwp(tech, w):
    return simulate(tech, w, SystemConfig(n_modules=20), npts=45)["specific_yield"]


def main():
    MOD = build_modern_csi()
    print("==== 器件级 (STC 效率 / γ_Pmax) ====")
    print(f"{'tech':<16}{'eff %':>8}{'γ %/°C':>10}")
    for t in [CSI_EARLY, MOD, PEROVSKITE, TANDEM_2T]:
        print(f"{t.name_cn:<16}{stc_eff(t):>8.1f}{gamma_pct(t):>10.2f}")
    dg_old = gamma_pct(PEROVSKITE)-gamma_pct(CSI_EARLY)
    dg_new = gamma_pct(PEROVSKITE)-gamma_pct(MOD)
    print(f"\nΔγ (perov - cSi):  早期 {dg_old:+.2f}  ->  现代 {dg_new:+.2f}   "
          f"(温度反转驱动力 ×{dg_new/dg_old:.2f})")

    # 系统级: 重算各省每 kWp 优势 (perov & tandem vs 现代晶硅)
    print("\n==== 系统级: 每 kWp 优势 (31 省) ====")
    yld = pd.read_csv("outputs/province_physics_yield.csv", encoding="utf-8-sig")
    ghi = yld[yld.tech == "晶硅"].set_index("province")["ghi_kwh_m2"]
    # 全部现算 (缓存的叠层用的是旧 γ; 此处用修正后 γ=-0.30)
    rows = []
    for p in PROVINCES:
        w = wx.from_pvgis_tmy(p.lat, p.lon, altitude=p.alt, name=p.key)
        rows.append({"province": p.name, "early": per_kwp(CSI_EARLY, w),
                     "mod": per_kwp(MOD, w), "per": per_kwp(PEROVSKITE, w),
                     "tan": per_kwp(TANDEM_2T, w)})
    df = pd.DataFrame(rows).set_index("province")
    pk_old, mod, pk_per, pk_tan = df["early"], df["mod"], df["per"], df["tan"]

    def summarize(label, pk_tech, base, tag):
        prov = [p for p in base.index if p in pk_tech.index and p in ghi.index]
        adv = np.array([(pk_tech[p]/base[p]-1)*100 for p in prov])
        g = np.array([ghi[p] for p in prov])
        r = np.corrcoef(g, adv)[0, 1]
        print(f"{label:<26}{adv.mean():>7.2f}{adv.min():>8.2f}{adv.max():>8.2f}{r:>8.2f}   {tag}")

    print(f"{'对比':<26}{'均值%':>7}{'最小':>8}{'最大':>8}{'r(辐照)':>8}")
    summarize("perov vs 早期晶硅", pk_per, pk_old, "(原文)")
    summarize("perov vs 现代晶硅", pk_per, mod, "(现实)")
    summarize("tandem vs 早期晶硅", pk_tan, pk_old, "(原文)")
    summarize("tandem vs 现代晶硅", pk_tan, mod, "(现实)")

    print("\n==== 一句话 ====")
    em, ep, et = stc_eff(MOD), stc_eff(PEROVSKITE), stc_eff(TANDEM_2T)
    print(f"现代晶硅 {em:.1f}% {'>' if em>ep else '<'} 单结钙钛矿 {ep:.1f}% "
          f"-> '单结钙钛矿效率更高'的说法{'不成立' if em>ep else '仍成立'}.")
    print(f"叠层 {et:.1f}% > 现代晶硅 {em:.1f}% -> 叠层 vs 现代晶硅的故事仍然成立.")


if __name__ == "__main__":
    main()
