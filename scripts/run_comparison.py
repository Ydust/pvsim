"""晶硅 vs 钙钛矿：运行特性全维度对比，输出图表 + 量化汇总 + 报告。

运行: python -m scripts.run_comparison
输出: outputs/figures/*.png, outputs/summary.csv, outputs/对比报告.md
"""

import sys
import os

import numpy as np
import pandas as pd

from pvsim import viz
from pvsim.viz import plt, color, LABEL_CN
from pvsim.materials import CSI_EARLY, PEROVSKITE
from pvsim.cell import operating_point
from pvsim import spectral as sp
from pvsim import weather as wx
from pvsim.system import SystemConfig, simulate
from pvsim.degradation import lifetime_energy, PEROVSKITE_SCENARIOS
from pvsim.lcoe import lcoe
from pvsim.hysteresis import hysteresis_curves
from pvsim import tandem as td

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

FIG = "outputs/figures"
TECHS = (CSI_EARLY, PEROVSKITE)
S = {}   # 汇总数字


def _slope(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    xm, ym = x.mean(), y.mean()
    return ((x - xm) * (y - ym)).sum() / ((x - xm) ** 2).sum()


# ---------------------------------------------------------------------------
def fig_iv_pv():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.6))
    for t in TECHS:
        op = operating_point(t, 1000.0, 25.0, ns=t.cells_in_series, npts=400)
        c = color(t.name)
        ax1.plot(op.v, op.i, color=c, label=f"{t.name_cn} (Pmax={op.pmp:.0f}W)")
        ax2.plot(op.v, op.v * op.i, color=c, label=t.name_cn)
        ax2.plot(op.vmp, op.pmp, "o", color=c)
        S[t.name] = dict(isc=op.isc, voc=op.voc, pmp=op.pmp, ff=op.ff,
                         eff=op.efficiency * 100)
    ax1.set(xlabel="电压 V (V)", ylabel="电流 I (A)", title="I-V 曲线 @STC")
    ax2.set(xlabel="电压 V (V)", ylabel="功率 P (W)", title="P-V 曲线 @STC (●=最大功率点)")
    ax1.legend(); ax2.legend()
    fig.suptitle("① 标准条件 (STC) I-V / P-V 特性", fontweight="bold")
    viz.save(fig, f"{FIG}/01_iv_pv.png")


def fig_temperature():
    temps = np.arange(15, 71, 2.0)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.6))
    for t in TECHS:
        ns = t.cells_in_series
        p = np.array([operating_point(t, 1000.0, float(T), ns=ns, npts=150).pmp for T in temps])
        e = np.array([operating_point(t, 1000.0, float(T), ns=ns, npts=150).efficiency for T in temps]) * 100
        p25 = operating_point(t, 1000.0, 25.0, ns=ns).pmp
        gamma = _slope(temps, p) / p25 * 100
        c = color(t.name)
        ax1.plot(temps, p / p25 * 100, color=c, label=f"{t.name_cn} (γ={gamma:.3f}%/°C)")
        ax2.plot(temps, e, color=c, label=t.name_cn)
        ret65 = operating_point(t, 1000.0, 65.0, ns=ns).pmp / p25 * 100
        S[t.name]["gamma_pmax"] = gamma
        S[t.name]["pretention_65C"] = ret65
    ax1.axvline(25, ls=":", color="gray"); ax1.axhline(100, ls=":", color="gray")
    ax1.set(xlabel="电池温度 (°C)", ylabel="相对功率 P/P(25°C) (%)",
            title="功率随温度变化 (越平越耐热)")
    ax2.set(xlabel="电池温度 (°C)", ylabel="效率 (%)", title="效率随温度变化")
    ax1.legend(); ax2.legend()
    fig.suptitle("② 温度响应：钙钛矿高温损失远小于晶硅", fontweight="bold")
    viz.save(fig, f"{FIG}/02_temperature.png")


