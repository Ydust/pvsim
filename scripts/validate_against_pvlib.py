"""pvsim 单二极管核心 vs pvlib calcparams_desoto + singlediode 一致性验证。

为 SoftwareX 工具论文准备的物理基线对照。在 4 个代表工况下对比 Pmp/Voc/Isc/FF。

对照前提：让两边的 I0(T) 法则对齐
  - pvsim 用 Ea_recomb 作为 I0(T) 激活能
  - pvlib De Soto 用 EgRef + dEgdT*(T-Tref) 修正 Eg(T)
  - 公平对照: 设 pvsim 的 Ea_recomb = X 同时设 pvlib EgRef = X, dEgdT = 0
                这样两边 I0(T) 完全同形, 偏差只反映 Lambert W 与数值精度。

运行: python -m scripts.validate_against_pvlib
"""

import sys
import numpy as np
import pvlib

from pvsim.materials import CSI_EARLY, PEROVSKITE
from pvsim.cell import operating_point

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

KB = 1.380649e-23
Q = 1.602176634e-19
TREF = 298.15


def compare(tech, label):
    ns = tech.cells_in_series
    a_ref = tech.n_ideality * ns * KB * TREF / Q   # 模组级 modified diode factor

    conditions = [
        ("STC",       1000.0, 25.0),
        ("热高辐照",   1000.0, 60.0),
        ("弱光",        200.0, 25.0),
        ("冷高辐照",   1200.0, -5.0),
    ]

    print(f"\n========== {label} (Ns={ns}, Ea_recomb={tech.Ea_recomb:.3f} eV) ==========")
    print(f"{'工况':<10}{'指标':<6}{'pvsim':>12}{'pvlib':>12}{'偏差 %':>12}")
    print("-" * 56)

    max_abs_pct = 0.0
    for cond, G, T in conditions:
        # pvsim
        op = operating_point(tech, G, T, effective_irradiance=G, ns=ns, npts=400)

        # pvlib (按 De Soto, 用 Ea_recomb 当 EgRef, dEgdT=0)
        IL, I0, Rs, Rsh, nNsVth = pvlib.pvsystem.calcparams_desoto(
            effective_irradiance=G, temp_cell=T,
            alpha_sc=tech.alpha_sc,
            a_ref=a_ref,
            I_L_ref=tech.I_L_ref,
            I_o_ref=tech.I_o_ref,
            R_sh_ref=tech.R_sh_ref * ns,
            R_s=tech.R_s * ns,
            EgRef=tech.Ea_recomb,
            dEgdT=0.0,
        )
        sd = pvlib.pvsystem.singlediode(
            photocurrent=IL, saturation_current=I0,
            resistance_series=Rs, resistance_shunt=Rsh, nNsVth=nNsVth,
        )

        for metric, ps, pl, unit in [
            ("Pmp", op.pmp, float(sd["p_mp"]), "W"),
            ("Voc", op.voc, float(sd["v_oc"]), "V"),
            ("Isc", op.isc, float(sd["i_sc"]), "A"),
            ("FF",  op.ff,  float(sd["p_mp"] / (sd["v_oc"] * sd["i_sc"])
                                 if sd["v_oc"] * sd["i_sc"] > 0 else 0), ""),
        ]:
            pct = (ps - pl) / pl * 100 if pl != 0 else 0
            max_abs_pct = max(max_abs_pct, abs(pct))
            print(f"{cond:<10}{metric:<6}{ps:>11.4f}{unit}{pl:>11.4f}{unit}{pct:>+11.4f}")
        print()

    print(f">>> {label} 最大绝对偏差: {max_abs_pct:.4f} %")
    return max_abs_pct


def main():
    err1 = compare(CSI_EARLY, "早期晶硅")
    err2 = compare(PEROVSKITE, "钙钛矿")
    print("\n========== 验证结论 ==========")
    print(f"晶硅最大偏差   : {err1:.4f} %")
    print(f"钙钛矿最大偏差 : {err2:.4f} %")
    overall = max(err1, err2)
    print(f"全局最大偏差   : {overall:.4f} %")
    if overall < 0.1:
        print("✓ 通过 (< 0.1%): pvsim 与 pvlib 数值一致, Lambert W 与 De Soto 平移均无明显误差")
    else:
        print("✗ 未通过, 检查 nNsVth 缩放或 I0(T) 法则对齐")


if __name__ == "__main__":
    main()
