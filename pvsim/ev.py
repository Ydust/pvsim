"""电动车充电桩负荷（车队 + 随机行为 + 涓流充电 + 可选 V2G 反向放电）。

把充电行为抽象成"充电会话"：哪天、几点插枪/拔枪、要补多少电、桩功率、车电池多大。
支持一队车(每天可能多辆), 到达/电量随机(固定种子可复现)。

由会话可得：
    无序充电 uncontrolled_demand：插枪即猛充(接近满时涓流减速) —— 常撞晚高峰。
    有序充电 flexible_demand：只要求拔枪前充够, 哪个小时充由打分决定(挪到光伏/谷电)。
    LP 聚合 daily_ev_aggregate：把每天在场车辆聚合成"一块可调度的车载电池"(供 ems 优化/ V2G)。

涓流(CC-CV近似)：荷电超过 ~80% 后充电功率线性降到额定的 ~25%。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class EVSession:
    day: int                 # 第几天(从0起)
    arrive_h: float          # 插枪时刻 (0-24)
    depart_h: float          # 拔枪时刻 (可>24 表示跨夜)
    energy_kwh: float        # 需补充的电量
    max_power_kw: float      # 充电桩功率上限
    battery_kwh: float = 60.0  # 车电池容量(用于涓流与V2G)
    v2g: bool = False        # 是否允许反向放电


# 典型场景 (到达均值h, 到达std, 停留h, 单次kWh, 桩kW, 车电池kWh)
_PROFILES = {
    "home": dict(arrive_mean=19.0, arrive_std=1.5, dwell=12.0, energy=10.0,
                 power=7.0, batt=60.0),
    "workplace": dict(arrive_mean=9.0, arrive_std=1.0, dwell=8.5, energy=10.0,
                      power=7.0, batt=60.0),
}


def fleet_sessions(kind: str = "home", n_vehicles: int = 1, n_days: int = 365,
                   charge_prob: float = 0.7, seed: int = 0) -> list[EVSession]:
    """生成一队车一年的充电会话列表。每辆车每天以 charge_prob 概率充一次。"""
    if kind not in _PROFILES:
        raise KeyError(f"未知充电场景 '{kind}', 可选: {list(_PROFILES)}")
    p = _PROFILES[kind]
    rng = np.random.default_rng(seed)
    out: list[EVSession] = []
    for v in range(n_vehicles):
        batt = float(max(30.0, rng.normal(p["batt"], 12.0)))   # 不同车不同电池
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
    """会话覆盖的时刻下标(含跨夜)。"""
    mask = (day_idx == s.day) & (hod >= s.arrive_h)
    if s.depart_h > 24:
        mask = mask | ((day_idx == s.day + 1) & (hod <= s.depart_h - 24))
    else:
        mask = mask & (hod <= s.depart_h)
    return np.where(mask)[0]


def _taper(frac_done: float) -> float:
    """涓流：已充比例 frac_done>0.8 后功率线性降到 0.25。"""
    if frac_done <= 0.8:
        return 1.0
    return max(0.25, 1.0 - (frac_done - 0.8) / 0.2 * 0.75)


def uncontrolled_demand(times: pd.DatetimeIndex,
                        sessions: list[EVSession]) -> pd.Series:
    """无序充电：插枪即按(带涓流的)最大功率充到补满。"""
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
    """有序充电：在窗口内按 preference 从高到低排时段充(含涓流功率上限)。"""
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
    """把每天在场车辆聚合成"一块车载电池"供 LP 优化调度使用。

    返回 {day: {idx, p_charge_cap, p_discharge_cap, energy_need, capacity}}，
    其中 idx 是当天窗口内的时刻下标(数组), p_*_cap 是各时刻可充/可放功率(数组),
    energy_need 是当天需净充入的电量, capacity 是可用作缓冲的总容量(V2G用)。
    """
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
            rec["cap"] += 0.5 * s.battery_kwh      # 最多借用半块车电池做缓冲
        rec["need"] += s.energy_kwh

    out = {}
    for d, rec in by_day.items():
        idx = np.where((rec["pc"] > 0) | (rec["pd"] > 0))[0]
        out[d] = dict(idx=idx, p_charge_cap=rec["pc"][idx],
                      p_discharge_cap=rec["pd"][idx],
                      energy_need=rec["need"], capacity=rec["cap"])
    return out
