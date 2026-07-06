"""31 省六角网格地图 (hex cartogram) — 消除地理面积偏差.

为什么用六角:
  - 经纬度散点: 新疆视觉巨大 vs 山东很小, 数据被地理面积扭曲
  - 六角: 每省一个等大单元, 视觉权重相等, 颜色/数值就是真正信息
  - 标准做法 (FT/Bloomberg/NYT 选举/经济地图)

布局: 31 省 (含 4 直辖市 5 自治区), 粗略保持地理方位:
       北 → 南 (y 减少)
       西 → 东 (x 增加)

输出: Fig 48 (3 子图: 2050 LCOE / 钙钛矿温度优势 / CO2 减排潜力, 全部六角化)
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import RegularPolygon

from pvsim import viz
from pvsim.provinces import PROVINCES, PROVINCE_PV_2024_GW, PROVINCE_CODE

TECH_EN = {"晶硅": "c-Si", "钙钛矿": "Perovskite", "叠层": "Tandem"}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# 中国 31 省六角网格坐标 (col, row), 粗略地理对应
# row 0 = 北 (上), row 9 = 南 (下); col 0 = 西 (左), col 7 = 东 (右)
# pointy-top hex, 奇数行 col 偏移 +0.5
HEX_LAYOUT = {
    "黑龙江": (6, 0),
    "内蒙古": (4, 1), "吉林": (5, 1),
    "辽宁":   (5, 2),
    "新疆":   (2, 3), "北京": (4, 3), "天津": (5, 3),
    "甘肃":   (3, 4), "山西": (4, 4), "河北": (5, 4), "山东": (6, 4),
    "青海":   (2, 5), "宁夏": (3, 5), "陕西": (4, 5), "河南": (5, 5), "江苏": (6, 5),
    "西藏":   (2, 6), "四川": (3, 6), "重庆": (4, 6), "湖北": (5, 6), "安徽": (6, 6), "上海": (7, 6),
    "云南":   (3, 7), "贵州": (4, 7), "湖南": (5, 7), "江西": (6, 7), "浙江": (7, 7),
    "广西":   (4, 8), "广东": (5, 8), "福建": (6, 8),
    "海南":   (5, 9),
}


def hex_xy(col, row):
    """六角中心坐标 (pointy-top, 奇数行右偏)."""
    x = col + (0.5 if row % 2 else 0)
    y = -row * np.sqrt(3) / 2     # y 越小越靠下
    return x, y


def draw_hex_map(ax, values, cmap="viridis", vmin=None, vmax=None,
                  fmt="{:.2f}", title="", value_label="",
                  hex_radius=0.5, fontsize=8, missing_color="#f0f0f0",
                  label_color="black"):
    """在 ax 上画六角地图.

    values: dict {province: value}
    """
    if vmin is None: vmin = min(values.values())
    if vmax is None: vmax = max(values.values())
    cmap_obj = plt.get_cmap(cmap)

    for prov, (col, row) in HEX_LAYOUT.items():
        x, y = hex_xy(col, row)
        if prov in values and not pd.isna(values[prov]):
            v = values[prov]
            t = (v - vmin) / (vmax - vmin) if vmax > vmin else 0.5
            t = max(0, min(1, t))
            face = cmap_obj(t)
            label = fmt.format(v)
        else:
            face = missing_color
            label = "-"
        hex_patch = RegularPolygon(
            (x, y), numVertices=6, radius=hex_radius,
            orientation=0, facecolor=face, edgecolor="black",
            linewidth=0.9, zorder=2,
        )
        ax.add_patch(hex_patch)
        # province code
        ax.text(x, y + 0.13, PROVINCE_CODE.get(prov, prov), ha="center",
                va="center", fontsize=fontsize, fontweight="bold", zorder=3,
                color=label_color)
        # value
        ax.text(x, y - 0.17, label, ha="center", va="center",
                fontsize=fontsize - 1, zorder=3, color=label_color)

    ax.set_aspect("equal")
    ax.set_xlim(0.5, 8.5); ax.set_ylim(-8.5, 0.8)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_visible(False)
    if title: ax.set_title(title, fontweight="bold", fontsize=12)

    # colorbar
    sm = plt.cm.ScalarMappable(norm=plt.Normalize(vmin=vmin, vmax=vmax),
                                 cmap=cmap_obj)
    sm.set_array([])
    cb = plt.colorbar(sm, ax=ax, shrink=0.7, pad=0.02)
    if value_label: cb.set_label(value_label, fontsize=10)
    return cb


def draw_sparkline_hex(ax, cx, cy, d_prov, prov, ymin, ymax, yr_arr,
                        colors_map, hex_radius, fontsize, techs,
                        ref_years=(2030, 2040), show_ref_lines=True):
    """单个 sparkline 六边形 (省级或图例参考)."""
    hex_patch = RegularPolygon(
        (cx, cy), numVertices=6, radius=hex_radius,
        orientation=0, facecolor="#fafafa", edgecolor="black",
        linewidth=0.7, zorder=1,
    )
    ax.add_patch(hex_patch)

    x_half = hex_radius * 0.78
    y_top = hex_radius * 0.32
    y_bot = -hex_radius * 0.42
    yr_norm = (yr_arr - yr_arr.min()) / (yr_arr.max() - yr_arr.min())

    # 省名 (顶部)
    ax.text(cx, cy + hex_radius * 0.62, prov, ha="center", va="center",
            fontsize=fontsize, fontweight="bold", zorder=4)

    # 参考竖线 2030/2040
    if show_ref_lines:
        for yr in ref_years:
            xrel = (yr - yr_arr.min()) / (yr_arr.max() - yr_arr.min())
            xref = cx - x_half + xrel * (2 * x_half)
            ax.plot([xref, xref], [cy + y_bot, cy + y_top],
                    "-", color="lightgray", lw=0.5, zorder=2)

    if d_prov is None or len(d_prov) == 0:
        ax.text(cx, cy, "—", ha="center", va="center", fontsize=fontsize+4)
        return

    # 三技折线
    for tech in techs:
        sub = d_prov[d_prov["tech"] == tech].set_index("year").reindex(yr_arr)
        lcs = sub["lcoe_cents_per_kwh"].values
        xs = cx - x_half + yr_norm * (2 * x_half)
        ys = cy + y_bot + (lcs - ymin) / (ymax - ymin) * (y_top - y_bot)
        ys = np.clip(ys, cy + y_bot, cy + y_top)
        ax.plot(xs, ys, color=colors_map[tech], lw=1.4, zorder=3,
                solid_capstyle="round")

    # 2050 三技终态小点
    end_lcs = {t: float(d_prov[(d_prov["tech"] == t) &
                                (d_prov["year"] == 2050)]
                          ["lcoe_cents_per_kwh"].values[0])
               for t in techs}
    winner = min(end_lcs, key=end_lcs.get)
    for tech, val in end_lcs.items():
        yy = cy + y_bot + (val - ymin) / (ymax - ymin) * (y_top - y_bot)
        yy = max(cy + y_bot, min(cy + y_top, yy))
        ax.plot(cx + x_half, yy, "o", color=colors_map[tech],
                ms=3.5 if tech == winner else 2.3, zorder=4,
                markeredgecolor="black" if tech == winner else "none",
                markeredgewidth=0.5)

    # 2050 赢家 LCOE 数值
    ax.text(cx, cy - hex_radius * 0.72,
            f"{end_lcs[winner]:.1f}¢ ({winner})",
            ha="center", va="center", fontsize=fontsize-1,
            color=colors_map[winner], fontweight="bold", zorder=4)


def draw_sparkline_hex_map(ax, lcoe_df, years=range(2025, 2051),
                            techs=("晶硅", "钙钛矿", "叠层"),
                            colors_map=None,
                            hex_radius=0.62, fontsize=9,
                            ymin=None, ymax=None):
    """每六边形内画三技 LCOE 2025-2050 sparkline.

    info density: 31 省 × 3 技 × 26 年 = 2418 数据点 / 一张图.
    """
    if colors_map is None:
        colors_map = {"晶硅": "#1f6fb2", "钙钛矿": "#e2641e", "叠层": "#2a9d4a"}
    if ymin is None:
        ymin = lcoe_df["lcoe_cents_per_kwh"].min() * 0.95
    if ymax is None:
        ymax = min(10, lcoe_df["lcoe_cents_per_kwh"].quantile(0.97))

    yr_arr = np.array(list(years))

    for prov, (col, row) in HEX_LAYOUT.items():
        cx, cy = hex_xy(col, row)
        d = lcoe_df[lcoe_df["province"] == prov]
        draw_sparkline_hex(ax, cx, cy, d, prov, ymin, ymax, yr_arr,
                            colors_map, hex_radius, fontsize, techs)

    ax.set_aspect("equal")
    ax.set_xlim(0.0, 9.5); ax.set_ylim(-8.7, 0.9)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_visible(False)


def make_sparkline_hex_figure():
    """Fig 49: 省级 LCOE 演化 sparkline-in-hex (论文 Joule 级单图武器)."""
    lcoe_df = pd.read_csv("outputs/province_physics_lcoe.csv",
                           encoding="utf-8-sig")
    colors_map = {"晶硅": "#1f6fb2", "钙钛矿": "#e2641e", "叠层": "#2a9d4a"}
    ymin, ymax = 1.5, 8.0
    yr_arr = np.arange(2025, 2051)
    hex_radius = 0.62; fontsize = 9
    techs = ("晶硅", "钙钛矿", "叠层")

    fig, ax = plt.subplots(figsize=(15, 14))
    draw_sparkline_hex_map(ax, lcoe_df, ymin=ymin, ymax=ymax,
                             colors_map=colors_map, hex_radius=hex_radius,
                             fontsize=fontsize)

    # legend: reference hex (Tibet) + axis explanation
    leg_cx, leg_cy = 0.8, -7.0
    leg_d = lcoe_df[lcoe_df["province"] == "西藏"]
    draw_sparkline_hex(ax, leg_cx, leg_cy, leg_d, "Example", ymin, ymax,
                        yr_arr, colors_map, hex_radius, fontsize, techs,
                        show_ref_lines=True)
    ax.annotate("Y axis: 1.5 -> 8.0 cents/kWh",
                xy=(leg_cx - hex_radius * 0.8, leg_cy),
                xytext=(leg_cx - 1.5, leg_cy + 0.2),
                fontsize=9, ha="right",
                arrowprops=dict(arrowstyle="->", color="gray", lw=0.8))
    ax.annotate("X axis: 2025 -> 2050\ngray lines = 2030 / 2040",
                xy=(leg_cx, leg_cy + hex_radius * 0.30),
                xytext=(leg_cx - 1.5, leg_cy + 0.9),
                fontsize=9, ha="right",
                arrowprops=dict(arrowstyle="->", color="gray", lw=0.8))
    ax.annotate("right dots = 2050 endpoint\nblack-edge dot = cheapest tech in 2050",
                xy=(leg_cx + hex_radius * 0.78, leg_cy - 0.15),
                xytext=(leg_cx + 1.6, leg_cy - 0.4),
                fontsize=9, ha="left",
                arrowprops=dict(arrowstyle="->", color="gray", lw=0.8))

    # colour legend
    for i, (tech, col) in enumerate(colors_map.items()):
        ax.plot([7.5, 7.9], [-7.5 - i*0.3]*2, color=col, lw=3)
        ax.text(8.0, -7.5 - i*0.3, TECH_EN[tech], fontsize=11, va="center",
                color=col, fontweight="bold")
    ax.text(7.5, -7.1, "LCOE by tech", fontsize=10, fontweight="bold")

    fig.suptitle("31 provinces x 3 techs x 26 years = 2418 data points, "
                 "sparkline-in-hex\n"
                 "Within-province LCOE evolution + endpoint winner + endpoint LCOE",
                 fontweight="bold", fontsize=13.5, y=0.985)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig("outputs/figures/49_sparkline_hexmap.png", dpi=140,
                 bbox_inches="tight")
    plt.close(fig)
    print("Fig 49 saved: outputs/figures/49_sparkline_hexmap.png")


def make_combined_hex_figure():
    """Fig 48: 三联六角地图 (yield / 钙钛矿温度优势 / 2050 LCOE / CO2 减排)."""
    yield_df = pd.read_csv("outputs/province_physics_yield.csv", encoding="utf-8-sig")
    lcoe_df = pd.read_csv("outputs/province_physics_lcoe.csv", encoding="utf-8-sig")
    carbon_df = pd.read_csv("outputs/province_carbon_potential.csv",
                             encoding="utf-8-sig")

    # 数据
    yield_csi = yield_df[yield_df["tech"] == "晶硅"].set_index("province")["yield_kwh_per_kwp"].to_dict()
    yield_pero = yield_df[yield_df["tech"] == "钙钛矿"].set_index("province")["yield_kwh_per_kwp"].to_dict()
    perov_adv = {p: (yield_pero[p] / yield_csi[p] - 1) * 100
                  for p in yield_csi if p in yield_pero}
    lcoe_2050 = lcoe_df[(lcoe_df["year"] == 2050) &
                        (lcoe_df["tech"] == "钙钛矿")].set_index("province")["lcoe_cents_per_kwh"].to_dict()
    carbon_2050 = carbon_df.set_index("province")["gtco2_25y"].to_dict()

    # 2x2 panel
    fig, axes = plt.subplots(2, 2, figsize=(15, 13))
    draw_hex_map(axes[0, 0], yield_csi, cmap="viridis", vmin=900, vmax=2050,
                  fmt="{:.0f}", value_label="kWh/kWp",
                  title="(a) c-Si annual yield (physics 8760h)")
    draw_hex_map(axes[0, 1], perov_adv, cmap="RdYlBu_r", vmin=1, vmax=8,
                  fmt="+{:.1f}%", value_label="temp. advantage %",
                  title="(b) Perovskite vs c-Si yield advantage")
    draw_hex_map(axes[1, 0], lcoe_2050, cmap="viridis_r", vmin=1.5, vmax=3.0,
                  fmt="{:.2f}", value_label="cents/kWh",
                  title="(c) Perovskite 2050 LCOE (NPV)")
    draw_hex_map(axes[1, 1], carbon_2050, cmap="YlOrRd", vmin=0, vmax=2.7,
                  fmt="{:.2f}", value_label="GtCO2",
                  title="(d) Perovskite 2050 fleet 25-yr CO2 abatement")

    fig.suptitle("31-province hex cartogram: physics-driven provincial substitution panel\n"
                 "(equal-area hexagons remove geographic-area visual bias)",
                 fontweight="bold", fontsize=14, y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig("outputs/figures/48_hexmap_panel.png", dpi=130,
                 bbox_inches="tight")
    plt.close(fig)
    print("Fig 48 saved: outputs/figures/48_hexmap_panel.png")

    # single panels too
    for name, values, cmap, vmin, vmax, fmt, vl, ttl in [
        ("48a_yield",    yield_csi,   "viridis",    900,  2050, "{:.0f}",  "kWh/kWp",
         "c-Si annual yield (kWh/kWp, physics 8760h)"),
        ("48b_perov_adv", perov_adv,  "RdYlBu_r",     1,     8, "+{:.1f}%", "temp. advantage %",
         "Perovskite temperature advantage (vs c-Si yield, %)"),
        ("48c_lcoe2050",  lcoe_2050,  "viridis_r",  1.5,   3.0, "{:.2f}",  "cents/kWh",
         "Perovskite 2050 LCOE (NPV, cents/kWh)"),
        ("48d_carbon",    carbon_2050, "YlOrRd",      0,   2.7, "{:.2f}",  "GtCO2",
         "2050 fleet 25-yr CO2 abatement (GtCO2)"),
    ]:
        fig, ax = plt.subplots(figsize=(9, 8))
        draw_hex_map(ax, values, cmap=cmap, vmin=vmin, vmax=vmax,
                      fmt=fmt, value_label=vl, title=ttl,
                      fontsize=10)
        fig.tight_layout()
        fig.savefig(f"outputs/figures/{name}.png", dpi=140,
                     bbox_inches="tight")
        plt.close(fig)
        print(f"  → {name}.png")


def draw_yinyang_hex_map(ax, top_values, bot_values, cmap_top, cmap_bot,
                          vmin_top, vmax_top, vmin_bot, vmax_bot,
                          hex_radius=0.55, fontsize=8,
                          label_top="", label_bot="",
                          fmt_top="{:.1f}", fmt_bot="{:.1f}"):
    """每六边形上下两半着色显示两变量 (yin-yang split).

    上半 = 物理变量 (yield/温度优势)
    下半 = 经济变量 (LCOE/CO2)
    """
    cmap_t = plt.get_cmap(cmap_top)
    cmap_b = plt.get_cmap(cmap_bot)
    r = hex_radius
    h = r * np.sqrt(3) / 2

    for prov, (col, row) in HEX_LAYOUT.items():
        cx, cy = hex_xy(col, row)
        # 上半梯形 (4 vertex)
        top_pts = [(cx + r, cy), (cx + r/2, cy + h),
                    (cx - r/2, cy + h), (cx - r, cy)]
        bot_pts = [(cx - r, cy), (cx - r/2, cy - h),
                    (cx + r/2, cy - h), (cx + r, cy)]
        # 颜色
        if prov in top_values:
            t = (top_values[prov] - vmin_top) / (vmax_top - vmin_top)
            ct = cmap_t(np.clip(t, 0, 1))
            label_t = fmt_top.format(top_values[prov])
        else:
            ct = "#f0f0f0"; label_t = "-"
        if prov in bot_values:
            t = (bot_values[prov] - vmin_bot) / (vmax_bot - vmin_bot)
            cb = cmap_b(np.clip(t, 0, 1))
            label_b = fmt_bot.format(bot_values[prov])
        else:
            cb = "#f0f0f0"; label_b = "-"
        ax.add_patch(plt.Polygon(top_pts, facecolor=ct, edgecolor="none",
                                  zorder=2))
        ax.add_patch(plt.Polygon(bot_pts, facecolor=cb, edgecolor="none",
                                  zorder=2))
        # 外框 + 中线
        ax.add_patch(RegularPolygon((cx, cy), 6, radius=r, orientation=0,
                                      facecolor="none", edgecolor="black",
                                      linewidth=0.9, zorder=3))
        ax.plot([cx-r, cx+r], [cy, cy], "-", color="black", lw=0.7, zorder=3)
        # 标签
        ax.text(cx, cy + h*0.45, prov, ha="center", va="center",
                fontsize=fontsize, fontweight="bold", zorder=4)
        ax.text(cx, cy + h*0.15, label_t, ha="center", va="center",
                fontsize=fontsize-1, zorder=4)
        ax.text(cx, cy - h*0.45, label_b, ha="center", va="center",
                fontsize=fontsize-1, zorder=4)

    ax.set_aspect("equal")
    ax.set_xlim(0.0, 9.5); ax.set_ylim(-8.7, 0.9)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_visible(False)

    # 两条 colorbar
    sm_t = plt.cm.ScalarMappable(norm=plt.Normalize(vmin_top, vmax_top), cmap=cmap_t)
    sm_t.set_array([])
    cb_t = plt.colorbar(sm_t, ax=ax, shrink=0.5, pad=0.02, location="right")
    cb_t.set_label(f"top: {label_top}", fontsize=10)
    sm_b = plt.cm.ScalarMappable(norm=plt.Normalize(vmin_bot, vmax_bot), cmap=cmap_b)
    sm_b.set_array([])
    cb_b = plt.colorbar(sm_b, ax=ax, shrink=0.5, pad=0.08, location="right")
    cb_b.set_label(f"bottom: {label_bot}", fontsize=10)


def make_yinyang_hex_figure():
    """Fig 51: 双变量 yin-yang hex (上半 yield, 下半 LCOE 2050)."""
    yield_df = pd.read_csv("outputs/province_physics_yield.csv", encoding="utf-8-sig")
    lcoe_df = pd.read_csv("outputs/province_physics_lcoe.csv", encoding="utf-8-sig")
    yield_csi = yield_df[yield_df["tech"] == "晶硅"].set_index("province")["yield_kwh_per_kwp"].to_dict()
    lcoe_2050 = lcoe_df[(lcoe_df["year"] == 2050) &
                          (lcoe_df["tech"] == "钙钛矿")].set_index("province")["lcoe_cents_per_kwh"].to_dict()

    fig, ax = plt.subplots(figsize=(13, 11))
    draw_yinyang_hex_map(
        ax, yield_csi, lcoe_2050,
        cmap_top="viridis", cmap_bot="viridis_r",
        vmin_top=900, vmax_top=2050, vmin_bot=1.5, vmax_bot=4.0,
        fmt_top="{:.0f}", fmt_bot="{:.2f}",
        label_top="c-Si yield (kWh/kWp)",
        label_bot="Perovskite 2050 LCOE (cents/kWh)",
        fontsize=9,
    )
    fig.suptitle("Fig 51 — Bivariate yin-yang hex: physical yield (top) + economic LCOE (bottom)\n"
                 "Resource band vs substitution value coupled per province in one map",
                 fontweight="bold", fontsize=13, y=0.98)
    fig.tight_layout()
    fig.savefig("outputs/figures/51_yinyang_hexmap.png", dpi=140,
                 bbox_inches="tight")
    plt.close(fig)
    print("Fig 51 saved: outputs/figures/51_yinyang_hexmap.png")


def make_pie_in_hex_figure():
    """Fig 52: pie-in-hex (每六边形内嵌 2050 三技份额饼图).

    省级 2050 部署份额: 用 26 年 LCOE 累积 softmax 分配.
    """
    from matplotlib.patches import Wedge
    lcoe_df = pd.read_csv("outputs/province_physics_lcoe.csv", encoding="utf-8-sig")
    colors_map = {"晶硅": "#1f6fb2", "钙钛矿": "#e2641e", "叠层": "#2a9d4a"}
    techs = ["晶硅", "钙钛矿", "叠层"]
    T = 0.5    # softmax 温度参数 (cents/kWh)

    # 各省 2025-2050 累计份额
    shares = {}
    for prov in HEX_LAYOUT:
        d = lcoe_df[lcoe_df["province"] == prov]
        if len(d) == 0:
            shares[prov] = None; continue
        cum = {t: 0.0 for t in techs}
        for yr in range(2025, 2051):
            lcs = {t: float(d[(d["tech"] == t) & (d["year"] == yr)]
                                ["lcoe_cents_per_kwh"].values[0])
                   for t in techs}
            # 叠层 2029 前不可用
            avail = [t for t in techs if not (t == "叠层" and yr < 2029)]
            weights = {t: np.exp(-lcs[t] / T) for t in avail}
            wsum = sum(weights.values())
            for t in avail: cum[t] += weights[t] / wsum
        total = sum(cum.values())
        shares[prov] = {t: cum[t]/total for t in techs}

    fig, ax = plt.subplots(figsize=(13, 11))
    r = 0.6; pie_r = r * 0.62
    for prov, (col, row) in HEX_LAYOUT.items():
        cx, cy = hex_xy(col, row)
        ax.add_patch(RegularPolygon((cx, cy), 6, radius=r, orientation=0,
                                      facecolor="#fafafa", edgecolor="black",
                                      linewidth=0.8, zorder=1))
        ax.text(cx, cy + r * 0.65, PROVINCE_CODE.get(prov, prov), ha="center",
                va="center", fontsize=9, fontweight="bold", zorder=4)
        s = shares[prov]
        if s is None:
            ax.text(cx, cy, "—", ha="center", va="center", fontsize=12); continue
        # 饼图 (顺时针, 12 点起)
        angle0 = 90
        max_tech = max(s, key=s.get)
        for tech in techs:
            frac = s[tech]
            if frac < 0.001: continue
            angle1 = angle0 - frac * 360
            w = Wedge((cx, cy), pie_r, angle1, angle0,
                       facecolor=colors_map[tech], edgecolor="white",
                       linewidth=0.7, zorder=2)
            ax.add_patch(w)
            # 份额数字标在大块上
            if frac > 0.15:
                mid_angle = (angle0 + angle1) / 2
                tx = cx + pie_r * 0.6 * np.cos(np.deg2rad(mid_angle))
                ty = cy + pie_r * 0.6 * np.sin(np.deg2rad(mid_angle))
                ax.text(tx, ty, f"{int(frac*100)}%", ha="center", va="center",
                        fontsize=7, color="white", fontweight="bold", zorder=4)
            angle0 = angle1
        # dominant-tech label (bottom)
        ax.text(cx, cy - r * 0.65, f"{TECH_EN[max_tech]} {int(s[max_tech]*100)}%",
                ha="center", va="center", fontsize=7.5,
                color=colors_map[max_tech], fontweight="bold", zorder=4)

    ax.set_aspect("equal")
    ax.set_xlim(0.0, 9.5); ax.set_ylim(-8.7, 0.9)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_visible(False)

    # 图例
    for i, (tech, col) in enumerate(colors_map.items()):
        ax.add_patch(plt.Rectangle((7.8, -0.4 - i*0.4), 0.3, 0.25,
                                     facecolor=col, edgecolor="black", lw=0.6))
        ax.text(8.2, -0.27 - i*0.4, TECH_EN[tech], fontsize=11, va="center",
                color=col, fontweight="bold")
    ax.text(7.8, 0.05, "2050 cumulative deployment share", fontsize=10, fontweight="bold")

    fig.suptitle("Fig 52 — Pie-in-hex: 2050 cumulative three-tech deployment share by province\n"
                 "(26-year LCOE softmax allocation, T=0.5 cents/kWh)",
                 fontweight="bold", fontsize=13, y=0.98)
    fig.tight_layout()
    fig.savefig("outputs/figures/52_pie_in_hex.png", dpi=140, bbox_inches="tight")
    plt.close(fig)
    print("Fig 52 saved: outputs/figures/52_pie_in_hex.png")
    return shares


def make_metals_constraint_hex_figure():
    """Fig 50: 关键金属约束 hex map (供给侧新维度).

    逻辑:
      2030 全国新增 ~100 GW/yr, 钙钛矿占 55%, 叠层 25% → 含铟技术总 80 GW
      In 强度 30 kg/MW × 80 GW = 2400 t/yr 需求
      2030 国产 ~676 t/yr → 缺口 3.5x
      省级按 2024 装机 share 分配, 暴露哪些省单独就吃掉全国铟产能多少%.
    """
    from pvsim.policy_data import (METAL_INTENSITY_KG_PER_MW,
                                     critical_metal_supply_t_per_yr,
                                     china_pv_target_gw)
    # 2030 全国新增 = target 2030 - target 2029, 取代表中值
    yrs, target = china_pv_target_gw()
    new_2030 = float(np.interp(2030, yrs, np.gradient(target)))    # ≈100 GW/yr
    new_2035 = float(np.interp(2035, yrs, np.gradient(target)))

    # 2030 vs 2035 部署份额 (与 portfolio_carbon 自然替代情景一致)
    share_2030 = {"晶硅": 0.20, "钙钛矿": 0.55, "叠层": 0.25}
    share_2035 = {"晶硅": 0.17, "钙钛矿": 0.46, "叠层": 0.37}

    # 全国年供应 2030 vs 2035
    yrs_m, supply = critical_metal_supply_t_per_yr()
    In_2030 = float(np.interp(2030, yrs_m, supply["In"]))     # t/yr
    Ag_2030 = float(np.interp(2030, yrs_m, supply["Ag"]))
    In_2035 = float(np.interp(2035, yrs_m, supply["In"]))
    Ag_2035 = float(np.interp(2035, yrs_m, supply["Ag"]))

    total_2024 = sum(PROVINCE_PV_2024_GW.values())

    def per_prov_metal(metal, year_total_gw, share, supply_t):
        """每省该年需求 (kg/yr) → 也算 % of national supply."""
        # 全国需求
        nat_perov_gw = year_total_gw * share["钙钛矿"]
        nat_tand_gw = year_total_gw * share["叠层"]
        nat_csi_gw = year_total_gw * share["晶硅"]
        kg_perov_per_gw = METAL_INTENSITY_KG_PER_MW["钙钛矿25y"][metal] * 1000
        kg_tand_per_gw = METAL_INTENSITY_KG_PER_MW["叠层"][metal] * 1000
        kg_csi_per_gw = METAL_INTENSITY_KG_PER_MW["晶硅25y"][metal] * 1000
        nat_demand_kg = (nat_perov_gw * kg_perov_per_gw +
                         nat_tand_gw * kg_tand_per_gw +
                         nat_csi_gw * kg_csi_per_gw)
        nat_demand_t = nat_demand_kg / 1000
        # 省级
        per_prov_t = {}
        per_prov_pct = {}
        for prov, gw in PROVINCE_PV_2024_GW.items():
            ps = gw / total_2024
            prov_demand_t = nat_demand_t * ps
            per_prov_t[prov] = prov_demand_t
            per_prov_pct[prov] = prov_demand_t / supply_t * 100
        return per_prov_t, per_prov_pct, nat_demand_t

    In_t_2030, In_pct_2030, In_nat_2030 = per_prov_metal("In", new_2030,
                                                            share_2030, In_2030)
    Ag_t_2030, Ag_pct_2030, Ag_nat_2030 = per_prov_metal("Ag", new_2030,
                                                            share_2030, Ag_2030)
    In_t_2035, In_pct_2035, In_nat_2035 = per_prov_metal("In", new_2035,
                                                            share_2035, In_2035)

    print(f"\n  indium constraint:")
    print(f"    2030 national demand {In_nat_2030:.0f} t/yr  vs  domestic {In_2030:.0f} t/yr "
          f"(gap {In_nat_2030/In_2030:.1f}x)")
    print(f"    2035 national demand {In_nat_2035:.0f} t/yr  vs  domestic {In_2035:.0f} t/yr "
          f"(gap {In_nat_2035/In_2035:.1f}x)")
    print(f"  silver constraint:")
    print(f"    2030 national demand {Ag_nat_2030:.0f} t/yr  vs  domestic {Ag_2030:.0f} t/yr "
          f"(share {Ag_nat_2030/Ag_2030*100:.0f}%)")

    fig, axes = plt.subplots(2, 2, figsize=(16, 13))

    draw_hex_map(axes[0, 0], In_t_2030, cmap="YlOrRd", vmin=0, vmax=350,
                  fmt="{:.0f}", value_label="t/yr",
                  title=f"(a) 2030 provincial indium demand (t/yr)\n"
                        f"national total {In_nat_2030:.0f} t/yr "
                        f"(domestic supply {In_2030:.0f} t/yr)",
                  fontsize=9)
    draw_hex_map(axes[0, 1], In_pct_2030, cmap="Reds", vmin=0, vmax=50,
                  fmt="{:.0f}%", value_label="% national supply",
                  title=f"(b) 2030 indium as % of national supply\n"
                        f"national total {In_nat_2030/In_2030*100:.0f}% "
                        f"(supply gap {In_nat_2030/In_2030:.1f}x)",
                  fontsize=9)
    draw_hex_map(axes[1, 0], Ag_t_2030, cmap="YlOrBr", vmin=0, vmax=180,
                  fmt="{:.0f}", value_label="t/yr",
                  title=f"(c) 2030 provincial silver demand (t/yr)\n"
                        f"national total {Ag_nat_2030:.0f} t/yr "
                        f"(domestic supply {Ag_2030:.0f} t/yr)",
                  fontsize=9)
    draw_hex_map(axes[1, 1], In_t_2035, cmap="YlOrRd", vmin=0, vmax=350,
                  fmt="{:.0f}", value_label="t/yr",
                  title=f"(d) 2035 indium demand (rising tandem share)\n"
                        f"national total {In_nat_2035:.0f} t/yr "
                        f"(domestic supply {In_2035:.0f} t/yr)",
                  fontsize=9)

    fig.suptitle("Fig 4 — Geographic distribution of critical-metal constraints "
                 "(supply-side bottleneck)\n"
                 "(a)(b)(d) perovskite+tandem ITO indium 30 kg/MW |"
                 " (c) silver electrode c-Si 10 + tandem 10 kg/MW",
                 fontweight="bold", fontsize=13.5, y=0.995)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig("outputs/figures/50_metals_constraint_hex.png", dpi=130,
                 bbox_inches="tight")
    plt.close(fig)
    print("Fig 4 (50) saved: outputs/figures/50_metals_constraint_hex.png")

    # top-5 provinces by indium share
    sorted_in = sorted(In_pct_2030.items(), key=lambda x: -x[1])
    print(f"\n  indium as % of national supply, top 5 provinces (2030):")
    for prov, pct in sorted_in[:5]:
        print(f"    {PROVINCE_CODE.get(prov,prov):3s}: {pct:.1f}% ({In_t_2030[prov]:.0f} t/yr)")


def main():
    viz.setup_en()
    os.makedirs("outputs/figures", exist_ok=True)
    make_combined_hex_figure()
    make_sparkline_hex_figure()
    make_metals_constraint_hex_figure()
    make_yinyang_hex_figure()
    make_pie_in_hex_figure()


if __name__ == "__main__":
    main()
