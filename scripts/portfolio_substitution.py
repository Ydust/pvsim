"""技术替代动力学: Wright 学习曲线驱动的自然交班 2025-2050。

三技术: 早期晶硅 / 钙钛矿(寿命随时间从15→25年演化) / 钙钛矿-晶硅叠层。
机制: 每年按各技术当前 LCOE merit-order 分配新建; 累计装机推动学习曲线下降。
**没有强制下限**, 共存只在过渡带中自然涌现, 主线是替代。

学习曲线 (Wright/Henderson, 每翻一倍累计装机降本):
  晶硅:    LR 18% (成熟, 学习放缓)  | 起始全球累计 1500 GW
  钙钛矿:  LR 27% (陡峭学习段)       | 起始 2 GW
  叠层:    LR 30% (处女期)            | 起始 5 GW
寿命:
  晶硅 25y 衰减 0.5%/yr; 叠层 25y 0.5%/yr
  钙钛矿: 寿命 2025=15y, 线性演化至 LIFE_PEROV_BREAKTHROUGH_YEAR 达 25y
  关键灵敏度参数: 钙钛矿寿命突破年 (默认 2032)
运行: python -m scripts.portfolio_substitution
输出: outputs/figures/33_substitution_lcoe.png / 34_substitution_share.png
      / 35_substitution_operating.png / 36_substitution_sensitivity.png
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt

from pvsim import viz
from pvsim.policy_data import china_pv_target_gw

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

YEARS = np.arange(2025, 2051)
N = len(YEARS)
TECHS = ["晶硅", "钙钛矿", "叠层"]
COLORS = {"晶硅": "#1f6fb2", "钙钛矿": "#e2641e", "叠层": "#2a9d4a"}

# 学习率 (每翻倍降本比例)
LR = {"晶硅": 0.18, "钙钛矿": 0.27, "叠层": 0.30}
# Wright 指数 b: cost = cost_0 × (Q/Q_0)^(-b), b = -log2(1-LR)
B = {k: -np.log2(1 - v) for k, v in LR.items()}

# 起始系统级 capex ($/W) — 含组件 + BOS + 安装. 数据源:
#   c-Si: BNEF Q4 2024 中国 utility-scale weighted avg $0.62/W → 取 $0.65
#   钙钛矿: GCL/Microquanta 2024-2025 商业化目标 $0.95/W (含 BOS 溢价)
#   叠层: NREL Cordell 2025 (OSTI 2481281) cell MSP $0.428/W (25%) + 系统 BOS $0.70 = $1.13
CAPEX_0 = {"晶硅": 0.65, "钙钛矿": 0.95, "叠层": 1.13}

# 起始全球累计 (GW), 含 ROW 早期商业化估算
Q_0 = {"晶硅": 1500.0, "钙钛矿": 5.0, "叠层": 1.0}

# 学习曲线下限 — 系统级 (含 BOS), 非组件级
#   IEA-PVPS / Fraunhofer ISE 2050 长期 floor: c-Si $0.40, 钙钛矿 $0.40, 叠层 $0.50
CAPEX_FLOOR = {"晶硅": 0.40, "钙钛矿": 0.40, "叠层": 0.50}

# 年最大 capex 降幅 (反映 fab 爬坡 + 良率提升的 2-3 年滞后)
MAX_CAPEX_DROP_PER_YR = 0.12

# 年发电 (kWh/kWp, 全国均值, 跟效率成正比)
#   晶硅 20% / 钙钛矿 22% / 叠层 28% (商业化目标)
YIELD = {"晶硅": 1400, "钙钛矿": 1540, "叠层": 1960}

# 外生 ROW 年部署基线 (GW/yr) — 不依赖中国决策, 反映美/欧/印/中东独立部署
def row_baseline(tech, year):
    if tech == "晶硅": return 150.0     # ROW c-Si 持续部署
    if tech == "钙钛矿":
        return max(0, min(40, (year - 2024) * 4))   # ROW 跟随中国后 ~2 年
    if tech == "叠层":
        if year < 2029: return 0.0
        return max(0, min(20, (year - 2028) * 3))
    return 0.0

# 可获性 (年最大新建 GW, 反映工业产能渐进爬坡上限)
def max_new(tech, year):
    if tech == "晶硅":
        return 350
    if tech == "钙钛矿":
        return max(0, min(120, (year - 2024) * 12))   # 2025=12GW, 2030=72GW, 2035=120GW
    if tech == "叠层":
        return max(0, min(180, (year - 2028) * 18))   # 2029=18GW, 2034=108GW, 2038=180GW
    return 0

INIT_FLEET = 887.0
DISCOUNT = 0.05


def perov_life(year, breakthrough_year=2032):
    """钙钛矿寿命随年份从 15 线性演化到 25 (在突破年达到)。"""
    if year >= breakthrough_year:
        return 25.0
    if year <= 2025:
        return 15.0
    return 15.0 + (year - 2025) * (25.0 - 15.0) / (breakthrough_year - 2025)


def life_of(tech, year, breakthrough_year=2032):
    if tech == "钙钛矿":
        return perov_life(year, breakthrough_year)
    return 25.0


def deg_rate(tech, year, breakthrough_year=2032):
    """衰减率 /yr。钙钛矿在突破前 1%/yr, 之后降到 0.5%/yr。"""
    if tech == "钙钛矿":
        return 0.005 if year >= breakthrough_year else 0.010
    return 0.005


def capex(tech, Q):
    raw = CAPEX_0[tech] * (max(Q, 0.1) / Q_0[tech]) ** (-B[tech])
    return max(raw, CAPEX_FLOOR[tech])      # 学习曲线下限


def lcoe(tech, Q, year, breakthrough_year=2032):
    """简化 LCOE: capex × (CRF + opex) / 年净发电."""
    cap = capex(tech, Q)
    L = life_of(tech, year, breakthrough_year)
    deg = deg_rate(tech, year, breakthrough_year)
    crf = DISCOUNT * (1 + DISCOUNT) ** L / ((1 + DISCOUNT) ** L - 1)
    opex_rate = 0.015                                            # 年运维费占 capex
    annual_yield = YIELD[tech] * (1 - L * deg / 2) / 1000.0      # kWh/W
    return cap * (crf + opex_rate) / annual_yield                # $/kWh


def init_present(year):
    if year < 2043: return INIT_FLEET
    if year > 2049: return 0.0
    return INIT_FLEET * (1 - (year - 2043) / 6)


def simulate(breakthrough_year=2032):
    """前向模拟: 逐年按 LCOE merit-order 分配新建容量, 累计装机推动学习。"""
    _, target = china_pv_target_gw(); target = target[1:]   # 2025-2050

    deploy = {k: np.zeros(N) for k in TECHS}
    lcoe_path = {k: np.zeros(N) for k in TECHS}
    cum_global = {k: Q_0[k] for k in TECHS}   # 全球累计 (含 ROW)
    capex_eff = {k: CAPEX_0[k] for k in TECHS}   # 有滞后的实际 capex

    # ROW 跟中国走部分 (国际供应链联动)
    ROW_FACTOR = 0.4

    for i, yr in enumerate(YEARS):
        # 累计 → 原始 Wright 推断 capex
        raw_capex = {k: capex(k, cum_global[k]) for k in TECHS}
        # 应用年度降幅封顶 (反映 fab 滞后 + 良率爬坡)
        for k in TECHS:
            if i == 0:
                capex_eff[k] = raw_capex[k]
            else:
                min_allowed = capex_eff[k] * (1 - MAX_CAPEX_DROP_PER_YR)
                capex_eff[k] = max(min_allowed, raw_capex[k], CAPEX_FLOOR[k])

        # 当前 LCOE (用滞后后的有效 capex)
        lcs = {}
        for k in TECHS:
            cap = capex_eff[k]
            L = life_of(k, yr, breakthrough_year)
            deg = deg_rate(k, yr, breakthrough_year)
            crf = DISCOUNT * (1 + DISCOUNT) ** L / ((1 + DISCOUNT) ** L - 1)
            annual_yield = YIELD[k] * (1 - L * deg / 2) / 1000.0
            lcs[k] = cap * (crf + 0.015) / annual_yield
            lcoe_path[k][i] = lcs[k] if max_new(k, yr) > 0 else np.nan

        # 在运容量 (按寿命扣除已退役)
        op = {k: 0.0 for k in TECHS}
        for k in TECHS:
            for j in range(i):
                inst_yr = YEARS[j]
                L = life_of(k, inst_yr, breakthrough_year)
                if yr - inst_yr < L:
                    op[k] += deploy[k][j]

        current_op_total = sum(op.values()) + init_present(yr)
        needed = max(0, target[i] - current_op_total)

        # Softmax 分配 (温度参数反映市场异质性 + 示范项目)
        # 价格差越小越平均, 越大越向便宜技术倾斜
        T = 0.008    # $/kWh = 0.8分/kWh, 严格 merit order, 但保留少量异质性
        weights = {k: np.exp(-lcs[k] / T) for k in TECHS if max_new(k, yr) > 0}
        wsum = sum(weights.values())
        targets = {k: needed * weights[k] / wsum for k in weights}
        # 受 max_new 上限约束, 溢出量再分配给未饱和技术
        leftover = 0.0
        for k in TECHS:
            cap = min(targets.get(k, 0) + leftover, max_new(k, yr))
            deploy[k][i] = cap
            leftover += targets.get(k, 0) - cap
        for k in TECHS:
            if leftover > 0.5 and deploy[k][i] < max_new(k, yr):
                extra = min(leftover, max_new(k, yr) - deploy[k][i])
                deploy[k][i] += extra; leftover -= extra

        # 更新全球累计:
        #   中国新建 + ROW 联动新建 (跟中国) + ROW 外生基线 (独立)
        for k in TECHS:
            row_followed = deploy[k][i] * ROW_FACTOR
            row_indep = row_baseline(k, yr)
            cum_global[k] += deploy[k][i] + row_followed + row_indep

    # 重新算在运
    operating = {k: np.zeros(N) for k in TECHS}
    for k in TECHS:
        for i in range(N):
            for j in range(i + 1):
                inst_yr = YEARS[j]
                L = life_of(k, inst_yr, breakthrough_year)
                if YEARS[i] - inst_yr < L:
                    operating[k][i] += deploy[k][j]

    # 交叉年 = 年新建份额超过对手的年份 (真正的"替代")
    cross = {}
    for src, dst in [("晶硅", "钙钛矿"), ("钙钛矿", "叠层")]:
        for i in range(N):
            if deploy[dst][i] > deploy[src][i] > 0:
                cross[f"{dst}新建超{src}"] = int(YEARS[i]); break
    return deploy, operating, lcoe_path, cross


def main():
    viz.setup()
    os.makedirs("outputs/figures", exist_ok=True)

    deploy, operating, lcoe_path, cross = simulate(breakthrough_year=2032)
    _, target = china_pv_target_gw(); target = target[1:]

    # ---------- Fig 33: LCOE 演变 + 交叉点 ----------
    fig, ax = plt.subplots(figsize=(11, 6))
    for k in TECHS:
        ax.plot(YEARS, lcoe_path[k] * 100, lw=2.4, color=COLORS[k], label=f"{k} LCOE")
    # LCOE 交叉点 (后进技术 LCOE 首次低于晶硅) — 标注用
    lcoe_cross = {}
    for k in ("钙钛矿", "叠层"):
        for i in range(N):
            if (not np.isnan(lcoe_path[k][i]) and not np.isnan(lcoe_path["晶硅"][i])
                    and lcoe_path[k][i] < lcoe_path["晶硅"][i]):
                lcoe_cross[k] = int(YEARS[i]); break
    ymax = float(np.nanmax([np.nanmax(lcoe_path[k]) for k in TECHS])) * 100
    offsets = {"钙钛矿": 0.96, "叠层": 0.82}
    for k, yr in lcoe_cross.items():
        ax.axvline(yr, color=COLORS[k], ls=":", lw=1.2, alpha=0.65)
        ax.annotate(f"{k} LCOE\n首次低于晶硅\n{yr}",
                    xy=(yr, lcoe_path[k][int(yr - 2025)] * 100),
                    xytext=(yr + 1.5, ymax * offsets[k]),
                    fontsize=9, color=COLORS[k], fontweight="bold",
                    arrowprops=dict(arrowstyle="->", color=COLORS[k], lw=1, alpha=0.7),
                    bbox=dict(boxstyle="round,pad=0.3", fc="white",
                              ec=COLORS[k], alpha=0.9))
    ax.set_xlabel("年"); ax.set_ylabel("LCOE (分/kWh)")
    ax.set_title("各技术 LCOE 演变 (Wright 学习曲线驱动)",
                 fontweight="bold")
    ax.grid(alpha=0.3); ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig("outputs/figures/33_substitution_lcoe.png", dpi=130)
    plt.close(fig)

    # ---------- Fig 34: 年新建份额 S 曲线 ----------
    fig, ax = plt.subplots(figsize=(11, 6))
    total = sum(deploy[k] for k in TECHS)
    bottom = np.zeros(N)
    for k in TECHS:
        share = np.where(total > 0, deploy[k] / np.maximum(total, 1e-9), 0)
        ax.fill_between(YEARS, bottom, bottom + share * 100,
                        color=COLORS[k], alpha=0.85, label=k)
        bottom += share * 100
    for label, yr in cross.items():
        ax.axvline(yr, color="black", ls=":", lw=1.2)
        ax.text(yr, 92, label, fontsize=9, ha="left", fontweight="bold")
    ax.set_xlabel("年"); ax.set_ylabel("年新建份额 (%)")
    ax.set_ylim(0, 100); ax.set_xlim(2025, 2050)
    ax.set_title("技术替代 S 曲线 (年新建份额随时间)",
                 fontweight="bold")
    ax.legend(loc="center right"); ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig("outputs/figures/34_substitution_share.png", dpi=130)
    plt.close(fig)

    # ---------- Fig 35: 在运结构 ----------
    fig, ax = plt.subplots(figsize=(11, 6))
    init_series = np.array([init_present(yr) for yr in YEARS])
    layers = [init_series] + [operating[k] for k in TECHS]
    labels = ["2024 存量(晶硅)"] + TECHS
    colors_list = ["#aaaaaa"] + [COLORS[k] for k in TECHS]
    ax.stackplot(YEARS, layers, labels=labels, colors=colors_list, alpha=0.85)
    ax.plot(YEARS, target, "k--", lw=1.5, label="国家目标")
    for label, yr in cross.items():
        ax.axvline(yr, color="white", ls=":", lw=1.5, alpha=0.7)
    ax.set_xlabel("年"); ax.set_ylabel("在运容量 (GW)")
    ax.set_title("在运结构: 自然涌现的三技术稳定共存格局",
                 fontweight="bold")
    ax.legend(loc="upper left", fontsize=9); ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig("outputs/figures/35_substitution_operating.png", dpi=130)
    plt.close(fig)

    # ---------- Fig 36: 2D 灵敏度 — 钙钛矿产能爬坡速度 × 叠层入场年 ----------
    # 产能爬坡决定替代时机, 叠层入场年决定 2050 终态结构
    import scripts.portfolio_substitution as M

    def simulate_with(perov_ramp, tandem_start):
        """临时改 max_new, 跑模拟, 复原."""
        orig = M.max_new
        def mn(tech, year):
            if tech == "晶硅": return 350
            if tech == "钙钛矿":
                return max(0, min(perov_ramp*10, (year-2024)*perov_ramp))
            if tech == "叠层":
                return max(0, min(180, (year-tandem_start+1)*18))
            return 0
        M.max_new = mn
        d, op, lc, cr = M.simulate(2032)
        M.max_new = orig
        return d, op, lc, cr

    perov_ramps = [6, 9, 12, 15, 18]    # GW/yr 爬坡速度
    tandem_starts = [2027, 2029, 2032]
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    # (a) 替代年 vs 钙钛矿产能爬坡 (叠层固定 2029)
    cross_years = []; perov_shares = []; tandem_shares = []
    for pr in perov_ramps:
        d, op, _, cr = simulate_with(pr, 2029)
        cross_years.append(cr.get("钙钛矿新建超晶硅", None))
        tot50 = sum(op[k][-1] for k in TECHS) + init_present(YEARS[-1])
        perov_shares.append(op["钙钛矿"][-1] / tot50 * 100)
        tandem_shares.append(op["叠层"][-1] / tot50 * 100)
    ax = axes[0]
    valid = [(p, y) for p, y in zip(perov_ramps, cross_years) if y]
    if valid:
        ax.plot([v[0] for v in valid], [v[1] for v in valid],
                "o-", color=COLORS["钙钛矿"], lw=2.4, ms=11)
        for p, y in valid:
            ax.annotate(f"{y}", (p, y), textcoords="offset points",
                        xytext=(8, 6), fontsize=10, fontweight="bold",
                        color=COLORS["钙钛矿"])
    ax.axvline(12, color="black", ls=":", lw=1, alpha=0.5)
    ax.text(12.2, ax.get_ylim()[0]+0.5, "基线\n12 GW/yr",
            fontsize=8, color="black", alpha=0.6)
    ax.set_xlabel("钙钛矿年产能爬坡 (GW/yr)")
    ax.set_ylabel("钙钛矿新建超晶硅年")
    ax.set_title("(a) 替代年 vs 钙钛矿产能爬坡速度", fontweight="bold")
    ax.grid(alpha=0.3)

    # (b) 2050 在运份额 vs 叠层入场年 (钙钛矿爬坡固定 12)
    ax = axes[1]
    p2050 = []; t2050 = []; c2050 = []
    for ts in tandem_starts:
        d, op, _, _ = simulate_with(12, ts)
        tot50 = sum(op[k][-1] for k in TECHS) + init_present(YEARS[-1])
        c2050.append(op["晶硅"][-1] / tot50 * 100)
        p2050.append(op["钙钛矿"][-1] / tot50 * 100)
        t2050.append(op["叠层"][-1] / tot50 * 100)
    x = np.arange(len(tandem_starts))
    width = 0.27
    ax.bar(x - width, c2050, width=width, color=COLORS["晶硅"], alpha=0.85, label="晶硅")
    ax.bar(x, p2050, width=width, color=COLORS["钙钛矿"], alpha=0.85, label="钙钛矿")
    ax.bar(x + width, t2050, width=width, color=COLORS["叠层"], alpha=0.85, label="叠层")
    for i, v in enumerate(c2050): ax.text(i-width, v+1, f"{v:.0f}%", ha="center", fontsize=9)
    for i, v in enumerate(p2050): ax.text(i, v+1, f"{v:.0f}%", ha="center", fontsize=9)
    for i, v in enumerate(t2050): ax.text(i+width, v+1, f"{v:.0f}%", ha="center", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels([f"{ts}" for ts in tandem_starts])
    ax.set_xlabel("叠层产业化入场年")
    ax.set_ylabel("2050 在运份额 (%)")
    ax.set_title("(b) 2050 终态结构 vs 叠层入场年", fontweight="bold")
    ax.legend(loc="upper right"); ax.grid(alpha=0.3, axis="y")
    ax.set_ylim(0, max(max(p2050), max(t2050)) + 10)
    fig.suptitle("替代动力学灵敏度: 产业爬坡是核心约束, 叠层入场年决定终态格局",
                 fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig("outputs/figures/36_substitution_sensitivity.png", dpi=130)
    plt.close(fig)

    # ---------- 数字总结 ----------
    print("\n========== 技术替代动力学 (基线: 钙钛矿寿命2032达标) ==========")
    print(f"\n交叉年:")
    for k, v in cross.items(): print(f"  {k}: {v}")
    print(f"\n2025-2050 累计中国新建 (GW):")
    for k in TECHS: print(f"  {k:<6}: {deploy[k].sum():>6.0f}")
    print(f"\n2050 在运份额 (%):")
    tot50 = sum(operating[k][-1] for k in TECHS) + init_present(YEARS[-1])
    for k in TECHS:
        print(f"  {k:<6}: {operating[k][-1]/tot50*100:>5.1f}%")
    print(f"\nLCOE @2025 / @2035 / @2050 (分/kWh):")
    for k in TECHS:
        l = lcoe_path[k]
        print(f"  {k:<6}: {l[0]*100:>4.2f} / {l[10]*100:>4.2f} / {l[-1]*100:>4.2f}")
    print(f"\n图: 33_lcoe / 34_share / 35_operating / 36_sensitivity")


if __name__ == "__main__":
    main()
