"""屋顶"光储充"一体化(深化版)：发电+储能+充电桩+能量管理+配网友好+运维诊断。

六块都做深, 并对比"现代晶硅"与"钙钛矿"。
运行: python -m scripts.run_microgrid
输出: outputs/microgrid/*.png, summary.csv, 报告.md
"""

import sys
import os

import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from pvsim import viz
from pvsim.viz import plt, color
from pvsim.materials import get_technology
from pvsim.cities import CITIES
from pvsim import weather as wx
from pvsim.system import SystemConfig, simulate, simulate_rooftop
from pvsim import load as ld, ev as evmod, tariff as tf, ems, grid as gd
from pvsim import diagnostics as dg
from pvsim.storage import Battery, health_trajectory

OUT = "outputs/microgrid"
TECHS = ("c-Si-modern", "perovskite")
# 屋顶三个面: 南坡30°(10块) + 东坡15°(5块) + 西坡15°(5块), 共20块
FACETS = [(30.0, 180.0, 10), (15.0, 90.0, 5), (15.0, 270.0, 5)]


def build_inputs(city_key="shanghai", tz="Asia/Shanghai"):
    city = next((c for c in CITIES if c.key == city_key), CITIES[8])
    loc = wx.get_location(latitude=city.lat, longitude=city.lon,
                          altitude=city.alt, name=city.name, tz=tz)
    try:
        raw = wx.from_pvgis_tmy(city.lat, city.lon, altitude=city.alt,
                                name=city.key).tz_convert(tz)
        src = "真实气象 PVGIS TMY"
    except Exception as e:
        raw = wx.synthetic_tmy_year(2023, loc, freq="1h", tmean=17.0)
        src = f"合成类TMY({type(e).__name__})"
    times = raw.index
    cfg = SystemConfig(n_modules=20, thermal_u0=20.0, thermal_u1=3.0)  # 屋顶高温

    pv, pv_south, kwp = {}, {}, {}
    for name in TECHS:
        t = get_technology(name)
        roof = simulate_rooftop(t, raw, loc, cfg, FACETS)            # 多朝向
        south = simulate_rooftop(t, raw, loc, cfg, [(30.0, 180.0, 20)])  # 全南对照
        pv[name] = (roof["ac_power"] / 1000.0).rename("pv_kw")
        pv_south[name] = (south["ac_power"] / 1000.0).rename("pv_kw")
        kwp[name] = roof["kwp"]
        print(f"  {t.name_cn}: {kwp[name]:.2f} kWp | 多朝向 {roof['specific_yield']:.0f} "
              f"vs 全南 {south['specific_yield']:.0f} kWh/kWp", flush=True)

    # 负荷: 居民 + 与气温挂钩的冷暖负荷 + 逐日波动
    load_kw = ld.load_profile(times, daily_kwh=12.0, kind="residential",
                              temp_air=raw["temp_air"], hvac_kw_per_degC=0.18,
                              daily_variation=0.12, seed=2)
    # 充电桩: 1辆车(可V2G)
    sess = evmod.fleet_sessions("home", n_vehicles=1, n_days=len(times)//24 + 1,
                                charge_prob=0.7, seed=1)
    for s in sess:
        s.v2g = True
    ev_unctrl = evmod.uncontrolled_demand(times, sess)
    ev_agg = evmod.daily_ev_aggregate(times, sess, allow_v2g=True)
    return dict(raw=raw, loc=loc, times=times, cfg=cfg, city=city, src=src,
                pv=pv, pv_south=pv_south, kwp=kwp, load=load_kw,
                sess=sess, ev_unctrl=ev_unctrl, ev_agg=ev_agg, tariff=tf.Tariff())


