"""组件 → 系统级仿真：阵列直流 → 逆变器 → 交流发电量。

把器件模型接到真实/合成气象时间序列上，算出系统级交流发电量 (kWh)、
比发电量 (kWh/kWp) 与性能比 PR——这些才是工程上对比两种技术运行表现的最终量。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import pvlib

from .materials import CellTechnology
from .cell import operating_point
from .module import array_dc_power, module_stc_power
from .temperature import cell_temperature
from .optics import effective_poa, bifacial_effective_irradiance
from .spectral import spectral_factor_from_zenith


@dataclass
class SystemConfig:
    n_modules: int = 20              # 组件数
    dc_ac_ratio: float = 1.2         # 直流/交流容量比 (逆变器相对偏小→高辐照时削顶)
    inverter_eta_nom: float = 0.96   # 逆变器标称效率
    dc_loss: float = 0.05            # 直流侧损失(污渍/线损/灰尘), 不含失配
    mismatch_loss: float = 0.02      # 组件间失配损失
    apply_spectral: bool = True      # 是否计入光谱失配
    apply_temperature: bool = True   # 是否计入温度降额(False→电池恒25°C, 供温度反事实分解)
    apply_iam: bool = True           # 是否计入入射角损失
    apply_bifacial: bool = True      # 是否计入双面增益(由技术 bifaciality 决定)
    # --- 稳健性分析旋钮 (默认值保持基线结果不变) ---
    albedo: float = 0.2              # 地面反照率 (沙漠/雪地高, 湿润区低)
    rear_view_factor: float = 0.4    # 双面背面视角因子
    thermal_u0: float = 25.0         # Faiman 散热系数 u0 (开放支架)
    thermal_u1: float = 6.84         # Faiman 散热系数 u1
    bifaciality_override: float | None = None  # 覆盖技术 bifaciality (None=用材料值)


def inverter_ac(dc_power, pdc0, eta_nom=0.96):
    """PVWatts 逆变器模型：直流→交流, 超过额定时削顶 (clipping)。"""
    return np.asarray(pvlib.inverter.pvwatts(np.asarray(dc_power, float),
                                             pdc0, eta_inv_nom=eta_nom))


def array_kwp(tech: CellTechnology, cfg: SystemConfig) -> float:
    """阵列 STC 额定容量 (kWp)。"""
    return cfg.n_modules * module_stc_power(tech) / 1000.0


def simulate(tech: CellTechnology, weather: pd.DataFrame, cfg: SystemConfig,
             npts: int = 120) -> dict:
    """对给定气象时间序列做系统级仿真。

    weather 需含列: poa_global, poa_direct, poa_diffuse, aoi,
                    temp_air, wind_speed, solar_zenith, ghi。
    返回 dict: 含逐时 DataFrame 和汇总指标。
    """
    w = weather
    poa_global = w["poa_global"].to_numpy(float)

    # 1) 入射角修正 → 有效 POA
    if cfg.apply_iam:
        eff = effective_poa(w["poa_direct"].to_numpy(float),
                            w["poa_diffuse"].to_numpy(float),
                            w["aoi"].to_numpy(float))
    else:
        eff = poa_global.copy()

    # 2) 双面增益 (早期晶硅 bifaciality=0 → 无增益)
    bifac = tech.bifaciality if cfg.bifaciality_override is None else cfg.bifaciality_override
    if cfg.apply_bifacial and bifac > 0:
        eff = bifacial_effective_irradiance(eff, w["ghi"].to_numpy(float),
                                            bifac, albedo=cfg.albedo,
                                            rear_view_factor=cfg.rear_view_factor)

    # 3) 光谱失配
    if cfg.apply_spectral:
        sf = spectral_factor_from_zenith(tech, w["solar_zenith"].to_numpy(float))
        eff = eff * sf
    else:
        sf = np.ones_like(poa_global)

    # 4) 电池温度 (apply_temperature=False → 恒25°C, 用于"温度机制"反事实分解)
    if cfg.apply_temperature:
        tcell = cell_temperature(poa_global, w["temp_air"].to_numpy(float),
                                 w["wind_speed"].to_numpy(float), model="faiman",
                                 u0=cfg.thermal_u0, u1=cfg.thermal_u1)
    else:
        tcell = np.full_like(poa_global, 25.0)

    # 5) 阵列直流功率 (效率分母用宽谱 POA, 电流用有效辐照)
    dc = array_dc_power(tech, poa_global, tcell, n_modules=cfg.n_modules,
                        effective_irradiance=eff,
                        mismatch_loss=cfg.mismatch_loss, npts=npts)
    dc = np.atleast_1d(dc) * (1.0 - cfg.dc_loss)

    # 6) 逆变器 → 交流 (含削顶)
    kwp = array_kwp(tech, cfg)
    pdc0 = kwp * 1000.0 / cfg.dc_ac_ratio          # 逆变器直流额定
    ac = inverter_ac(dc, pdc0, cfg.inverter_eta_nom)

    # 时间步长 (小时)
    idx = w.index
    if isinstance(idx, pd.DatetimeIndex) and len(idx) > 1:
        dt_h = (idx[1] - idx[0]).total_seconds() / 3600.0
    else:
        dt_h = 1.0

    energy_dc_kwh = float(np.sum(dc) * dt_h / 1000.0)
    energy_ac_kwh = float(np.sum(ac) * dt_h / 1000.0)
    poa_insol_kwh_m2 = float(np.sum(poa_global) * dt_h / 1000.0)

    specific_yield = energy_ac_kwh / kwp if kwp > 0 else 0.0   # kWh/kWp
    # 性能比 PR = 实际产出 / 理论产出(按 POA 与额定)
    ref_yield = poa_insol_kwh_m2 / 1.0     # kWh/kWp 等效 (G_STC=1kW/m^2)
    pr = specific_yield / ref_yield if ref_yield > 0 else 0.0

    out = pd.DataFrame({
        "poa_global": poa_global,
        "eff_irradiance": eff,
        "spectral_factor": sf,
        "tcell": tcell,
        "dc_power": dc,
        "ac_power": ac,
    }, index=idx)

    return {
        "timeseries": out,
        "kwp": kwp,
        "energy_dc_kwh": energy_dc_kwh,
        "energy_ac_kwh": energy_ac_kwh,
        "specific_yield": specific_yield,
        "performance_ratio": pr,
        "poa_insolation_kwh_m2": poa_insol_kwh_m2,
        "clipping_kwh": max(0.0, energy_dc_kwh * cfg.inverter_eta_nom - energy_ac_kwh),
    }


def simulate_rooftop(tech: CellTechnology, raw_weather: pd.DataFrame, location,
                     cfg: SystemConfig, facets) -> dict:
    """多朝向屋顶：每个屋面单独转置辐照(POA)再仿真, 汇总交流功率。

    raw_weather 需含 ghi/dni/dhi/temp_air/wind_speed(from_pvgis_tmy / make_weather 的输出均可)。
    facets: [(倾角°, 方位角°, 组件数), ...]，方位角 180=正南, 90=正东, 270=正西。
    各屋面视作独立子阵+逆变器, 交流侧相加。返回 {ac_power, kwp, parts, specific_yield}。
    """
    from dataclasses import replace
    from .weather import make_weather

    total_ac = None
    total_kwp = 0.0
    parts = {}
    for tilt, azimuth, nmod in facets:
        w = make_weather(raw_weather.index, location,
                         raw_weather["ghi"], raw_weather["dni"], raw_weather["dhi"],
                         raw_weather["temp_air"], raw_weather["wind_speed"],
                         surface_tilt=tilt, surface_azimuth=azimuth)
        r = simulate(tech, w, replace(cfg, n_modules=nmod), npts=80)
        ac = r["timeseries"]["ac_power"]
        total_ac = ac if total_ac is None else total_ac + ac
        total_kwp += r["kwp"]
        parts[(tilt, azimuth)] = ac
    dt_h = (total_ac.index[1] - total_ac.index[0]).total_seconds() / 3600.0
    energy = float(total_ac.sum()) * dt_h / 1000.0
    return {"ac_power": total_ac, "kwp": total_kwp, "parts": parts,
            "energy_ac_kwh": energy,
            "specific_yield": energy / total_kwp if total_kwp > 0 else 0.0}
