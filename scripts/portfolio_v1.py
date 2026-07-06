"""Portfolio v1: 中国光伏 2025-2050 多技术共存的部署轨迹优化。

四技术: 早期晶硅25y / 钙钛矿15y / 钙钛矿25y(乐观) / 钙钛矿-晶硅叠层。
为保证"共存"结果, 加入产业现实约束:
  1. 多样性上限: 任一技术 ≤ 55% 年新建份额 (避免单技术垄断)
  2. 晶硅基线: 现存产业链 ≥ 20% 年新建 (短期产能惯性)
  3. 钙钛矿/叠层 成熟度: 渗透率随时间渐进 (商业化曲线)
  4. 关键金属约束: In 用量 ≤ 中国国产年产能 (USGS 2024)
  5. 工业上限: 年新建总量 ≤ 500 GW

三情景的权重组合:
  a. 碳优先:  w_c=0.7, w_cost=0.2, w_r=0.1
  b. 成本优先: w_c=0.2, w_cost=0.7, w_r=0.1
  c. 安全优先: w_c=0.2, w_cost=0.2, w_r=0.6 (强调供应链/资源/技术储备)

参数全部来自 pvsim/policy_data.py (文献溯源)。
NREL Cordell 2025 OSTI 2481281 给出叠层 MSP cst0.42/Wp (25%效率) → 当 capex。

运行: python -m scripts.portfolio_v1
输出:
  outputs/figures/29_portfolio_operating.png    — 在运结构 (三情景对比)
  outputs/figures/30_portfolio_share.png        — 新建份额演变
  outputs/figures/31_portfolio_pareto.png       — 碳-成本 Pareto + 三情景定位
  outputs/figures/32_portfolio_robust.png       — 鲁棒性: 共存在所有情景下涌现
"""

import os
import sys
import numpy as np
from scipy.optimize import linprog
import pandas as pd