def run_scenarios(D):
    rows, detail = [], {}
    for name in TECHS:
        pv = D["pv"][name]
        pref = ems.pv_surplus_preference(pv, D["load"], D["tariff"])
        ev_smart = evmod.flexible_demand(D["times"], D["sess"], pref)
        no_batt = Battery(capacity_kwh=0.01, power_kw=0.0)
        batt = Battery(capacity_kwh=10.0, power_kw=5.0)
        cap_kw = 0.45 * D["kwp"][name]
        detail[name] = {}

        runs = {
            "①光伏直供(无电池/无序充)": lambda: ems.dispatch(
                pv, D["load"], D["ev_unctrl"], no_batt, D["tariff"],
                ems.GridConfig(), "self_consumption"),
            "②规则·自发自用": lambda: ems.dispatch(
                pv, D["load"], ev_smart, batt, D["tariff"],
                ems.GridConfig(), "self_consumption"),
            "③最优调度(LP+V2G)": lambda: ems.dispatch_optimal(
                pv, D["load"], batt, D["ev_agg"], D["tariff"], ems.GridConfig()),
            "④最优+配网友好(限倒送)": lambda: ems.dispatch_optimal(
                pv, D["load"], batt, D["ev_agg"], D["tariff"],
                ems.GridConfig(export_limit_kw=cap_kw)),
        }
        for label, fn in runs.items():
            res = fn(); sm = res["summary"]; detail[name][label] = res
            rows.append(dict(板子=get_technology(name).name_cn, 场景=label,
                             自发自用=sm["self_consumption_rate"],
                             自给=sm["self_sufficiency_rate"],
                             年电费=sm["annual_bill_yuan"],
                             电池折旧=sm.get("battery_wear_yuan", 0.0),
                             最大倒送=sm["max_export_kw"],
                             弃光=sm["curtailed_kwh"],
                             循环=sm["battery_cycles"]))
    return pd.DataFrame(rows), detail


def print_table(df, D):
    k = D["kwp"]
    print("\n" + "=" * 80)
    print(f"屋顶光储充(深化)：现代晶硅 vs 钙钛矿（{D['city'].name}, {D['src']}, 多朝向屋顶）")
    print(f"装机: 现代晶硅 {k['c-Si-modern']:.2f} kWp, 钙钛矿 {k['perovskite']:.2f} kWp")
    print("=" * 80)
    for _, r in df.iterrows():
        print(f"[{r['板子']}] {r['场景']}")
        print(f"   自发自用 {r['自发自用']*100:5.1f}% | 自给 {r['自给']*100:5.1f}% | "
              f"年电费 {r['年电费']:7.0f}元 | 电池折旧 {r['电池折旧']:5.0f}元 | "
              f"最大倒送 {r['最大倒送']:4.1f}kW | 弃光 {r['弃光']:5.0f}度 | 循环 {r['循环']:4.0f}")
    print("=" * 80)


def eval_grid(D, detail):
    """配网友好评估: 无序充(场景①) vs 最优+友好(场景④), 含/不含无功调节。"""
    cfg = gd.FeederConfig()
    rows, gts = [], {}
    for name in TECHS:
        for label in ("①光伏直供(无电池/无序充)", "④最优+配网友好(限倒送)"):
            ts = detail[name][label]["timeseries"]
            g_no = gd.evaluate(ts, D["kwp"][name], cfg, apply_voltvar=False)
            g_vv = gd.evaluate(ts, D["kwp"][name], cfg, apply_voltvar=True)
            gts[(name, label)] = {"vv": g_vv, "no": g_no}
            m = g_vv["metrics"]; m0 = g_no["metrics"]
            rows.append(dict(板子=get_technology(name).name_cn, 场景=label[:6],
                             最高电压_无调节=m0["max_voltage_no_var_pu"],
                             最高电压_有调节=m["max_voltage_pu"],
                             过压时数=m["overvoltage_hours"],
                             过压时数_无调节=m0["overvoltage_hours_no_var"],
                             变压器过载时数=m["transformer_overload_hours"],
                             最大爬坡=m["max_ramp_kw_per_min"]))
    return pd.DataFrame(rows), gts