def fig_lowlight():
    irr = np.array([50, 100, 150, 200, 300, 400, 600, 800, 1000.0])
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.6))
    for t in TECHS:
        ns = t.cells_in_series
        eff = np.array([operating_point(t, float(G), 25.0, ns=ns, npts=200).efficiency for G in irr]) * 100
        e1000 = eff[-1]
        c = color(t.name)
        ax1.plot(irr, eff, "o-", color=c, label=t.name_cn)
        ax2.plot(irr, eff / e1000 * 100, "o-", color=c, label=t.name_cn)
        rel200 = operating_point(t, 200.0, 25.0, ns=ns).efficiency / \
                 operating_point(t, 1000.0, 25.0, ns=ns).efficiency * 100
        S[t.name]["rel_eff_200"] = rel200
    ax1.set(xlabel="辐照 G (W/m²)", ylabel="效率 (%)", title="效率随辐照变化")
    ax2.axhline(100, ls=":", color="gray")
    ax2.set(xlabel="辐照 G (W/m²)", ylabel="相对效率 η/η(1000) (%)",
            title="弱光相对效率 (越高弱光越好)")
    ax1.legend(); ax2.legend()
    fig.suptitle("③ 弱光响应：钙钛矿低辐照下效率保持更好", fontweight="bold")
    viz.save(fig, f"{FIG}/03_lowlight.png")


def fig_spectral():
    wl = np.linspace(300, 1250, 500)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 4.6))
    wlr, Er = sp.reference_am15g()
    ax1b = ax1.twinx()
    m = (wlr >= 300) & (wlr <= 1250)
    ax1b.fill_between(wlr[m], Er[m], color="gold", alpha=0.25, label="AM1.5G 光谱")
    ax1b.set_ylabel("光谱辐照 (W/m²/nm)")
    for t in TECHS:
        ax1.plot(wl, sp.eqe(t, wl) * 100, color=color(t.name), label=f"{t.name_cn} EQE")
    ax1.set(xlabel="波长 (nm)", ylabel="外量子效率 EQE (%)",
            title="光谱响应 (钙钛矿~800nm截止, 晶硅到~1100nm)")
    ax1.legend(loc="upper right"); ax1b.legend(loc="center right")

    conds = list(sp.SPECTRUM_CONDITIONS.keys())
    x = np.arange(len(conds)); w = 0.36
    for i, t in enumerate(TECHS):
        sfs = [sp.spectral_mismatch_factor(t, *sp.generate_spectrum(z))
               for z in sp.SPECTRUM_CONDITIONS.values()]
        ax2.bar(x + (i - 0.5) * w, sfs, w, color=color(t.name), label=t.name_cn)
        S[t.name]["sf_lowsun"] = sfs[-1]
        S[t.name]["sf_highsun"] = sfs[0]
    ax2.axhline(1.0, ls=":", color="gray")
    ax2.set_xticks(x); ax2.set_xticklabels(conds, fontsize=9)
    ax2.set(ylabel="光谱失配因子 SF (=1即AM1.5G)", title="不同光谱条件下的相对增益")
    ax2.set_ylim(0.9, 1.05); ax2.legend()
    fig.suptitle("④ 光谱响应：钙钛矿偏好蓝光/高太阳, 晶硅吃近红外/低太阳", fontweight="bold")
    fig.subplots_adjust(wspace=0.5)
    viz.save(fig, f"{FIG}/04_spectral.png")


def fig_daily():
    loc = wx.get_location()
    day = wx.clear_sky_day("2023-06-21", loc, freq="20min", tmean=32.0)
    cfg = SystemConfig(n_modules=20)
    fig, ax1 = plt.subplots(figsize=(9, 5))
    ax2 = ax1.twinx()
    hrs = day.index.hour + day.index.minute / 60
    for t in TECHS:
        r = simulate(t, day, cfg, npts=120)
        ts = r["timeseries"]
        ax1.plot(hrs, ts["ac_power"] / r["kwp"], color=color(t.name),
                 label=f"{t.name_cn} (日比发电 {r['specific_yield']:.2f} kWh/kWp)")
        S[t.name]["daily_yield_hot"] = r["specific_yield"]
        S[t.name]["pr_hot_day"] = r["performance_ratio"]
    # 共用电池温度曲线(两者温度模型一致)
    r0 = simulate(CSI_EARLY, day, cfg, npts=80)
    ax2.plot(hrs, r0["timeseries"]["tcell"], color="firebrick", ls="--",
             alpha=0.6, label="电池温度")
    ax1.set(xlabel="时刻 (h)", ylabel="单位容量交流功率 (W/kWp)",
            title="夏至晴天 (上海) 单日出力对比")
    ax2.set_ylabel("电池温度 (°C)", color="firebrick")
    ax1.legend(loc="upper left"); ax2.legend(loc="upper right")
    fig.suptitle("⑤ 实际运行(高温日)：钙钛矿因耐热, 单位容量出力更高", fontweight="bold")
    viz.save(fig, f"{FIG}/05_daily_hotday.png")


