"""入射角修正 (IAM) 与双面增益。

IAM (Incidence Angle Modifier): 太阳斜射时玻璃/封装反射增大，透到电池的光减少。
    这主要是组件光学（玻璃+减反膜）效应，两种技术差异不大，但影响早晚发电量。

双面增益: 组件背面也能接收地面反射光发电。早期晶硅为单面 (bifaciality=0)，无此增益；
    本模块用简化模型量化"若具备双面"的增量，主要用于说明早期晶硅在此维度的劣势。
"""

from __future__ import annotations

import numpy as np
import pvlib


def iam(aoi_deg, model: str = "martin_ruiz", **kwargs) -> np.ndarray:
    """入射角修正系数 (0-1)。aoi_deg: 入射角(度)。"""
    aoi_deg = np.asarray(aoi_deg, float)
    if model == "martin_ruiz":
        return np.asarray(pvlib.iam.martin_ruiz(aoi_deg, **kwargs))
    elif model == "physical":
        return np.asarray(pvlib.iam.physical(aoi_deg, **kwargs))
    elif model == "ashrae":
        return np.asarray(pvlib.iam.ashrae(aoi_deg, **kwargs))
    raise ValueError(f"未知 IAM 模型: {model}")


def effective_poa(poa_direct, poa_diffuse, aoi_deg,
                  model: str = "martin_ruiz") -> np.ndarray:
    """考虑 IAM 后的有效 POA 辐照。

    直射分量按 IAM(aoi) 透射；散射分量用 Martin-Ruiz 散射 IAM 近似(~0.95)。
    """
    poa_direct = np.asarray(poa_direct, float)
    poa_diffuse = np.asarray(poa_diffuse, float)
    iam_b = iam(aoi_deg, model=model)
    iam_d = 0.95  # 散射光等效 IAM (近似常数)
    return poa_direct * iam_b + poa_diffuse * iam_d


def rear_irradiance(ghi, albedo: float = 0.2, rear_view_factor: float = 0.4):
    """背面接收的地面反射辐照 (W/m^2) 简化模型。

    rear_poa ≈ GHI × 地面反照率 × 背面视角因子。
    rear_view_factor 取决于安装高度/间距, 典型 0.3-0.5。
    """
    ghi = np.asarray(ghi, float)
    return ghi * albedo * rear_view_factor


def bifacial_effective_irradiance(front_eff, ghi, bifaciality: float,
                                  albedo: float = 0.2,
                                  rear_view_factor: float = 0.4) -> np.ndarray:
    """双面组件的等效正面辐照 = 正面有效辐照 + 双面率×背面辐照。

    bifaciality=0 (早期单面晶硅) 时退化为纯正面, 无增益。
    """
    front_eff = np.asarray(front_eff, float)
    rear = rear_irradiance(ghi, albedo, rear_view_factor)
    return front_eff + bifaciality * rear