# ----------------------------- 图 -----------------------------
def fig_day(detail, name="perovskite", month=7, day=15):
    ts = detail[name]["③最优调度(LP+V2G)"]["timeseries"]
    d = ts[(ts.index.month == month) & (ts.index.day == day)]
    h = d.index.hour + d.index.minute / 60.0
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 6.6), sharex=True,
                                 height_ratios=[3, 1])
    a1.plot(h, d["pv_kw"], color=color(name), lw=2, label="光伏发电")
    a1.plot(h, d["demand_kw"], color="#444", lw=1.6, label="用电(含车)")
    a1.plot(h, d["import_kw"], color="#D14520", lw=1.1, ls="--", label="买电")
    a1.plot(h, d["export_kw"], color="#1D9E75", lw=1.1, ls="--", label="上网")
    a1.fill_between(h, 0, d["batt_kw"].clip(lower=0), color="#85B7EB", alpha=0.5, label="电池充")
    a1.fill_between(h, 0, d["batt_kw"].clip(upper=0), color="#EF9F27", alpha=0.5, label="电池放")
    a1.axhline(0, color="gray", lw=0.6)
    a1.set(ylabel="功率 (kW)", title=f"{get_technology(name).name_cn}屋顶 最优调度单日 ({month}月{day}日)")
    a1.legend(ncol=3, fontsize=8, loc="upper left")
    a2.plot(h, d["soc_kwh"], color="#534AB7", lw=2)
    a2.set(xlabel="时刻 (h)", ylabel="电量(kWh)", xlim=(0, 24)); a2.set_xticks(range(0, 25, 3))
    viz.save(fig, f"{OUT}/01_单日运行.png")


def fig_compare(df):
    scens = list(dict.fromkeys(df["场景"]))
    x = np.arange(len(scens)); w = 0.38
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))
    for ax, (col, unit, sc) in zip(axes, [("自发自用", "%", 100),
                                          ("年电费", "元", 1), ("最大倒送", "kW", 1)]):
        for i, cn in enumerate(["现代晶硅", "钙钛矿"]):
            sub = df[df["板子"] == cn]
            c = color("c-Si-modern" if cn == "现代晶硅" else "perovskite")
            ax.bar(x + (i - 0.5) * w, sub[col].to_numpy() * sc, w, color=c, label=cn)
        ax.set_xticks(x); ax.set_xticklabels([f"{i+1}" for i in range(len(scens))])
        ax.set(ylabel=unit, title=col); ax.legend(fontsize=8)
    axes[0].set_xlabel("①直供 ②规则自用 ③最优 ④最优+配网友好")
    fig.suptitle("现代晶硅 vs 钙钛矿：各场景对比", fontweight="bold")
    fig.tight_layout(); viz.save(fig, f"{OUT}/02_场景对比.png")


def fig_grid(gts, name="perovskite"):
    """历时曲线: 全年电压/变压器负载从高到低排, 直接看"多少时间越限/过载"。"""
    g1 = gts[(name, "①光伏直供(无电池/无序充)")]
    g4 = gts[(name, "④最优+配网友好(限倒送)")]
    v_no = np.sort(g1["no"]["timeseries"]["v_pu"].to_numpy())[::-1]
    v_vv = np.sort(g1["vv"]["timeseries"]["v_pu"].to_numpy())[::-1]
    pct = np.arange(len(v_no)) / len(v_no) * 100
    t1 = np.sort(g1["vv"]["timeseries"]["transformer_loading"].to_numpy())[::-1] * 100
    t4 = np.sort(g4["vv"]["timeseries"]["transformer_loading"].to_numpy())[::-1] * 100

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4.8))
    a1.plot(pct, v_no, color="#D14520", lw=1.8, ls="--", label="不调无功")
    a1.plot(pct, v_vv, color="#1D9E75", lw=2, label="无功电压调节后")
    a1.axhline(1.07, color="gray", ls=":", lw=1.2, label="电压上限 1.07")
    a1.set(xlabel="超过纵轴电压的时间占比 (%)", ylabel="并网点电压 (标幺)",
           xlim=(0, 12), ylim=(1.0, 1.12), title="① 中午倒灌→电压历时曲线")
    a1.legend(fontsize=8)
    a2.plot(pct, t1, color="#888", lw=1.8, label="①无序充电")
    a2.plot(pct, t4, color=color(name), lw=2, label="④最优+限倒送")
    a2.axhline(100, color="#D14520", ls=":", lw=1.2, label="变压器满载")
    a2.set(xlabel="超过纵轴负载的时间占比 (%)", ylabel="变压器负载率 (%)",
           xlim=(0, 18), title="变压器负载历时(最优挤谷充→夜间反更重)")
    a2.legend(fontsize=8)
    fig.suptitle(f"{get_technology(name).name_cn}台区(20户) 配网友好", fontweight="bold")
    fig.tight_layout(); viz.save(fig, f"{OUT}/03_配网电压.png")


