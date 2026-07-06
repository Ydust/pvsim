"""电池储能模型（功率/容量约束 + 充放电效率 + 荷电状态 SOC + 多年老化）。

负责"电池这块硬件"的物理：能存多少、出力多大、来回有多少损耗、当前还剩多少电，
以及**用久了/用狠了容量会掉多少**（老化）。具体什么时候充放由 ems.py 决定。

约定：功率 p_kw 在"交流侧/系统侧"计量。
    p_kw > 0  充电（系统把电送进电池）
    p_kw < 0  放电（电池把电送回系统）
充进电池 = p_kw·Δt·η_chg；放电时电池实际放出 = |p_kw|·Δt/η_dis。

老化（容量衰减到额定的 80% 视为寿命终点 EOL）：
    日历老化：随时间, 与温度相关(Arrhenius, 每升10°C约快一倍)。
    循环老化：随累计吞吐(等效满循环数)。
    两者叠加。参数取磷酸铁锂(LFP)代表值: 循环寿命~6000次, 日历寿命~15年到80%。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Battery:
    """电池参数（典型家用/工商业磷酸铁锂）。"""
    capacity_kwh: float = 10.0       # 额定(全新)容量 kWh
    power_kw: float = 5.0            # 最大充/放电功率 kW
    eta_chg: float = 0.95           # 充电效率
    eta_dis: float = 0.95           # 放电效率
    soc_min_frac: float = 0.10      # 最低可用荷电(保护电池)
    soc_max_frac: float = 1.00      # 最高荷电
    # --- 老化参数 ---
    cycle_life_efc: float = 6000.0   # 等效满循环数到 80% 容量(LFP)
    calendar_life_years: float = 15.0  # 仅日历老化到 80% 的年数
    wear_cost_per_kwh: float = 0.10  # 每吞吐 1kWh 的折旧成本(元), 供经济调度/核算
    aging_temp_c: float = 25.0       # 电池平均工作温度(影响日历老化)

    @property
    def soc_min_kwh(self) -> float:
        return self.soc_min_frac * self.capacity_kwh

    @property
    def soc_max_kwh(self) -> float:
        return self.soc_max_frac * self.capacity_kwh

    @property
    def usable_kwh(self) -> float:
        return self.soc_max_kwh - self.soc_min_kwh

    def scaled(self, capacity_kwh: float) -> "Battery":
        """返回一个容量被改写的副本(其余参数不变), 用于"第N年容量"下的仿真。"""
        from dataclasses import replace
        return replace(self, capacity_kwh=capacity_kwh)


@dataclass
class BatteryState:
    soc_kwh: float                  # 当前电量 kWh
    throughput_kwh: float = 0.0     # 累计吞吐(进电池的电量), 用于循环老化


def request(bat: Battery, st: BatteryState, p_kw: float, dt_h: float) -> float:
    """请求以 p_kw 充(+)/放(-)电 dt_h 小时，按物理上限裁剪并更新 SOC。

    返回**实际**发生的交流侧功率 (kW, 符号同 p_kw)。
    """
    if p_kw >= 0:   # ---- 充电 ----
        p = min(p_kw, bat.power_kw)
        room_kwh = bat.soc_max_kwh - st.soc_kwh
        stored = p * dt_h * bat.eta_chg
        if stored > room_kwh:
            p = room_kwh / (dt_h * bat.eta_chg) if dt_h > 0 else 0.0
            stored = room_kwh
        st.soc_kwh += stored
        st.throughput_kwh += stored
        return p
    else:           # ---- 放电 ----
        p = min(-p_kw, bat.power_kw)
        avail_kwh = st.soc_kwh - bat.soc_min_kwh
        drawn = p * dt_h / bat.eta_dis
        if drawn > avail_kwh:
            p = avail_kwh * bat.eta_dis / dt_h if dt_h > 0 else 0.0
            drawn = avail_kwh
        st.soc_kwh -= drawn
        return -p


def equivalent_full_cycles(bat: Battery, st: BatteryState) -> float:
    """等效满充放循环数 = 累计吞吐 / 容量。"""
    return st.throughput_kwh / bat.capacity_kwh if bat.capacity_kwh > 0 else 0.0


# ---------------- 多年老化 ----------------
def _arrhenius(temp_c: float) -> float:
    """日历老化温度加速因子：以25°C为基准, 每升10°C约快一倍。"""
    return 2.0 ** ((temp_c - 25.0) / 10.0)


def capacity_fraction(bat: Battery, years: float, throughput_kwh: float) -> float:
    """给定运行年数与累计吞吐，返回剩余容量比例(相对全新)。

    衰减到 0.80 视为寿命终点；日历+循环线性叠加(工程常用近似)。
    """
    cal = 0.20 / max(bat.calendar_life_years, 1e-9) * years * _arrhenius(bat.aging_temp_c)
    cyc = 0.20 / max(bat.cycle_life_efc * bat.capacity_kwh, 1e-9) * throughput_kwh
    return max(1.0 - cal - cyc, 0.0)


def health_trajectory(bat: Battery, annual_throughput_kwh: float,
                      horizon_years: int = 20) -> dict:
    """逐年容量轨迹 + 何时跌破 80%(需更换)。annual_throughput_kwh: 每年吞吐量。"""
    import numpy as np
    years = np.arange(0, horizon_years + 1)
    cap_frac = np.array([capacity_fraction(bat, float(y), annual_throughput_kwh * y)
                         for y in years])
    below = np.where(cap_frac < 0.80)[0]
    eol_year = float(years[below[0]]) if len(below) else float("inf")
    return {
        "years": years,
        "capacity_fraction": cap_frac,
        "capacity_kwh": cap_frac * bat.capacity_kwh,
        "eol_year": eol_year,                # 跌破80%的年份(需更换)
        "annual_efc": annual_throughput_kwh / bat.capacity_kwh if bat.capacity_kwh > 0 else 0.0,
    }
