"""Grid connection and operating constraints."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class FeederConfig:
    dvdp_pu_per_kw: float = 0.0009
    dvdq_pu_per_kvar: float = 0.0007
    v_ref_pu: float = 1.02
    v_upper_pu: float = 1.07
    v_lower_pu: float = 0.93
    vv_deadband: float = 0.02
    transformer_kva: float = 100.0
    n_houses: int = 20
    pf_min: float = 0.95


def _q_capability(p_kw: float, s_rating_kw: float, pf_min: float) -> float:

    p = abs(p_kw)
    q_by_pf = p * np.tan(np.arccos(pf_min)) if p > 1e-6 else s_rating_kw * 0.3
    q_by_s = np.sqrt(max(s_rating_kw**2 - p**2, 0.0))
    return float(min(q_by_pf, q_by_s))


def voltage(p_net_house_kw, q_house_kvar, cfg: FeederConfig):

    p_feeder = cfg.n_houses * np.asarray(p_net_house_kw, float)
    q_feeder = cfg.n_houses * np.asarray(q_house_kvar, float)
    return cfg.v_ref_pu + cfg.dvdp_pu_per_kw * p_feeder + cfg.dvdq_pu_per_kvar * q_feeder


def voltvar_q(p_net_house_kw, v_no_q, s_rating_kw: float, cfg: FeederConfig):

    p = np.asarray(p_net_house_kw, float)
    v = np.asarray(v_no_q, float)
    hi = cfg.v_upper_pu - cfg.vv_deadband
    lo = cfg.v_lower_pu + cfg.vv_deadband
    q = np.zeros_like(v)

    over = v > hi
    under = v < lo
    need_dv = np.where(over, hi - v, np.where(under, lo - v, 0.0))
    q_feeder_need = need_dv / cfg.dvdq_pu_per_kvar
    q_need = q_feeder_need / cfg.n_houses

    for i in range(len(q)):
        if need_dv[i] == 0.0:
            continue
        cap = _q_capability(p[i], s_rating_kw, cfg.pf_min)
        q[i] = float(np.clip(q_need[i], -cap, cap))
    return q


def evaluate(ts: pd.DataFrame, kwp: float, cfg: FeederConfig | None = None,
             apply_voltvar: bool = True, dt_h: float = 1.0) -> dict:

    cfg = cfg or FeederConfig()
    p_net = (ts["export_kw"] - ts["import_kw"]).to_numpy(float)

    v_noq = voltage(p_net, 0.0, cfg)
    if apply_voltvar:
        q = voltvar_q(p_net, v_noq, kwp, cfg)
    else:
        q = np.zeros_like(p_net)
    v = voltage(p_net, q, cfg)


    s_feeder = np.sqrt((cfg.n_houses * p_net) ** 2 + (cfg.n_houses * q) ** 2)
    transformer_loading = s_feeder / cfg.transformer_kva


    ramp = np.abs(np.diff(cfg.n_houses * p_net, prepend=(cfg.n_houses * p_net)[0])) / (dt_h * 60.0)

    out = pd.DataFrame({
        "v_pu_no_var": v_noq, "v_pu": v, "q_kvar": q,
        "transformer_loading": transformer_loading, "ramp_kw_per_min": ramp,
    }, index=ts.index)

    metrics = {
        "max_voltage_pu": float(v.max()),
        "min_voltage_pu": float(v.min()),
        "max_voltage_no_var_pu": float(v_noq.max()),
        "overvoltage_hours": int((v > cfg.v_upper_pu).sum()),
        "overvoltage_hours_no_var": int((v_noq > cfg.v_upper_pu).sum()),
        "undervoltage_hours": int((v < cfg.v_lower_pu).sum()),
        "transformer_overload_hours": int((transformer_loading > 1.0).sum()),
        "max_transformer_loading": float(transformer_loading.max()),
        "max_ramp_kw_per_min": float(ramp.max()),
    }
    return {"timeseries": out, "metrics": metrics}
