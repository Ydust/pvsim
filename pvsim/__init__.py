"""pvsim —— 晶硅 vs 钙钛矿光伏器件运行特性对比仿真。

模块组成:
    materials   器件参数库 (早期晶硅 / 单结钙钛矿, 文献值)
    cell        单二极管电池核心模型 (I-V, Pmax, 效率)
    temperature 电池温度模型 (Faiman / NOCT)
    spectral    光谱响应与光谱失配
    optics      入射角 (AOI/IAM) 与双面增益
    module      电池→组件缩放
    system      组件→系统 (逆变器 + 系统损耗)
    degradation 多年衰减/寿命
    lcoe        平准化度电成本
    hysteresis  钙钛矿 I-V 迟滞
    tandem      钙钛矿/晶硅叠层电池
    weather     合成气象曲线 + 真实气象(TMY)
"""

from .materials import (
    CSI_EARLY,
    PEROVSKITE,
    TECHNOLOGIES,
    get_technology,
)
from .cell import operating_point, OperatingPoint, translate_params, i_from_v

__all__ = [
    "CSI_EARLY",
    "PEROVSKITE",
    "TECHNOLOGIES",
    "get_technology",
    "operating_point",
    "OperatingPoint",
    "translate_params",
    "i_from_v",
]
