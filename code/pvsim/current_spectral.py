"""光谱响应与光谱失配。

晶硅吸收到近红外 (~1100nm)，钙钛矿在带隙 (~800nm) 锐截止、蓝光响应好。
不同太阳几何下的晴空光谱会发生变化。正午光谱更蓝,早晚因大气质量增加而红移。
本模块量化的是 SPECTRL2 晴空谱中的太阳天顶角和大气质量效应,不包含云致光谱蓝移。

两端钙钛矿/晶硅叠层不使用单一宽谱 EQE。顶电池和受顶电池滤光后的硅底电池
分别积分光生电流。基准响应族先分别按各自参考电流归一化，再取较小值，
等价于固定收集系数使参考态电流匹配，并非直接取未经缩放的原始电流之比。
两个带隙的反向温度漂移
也进入匹配计算，因此可以表达 2T 器件偏离 STC 电流匹配的行为。

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


HC_EV_NM = 1239.841984
TANDEM_TOP_EG_REF = 1.68
TANDEM_TOP_DEG_DT = 0.0003
TANDEM_BOTTOM_EG_REF = 1.121
TANDEM_BOTTOM_DEG_DT = -0.0002677 * TANDEM_BOTTOM_EG_REF  # eV/K from relative coefficient in 1/K


def _band_response(
    wl_nm: np.ndarray,
    lambda_min: float,
    lambda_gap: float,
    eqe_peak: float,
    edge_width: float,
    blue_rolloff: float,
) -> np.ndarray:
    wl = np.asarray(wl_nm, float)
    blue = 1.0 / (
        1.0 + np.exp(-(wl - lambda_min) / (blue_rolloff / 4.0))
    )
    red = 1.0 / (
        1.0 + np.exp((wl - lambda_gap) / (edge_width / 4.0))
    )
    return eqe_peak * blue * red


def eqe(tech: CellTechnology, wl_nm: np.ndarray) -> np.ndarray:
    """外量子效率 EQE(λ) 简化模型：蓝端上升 + 平台 + 带隙锐截止。

    用两个 sigmoid 拼出梯形：短波端在 lambda_min 附近升起，
    长波端在 lambda_gap (带隙) 附近按 edge_width 锐截止。
    """
    sr = tech.spectral
    return _band_response(
        wl_nm,
        sr.lambda_min,
        sr.lambda_gap,
        sr.eqe_peak,
        sr.edge_width,
        sr.blue_rolloff,
    )


def _jph_weight(eqe_vals: np.ndarray, E: np.ndarray, wl: np.ndarray) -> float:
    """光生电流权重 ∝ ∫ EQE(λ)·E(λ)·λ dλ （λ 把能量谱转成光子通量, 常数已约去）。"""
    integrand = eqe_vals * E * wl
    return float(np.trapezoid(integrand, wl))


def _broadband(E: np.ndarray, wl: np.ndarray) -> float:
    """宽谱辐照 ∫ E dλ (W/m^2)。"""
    return float(np.trapezoid(E, wl))


def _tandem_subcell_weights(
    wl_nm: np.ndarray, E: np.ndarray, tcell_C: float
) -> tuple[float, float]:
    """Return top and filtered-bottom photon-current weights for a 2T tandem."""
    delta_t = float(tcell_C) - 25.0
    eg_top = TANDEM_TOP_EG_REF + TANDEM_TOP_DEG_DT * delta_t
    eg_bottom = TANDEM_BOTTOM_EG_REF + TANDEM_BOTTOM_DEG_DT * delta_t
    lambda_top = HC_EV_NM / eg_top
    lambda_bottom = HC_EV_NM / eg_bottom

    top_collection = _band_response(
        wl_nm, 350.0, lambda_top, 0.90, 25.0, 60.0
    )
    top_absorption = _band_response(
        wl_nm, 330.0, lambda_top, 0.97, 20.0, 50.0
    )
    silicon_collection = _band_response(
        wl_nm, 350.0, lambda_bottom, 0.95, 50.0, 70.0
    )
    bottom_collection = silicon_collection * np.clip(1.0 - top_absorption, 0.0, 1.0)
    return (
        _jph_weight(top_collection, E, np.asarray(wl_nm, float)),
        _jph_weight(bottom_collection, E, np.asarray(wl_nm, float)),
    )


@lru_cache(maxsize=1)
def reference_am15g():
    """ASTM G173 AM1.5G 全局倾斜参考光谱 (波长 nm, 光谱辐照 W/m^2/nm)。"""
    df = pvlib.spectrum.get_reference_spectra(standard="ASTM G173-03")
    wl = df.index.to_numpy(dtype=float)
    E = df["global"].to_numpy(dtype=float)
    return wl, E


@lru_cache(maxsize=1)
def _tandem_reference_subcell_yields() -> tuple[float, float]:
    wl, E = reference_am15g()
    broadband = _broadband(E, wl)
    top, bottom = _tandem_subcell_weights(wl, E, 25.0)
    return top / broadband, bottom / broadband


def tandem_subcell_relative_currents(
    wl_nm: np.ndarray, E: np.ndarray, tcell_C: float = 25.0
) -> tuple[float, float]:
    """Subcell currents per broadband watt, normalized to each AM1.5G value."""
    wl = np.asarray(wl_nm, float)
    spectrum = np.asarray(E, float)
    broadband = _broadband(spectrum, wl)
    if broadband <= 0:
        return 0.0, 0.0
    top, bottom = _tandem_subcell_weights(wl, spectrum, tcell_C)
    top_ref, bottom_ref = _tandem_reference_subcell_yields()
    return top / broadband / top_ref, bottom / broadband / bottom_ref


def tandem_current_matching_factor(
    wl_nm: np.ndarray, E: np.ndarray, tcell_C: float = 25.0,
    *, normalization: str = "reference_matched",
) -> float:
    """Relative 2T current in a specified idealized response family.

    The historical/default family assumes reference-current matching by fixed
    collection attenuation of the higher-current subcell. It does not establish
    a complete device design consistent with independently prescribed STC power.
    ``unscaled_ratio`` preserves the raw EQE integrals' reference-current ratio
    as a structural control, also holding the separate electrical model fixed.
    """
    if normalization == "unscaled_ratio":
        wl = np.asarray(wl_nm, float)
        broadband = _broadband(np.asarray(E, float), wl)
        if broadband <= 0:
            return 0.0
        top, bottom = _tandem_subcell_weights(wl, np.asarray(E, float), tcell_C)
        top_ref, bottom_ref = _tandem_reference_subcell_yields()
        return float(min(top, bottom) / broadband / min(top_ref, bottom_ref))
    if normalization != "reference_matched":
        raise ValueError(f"Unknown tandem normalization: {normalization}")
    top, bottom = tandem_subcell_relative_currents(wl_nm, E, tcell_C)
    return float(min(top, bottom))


def spectral_mismatch_factor(tech: CellTechnology, wl_nm, E) -> float:
    """给定光谱 (wl_nm, E[W/m^2/nm]) 下该技术的光谱失配因子 SF。"""
    if tech.name == "tandem":
        return tandem_current_matching_factor(wl_nm, E, 25.0)

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


@lru_cache(maxsize=1)
def _tandem_sf_table(
    n_zenith: int = 13, n_temperature: int = 10
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    zeniths = np.linspace(0.0, 88.0, n_zenith)
    temperatures = np.linspace(-10.0, 80.0, n_temperature)
    values = np.empty((n_temperature, n_zenith), dtype=float)
    spectra = [generate_spectrum(float(zenith)) for zenith in zeniths]
    for ti, temperature in enumerate(temperatures):
        for zi, (wl, spectrum) in enumerate(spectra):
            values[ti, zi] = tandem_current_matching_factor(
                wl, spectrum, float(temperature)
            )
    return zeniths, temperatures, values


def _bilinear_lookup(
    x,
    y,
    x_grid: np.ndarray,
    y_grid: np.ndarray,
    values: np.ndarray,
) -> np.ndarray:
    x_arr, y_arr = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float))
    x_clip = np.clip(x_arr, x_grid[0], x_grid[-1])
    y_clip = np.clip(y_arr, y_grid[0], y_grid[-1])
    xi = np.clip(np.searchsorted(x_grid, x_clip, side="right") - 1, 0, len(x_grid) - 2)
    yi = np.clip(np.searchsorted(y_grid, y_clip, side="right") - 1, 0, len(y_grid) - 2)
    xf = (x_clip - x_grid[xi]) / (x_grid[xi + 1] - x_grid[xi])
    yf = (y_clip - y_grid[yi]) / (y_grid[yi + 1] - y_grid[yi])
    v00 = values[yi, xi]
    v10 = values[yi, xi + 1]
    v01 = values[yi + 1, xi]
    v11 = values[yi + 1, xi + 1]
    return (
        v00 * (1.0 - xf) * (1.0 - yf)
        + v10 * xf * (1.0 - yf)
        + v01 * (1.0 - xf) * yf
        + v11 * xf * yf
    )


@lru_cache(maxsize=1)
def _tandem_reference_temperature_table(
    n_temperature: int = 19,
) -> tuple[np.ndarray, np.ndarray]:
    temperatures = np.linspace(-10.0, 80.0, n_temperature)
    wl, spectrum = reference_am15g()
    values = np.array(
        [
            tandem_current_matching_factor(wl, spectrum, float(temperature))
            for temperature in temperatures
        ]
    )
    return temperatures, values


def tandem_reference_spectrum_factor(tcell_C) -> np.ndarray:
    """2T current-matching factor at AM1.5G while retaining temperature shift."""
    temperatures, values = _tandem_reference_temperature_table()
    return np.interp(
        np.clip(np.asarray(tcell_C, float), temperatures[0], temperatures[-1]),
        temperatures,
        values,
    )


def spectral_factor_from_zenith(
    tech: CellTechnology, zenith_deg, tcell_C=None
) -> np.ndarray:
    """由太阳天顶角插值得到光谱失配因子 SF（时间序列用，避免逐时跑 SPECTRL2）。"""
    zen = np.asarray(zenith_deg, float)
    if tech.name == "tandem":
        temperature = 25.0 if tcell_C is None else tcell_C
        zeniths, temperatures, values = _tandem_sf_table()
        return _bilinear_lookup(zen, temperature, zeniths, temperatures, values)
    zt, sft = _sf_table(tech.name)
    sf = np.interp(np.clip(zen, 0.0, 88.0), zt, sft)
    return sf
