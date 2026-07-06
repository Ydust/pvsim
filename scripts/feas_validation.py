"""#6 可行性: 孪生 vs 真实机队 —— 用各省/全国"利用小时数"(=kWh/kWp/年)做地面验证。

孪生算的是干净物理(含温度/光谱/IAM/逆变器), 不含: 弃光、积灰、停机、可用率等真实运维损失。
故孪生应**系统性高于**真实利用小时数, 差额≈真实系统损失(标准约 14-20%); 且**地理格局应吻合**。

真值表:
  - data/source_tables/provincial_fleet_hours_2024.csv
  - 格局: 西北最高, 西南/华中较低

运行: python -m scripts.feas_validation
"""

import sys
import numpy as np
import pandas as pd

from pvsim.provinces import PROVINCE_PV_2024_GW
from pvsim.source_data import load_fleet_hours

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

FLEET_HOURS = load_fleet_hours()


def main():
    y = pd.read_csv("outputs/province_physics_yield.csv", encoding="utf-8-sig")
    csi = y[y.tech == "晶硅"].set_index("province")          # 现代晶硅
    sy = csi["yield_kwh_per_kwp"]
    pr = csi["PR"] if "PR" in csi else None

    # 1) 全国量级
    tot = sum(PROVINCE_PV_2024_GW.values())
    nat = sum(sy[p]*PROVINCE_PV_2024_GW.get(p, 0)/tot for p in sy.index if p in PROVINCE_PV_2024_GW)
    national_fleet_hours = sum(
        FLEET_HOURS[p] * PROVINCE_PV_2024_GW.get(p, 0) / tot
        for p in FLEET_HOURS
    )
    print("=== 1. 全国量级 ===")
    print(f"孪生 全国装机加权 比发电 = {nat:.0f} kWh/kWp/年")
    print(f"真实 全国机队利用小时数 ≈ {national_fleet_hours:.0f} h/年")
    loss = (1 - national_fleet_hours/nat)*100
    print(f"-> 孪生高出 {nat-national_fleet_hours:.0f}, 隐含真实系统损失 {loss:.0f}% "
          f"(弃光+积灰+停机+可用率; 标准 PVsyst 损失约 14-20%) -> {'合理' if 8 <= loss <= 28 else '需查'}")
    if pr is not None:
        print(f"孪生 PR(性能比)范围 {pr.min():.2f}-{pr.max():.2f} (真实优良电站 ~0.80-0.85)")

    # 2) 地理格局相关性
    print("\n=== 2. 地理格局 (孪生 vs 省级利用小时数) ===")
    prov = [p for p in FLEET_HOURS if p in sy.index]
    tw = np.array([sy[p] for p in prov])
    re = np.array([FLEET_HOURS[p] for p in prov])
    r = np.corrcoef(tw, re)[0, 1]
    print(f"  {len(prov)} 省: r(孪生比发电, 利用小时数) = {r:.2f}")
    print(f"  孪生 比发电 范围 {tw.min():.0f}-{tw.max():.0f}; 真值范围 {re.min()}-{re.max()}")
    # 高/低各举几例
    order = np.argsort(-re)
    print("  最高几省:", ", ".join(f"{prov[i]}(孪{tw[i]:.0f}/真{re[i]})" for i in order[:3]))
    print("  最低几省:", ", ".join(f"{prov[i]}(孪{tw[i]:.0f}/真{re[i]})" for i in order[-3:]))

    print("\n=== 结论 ===")
    verdict = "可行 ✓" if (r >= 0.6 and 8 <= loss <= 28) else "需细化"
    print(f"{verdict}: 孪生地理格局与机队吻合(r={r:.2f}), 量级差≈真实系统损失({loss:.0f}%)。")
    print("下一步: 如需要多年均, 在源表中增加 year 与 source_url 后重新运行本脚本。")


if __name__ == "__main__":
    main()
