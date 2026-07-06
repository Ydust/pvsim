"""光谱响应与光谱失配。

晶硅吸收到近红外 (~1100nm)，钙钛矿在带隙 (~800nm) 锐截止、蓝光响应好。
不同太阳几何下的晴空光谱会发生变化。正午光谱更蓝,早晚因大气质量增加而红移。
本模块量化的是 SPECTRL2 晴空谱中的太阳天顶角和大气质量效应,不包含云致光谱蓝移。

核心量: 光谱失配因子 SF (spectral mismatch factor)
    SF = (Jph(光谱)/G_broadband(光谱)) / (Jph(AM1.5G)/1000)
    物理含义: 相比 STC 标定光谱, 单位宽谱辐照下该电池多产/少产多少电流。
    SF=1 即 AM1.5G; SF>1 表示该光谱对此电池更"友好"。
有效辐照 effective_irradiance = 宽谱POA辐照 × SF, 再送入电池模型。

参考光谱用 ASTM G173 (pvlib)，任意工况光谱用 SPECTRL2 (Bird & Riordan, pvlib) 生成。
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
import pvlib

from .materials import CellTechnology


def eqe(tech: CellTechnology, wl_nm: np.ndarray) -> np.ndarray:
    """外量子效率 EQE(λ) 简化模型：蓝端上升 + 平台 + 带隙锐截止。

    用两个 sigmoid 拼出梯形：短波端在 lambda_min 附近升起，
    长波端在 lambda_gap (带隙) 附近按 edge_width 锐截止。
    """
    sr = tech.spectral
    wl = np.asarray(wl_nm, float)
    # 蓝端上升 (在 lambda_min 处约为 0.5)
    blue = 1.0 / (1.0 + np.exp(-(wl - sr.lambda_min) / (sr.blue_rolloff / 4.0)))
    # 带隙截止 (在 lambda_gap 处约为 0.5)
    red = 1.0 / (1.0 + np.exp((wl - sr.lambda_gap) / (sr.edge_width / 4.0)))
    return sr.eqe_peak * blue * red


def _jph_weight(eqe_vals: np.ndarray, E: np.ndarray, wl: np.ndarray) -> float:
    """光生电流权重 ∝ ∫ EQE(λ)·E(λ)·λ dλ （λ 把能量谱转成光子通量, 常数已约去）。"""
    integrand = eqe_vals * E * wl
    return float(np.trapezoid(integrand, wl))


def _broadband(E: np.ndarray, wl: np.ndarray) -> float:
    """宽谱辐照 ∫ E dλ (W/m^2)。"""
    return float(np.trapezoid(E, wl))


@lru_cache(maxsize=1)
def reference_am15g():
    """ASTM G173 AM1.5G 全局倾斜参考光谱 (波长 nm, 光谱辐照 W/m^2/nm)。"""
    df = pvlib.spectrum.get_reference_spectra(standard="ASTM G173-03")
    wl = df.index.to_numpy(dtype=float)
    E = df["global"].to_numpy(dtype=float)
    return wl, E


def spectral_mismatch_factor(tech: CellTechnology, wl_nm, E) -> float:
    """给定光谱 (wl_nm, E[W/m^2/nm]) 下该技术的光谱失配因子 SF。"""
    wl = np.asarray(wl_nm, float)
    E = np.asarray(E, float)
    # 该光谱下的电流权重 / 宽谱辐照
    jph = _jph_weight(eqe(tech, wl), E, wl)
    g = _broadband(E, wl)
    ratio_spec = jph / g if g > 0 else 0.0
    # AM1.5G 参考
    wl_ref, E_ref = reference_am15g()
    jph_ref = _jph_weight(eqe(tech, wl_ref), E_ref, wl_ref)
    g_ref = _broadband(E_ref, wl_ref)
    ratio_ref = jph_ref / g_ref
    return ratio_spec / ratio_ref if ratio_ref > 0 else 1.0


def generate_spectrum(apparent_zenith: float, surface_tilt: float = 0.0,
                      ground_albedo: float = 0.2, pressure: float = 101325.0,
                      precipitable_water: float = 1.4, ozone: float = 0.3,
                      aod500: float = 0.1, dayofyear: int = 172):
    """用 SPECTRL2 生成给定太阳天顶角下的 POA 全局光谱 (clear-sky)。

    返回 (wl_nm, E[W/m^2/nm])。天顶角越大 (早晚) → 大气程长越长 → 光谱越红移。
    """
    am = pvlib.atmosphere.get_relative_airmass(apparent_zenith)
    if not np.isfinite(am):
        am = 40.0
    aoi = apparent_zenith if surface_tilt == 0.0 else abs(apparent_zenith - surface_tilt)
    out = pvlib.spectrum.spectrl2(
        apparent_zenith=apparent_zenith,
        aoi=aoi,
        surface_tilt=surface_tilt,
        ground_albedo=ground_albedo,
        surface_pressure=pressure,
        relative_airmass=am,
        precipitable_water=precipitable_water,
        ozone=ozone,
        aerosol_turbidity_500nm=aod500,
        dayofyear=dayofyear,
    )
    wl = np.asarray(out["wavelength"], float)
    E = np.asarray(out["poa_global"], float).ravel()
    return wl, E


# 几种代表性光谱条件 (天顶角)
SPECTRUM_CONDITIONS = {
    "正午(高太阳)": 20.0,
    "上午/下午": 60.0,
    "清晨/傍晚(低太阳)": 78.0,
}


def condition_spectral_factors(tech: CellTechnology) -> dict:
    """返回该技术在各代表性光谱条件下的 SF。"""
    result = {}
    for label, zen in SPECTRUM_CONDITIONS.items():
        wl, E = generate_spectrum(zen)
        result[label] = spectral_mismatch_factor(tech, wl, E)
    return result


@lru_cache(maxsize=8)
def _sf_table(tech_name: str, n: int = 13):
    """预计算 SF 关于太阳天顶角的查表 (天顶角 0..88°)。"""
    from .materials import get_technology
    tech = get_technology(tech_name)
    zeniths = np.linspace(0.0, 88.0, n)
    sfs = []
    for z in zeniths:
        wl, E = generate_spectrum(float(z))
        sfs.append(spectral_mismatch_factor(tech, wl, E))
    return zeniths, np.array(sfs)


def spectral_factor_from_zenith(tech: CellTechnology, zenith_deg) -> np.ndarray:
    """由太阳天顶角插值得到光谱失配因子 SF（时间序列用，避免逐时跑 SPECTRL2）。"""
    zen = np.asarray(zenith_deg, float)
    zt, sft = _sf_table(tech.name)
    sf = np.interp(np.clip(zen, 0.0, 88.0), zt, sft)
    return sf