def fig_annual():
    loc = wx.get_location()
    cfg = SystemConfig(n_modules=20)
    sources = {
        "理想晴空年": wx.clear_sky_year(2023, loc, freq="1h"),
        "类TMY(含云)": wx.synthetic_tmy_year(2023, loc, freq="1h"),
    }
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.6))
    labels = list(sources.keys()); x = np.arange(len(labels)); w = 0.36
    for i, t in enumerate(TECHS):
        sy, pr = [], []
        for df in sources.values():
            r = simulate(t, df, cfg, npts=100)
            sy.append(r["specific_yield"]); pr.append(r["performance_ratio"])
        ax1.bar(x + (i - 0.5) * w, sy, w, color=color(t.name), label=t.name_cn)
        ax2.bar(x + (i - 0.5) * w, pr, w, color=color(t.name), label=t.name_cn)
        S[t.name]["annual_yield_tmy"] = sy[1]
        S[t.name]["annual_pr_tmy"] = pr[1]
    for ax, ttl, yl in [(ax1, "年比发电量", "kWh/kWp"), (ax2, "性能比 PR", "PR")]:
        ax.set_xticks(x); ax.set_xticklabels(labels)
        ax.set(ylabel=yl, title=ttl); ax.legend()
    fig.suptitle("⑥ 全年发电量：钙钛矿比发电量与性能比更高(温度+弱光累积优势)", fontweight="bold")
    viz.save(fig, f"{FIG}/06_annual_yield.png")


def fig_degradation():
    # 用类TMY年第1年发电量
    loc = wx.get_location(); cfg = SystemConfig(n_modules=20)
    tmy = wx.synthetic_tmy_year(2023, loc, freq="1h")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.6))
    e1 = {}
    for t in TECHS:
        r = simulate(t, tmy, cfg, npts=100)
        e1[t.name] = r["energy_ac_kwh"]
    # 晶硅
    le_c = lifetime_energy(CSI_EARLY, e1["c-Si"])
    ax1.plot(le_c["years"], le_c["retention"] * 100, color=color("c-Si"),
             marker="o", ms=3, label=f"早期晶硅 (T80>{CSI_EARLY.lifetime_years:.0f}yr)")
    ax2.plot(le_c["years"], le_c["cumulative_kwh"], color=color("c-Si"), label="早期晶硅")
    S["c-Si"]["t80"] = le_c["t80_year"]
    S["c-Si"]["lifetime_kwh"] = float(le_c["cumulative_kwh"][-1])
    # 钙钛矿三情景
    styles = {"乐观(改进封装)": "-", "代表性": "--", "悲观(早期器件)": ":"}
    for sc, ls in styles.items():
        le = lifetime_energy(PEROVSKITE, e1["perovskite"], sc)
        ax1.plot(le["years"], le["retention"] * 100, color=color("perovskite"),
                 ls=ls, label=f"钙钛矿-{sc} (T80={le['t80_year']:.1f}yr)")
        ax2.plot(le["years"], le["cumulative_kwh"], color=color("perovskite"), ls=ls)
        if sc == "代表性":
            S["perovskite"]["t80"] = le["t80_year"]
            S["perovskite"]["lifetime_kwh"] = float(le["cumulative_kwh"][-1])
    ax1.axhline(80, ls="-", color="red", alpha=0.4, lw=1)
    ax1.set(xlabel="运行年数", ylabel="性能保持率 (%)", title="衰减曲线 (红线=80%)")
    ax2.set(xlabel="运行年数", ylabel="累计发电量 (kWh)", title="寿命累计发电量")
    ax1.legend(fontsize=8); ax2.legend(fontsize=9)
    fig.suptitle("⑦ 衰减与寿命：晶硅极稳定, 钙钛矿衰减快/寿命短(最大劣势)", fontweight="bold")
    viz.save(fig, f"{FIG}/07_degradation.png")


