"""电池温度模型。

光伏器件实际工作温度通常高于环境温度（吸收的光大部分变成热）。电池越热，
晶硅功率损失越大、钙钛矿损失小——所以温度模型是量化"温度响应"优劣的前提。

提供两种常用模型：
    - Faiman (2008)：考虑风速散热，pvlib/IEC 标准之一（默认）。
    - NOCT：基于标称工作温度的简化线性模型。
"""

from __future__ import annotations

import numpy as np


def faiman(poa_global, temp_air, wind_speed=1.0, u0=25.0, u1=6.84):
    """Faiman 电池温度模型。

    Tcell = Tair + G_poa / (u0 + u1 * wind)
    u0, u1 默认取 pvlib/IEC 61853 典型值（玻璃-透明背板组件）。
    """
    poa_global = np.asarray(poa_global, float)
    temp_air = np.asarray(temp_air, float)
    wind_speed = np.asarray(wind_speed, float)
    return temp_air + poa_global / (u0 + u1 * wind_speed)


def noct_cell_temp(poa_global, temp_air, noct=45.0):
    """NOCT 简化模型：Tcell = Tair + (NOCT-20)/800 * G_poa。"""
    poa_global = np.asarray(poa_global, float)
    temp_air = np.asarray(temp_air, float)
    return temp_air + (noct - 20.0) / 800.0 * poa_global


def cell_temperature(poa_global, temp_air, wind_speed=1.0, model="faiman",
                     noct=45.0, u0=25.0, u1=6.84):
    """统一入口：返回电池温度 (°C)。

    u0, u1: Faiman 散热系数, 反映安装方式。默认开放支架 (u0=25, u1=6.84)。
    屋顶贴装散热差 → 取较小 u0/u1 (如 u0=20, u1=3) → 电池更热。
    """
    if model == "faiman":
        return faiman(poa_global, temp_air, wind_speed, u0=u0, u1=u1)
    elif model == "noct":
        return noct_cell_temp(poa_global, temp_air, noct)
    raise ValueError(f"未知温度模型: {model}")
