"""Electric vehicle charging demand."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class EVSession:
    day: int
    arrive_h: float
    depart_h: float
    energy_kwh: float
    max_power_kw: float
    battery_kwh: float = 60.0
    v2g: bool = False


_PROFILES = {
    "home": dict(arrive_mean=19.0, arrive_std=1.5, dwell=12.0, energy=10.0,
                 power=7.0, batt=60.0),
    "workplace": dict(arrive_mean=9.0, arrive_std=1.0, dwell=8.5, energy=10.0,
                      power=7.0, batt=60.0),
}


def fleet_sessions(kind: str = "home", n_vehicles: int = 1, n_days: int = 365,
                   charge_prob: float = 0.7, seed: int = 0) -> list[EVSession]:

    if kind not in _PROFILES:
        raise KeyError(f"Unknown charging scenario '{kind}', optional: {list(_PROFILES)}")
    p = _PROFILES[kind]
    rng = np.random.default_rng(seed)
    out: list[EVSession] = []
    for v in range(n_vehicles):
        batt = float(max(30.0, rng.normal(p["batt"], 12.0)))
        for d in range(n_days):
            if rng.random() > charge_prob:
                continue
            arrive = float(np.clip(rng.normal(p["arrive_mean"], p["arrive_std"]), 0, 23.5))
            energy = float(np.clip(rng.normal(p["energy"], p["energy"] * 0.3),
                                   2.0, 0.7 * batt))
            out.append(EVSession(day=d, arrive_h=arrive, depart_h=arrive + p["dwell"],
                                 energy_kwh=energy, max_power_kw=p["power"],
                                 battery_kwh=batt, v2g=False))
    return out


def _dt_hours(times: pd.DatetimeIndex) -> float:
    return (times[1] - times[0]).total_seconds() / 3600.0 if len(times) > 1 else 1.0


def _window_idx(times, hod, day_idx, s: EVSession):

    mask = (day_idx == s.day) & (hod >= s.arrive_h)
    if s.depart_h > 24:
        mask = mask | ((day_idx == s.day + 1) & (hod <= s.depart_h - 24))
    else:
        mask = mask & (hod <= s.depart_h)
    return np.where(mask)[0]


def _taper(frac_done: float) -> float:

    if frac_done <= 0.8:
        return 1.0
    return max(0.25, 1.0 - (frac_done - 0.8) / 0.2 * 0.75)


def uncontrolled_demand(times: pd.DatetimeIndex,
                        sessions: list[EVSession]) -> pd.Series:

    times = pd.DatetimeIndex(times)
    dt = _dt_hours(times)
    demand = np.zeros(len(times))
    d0 = times.normalize()[0]
    hod = times.hour.to_numpy() + times.minute.to_numpy() / 60.0
    day_idx = (times.normalize() - d0).days.to_numpy()
    for s in sessions:
        idxs = _window_idx(times, hod, day_idx, s)
        done = 0.0
        for i in idxs:
            if done >= s.energy_kwh - 1e-9:
                break
            pmax = s.max_power_kw * _taper(done / s.energy_kwh)
            step = min(pmax * dt, s.energy_kwh - done)
            demand[i] += step / dt
            done += step
    return pd.Series(demand, index=times, name="ev_kw")


def flexible_demand(times: pd.DatetimeIndex, sessions: list[EVSession],
                    preference: np.ndarray) -> pd.Series:

    times = pd.DatetimeIndex(times)
    dt = _dt_hours(times)
    demand = np.zeros(len(times))
    d0 = times.normalize()[0]
    hod = times.hour.to_numpy() + times.minute.to_numpy() / 60.0
    day_idx = (times.normalize() - d0).days.to_numpy()
    pref = np.asarray(preference, float)
    for s in sessions:
        win = _window_idx(times, hod, day_idx, s)
        if len(win) == 0:
            continue
        order = win[np.argsort(-pref[win])]
        done = 0.0
        for i in order:
            if done >= s.energy_kwh - 1e-9:
                break
            pmax = s.max_power_kw * _taper(done / s.energy_kwh)
            step = min(pmax * dt, s.energy_kwh - done)
            demand[i] += step / dt
            done += step
    return pd.Series(demand, index=times, name="ev_kw")


def daily_ev_aggregate(times: pd.DatetimeIndex, sessions: list[EVSession],
                       allow_v2g: bool = False) -> dict:

    times = pd.DatetimeIndex(times)
    n = len(times)
    d0 = times.normalize()[0]
    hod = times.hour.to_numpy() + times.minute.to_numpy() / 60.0
    day_idx = (times.normalize() - d0).days.to_numpy()

    by_day: dict[int, dict] = {}
    for s in sessions:
        win = _window_idx(times, hod, day_idx, s)
        if len(win) == 0:
            continue
        rec = by_day.setdefault(s.day, dict(pc=np.zeros(n), pd=np.zeros(n),
                                            need=0.0, cap=0.0))
        rec["pc"][win] += s.max_power_kw
        if allow_v2g and s.v2g:
            rec["pd"][win] += s.max_power_kw
            rec["cap"] += 0.5 * s.battery_kwh
        rec["need"] += s.energy_kwh

    out = {}
    for d, rec in by_day.items():
        idx = np.where((rec["pc"] > 0) | (rec["pd"] > 0))[0]
        out[d] = dict(idx=idx, p_charge_cap=rec["pc"][idx],
                      p_discharge_cap=rec["pd"][idx],
                      energy_need=rec["need"], capacity=rec["cap"])
    return out
