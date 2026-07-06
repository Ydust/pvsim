"""建筑用电负荷曲线（合成，含与气温挂钩的冷暖负荷）。

按建筑类型合成逐时用电(kW)。形状取自典型负荷研究的定性特征：
    residential 居民：早(7-9)、晚(18-22)双峰；commercial 工商业：白天单峰；flat 近恒定。

升级点：
    1) 冷暖负荷与**气温**挂钩——气温超出舒适区(默认18-26°C)就线性增加空调/采暖用电。
       这让用电和天气、光伏出力产生真实耦合(大热天空调多, 正好和中午光伏对上)。
    2) 逐日随机波动(daily_variation), 让每天不完全一样, 更接近真实。
基础负荷按 daily_kwh 缩放, 冷暖负荷叠加在其上(总量会高于 daily_kwh, 返回时可查分项)。
"""

from __future__ import annotations

import numpy as np
import pandas as pd


_SHAPES = {
    "residential": np.array([
        0.45, 0.40, 0.38, 0.37, 0.38, 0.45, 0.70, 1.05,
        1.10, 0.85, 0.70, 0.65, 0.65, 0.60, 0.58, 0.62,
        0.75, 1.05, 1.55, 1.70, 1.60, 1.30, 0.90, 0.60,
    ]),
    "commercial": np.array([
        0.25, 0.22, 0.20, 0.20, 0.22, 0.30, 0.50, 0.85,
        1.30, 1.65, 1.80, 1.80, 1.55, 1.70, 1.75, 1.60,
        1.40, 1.10, 0.80, 0.55, 0.45, 0.40, 0.35, 0.30,
    ]),
    "flat": np.ones(24),
}

# 冷暖负荷的日内形状(空调白天/傍晚重, 采暖早晚重); 均值=1
_HVAC_COOL = np.array([0.5, 0.4, 0.35, 0.3, 0.3, 0.3, 0.4, 0.6,
                       0.8, 1.0, 1.2, 1.35, 1.45, 1.5, 1.5, 1.45,
                       1.4, 1.3, 1.2, 1.1, 1.0, 0.85, 0.7, 0.6])
_HVAC_HEAT = np.array([0.8, 0.7, 0.65, 0.6, 0.6, 0.7, 1.1, 1.4,
                       1.3, 1.0, 0.8, 0.7, 0.65, 0.65, 0.7, 0.8,
                       1.0, 1.3, 1.5, 1.5, 1.4, 1.2, 1.0, 0.9])


def daily_shape(kind: str = "residential") -> np.ndarray:
    if kind not in _SHAPES:
        raise KeyError(f"未知负荷类型 '{kind}', 可选: {list(_SHAPES)}")
    s = _SHAPES[kind].astype(float)
    return s / s.mean()


def _seasonal_factor(doy: np.ndarray, summer_bump=0.20, winter_bump=0.12) -> np.ndarray:
    summer = summer_bump * np.cos(2 * np.pi * (doy - 200) / 365.0)
    winter = winter_bump * np.cos(2 * np.pi * (doy - 15) / 365.0)
    return 1.0 + np.clip(summer, 0, None) + np.clip(winter, 0, None)


def load_profile(times: pd.DatetimeIndex, daily_kwh: float = 14.0,
                 kind: str = "residential", seasonal: bool = True,
                 weekend_factor: float = 1.10,
                 temp_air=None, hvac_kw_per_degC: float = 0.0,
                 comfort_band=(18.0, 26.0), cop: float = 3.0,
                 daily_variation: float = 0.0, seed: int = 0,
                 return_parts: bool = False):
    """生成逐时用电(kW)。

    temp_air + hvac_kw_per_degC>0 时叠加冷暖负荷:
        制冷电功率 = (T-上限)·hvac_kw_per_degC / COP   (T>上限)
        采暖电功率 = (下限-T)·hvac_kw_per_degC / COP   (T<下限)
    daily_variation: 逐日随机起伏的相对幅度(如0.15即±15%)。
    return_parts=True 时返回 (总负荷, 基础负荷, 冷暖负荷) 三条序列。
    """
    times = pd.DatetimeIndex(times)
    shape = daily_shape(kind)
    hour = times.hour.to_numpy()
    base = shape[hour]
    if seasonal:
        base = base * _seasonal_factor(times.dayofyear.to_numpy())
    if weekend_factor != 1.0:
        is_weekend = times.dayofweek.to_numpy() >= 5
        base = base * np.where(is_weekend, weekend_factor, 1.0)
    if daily_variation > 0:
        rng = np.random.default_rng(seed)
        d0 = times.normalize()
        ndays = d0.nunique()
        day_scale = 1.0 + rng.normal(0, daily_variation, ndays)
        day_scale = np.clip(day_scale, 0.4, 1.8)
        di = (d0 - d0[0]).days.to_numpy()
        base = base * day_scale[di]

    avg_kw = daily_kwh / 24.0
    base_kw = base / base.mean() * avg_kw          # 基础负荷(缩放到 daily_kwh)

    hvac_kw = np.zeros(len(times))
    if temp_air is not None and hvac_kw_per_degC > 0:
        T = np.asarray(temp_air, float)
        lo, hi = comfort_band
        cool = np.clip(T - hi, 0, None) * hvac_kw_per_degC / cop
        heat = np.clip(lo - T, 0, None) * hvac_kw_per_degC / cop
        hvac_kw = cool * _HVAC_COOL[hour] / _HVAC_COOL.mean() \
            + heat * _HVAC_HEAT[hour] / _HVAC_HEAT.mean()

    total = base_kw + hvac_kw
    if return_parts:
        return (pd.Series(total, index=times, name="load_kw"),
                pd.Series(base_kw, index=times, name="base_kw"),
                pd.Series(hvac_kw, index=times, name="hvac_kw"))
    return pd.Series(total, index=times, name="load_kw")
