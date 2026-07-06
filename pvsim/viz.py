"""绘图基础设置：中文字体、统一配色与样式。"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")            # 无界面后端，直接出图文件
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# 两种技术的统一配色
COLORS = {
    "c-Si": "#1f6fb2",          # 蓝 = 晶硅
    "c-Si-modern": "#1f6fb2",   # 蓝 = 现代晶硅(同晶硅色系)
    "perovskite": "#e2641e",    # 橙 = 钙钛矿
    "tandem": "#2a9d4a",        # 绿 = 叠层
}
LABEL_CN = {"c-Si": "早期晶硅", "c-Si-modern": "现代晶硅",
            "perovskite": "钙钛矿", "tandem": "钙钛矿/晶硅叠层"}


def setup(font_size: int = 12):
    """配置中文字体与全局样式。"""
    avail = set(f.name for f in fm.fontManager.ttflist)
    for cand in ["Microsoft YaHei", "SimHei", "DengXian", "SimSun"]:
        if cand in avail:
            plt.rcParams["font.sans-serif"] = [cand]
            break
    plt.rcParams["axes.unicode_minus"] = False    # 正常显示负号
    plt.rcParams["font.size"] = font_size
    plt.rcParams["axes.grid"] = True
    plt.rcParams["grid.alpha"] = 0.3
    plt.rcParams["figure.dpi"] = 110
    plt.rcParams["savefig.bbox"] = "tight"


def setup_en(font_size: int = 12):
    """英文论文绘图样式 (Joule/Applied Energy 投稿用, 干净无衬线)。"""
    avail = set(f.name for f in fm.fontManager.ttflist)
    for cand in ["Arial", "Helvetica", "DejaVu Sans", "Liberation Sans"]:
        if cand in avail:
            plt.rcParams["font.sans-serif"] = [cand]
            break
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.size"] = font_size
    plt.rcParams["axes.grid"] = True
    plt.rcParams["grid.alpha"] = 0.3
    plt.rcParams["figure.dpi"] = 110
    plt.rcParams["savefig.bbox"] = "tight"

# 技术英文标签 (图例/标题统一用)
LABEL_EN = {"c-Si": "c-Si", "perovskite": "Perovskite", "tandem": "Tandem"}
TECH_EN = {"晶硅": "c-Si", "钙钛矿": "Perovskite", "叠层": "Tandem"}


def color(tech_name: str) -> str:
    return COLORS.get(tech_name, "#888888")


def save(fig, path: str):
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path