def fig_lcoe():
    loc = wx.get_location(); cfg = SystemConfig(n_modules=20)
    tmy = wx.synthetic_tmy_year(2023, loc, freq="1h")
    fig, ax = plt.subplots(figsize=(9, 5))
    bars, vals, colors = [], [], []
    rc = simulate(CSI_EARLY, tmy, cfg, npts=100)
    lc = lcoe(CSI_EARLY, rc["kwp"], rc["energy_ac_kwh"])
    bars.append("早期晶硅"); vals.append(lc["lcoe"] * 100); colors.append(color("c-Si"))
    S["c-Si"]["lcoe_cents"] = lc["lcoe"] * 100
    rp = simulate(PEROVSKITE, tmy, cfg, npts=100)
    for sc in PEROVSKITE_SCENARIOS:
        lp = lcoe(PEROVSKITE, rp["kwp"], rp["energy_ac_kwh"], sc)
        bars.append(f"钙钛矿\n{sc}"); vals.append(lp["lcoe"] * 100); colors.append(color("perovskite"))
        if sc == "代表性":
            S["perovskite"]["lcoe_cents"] = lp["lcoe"] * 100
    b = ax.bar(bars, vals, color=colors)
    ax.bar_label(b, fmt="%.2f", padding=2)
    ax.axhline(S["c-Si"]["lcoe_cents"], ls=":", color=color("c-Si"), alpha=0.6)
    ax.set(ylabel="LCOE (分/kWh)", title="⑧ 平准化度电成本 LCOE：寿命短拉高钙钛矿成本")
    fig.suptitle("⑧ 度电成本：钙钛矿能否胜出取决于稳定性情景", fontweight="bold")
    viz.save(fig, f"{FIG}/08_lcoe.png")


def fig_hysteresis():
    h = hysteresis_curves(PEROVSKITE)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.6))
    cp = color("perovskite")
    ax1.plot(h.reverse.v, h.reverse.i, color=cp, label=f"反向扫描 (Pmax={h.reverse.pmp:.0f}W)")
    ax1.plot(h.forward.v, h.forward.i, color=cp, ls="--", label=f"正向扫描 (Pmax={h.forward.pmp:.0f}W)")
    op_c = operating_point(CSI_EARLY, 1000, 25, ns=CSI_EARLY.cells_in_series)
    ax1.plot(op_c.v, op_c.i, color=color("c-Si"), alpha=0.5, label="晶硅(无迟滞)")
    ax1.set(xlabel="电压 (V)", ylabel="电流 (A)", title="I-V: 钙钛矿正反扫不重合")
    ax2.plot(h.reverse.v, h.reverse.v * h.reverse.i, color=cp, label="反向扫描")
    ax2.plot(h.forward.v, h.forward.v * h.forward.i, color=cp, ls="--", label="正向扫描")
    ax2.axhline(h.stabilized_pmax, color="gray", ls=":", label=f"稳态MPPT≈{h.stabilized_pmax:.0f}W")
    ax2.set(xlabel="电压 (V)", ylabel="功率 (W)",
            title=f"P-V (迟滞指数 HI={h.hysteresis_index*100:.1f}%, MPPT损失≈{h.mppt_loss*100:.1f}%)")
    ax1.legend(); ax2.legend()
    fig.suptitle("⑨ I-V 迟滞：钙钛矿特有, 致测量歧义与MPPT损失(晶硅无)", fontweight="bold")
    S["perovskite"]["hysteresis_index"] = h.hysteresis_index * 100
    S["perovskite"]["mppt_loss"] = h.mppt_loss * 100
    S["c-Si"]["hysteresis_index"] = 0.0
    viz.save(fig, f"{FIG}/09_hysteresis.png")