def fig_diagnosis(D, name="perovskite"):
    demo = dg.run_diagnosis_demo(get_technology(name), D["raw"], D["cfg"],
                                 soiling_start=120, soiling_loss=0.18)
    pi_t = demo["twin"]["pi_daily"]; pi_n = demo["naive"]["pi_daily"]
    x = np.arange(len(pi_t))
    fig, ax = plt.subplots(figsize=(11, 4.8))
    ax.plot(x, pi_n.to_numpy() * 100, color="#B4B2A9", lw=1,
            label=f"朴素基线 (误报 {demo['false_alarms_naive']} 天)")
    ax.plot(x, pi_t.to_numpy() * 100, color=color(name), lw=1.4,
            label=f"物理孪生 (误报 {demo['false_alarms_twin']} 天)")
    ax.axhline(94, color="#D14520", ls="--", lw=1, label="报警阈值 94%")
    ax.axvline(120, color="gray", ls=":", lw=1)
    o = demo["twin"]["onset_day"]
    if o is not None:
        ax.annotate(f"第{o}天发现, 估损失{demo['twin']['est_loss']*100:.0f}%\n判定:{demo['twin']['fault_type']}",
                    xy=(o, 80), xytext=(o + 25, 70), fontsize=9,
                    arrowprops=dict(arrowstyle="->", color=color(name)))
    ax.set(xlabel="一年中第几天", ylabel="逐日性能指数 PI (%)", ylim=(60, 115),
           title=f"{get_technology(name).name_cn}屋顶 运维诊断: 第120天起积灰")
    ax.legend(loc="lower left", fontsize=9); fig.tight_layout()
    viz.save(fig, f"{OUT}/04_运维诊断.png")
    return demo


def fig_battery_health(detail, name="perovskite"):
    thru = detail[name]["②规则·自发自用"]["summary"]["battery_throughput_kwh"]
    h = health_trajectory(Battery(10.0, 5.0), thru, horizon_years=20)
    fig, ax = plt.subplots(figsize=(8, 4.6))
    ax.plot(h["years"], h["capacity_fraction"] * 100, color="#534AB7", marker="o", ms=3)
    ax.axhline(80, color="#D14520", ls="--", lw=1, label="更换阈值 80%")
    if np.isfinite(h["eol_year"]):
        ax.axvline(h["eol_year"], color="#D14520", ls=":", lw=1)
        ax.annotate(f"第{h['eol_year']:.0f}年需更换", xy=(h["eol_year"], 80),
                    xytext=(h["eol_year"] - 8, 86), fontsize=9,
                    arrowprops=dict(arrowstyle="->", color="#D14520"))
    ax.set(xlabel="运行年数", ylabel="电池容量保持率(%)",
           title=f"电池老化(年吞吐{thru:.0f}度≈{h['annual_efc']:.0f}次满循环)")
    ax.legend(fontsize=9); fig.tight_layout()
    viz.save(fig, f"{OUT}/05_电池老化.png")
    return h


def fig_roof(D, name="perovskite", month=6, day=21):
    multi = D["pv"][name]; south = D["pv_south"][name]
    dm = multi[(multi.index.month == month) & (multi.index.day == day)]
    ds = south[(south.index.month == month) & (south.index.day == day)]
    h = dm.index.hour + dm.index.minute / 60.0
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    ax.plot(h, ds.to_numpy(), color="#888", lw=1.8, ls="--", label="全朝南")
    ax.plot(h, dm.to_numpy(), color=color(name), lw=2, label="南+东+西多朝向")
    ax.set(xlabel="时刻(h)", ylabel="发电功率(kW)", xlim=(0, 24),
           title=f"{get_technology(name).name_cn}屋顶 多朝向 vs 全南 ({month}月{day}日)")
    ax.set_xticks(range(0, 25, 3)); ax.legend(fontsize=9); fig.tight_layout()
    viz.save(fig, f"{OUT}/06_多朝向屋顶.png")


