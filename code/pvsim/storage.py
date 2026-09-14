"""Battery constraints, efficiency and aging."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Battery:

    capacity_kwh: float = 10.0
    power_kw: float = 5.0
    eta_chg: float = 0.95
    eta_dis: float = 0.95
    soc_min_frac: float = 0.10
    soc_max_frac: float = 1.00

    cycle_life_efc: float = 6000.0
    calendar_life_years: float = 15.0
    wear_cost_per_kwh: float = 0.10
    aging_temp_c: float = 25.0
    cal_aging_exponent: float = 0.75
    cyc_aging_exponent: float = 0.55

    dod_ref_frac: float = 1.0
    dod_stress_exponent: float = 1.0
    soc_ref_frac: float = 0.5
    soc_doubling_frac: float = 0.30

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

        from dataclasses import replace
        return replace(self, capacity_kwh=capacity_kwh)


@dataclass
class BatteryState:
    soc_kwh: float
    throughput_kwh: float = 0.0


def request(bat: Battery, st: BatteryState, p_kw: float, dt_h: float) -> float:

    if p_kw >= 0:
        p = min(p_kw, bat.power_kw)
        room_kwh = bat.soc_max_kwh - st.soc_kwh
        stored = p * dt_h * bat.eta_chg
        if stored > room_kwh:
            p = room_kwh / (dt_h * bat.eta_chg) if dt_h > 0 else 0.0
            stored = room_kwh
        st.soc_kwh += stored
        st.throughput_kwh += stored
        return p
    else:
        p = min(-p_kw, bat.power_kw)
        avail_kwh = st.soc_kwh - bat.soc_min_kwh
        drawn = p * dt_h / bat.eta_dis
        if drawn > avail_kwh:
            p = avail_kwh * bat.eta_dis / dt_h if dt_h > 0 else 0.0
            drawn = avail_kwh
        st.soc_kwh -= drawn
        return -p


def equivalent_full_cycles(bat: Battery, st: BatteryState) -> float:

    return st.throughput_kwh / bat.capacity_kwh if bat.capacity_kwh > 0 else 0.0


def _arrhenius(temp_c: float) -> float:

    return 2.0 ** ((temp_c - 25.0) / 10.0)


def capacity_fraction(
    bat: Battery,
    years: float,
    throughput_kwh: float,
    avg_dod_frac: float | None = None,
    avg_soc_frac: float | None = None,
) -> float:

    af = _arrhenius(bat.aging_temp_c)

    soc_factor = 1.0
    if avg_soc_frac is not None:
        soc_factor = 2.0 ** ((avg_soc_frac - bat.soc_ref_frac) / max(bat.soc_doubling_frac, 1e-9))
    cal = 0.20 * af * soc_factor * (years / max(bat.calendar_life_years, 1e-9)) ** bat.cal_aging_exponent

    dod_factor = 1.0
    if avg_dod_frac is not None and avg_dod_frac > 0:
        dod_factor = (avg_dod_frac / max(bat.dod_ref_frac, 1e-9)) ** bat.dod_stress_exponent
    efc_life_kwh = max(bat.cycle_life_efc * bat.capacity_kwh, 1e-9)
    cyc = 0.20 * af * dod_factor * (throughput_kwh / efc_life_kwh) ** bat.cyc_aging_exponent

    return max(1.0 - cal - cyc, 0.0)


def health_trajectory(
    bat: Battery,
    annual_throughput_kwh: float,
    horizon_years: int = 20,
    avg_dod_frac: float | None = None,
    avg_soc_frac: float | None = None,
) -> dict:

    import numpy as np
    years = np.arange(0, horizon_years + 1)
    cap_frac = np.array([
        capacity_fraction(
            bat, float(y), annual_throughput_kwh * y,
            avg_dod_frac=avg_dod_frac, avg_soc_frac=avg_soc_frac,
        )
        for y in years
    ])
    below = np.where(cap_frac < 0.80)[0]
    eol_year = float(years[below[0]]) if len(below) else float("inf")
    return {
        "years": years,
        "capacity_fraction": cap_frac,
        "capacity_kwh": cap_frac * bat.capacity_kwh,
        "eol_year": eol_year,
        "annual_efc": annual_throughput_kwh / bat.capacity_kwh if bat.capacity_kwh > 0 else 0.0,
    }