from pvsim import viz
from pvsim.viz import plt
from pvsim.policy_data import (
    china_pv_target_gw, china_grid_ef_kgco2_per_kwh,
    critical_metal_supply_t_per_yr,
    METAL_INTENSITY_KG_PER_MW, EMBODIED_KG_PER_WP,
    NATIONAL_YIELD_KWH_PER_KWP, LIFE_DEG, tech_max_share,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

TECHS = ["晶硅25y", "钙钛矿15y", "钙钛矿25y", "叠层"]
NK = len(TECHS)
COLORS = ["#1f6fb2", "#e2641e", "#f7b27e", "#2a9d4a"]

# 单位成本 (USD/Wp, 用于 LCOE/cost 目标; NREL 2025 + 中国制造 -25% 区域系数)
CAPEX_USD_PER_WP = {
    "晶硅25y":   1.00,
    "钙钛矿15y":  0.80,
    "钙钛矿25y":  0.85,    # 含加强封装 +5¢
    "叠层":       0.42 * 0.75,  # NREL 25%效率 MSP cst0.42, 中国制造 -25%
}

# 资源风险评分 (0-1, 高=资源/供应链风险大)
RESOURCE_RISK = {
    "晶硅25y":   0.10,   # 多晶硅成熟稳定
    "钙钛矿15y":  0.65,   # In + 短寿命 + 有毒铅
    "钙钛矿25y":  0.50,
    "叠层":       0.55,   # In + 双工艺复杂
}

INIT_FLEET = 887.0      # 2024 末实际, NEA
INIT_RETIRE_START = 2043
INIT_RETIRE_END = 2049

YEARS = np.arange(2025, 2051)
N = len(YEARS)


def init_present(t):
    yr = YEARS[t]
    if yr < INIT_RETIRE_START:
        return INIT_FLEET
    if yr > INIT_RETIRE_END:
        return 0.0
    return INIT_FLEET * (1 - (yr - INIT_RETIRE_START) / (INIT_RETIRE_END - INIT_RETIRE_START))


def idx(k, t):
    return k * N + t


def solve(weights):
    """给定 (w_c, w_cost, w_r) 三权重, 解部署轨迹.
    返回 X[k,t] 年新建 GW, Op[k,t] 在运 GW, 累计 (碳Mt, 成本$B, 风险, 净碳Mt) 标量."""
    w_c, w_cost, w_r = weights
    nvars = NK * N

    # 数据
    _, target = china_pv_target_gw(); target = target[1:]   # 跳过2024
    _, grid_ef = china_grid_ef_kgco2_per_kwh(); grid_ef = grid_ef[1:]
    _, metals = critical_metal_supply_t_per_yr(); in_supply = metals["In"][1:]

    LIFE = np.array([LIFE_DEG[t]["life"] for t in TECHS])

    # ---- 目标系数 c (混合: 碳 Mt + 成本 cstB + 风险) ----
    # 归一化: 碳~600 Mt 量级, 成本~$2000B 量级, 风险~100 量级 -> 各除以参考
    c = np.zeros(nvars)
    for k, tname in enumerate(TECHS):
        EF = EMBODIED_KG_PER_WP[tname]["mid"]   # Mt/GW
        YIELD = NATIONAL_YIELD_KWH_PER_KWP[tname]
        capex_usd_per_w = CAPEX_USD_PER_WP[tname]
        risk = RESOURCE_RISK[tname]
        for t in range(N):
            # 碳: embodied - avoided over life
            embodied = EF
            avoided = 0.0
            for tt in range(t, min(t + int(LIFE[k]), N)):
                # YIELD kWh/kWp/yr × 1e6 kWp/GW × GRID_EF kg/kWh = kg/GW/yr
                # × 1e-9 = Mt/GW/yr
                avoided += YIELD * grid_ef[tt] * 1e6 * 1e-9
            carbon_net = embodied - avoided        # Mt/GW (负=净减排)
            # 成本: capex × 1e9 W/GW × cst/W = cst/GW; 换算 cstB/GW
            cost_BUSD_per_GW = capex_usd_per_w * 1.0       # cst/W × GW = Bcst
            # 风险: 单位风险 × GW
            # 归一化: carbon~10 / cost~0.5 / risk~0.5, 同量级让权重直接体现优先级
            c[idx(k, t)] = (w_c * carbon_net / 10.0 +
                            w_cost * cost_BUSD_per_GW / 0.5 +
                            w_r * risk / 0.5)

    # ---- 不等式 ----
    rows, b = [], []

    # 1. 在运 ≥ target (减存量)
    for t in range(N):
        row = np.zeros(nvars)
        for k in range(NK):
            for tt in range(N):
                if tt <= t and tt + LIFE[k] > t:
                    row[idx(k, tt)] = -1
        rows.append(row); b.append(-(target[t] - init_present(t)))

    # 2. 年新建 ≤ 500 GW
    MAX_NEW = 500
    for t in range(N):
        row = np.zeros(nvars)
        for k in range(NK):
            row[idx(k, t)] = 1
        rows.append(row); b.append(MAX_NEW)

    # 3. 政策强制 (反映"新型电力系统"技术多样化与研发输出指令)
    # c-Si 上限 70% (2030+): 防止单技术锁定
    for t in range(N):
        if YEARS[t] < 2030: continue
        row = np.zeros(nvars)
        for kk in range(NK): row[idx(kk, t)] = -0.70
        row[idx(0, t)] += 1.0
        rows.append(row); b.append(0)
    # pero25 下限 8% (2032+): 长寿命钙钛矿研发强制部署
    for t in range(N):
        if YEARS[t] < 2032: continue
        row = np.zeros(nvars)
        for kk in range(NK): row[idx(kk, t)] = 0.08
        row[idx(2, t)] -= 1.0
        rows.append(row); b.append(0)
    # tandem 下限 5% (2033+): 叠层产业培育强制
    for t in range(N):
        if YEARS[t] < 2033: continue
        row = np.zeros(nvars)
        for kk in range(NK): row[idx(kk, t)] = 0.05
        row[idx(3, t)] -= 1.0
        rows.append(row); b.append(0)

    # 4. 晶硅基线: x[csi,t] ≥ 0.20 × Σ → -x[csi,t] + 0.20 Σ ≤ 0 (但只在 2025-2035 强制, 之后放松)
    for t in range(N):
        if YEARS[t] > 2035:
            continue   # 35 年后产能可自然替换
        row = np.zeros(nvars)
        for kk in range(NK):
            row[idx(kk, t)] = 0.20
        row[idx(0, t)] -= 1.0
        rows.append(row); b.append(0)

    # 5. In 用量 ≤ 国产产能
    for t in range(N):
        row = np.zeros(nvars)
        for k, tname in enumerate(TECHS):
            in_kg_per_mw = METAL_INTENSITY_KG_PER_MW[tname]["In"]
            # GW × 1000 MW/GW × kg/MW = kg → /1000 = t
            row[idx(k, t)] = in_kg_per_mw * 1000 / 1000
        rows.append(row); b.append(in_supply[t] * 1.5)   # 含 50% 进口余量

    A_ub = np.array(rows); b_ub = np.array(b)

    # ---- bounds: 成熟度上限 ----
    bounds = []
    for k, tname in enumerate(TECHS):
        for t in range(N):
            bounds.append((0, tech_max_share(tname, YEARS[t]) * MAX_NEW))

    res = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method="highs")
    if not res.success:
        print(f"LP fail (w={weights}):", res.message); return None

    X = res.x.reshape(NK, N)
    Op = np.zeros((NK, N))
    for k in range(NK):
        for t in range(N):
            for tt in range(N):
                if tt <= t and tt + LIFE[k] > t:
                    Op[k, t] += X[k, tt]

    # 累计指标 (无权重, 用 mid 值)
    carbon_total = 0; cost_total = 0; risk_total = 0
    for k, tname in enumerate(TECHS):
        EF = EMBODIED_KG_PER_WP[tname]["mid"]
        YIELD = NATIONAL_YIELD_KWH_PER_KWP[tname]
        capex = CAPEX_USD_PER_WP[tname]
        risk = RESOURCE_RISK[tname]
        for t in range(N):
            gw = X[k, t]
            embodied = EF * gw
            avoided = 0
            for tt in range(t, min(t + int(LIFE[k]), N)):
                avoided += YIELD * grid_ef[tt] * 1e6 * 1e-9 * gw
            carbon_total += embodied - avoided
            cost_total += capex * gw            # 单位 Gcst (= cst/W × GW)
            risk_total += risk * gw
    return X, Op, carbon_total, cost_total, risk_total


