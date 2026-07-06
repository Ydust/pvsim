"""Portfolio v0: 三/四技术混合部署 2025-2050 最小化全生命周期碳。

决策变量: x[k, t] = 技术 k 在年份 t 新建容量 (GW); 共 4×26 = 104 个变量。
目标: 累计净 CO2 = 隐含碳 − 在运避碳 (考虑寿命和电网逐年脱碳)
约束:
  - 在运容量 >= 国家目标 (从 800 GW 线性增到 2400 GW 到 2050)
  - 年新建总量 ≤ 500 GW/yr (工业上限)
  - 各技术成熟度上限 (按可获得份额上界)
求解: scipy.optimize.linprog (HiGHS 后端)

运行: python -m scripts.portfolio_v0
输出: outputs/figures/28_portfolio_v0.png + 控制台关键数
"""

import sys
import os
import numpy as np
from scipy.optimize import linprog

from pvsim import viz
from pvsim.viz import plt

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ---- 设置 ----
YEARS = np.arange(2025, 2051)              # 26 年
N = len(YEARS)
TECHS = ["晶硅25y", "钙钛矿15y", "钙钛矿25y", "叠层"]
NK = len(TECHS)

LIFE = np.array([25, 15, 25, 25])           # 寿命 (年)
EF = np.array([0.50, 0.15, 0.18, 0.20])     # 隐含碳 kg/Wp = Mt/GW
YIELD = np.array([1400, 1470, 1470, 1520])  # 年发电 kWh/kWp

GRID_EF = np.linspace(0.58, 0.20, N)        # 电网逐年脱碳 0.58→0.20 kgCO2/kWh

TARGET = np.linspace(800, 2400, N)          # 在运目标 (GW)
MAX_NEW = 500                                # 年新建上限 (GW/yr)
INIT_FLEET = 387                            # 2024 末真实存量(GW), 来自GEM, 假设晶硅, 25年寿命平均装机于2018年, 2043起逐步退役


def avail(k, year):
    """技术 k 在年份 year 可占的最大新建份额 (0-1)。"""
    if k == 0:                              # 晶硅
        return 1.0
    if k == 1:                              # 钙钛矿 15y
        return max(0, min(0.9, (year - 2025) / 4.0))
    if k == 2:                              # 钙钛矿 25y (寿命达标)
        return max(0, min(0.7, (year - 2030) / 5.0))
    if k == 3:                              # 叠层
        return max(0, min(0.6, (year - 2030) / 5.0))
    return 0.0


def idx(k, t):
    return k * N + t


def main():
    viz.setup()
    nvars = NK * N

    # ---- 目标系数 c ----
    c = np.zeros(nvars)
    for k in range(NK):
        for t in range(N):
            embodied = EF[k]                          # Mt/GW
            avoided = 0.0
            for tt in range(t, min(t + int(LIFE[k]), N)):
                avoided += YIELD[k] * GRID_EF[tt] / 1e6   # MtCO2/yr per GW
            c[idx(k, t)] = embodied - avoided

    # ---- 不等式约束 A_ub x ≤ b_ub ----
    rows, b = [], []
    # 在运 ≥ 目标 → -在运 ≤ -target (减去存量贡献)
    for t in range(N):
        row = np.zeros(nvars)
        for k in range(NK):
            for tt in range(N):
                if tt <= t and tt + LIFE[k] > t:
                    row[idx(k, tt)] = -1
        # 存量贡献: 2018 投产平均, 2043 (=2018+25) 起退役; YEARS[t] < 2043 时 INIT 仍在运
        init_present = INIT_FLEET if YEARS[t] < 2043 else max(0, INIT_FLEET * (1 - (YEARS[t] - 2042) / 6))
        rows.append(row); b.append(-(TARGET[t] - init_present))
    # 年新建总量 ≤ MAX_NEW
    for t in range(N):
        row = np.zeros(nvars)
        for k in range(NK):
            row[idx(k, t)] = 1
        rows.append(row); b.append(MAX_NEW)

    A_ub = np.array(rows); b_ub = np.array(b)

    # ---- bound: 0 ≤ x[k,t] ≤ avail(k,t) × MAX_NEW ----
    bounds = []
    for k in range(NK):
        for t in range(N):
            bounds.append((0, avail(k, YEARS[t]) * MAX_NEW))

    print(f"求解 LP: {nvars} 变量, {len(rows)} 不等式约束")
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method="highs")
    if not res.success:
        print("失败:", res.message); return

    X = res.x.reshape(NK, N)               # 年新建 GW
    print(f"最小累计净 CO2 = {res.fun:.0f} Mt (注: 负数 = 净减排)")
    # 在运容量 (含存量)
    Op = np.zeros((NK + 1, N))
    for k in range(NK):
        for t in range(N):
            for tt in range(N):
                if tt <= t and tt + LIFE[k] > t:
                    Op[k, t] += X[k, tt]
    for t in range(N):
        init_present = INIT_FLEET if YEARS[t] < 2043 else max(0, INIT_FLEET * (1 - (YEARS[t] - 2042) / 6))
        Op[NK, t] = init_present

    # ---- 绘图 ----
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.2))
    colors = ["#1f6fb2", "#e2641e", "#f7b27e", "#2a9d4a"]

    ax1.stackplot(YEARS, X, labels=TECHS, colors=colors, alpha=0.85)
    ax1.plot(YEARS, X.sum(axis=0), "k--", lw=1, label="年新建合计")
    ax1.set_xlabel("年"); ax1.set_ylabel("年新建容量 (GW)")
    ax1.set_title("最优年新建结构")
    ax1.legend(fontsize=8, loc="upper left"); ax1.grid(alpha=0.3)

    ax2.stackplot(YEARS, Op, labels=TECHS + ["存量(2024晶硅)"],
                  colors=colors + ["#888888"], alpha=0.85)
    ax2.plot(YEARS, TARGET, "k--", lw=1.5, label="国家目标")
    ax2.set_xlabel("年"); ax2.set_ylabel("在运容量 (GW)")
    ax2.set_title("最优在运结构 vs 目标")
    ax2.legend(fontsize=8, loc="upper left"); ax2.grid(alpha=0.3)

    fig.suptitle(f"中国光伏 2025-2050 最优技术组合 (LP v0)  -  累计净 CO2 = {res.fun:.0f} Mt",
                 fontweight="bold")
    fig.tight_layout()
    os.makedirs("outputs/figures", exist_ok=True)
    fig.savefig("outputs/figures/28_portfolio_v0.png", dpi=130)
    plt.close(fig)
    print("已生成 outputs/figures/28_portfolio_v0.png")

    # 简表
    print("\n各技术 2025-2050 累计新建 (GW):")
    for k, name in enumerate(TECHS):
        print(f"  {name}: {X[k].sum():.0f} GW")


if __name__ == "__main__":
    main()