def write_report(df, D, demo, gdf, bh, suite):
    df.to_csv(f"{OUT}/summary.csv", index=False, encoding="utf-8-sig")
    suite.to_csv(f"{OUT}/诊断评测.csv", index=False, encoding="utf-8-sig")
    gdf.to_csv(f"{OUT}/配网评估.csv", index=False, encoding="utf-8-sig")

    def tbl(d):
        cols = list(d.columns)
        out = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
        for _, r in d.iterrows():
            out.append("| " + " | ".join(
                (f"{v:.2f}" if isinstance(v, float) else str(v)) for v in r) + " |")
        return "\n".join(out)

    lines = [
        "# 屋顶光储充一体化（深化版）：现代晶硅 vs 钙钛矿\n",
        f"> {D['city'].name}, {D['src']}, 多朝向屋顶(南30°+东西15°), 屋顶高温; "
        "居民负荷(含空调随气温)+家用充电桩(可V2G)+10kWh电池(含老化)+分时电价。\n",
        "## 六块都做深了\n",
        "- **屋顶光伏**: system.simulate_rooftop 多朝向(南/东/西分别转置辐照再汇总)。",
        "- **储能**: storage.py 加多年老化(日历+循环+温度), 可算更换年限/折旧。",
        "- **充电桩**: ev.py 车队+随机+涓流(CC-CV)+V2G 反向放电。",
        "- **能量管理**: ems.py 规则调度 + 按天线性规划(LP)最优调度(最省钱基准)。",
        "- **配网友好**: grid.py 台区电压模型 + 无功电压调节(Volt-VAR) + 变压器过载/爬坡。",
        "- **运维诊断**: diagnostics.py 5类故障 + 物理特征分类器 + 孪生vs朴素误报对比。\n",
        "## 各场景关键数字\n", tbl(df),
        "\n## 能量管理: 规则 vs 最优\n",
    ]
    for cn in ["现代晶硅", "钙钛矿"]:
        r2 = df[(df["板子"] == cn) & (df["场景"] == "②规则·自发自用")].iloc[0]
        r3 = df[(df["板子"] == cn) & (df["场景"] == "③最优调度(LP+V2G)")].iloc[0]
        lines.append(f"- {cn}: 规则年电费 {r2['年电费']:.0f}元 → 最优 {r3['年电费']:.0f}元 "
                     f"(再省 {r2['年电费']-r3['年电费']:.0f}元)。")
    lines += [
        "\n## 配网友好评估(台区20户)\n", tbl(gdf),
        "\n## 电池老化\n",
        f"- 年吞吐≈{bh['annual_efc']:.0f}次满循环, 容量跌到80%约在第 "
        f"{bh['eol_year']:.0f} 年(需更换)。",
        "\n## 运维诊断\n",
        f"- 积灰演示: 物理孪生第 {demo['twin']['onset_day']} 天发现、估损失 "
        f"{demo['twin']['est_loss']*100:.0f}%、判定「{demo['twin']['fault_type']}」; "
        f"全年误报 孪生 {demo['false_alarms_twin']} vs 朴素 {demo['false_alarms_naive']} 天。",
        "- 5类故障分类评测:\n", tbl(suite),
    ]
    with open(f"{OUT}/报告.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    viz.setup()
    os.makedirs(OUT, exist_ok=True)
    print("构建输入(多朝向发电/负荷/车队/电价) ...", flush=True)
    D = build_inputs()
    print("跑场景(规则 + 最优LP) × 2种板子 ...", flush=True)
    df, detail = run_scenarios(D)
    print_table(df, D)
    print("配网友好评估 ...", flush=True)
    gdf, gts = eval_grid(D, detail)
    print("运维诊断评测 ...", flush=True)
    suite = dg.evaluate_suite(get_technology("perovskite"), D["raw"], D["cfg"])
    print("\n[诊断分类评测]\n" + suite.to_string(index=False))
    print("画图 ...", flush=True)
    fig_day(detail); fig_compare(df); fig_grid(gts)
    demo = fig_diagnosis(D); bh = fig_battery_health(detail); fig_roof(D)
    write_report(df, D, demo, gdf, bh, suite)
    print(f"\n完成。图/表/报告在 {OUT}/")


if __name__ == "__main__":
    main()