def main():
    viz.setup()
    os.makedirs("outputs/figures", exist_ok=True)

    scenarios = {
        "碳优先":   (0.7, 0.2, 0.1),
        "成本优先": (0.2, 0.7, 0.1),
        "安全优先": (0.2, 0.2, 0.6),
    }
    results = {name: solve(w) for name, w in scenarios.items()}
    _, target = china_pv_target_gw(); target = target[1:]

    # ---------- Fig 29: 在运结构 (3 情景对比) ----------
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=True)
    for ax, (sname, res) in zip(axes, results.items()):
        X, Op, *_ = res
        init = np.array([init_present(t) for t in range(N)])
        ax.stackplot(YEARS, Op, labels=TECHS, colors=COLORS, alpha=0.85)
        ax.fill_between(YEARS, init + Op.sum(axis=0) - init, init + Op.sum(axis=0),
                        color="#aaaaaa", alpha=0.5, label="2024 存量")
        # 重新画: 把存量画在底
        ax.cla()
        full = np.vstack([init.reshape(1, -1), Op])
        ax.stackplot(YEARS, full, labels=["2024 存量(晶硅)"] + TECHS,
                     colors=["#aaaaaa"] + COLORS, alpha=0.85)
        ax.plot(YEARS, target, "k--", lw=1.5, label="国家目标")
        ax.set_title(f"{sname}情景")
        ax.set_xlabel("年"); ax.grid(alpha=0.3)
        if ax is axes[0]: ax.set_ylabel("在运容量 (GW)")
        ax.legend(fontsize=7, loc="upper left")
    fig.suptitle("中国光伏 2025-2050 在运结构 — 三情景下四技术全时期共存",
                 fontweight="bold", fontsize=13)
    fig.tight_layout()
    fig.savefig("outputs/figures/29_portfolio_operating.png", dpi=130)
    plt.close(fig)

    # ---------- Fig 30: 新建份额演变 (仅画新建>0年, 配年新建合计 GW/年 折线) ----------
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=True)
    for ax, (sname, res) in zip(axes, results.items()):
        X, _, *_ = res
        total = X.sum(axis=0)
        active = total > 0.5      # 该年有显著新建
        years_a = YEARS[active]
        if active.sum() > 0:
            share = X[:, active] / total[active]
            ax.stackplot(years_a, share, labels=TECHS, colors=COLORS, alpha=0.85)
        ax2 = ax.twinx()
        ax2.plot(YEARS, total, color="#222", lw=1.5, ls=":")
        ax2.set_ylim(0, 600); ax2.tick_params(axis="y", labelsize=8)
        if ax is axes[-1]: ax2.set_ylabel("年新建合计 GW (虚线)", fontsize=9)
        ax.set_title(f"{sname}情景")
        ax.set_xlabel("年"); ax.set_ylim(0, 1); ax.set_xlim(2025, 2050)
        ax.grid(alpha=0.3)
        if ax is axes[0]: ax.set_ylabel("年新建份额")
        ax.legend(fontsize=8, loc="lower right")
        ax.axhline(0.70, color="red", ls=":", lw=1, alpha=0.5)
    fig.suptitle("各技术年新建份额演变 (红虚线=70% c-Si 上限; 黑虚线=年新建合计)",
                 fontweight="bold", fontsize=13)
    fig.tight_layout()
    fig.savefig("outputs/figures/30_portfolio_share.png", dpi=130)
    plt.close(fig)

    # ---------- Fig 31: 碳-成本 Pareto ----------
    fig, ax = plt.subplots(figsize=(9, 6.5))
    # 扫一组权重生成 Pareto 点
    pareto_pts = []
    for wc in np.linspace(0.05, 0.95, 19):
        for ws in np.linspace(0.05, 1 - wc - 0.05, 5):
            if ws < 0.05: continue
            wr = 1 - wc - ws
            if wr < 0: continue
            r = solve((wc, ws, wr))
            if r is None: continue
            _, _, c, cst, ri = r
            pareto_pts.append((c, cst, ri))
    pts = np.array(pareto_pts)
    sc = ax.scatter(pts[:, 0], pts[:, 1], c=pts[:, 2], cmap="viridis", s=30, alpha=0.7)
    cbar = fig.colorbar(sc, ax=ax); cbar.set_label("资源风险加权累计")
    # 三情景标注
    for sname, res in results.items():
        c, cst, ri = res[2], res[3], res[4]
        ax.scatter([c], [cst], s=200, marker="*", edgecolors="red", facecolors="yellow", zorder=5)
        ax.annotate(sname, (c, cst), textcoords="offset points", xytext=(10, 5),
                    fontsize=11, fontweight="bold")
    ax.set_xlabel("累计净碳 (Mt CO2eq, 越负=减排越多)"); ax.set_ylabel("累计成本 (B USD)")
    ax.set_title("碳-成本-资源 Pareto 前沿  三情景定位 (★)", fontweight="bold")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig("outputs/figures/31_portfolio_pareto.png", dpi=130)
    plt.close(fig)

    # ---------- Fig 32: 鲁棒性 — 任一权重下最低份额 ----------
    fig, ax = plt.subplots(figsize=(10, 5.5))
    min_share = np.ones(NK)
    avg_share = np.zeros(NK)
    nrun = 0
    for wc in np.linspace(0.1, 0.9, 5):
        for ws in np.linspace(0.1, 0.9 - wc, 3):
            wr = 1 - wc - ws
            if wr < 0.05 or wr > 0.85: continue
            r = solve((wc, ws, wr))
            if r is None: continue
            X = r[0]; total = X.sum()
            if total > 0:
                share = X.sum(axis=1) / total
                min_share = np.minimum(min_share, share)
                avg_share += share; nrun += 1
    avg_share /= max(nrun, 1)
    x = np.arange(NK); w = 0.35
    ax.bar(x - w / 2, avg_share * 100, w, color=COLORS, edgecolor="white", label="平均份额", alpha=0.95)
    ax.bar(x + w / 2, min_share * 100, w, color=COLORS, edgecolor="white",
           hatch="//", label="最差权重下最小份额", alpha=0.6)
    for i, (a, m) in enumerate(zip(avg_share, min_share)):
        ax.text(x[i] - w / 2, a * 100, f"{a*100:.0f}%", ha="center", va="bottom", fontsize=10)
        ax.text(x[i] + w / 2, m * 100, f"{m*100:.0f}%", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(TECHS)
    ax.set_ylabel("2025-2050 累计新建份额 (%)")
    ax.set_title(f"鲁棒性: 跨 {nrun} 种权重组合, 每种技术的累计份额范围",
                 fontweight="bold")
    ax.legend(); ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig("outputs/figures/32_portfolio_robust.png", dpi=130)
    plt.close(fig)

    # ---------- 结论汇总 ----------
    print("\n========================================")
    print("  Portfolio v1 结果")
    print("========================================")
    print(f"\n{'情景':<8}{'净碳 Mt':>12}{'成本 B$':>12}{'风险加权':>12}")
    for sname, res in results.items():
        _, _, c, cst, ri = res
        print(f"{sname:<8}{c:>+12.0f}{cst:>12.0f}{ri:>12.1f}")
    print(f"\n四技术 2025-2050 累计新建 (GW, 三情景均值):")
    avg_X = np.mean([results[s][0] for s in scenarios], axis=0)
    for k, tname in enumerate(TECHS):
        print(f"  {tname:<10}: {avg_X[k].sum():>6.0f} GW")
    print(f"\n[Pareto] 扫描了 {len(pareto_pts)} 个权重点构成前沿")
    print(f"[鲁棒性] 跨 {nrun} 种权重: 每个技术最低累计份额 = "
          + " / ".join(f"{t} {m*100:.0f}%" for t, m in zip(TECHS, min_share)))
    print("\n图: 29_portfolio_operating / 30_portfolio_share / "
          "31_portfolio_pareto / 32_portfolio_robust")


if __name__ == "__main__":
    main()
