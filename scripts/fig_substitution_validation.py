"""Main Fig 6 — 替代模型去玩具化 (Gap 2): 历史类比校准 + 蒙特卡洛不确定性.

钙钛矿无部署历史 → 无法直接校准. 故:
  (A) 用已发生的真实技术替代 (多晶→单晶硅, 2015-2023) 校准 softmax 分配机制,
      证明"LCOE merit-order + 学习曲线"能复现真实份额演化, 拟合温度参数 T.
  (B) 蒙特卡洛: 对 6 个不确定参数联合采样 1000 次, 给替代轨迹 P10/P50/P90 带,
      取代被审稿人诟病的 OAT 单因子灵敏度.
  (C) 明确定位: 模型是"经历史校准的情景探索工具", 不是点预测.

运行: python -m scripts.fig_substitution_validation
输出: outputs/figures/MainFig6_substitution_validation.png/.pdf
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from pvsim import viz
from pvsim.economic_priors import MC_DRAWS, MC_RANDOM_SEED, sample_mc_inputs
from pvsim.provinces import PROVINCE_PV_2024_GW
from pvsim.policy_data import china_pv_target_gw

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

COLORS = {"晶硅": "#1f6fb2", "钙钛矿": "#e2641e", "叠层": "#2a9d4a"}

# ============================================================
# (A) 历史: 多晶→单晶硅替代 2015-2023 (ITRPV / CPIA / PV InfoLink)
# ============================================================
HIST_YEARS = np.arange(2015, 2024)
# 单晶全球市占率 (ITRPV 2021/2023 路线图)
MONO_SHARE_OBS = np.array([0.24, 0.28, 0.35, 0.46, 0.62, 0.84, 0.92, 0.96, 0.98])
# 组件均价 $/W (PVInsights/ITRPV 年均)
MULTI_PRICE = np.array([0.57, 0.48, 0.37, 0.28, 0.23, 0.21, 0.25, 0.26, 0.18])
MONO_PRICE  = np.array([0.67, 0.55, 0.41, 0.30, 0.24, 0.21, 0.24, 0.25, 0.17])
# 量产效率 % (单晶 PERC→TOPCon 领先, 多晶停滞)
MULTI_EFF = np.array([15.8, 16.3, 17.0, 17.6, 18.2, 18.8, 19.2, 19.5, 19.8])
MONO_EFF  = np.array([16.5, 17.2, 18.3, 19.2, 20.3, 21.2, 22.0, 22.8, 23.3])

AREA_BOS = 45.0     # $/m^2 面积相关 BOS (支架/土地/线缆)
FIXED_BOS = 0.22    # $/W 固定 BOS (逆变器/并网)
DISCOUNT = 0.05
OPEX = 0.015
YIELD_REF = 1400.0  # kWh/kWp (LCOE 计算基准, 两技相同)


def system_lcoe(module_price, eff_pct, life=25, deg=0.007):
    """系统级 LCOE (分/kWh): 含面积 BOS (高效率→低面积成本)."""
    w_per_m2 = eff_pct * 10.0   # eff% → W/m^2 (STC 1000 W/m^2)
    sys_price = module_price + AREA_BOS / w_per_m2 + FIXED_BOS   # $/W
    crf = DISCOUNT * (1+DISCOUNT)**life / ((1+DISCOUNT)**life - 1)
    ann = YIELD_REF * (1 - life*deg/2) / 1000.0
    return sys_price * (crf + OPEX) / ann * 100   # 分/kWh


def calibrate_T():
    """拟合 softmax 温度 T: 由 LCOE 差复现单晶份额演化."""
    lc_multi = np.array([system_lcoe(MULTI_PRICE[i], MULTI_EFF[i])
                         for i in range(len(HIST_YEARS))])
    lc_mono = np.array([system_lcoe(MONO_PRICE[i], MONO_EFF[i])
                        for i in range(len(HIST_YEARS))])
    best_T, best_rmse, best_pred = None, 1e9, None
    for T in np.arange(0.05, 1.5, 0.01):
        w_mono = np.exp(-lc_mono / T)
        w_multi = np.exp(-lc_multi / T)
        pred = w_mono / (w_mono + w_multi)
        rmse = np.sqrt(np.mean((pred - MONO_SHARE_OBS) ** 2))
        if rmse < best_rmse:
            best_rmse, best_T, best_pred = rmse, T, pred
    ss_res = np.sum((best_pred - MONO_SHARE_OBS) ** 2)
    ss_tot = np.sum((MONO_SHARE_OBS - MONO_SHARE_OBS.mean()) ** 2)
    r2 = 1 - ss_res / ss_tot
    return best_T, best_rmse, r2, best_pred, lc_multi, lc_mono


# ============================================================
# (B) 前向替代模型 (蒙特卡洛用), 物理 yield 驱动
# ============================================================
YEARS = np.arange(2025, 2051)
NY = len(YEARS)
TECHS = ["晶硅", "钙钛矿", "叠层"]
CAPEX_0 = {"晶硅": 0.65, "钙钛矿": 0.95, "叠层": 1.13}
Q_0 = {"晶硅": 1500.0, "钙钛矿": 12.0, "叠层": 4.0}
INIT_FLEET = 887.0
ROW = 0.4


def nat_yield():
    df = pd.read_csv("outputs/province_physics_yield.csv", encoding="utf-8-sig")
    tot = sum(PROVINCE_PV_2024_GW.values())
    return {t: sum(r["yield_kwh_per_kwp"] * PROVINCE_PV_2024_GW.get(r["province"], 0) / tot
                   for _, r in df[df["tech"] == t].iterrows()) for t in TECHS}


def max_new(tech, yr):
    if tech == "晶硅": return 350
    if tech == "钙钛矿": return max(0, min(120, (yr-2024)*12))
    if tech == "叠层": return max(0, min(180, (yr-2028)*18))
    return 0


def init_present(yr):
    if yr < 2043: return INIT_FLEET
    if yr > 2049: return 0.0
    return INIT_FLEET * (1 - (yr-2043)/6)


# 外生全球新建轨迹 (GW/yr) — 驱动学习曲线, 反映 ROW 主导的产业爬坡,
# 与中国 merit-order 分配解耦 (中国不是钙钛矿/叠层学习的唯一推手).
def global_new_schedule():
    a = np.arange(NY)
    return {"晶硅": np.linspace(80, 30, NY) + np.linspace(0, 20, NY),
            "钙钛矿": np.minimum(a*4+5, 100.0),
            "叠层": np.maximum(0, np.minimum(a*3-12, 80.0))}


def capex_and_lcoe(yields, LR, floor, breakthrough, life_final=25.0):
    """外生学习: capex 由全球部署轨迹驱动. 钙钛矿寿命阶跃突破到 life_final.

    life_final < 25 表示寿命问题未完全解决 (真实不确定性核心).
    """
    B = {k: -np.log2(1-v) for k, v in LR.items()}
    sched = global_new_schedule()
    cum = {k: Q_0[k] for k in TECHS}; cap = dict(CAPEX_0)
    lcoe = {k: np.zeros(NY) for k in TECHS}
    # 突破后衰减率按寿命线性映射 (寿命越长衰减越低)
    deg_final = 0.030 + (life_final - 15) / 10 * (0.007 - 0.030)
    for i, yr in enumerate(YEARS):
        for k in TECHS:
            raw = max(floor[k], CAPEX_0[k]*(max(cum[k],0.1)/Q_0[k])**(-B[k]))
            cap[k] = raw if i == 0 else max(cap[k]*0.88, raw, floor[k])
            if k == "钙钛矿":
                if yr >= breakthrough:
                    life, deg = life_final, deg_final
                else:
                    life, deg = 15.0, 0.030
            else:
                life, deg = 25.0, (0.007 if k == "晶硅" else 0.012)
            crf = DISCOUNT*(1+DISCOUNT)**life/((1+DISCOUNT)**life-1)
            ann = yields[k]*(1-life*deg/2)/1000.0
            lcoe[k][i] = cap[k]*(crf+OPEX)/ann*100
        for k in TECHS:
            cum[k] += sched[k][i]*(1+ROW)
    return lcoe


def forward(yields, LR, floor, breakthrough, T, life_final=25.0):
    """capex/lcoe 外生 (解耦学习); softmax T 只管中国新建份额分配."""
    lcoe = capex_and_lcoe(yields, LR, floor, breakthrough, life_final)
    _, target = china_pv_target_gw(); target = target[1:]
    deploy = {k: np.zeros(NY) for k in TECHS}
    for i, yr in enumerate(YEARS):
        op = {k: sum(deploy[k][j] for j in range(i)
                     if yr-YEARS[j] < (15 if k=="钙钛矿" else 25)) for k in TECHS}
        need = max(0, target[i] - sum(op.values()) - init_present(yr))
        wts = {k: np.exp(-lcoe[k][i]/T) for k in TECHS if max_new(k, yr) > 0}
        s = sum(wts.values())
        tg = {k: need*wts[k]/s for k in wts}
        left = 0.0
        for k in TECHS:
            c = min(tg.get(k,0)+left, max_new(k, yr)); deploy[k][i] = c
            left += tg.get(k,0)-c
        for k in TECHS:
            if left > 0.5 and deploy[k][i] < max_new(k, yr):
                e = min(left, max_new(k, yr)-deploy[k][i]); deploy[k][i] += e; left -= e
    cross = next((int(YEARS[i]) for i in range(NY) if lcoe["钙钛矿"][i] < lcoe["晶硅"][i]), 2051)
    share = {k: deploy[k]/np.maximum(sum(deploy[t] for t in TECHS), 1e-9) for k in TECHS}
    return share, cross


def main():
    viz.setup_en()
    os.makedirs("outputs/figures", exist_ok=True)

    print("[A] historical analog calibration (multi->mono)...")
    T_fit, rmse, r2, pred, lc_multi, lc_mono = calibrate_T()
    print(f"  fitted T={T_fit:.2f} cents/kWh, RMSE={rmse*100:.1f}%, R2={r2:.3f}")

    print(f"[B] Monte Carlo {MC_DRAWS} runs...")
    yields = nat_yield()
    rng = np.random.default_rng(MC_RANDOM_SEED)
    cross_samples = []
    perov_share_2050 = []
    share_paths = {k: [] for k in TECHS}
    for _ in range(MC_DRAWS):
        LR, floor, bt, life_final, T = sample_mc_inputs(rng, T_fit)
        share, cross = forward(yields, LR, floor, bt, T, life_final)
        cross_samples.append(cross)
        perov_share_2050.append(share["钙钛矿"][-1]*100)
        for k in TECHS:
            share_paths[k].append(share[k]*100)
    cross_samples = np.array(cross_samples)
    for k in TECHS:
        share_paths[k] = np.array(share_paths[k])

    # ===== 出图 3 panel =====
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), dpi=300)

    # (a) 历史校准
    ax = axes[0]
    ax.plot(HIST_YEARS, MONO_SHARE_OBS*100, "o", color="black", ms=8,
            label="Mono share, observed (ITRPV)", zorder=4)
    ax.plot(HIST_YEARS, pred*100, "-", color="#e2641e", lw=2,
            label=f"softmax model (T={T_fit:.2f})", zorder=3)
    ax.set_xlabel("Year", fontsize=9); ax.set_ylabel("Mono-Si market share (%)", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.set_title("(a) Historical calibration: multi->mono", fontsize=11,
                 fontweight="bold", loc="left", pad=3)
    ax.text(0.05, 0.74, f"R$^2$ = {r2:.3f}\nRMSE = {rmse*100:.1f}%\n"
            "$\\rightarrow$ mechanism credible",
            transform=ax.transAxes, fontsize=8.5,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", lw=0.5))
    ax.legend(fontsize=7.5, loc="lower right", frameon=False)
    ax.grid(alpha=0.25, lw=0.3)

    # (b) Monte Carlo share fan
    ax = axes[1]
    EN = {"晶硅": "c-Si", "钙钛矿": "Perovskite", "叠层": "Tandem"}
    for k in TECHS:
        p10 = np.percentile(share_paths[k], 10, axis=0)
        p50 = np.percentile(share_paths[k], 50, axis=0)
        p90 = np.percentile(share_paths[k], 90, axis=0)
        ax.fill_between(YEARS, p10, p90, color=COLORS[k], alpha=0.2, linewidth=0)
        ax.plot(YEARS, p50, color=COLORS[k], lw=2, label=EN[k])
    ax.set_xlabel("Year", fontsize=9); ax.set_ylabel("Annual new-build share (%)", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.set_title(f"(b) Monte Carlo ({MC_DRAWS} runs): P10-P90 band", fontsize=11,
                 fontweight="bold", loc="left", pad=3)
    ax.legend(fontsize=7.5, loc="center right", frameon=False)
    ax.set_xlim(2025, 2050); ax.set_ylim(0, 100); ax.grid(alpha=0.25, lw=0.3)

    # (c) perovskite-beats-c-Si crossover-year distribution
    ax = axes[2]
    valid = cross_samples[cross_samples <= 2050]
    ax.hist(valid, bins=range(2026, 2046), color="#e2641e", alpha=0.8,
            edgecolor="black", linewidth=0.4)
    p10c, p50c, p90c = np.percentile(valid, [10, 50, 90]) if len(valid) else (0, 0, 0)
    for v, lab, c in [(p10c, "P10", "#2a9d4a"), (p50c, "P50", "black"),
                      (p90c, "P90", "#d62728")]:
        ax.axvline(v, color=c, ls="--", lw=1.2)
        ax.text(v, ax.get_ylim()[1]*0.92, f"{lab}\n{v:.0f}", fontsize=7,
                ha="center", color=c, fontweight="bold")
    ax.set_xlabel("Perovskite-beats-c-Si crossover year", fontsize=9)
    ax.set_ylabel("Frequency (/1000)", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.set_title("(c) Crossover-year uncertainty", fontsize=11, fontweight="bold",
                 loc="left", pad=3)
    ax.grid(alpha=0.25, lw=0.3, axis="y")

    fig.suptitle("Fig 6 — Substitution model: historical calibration (R$^2$=%.2f) + "
                 "Monte Carlo uncertainty (crossover P10-P90: %d-%d)"
                 % (r2, p10c, p90c), fontsize=12, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig("outputs/figures/MainFig6_substitution_validation.png", dpi=300,
                bbox_inches="tight")
    fig.savefig("outputs/figures/MainFig6_substitution_validation.pdf",
                bbox_inches="tight")
    plt.close(fig)
    print(f"\nMain Fig 6 saved.")
    print(f"  crossover year P10/P50/P90 = {p10c:.0f}/{p50c:.0f}/{p90c:.0f}")
    print(f"  perovskite 2050 share P10/P50/P90 = "
          f"{np.percentile(perov_share_2050,10):.0f}/"
          f"{np.percentile(perov_share_2050,50):.0f}/"
          f"{np.percentile(perov_share_2050,90):.0f}%")
    print(f"  never-substitutes (>2050) fraction: {np.mean(cross_samples>2050)*100:.1f}%")


if __name__ == "__main__":
    main()