def fig_tandem():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.6))
    pero, csi = td.reference_single_junctions()
    t = td.tandem_perovskite_silicon()
    names = ["单结晶硅\n(理想)", "单结钙钛矿\n(理想)", "钙钛矿/晶硅\n叠层"]
    effs = [csi.efficiency, pero.efficiency, t.efficiency]
    cols = [color("c-Si"), color("perovskite"), color("tandem")]
    b = ax1.bar(names, effs, color=cols); ax1.bar_label(b, fmt="%.1f%%")
    ax1.set(ylabel="效率 (%)", title="叠层突破单结极限")
    egs, effscan, eg_opt, eff_opt = td.optimal_top_bandgap()
    ax2.plot(egs, effscan, color=color("tandem"))
    ax2.plot(eg_opt, eff_opt, "o", color="red",
             label=f"最优顶带隙 {eg_opt:.2f}eV → {eff_opt:.1f}%")
    ax2.set(xlabel="顶电池(钙钛矿)带隙 (eV)", ylabel="叠层效率 (%)",
            title="电流匹配: 顶电池带隙寻优"); ax2.legend()
    fig.suptitle("⑩ 叠层电池：钙钛矿最大潜力 — 作顶电池叠在晶硅上突破极限", fontweight="bold")
    S["tandem"] = dict(efficiency=t.efficiency, eg_opt=eg_opt, eff_opt=eff_opt,
                       mismatch=t.current_mismatch * 100, voc=t.voc)
    viz.save(fig, f"{FIG}/10_tandem.png")


