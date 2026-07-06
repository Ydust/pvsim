"""多年衰减与寿命模型。

这是钙钛矿相对晶硅最大的劣势所在：晶硅极稳定（~0.5-0.7%/年, 25-30 年寿命），
钙钛矿对湿/热/UV/离子迁移敏感，初期 burn-in 大、年衰减快、设计寿命短。
钙钛矿衰减不确定性极大，故提供乐观/代表/悲观三种情景。

衰减曲线: 性能保持率 P(t)/P0
    - 初期 burn-in: [0, burn_in_years] 内由 1.0 线性降到 (1 - burn_in_loss)
    - 之后: 按年衰减率线性下降，下限 0
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .materials import CellTechnology


# 钙钛矿衰减情景 (burn_in 总损失, 年衰减率)
PEROVSKITE_SCENARIOS = {
    "乐观(改进封装)": dict(burn_in_loss=0.05, degradation_rate=0.010),
    "代表性": dict(burn_in_loss=0.10, degradation_rate=0.030),
    "悲观(早期器件)": dict(burn_in_loss=0.15, degradation_rate=0.060),
}


@dataclass
class DegradationProfile:
    burn_in_loss: float
    burn_in_years: float
    degradation_rate: float
    lifetime_years: float


def profile_for(tech: CellTechnology, scenario: str | None = None) -> DegradationProfile:
    """取技术的衰减参数；钙钛矿可指定情景覆盖。"""
    burn = tech.burn_in_loss
    rate = tech.degradation_rate
    if scenario and tech.name == "perovskite":
        s = PEROVSKITE_SCENARIOS[scenario]
        burn, rate = s["burn_in_loss"], s["degradation_rate"]
    return DegradationProfile(burn, tech.burn_in_years, rate, tech.lifetime_years)


def retention(prof: DegradationProfile, t_years) -> np.ndarray:
    """性能保持率 P(t)/P0（t 为运行年数, 可数组）。"""
    t = np.asarray(t_years, float)
    by = max(prof.burn_in_years, 1e-9)
    # burn-in 段线性
    burn = 1.0 - prof.burn_in_loss * np.clip(t / by, 0.0, 1.0)
    # burn-in 之后的线性衰减
    after = np.where(t > prof.burn_in_years,
                     prof.degradation_rate * (t - prof.burn_in_years), 0.0)
    return np.clip(burn - after, 0.0, 1.0)


def annual_retention_series(prof: DegradationProfile, horizon_years=None):
    """逐年(年中)平均保持率序列，用于累计发电量。"""
    n = int(np.ceil(horizon_years if horizon_years else prof.lifetime_years))
    mid = np.arange(n) + 0.5         # 取每年年中
    return retention(prof, mid)


def lifetime_energy(tech: CellTechnology, year1_energy_kwh: float,
                    scenario: str | None = None, horizon_years=None):
    """给定第1年发电量，按衰减推算逐年与累计发电量。

    返回 dict: years, yearly_kwh, cumulative_kwh, retention, t80_year。
    """
    prof = profile_for(tech, scenario)
    n = int(np.ceil(horizon_years if horizon_years else prof.lifetime_years))
    ret = annual_retention_series(prof, n)
    # 以第1年(年中保持率)归一，使第1年≈year1_energy
    yearly = year1_energy_kwh * ret / ret[0]
    cumulative = np.cumsum(yearly)
    # T80: 保持率首次跌破 0.8 的运行年
    fine_t = np.linspace(0, n, n * 12 + 1)
    fine_r = retention(prof, fine_t)
    below = np.where(fine_r < 0.80)[0]
    t80 = float(fine_t[below[0]]) if len(below) else float("inf")
    return {
        "years": np.arange(1, n + 1),
        "yearly_kwh": yearly,
        "cumulative_kwh": cumulative,
        "retention": ret,
        "t80_year": t80,
        "profile": prof,
    }