# ---------------------------------------------------------------------------
def write_summary():
    c, p = S["c-Si"], S["perovskite"]
    rows = [
        ("STC效率 (%)", f"{c['eff']:.1f}", f"{p['eff']:.1f}", "钙钛矿"),
        ("STC最大功率 (W/组件)", f"{c['pmp']:.0f}", f"{p['pmp']:.0f}", "钙钛矿"),
        ("温度系数 γ_Pmax (%/°C)", f"{c['gamma_pmax']:.3f}", f"{p['gamma_pmax']:.3f}", "钙钛矿"),
        ("65°C功率保持 (%)", f"{c['pretention_65C']:.1f}", f"{p['pretention_65C']:.1f}", "钙钛矿"),
        ("弱光相对效率@200 (%)", f"{c['rel_eff_200']:.1f}", f"{p['rel_eff_200']:.1f}", "钙钛矿"),
        ("低太阳光谱因子SF", f"{c['sf_lowsun']:.3f}", f"{p['sf_lowsun']:.3f}", "晶硅"),
        ("高太阳光谱因子SF", f"{c['sf_highsun']:.3f}", f"{p['sf_highsun']:.3f}", "钙钛矿"),
        ("高温日比发电 (kWh/kWp)", f"{c['daily_yield_hot']:.2f}", f"{p['daily_yield_hot']:.2f}", "钙钛矿"),
        ("年比发电量 (kWh/kWp)", f"{c['annual_yield_tmy']:.0f}", f"{p['annual_yield_tmy']:.0f}", "钙钛矿"),
        ("年性能比 PR", f"{c['annual_pr_tmy']:.3f}", f"{p['annual_pr_tmy']:.3f}", "钙钛矿"),
        ("T80寿命 (年)", f">{CSI_EARLY.lifetime_years:.0f}", f"{p['t80']:.1f}", "晶硅"),
        ("寿命累计发电 (kWh)", f"{c['lifetime_kwh']:.0f}", f"{p['lifetime_kwh']:.0f}", "晶硅"),
        ("LCOE (分/kWh)", f"{c['lcoe_cents']:.2f}", f"{p['lcoe_cents']:.2f}", "晶硅"),
        ("I-V迟滞指数 HI (%)", f"{c['hysteresis_index']:.1f}", f"{p['hysteresis_index']:.1f}", "晶硅"),
    ]
    cols = ["对比维度", "早期晶硅", "钙钛矿", "占优方"]
    df = pd.DataFrame(rows, columns=cols)
    df.to_csv("outputs/summary.csv", index=False, encoding="utf-8-sig")

    def to_md_table(columns, data):
        out = ["| " + " | ".join(columns) + " |",
               "| " + " | ".join("---" for _ in columns) + " |"]
        for r in data:
            out.append("| " + " | ".join(str(x) for x in r) + " |")
        return "\n".join(out)

    lines = [
        "# 晶硅 vs 钙钛矿 光伏器件运行特性 量化对比报告\n",
        "> 仿真器件: 早期晶硅 (组件效率~15.4%) vs 单结钙钛矿 (~19.3%), 归一到相同面积。",
        "> 单二极管物理模型, 温度系数经文献标定, 上海气象, 系统级(含逆变器/损耗)。\n",
        "## 核心量化结论\n",
        to_md_table(cols, rows),
        "\n## 各维度解读\n",
        f"**① 效率/功率**: 钙钛矿单结效率 {p['eff']:.1f}% 高于早期晶硅 {c['eff']:.1f}%; 同面积下组件功率更高。",
        f"**② 温度 (钙钛矿优势)**: γ_Pmax {p['gamma_pmax']:.3f} vs {c['gamma_pmax']:.3f} %/°C; "
        f"升到65°C时钙钛矿保持 {p['pretention_65C']:.0f}% 功率, 晶硅仅 {c['pretention_65C']:.0f}%。",
        f"**③ 弱光 (钙钛矿优势)**: 200W/m²下钙钛矿相对效率 {p['rel_eff_200']:.1f}%, 晶硅 {c['rel_eff_200']:.1f}%。",
        f"**④ 光谱**: 晶硅在低太阳(红移)占优(SF {c['sf_lowsun']:.3f}>{p['sf_lowsun']:.3f}), "
        f"钙钛矿在高太阳(蓝光足)占优。",
        f"**⑤⑥ 发电量 (钙钛矿优势)**: 高温日比发电 {p['daily_yield_hot']:.2f} vs {c['daily_yield_hot']:.2f} kWh/kWp; "
        f"全年 {p['annual_yield_tmy']:.0f} vs {c['annual_yield_tmy']:.0f} kWh/kWp, PR {p['annual_pr_tmy']:.3f} vs {c['annual_pr_tmy']:.3f}。",
        f"**⑦ 衰减/寿命 (晶硅优势, 钙钛矿最大劣势)**: 晶硅25年仍>80%; 钙钛矿(代表情景)T80仅 {p['t80']:.1f} 年。",
        f"**⑧ LCOE (晶硅优势)**: 尽管钙钛矿初装更便宜、发电更多, 但寿命短致 LCOE {p['lcoe_cents']:.2f} > 晶硅 {c['lcoe_cents']:.2f} 分/kWh。",
        f"**⑨ I-V迟滞 (晶硅优势)**: 钙钛矿 HI={p['hysteresis_index']:.1f}%, 致测量歧义与~{p['mppt_loss']:.1f}% MPPT损失; 晶硅无。",
        f"**⑩ 叠层 (钙钛矿最大潜力)**: 钙钛矿/晶硅叠层效率 {S['tandem']['efficiency']:.1f}%, "
        f"最优顶带隙 {S['tandem']['eg_opt']:.2f}eV 可达 {S['tandem']['eff_opt']:.1f}%, 远超单结极限。\n",
        "## 总结\n",
        "- **钙钛矿的优势**: 效率高、温度系数小(耐高温)、弱光好、蓝光/高太阳光谱友好 → 实际运行单位容量发电更多。",
        "- **钙钛矿的劣势**: 衰减快、寿命短、有I-V迟滞 → 寿命累计发电与LCOE劣于晶硅。",
        "- **关键变量**: 稳定性。一旦封装/组分改进把寿命提上去(乐观情景), 钙钛矿LCOE即可逼近甚至反超晶硅。",
        "- **最大机会**: 钙钛矿/晶硅叠层, 用钙钛矿做顶电池突破单结效率极限(>30%)。",
    ]
    with open("outputs/对比报告.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    viz.setup()
    os.makedirs(FIG, exist_ok=True)
    steps = [
        ("① STC I-V/P-V", fig_iv_pv),
        ("② 温度响应", fig_temperature),
        ("③ 弱光响应", fig_lowlight),
        ("④ 光谱响应", fig_spectral),
        ("⑤ 高温日出力", fig_daily),
        ("⑥ 全年发电量", fig_annual),
        ("⑦ 衰减/寿命", fig_degradation),
        ("⑧ LCOE", fig_lcoe),
        ("⑨ I-V迟滞", fig_hysteresis),
        ("⑩ 叠层电池", fig_tandem),
    ]
    for name, fn in steps:
        print(f"  生成 {name} ...", flush=True)
        fn()
    write_summary()
    print("\n完成。图表在 outputs/figures/, 汇总 outputs/summary.csv, 报告 outputs/对比报告.md")


if __name__ == "__main__":
    main()
