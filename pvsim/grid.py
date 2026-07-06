"""配网友好：台区电压 + 无功(Volt-VAR)调节 + 变压器过载 + 爬坡。

分布式光伏/充电桩对配电网的真实影响主要在**并网点电压**和**台区变压器**上：
    - 中午大发、自己用不完往电网倒灌 → 并网点电压被顶高(可能越上限)。
    - 傍晚充电桩齐充 → 大量取电 → 电压被拉低(可能越下限)、变压器过载。
本模块用线性化的"电压-功率灵敏度"近似台区电压, 并实现逆变器**无功电压调节**
(Volt-VAR: 电压高了吸收无功把它压回来), 量化越限/过载/爬坡, 与"是否友好"挂钩。

电压线性化(末端并网点, 标幺值):  V = V_ref + dV/dP·P_馈线 + dV/dQ·Q_馈线
其中 P_馈线 = 户数 × 单户净注入(倒送为正)。弱馈线 dV/dP 大、易越压。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class FeederConfig:
    dvdp_pu_per_kw: float = 0.0009    # 每馈线净注入1kW, 电压抬升(pu); 弱馈线更大
    dvdq_pu_per_kvar: float = 0.0007  # 无功对电压的灵敏度
    v_ref_pu: float = 1.02            # 空载时并网点电压(略高于1, 因上游调压)
    v_upper_pu: float = 1.07          # 越上限(GB/T 12325: 标称±7%)
    v_lower_pu: float = 0.93          # 越下限
    vv_deadband: float = 0.02         # Volt-VAR 死区(距上/下限多少开始动作)
    transformer_kva: float = 100.0    # 台区变压器容量
    n_houses: int = 20                # 同一台区/馈线户数(把单户放大到台区)
    pf_min: float = 0.95              # 逆变器最小功率因数(限制可调无功)


def _q_capability(p_kw: float, s_rating_kw: float, pf_min: float) -> float:
    """逆变器在出力 |p| 下还能提供多少无功(kvar)。受视在容量与最小功率因数双重限制。"""
    p = abs(p_kw)
    q_by_pf = p * np.tan(np.arccos(pf_min)) if p > 1e-6 else s_rating_kw * 0.3
    q_by_s = np.sqrt(max(s_rating_kw**2 - p**2, 0.0))
    return float(min(q_by_pf, q_by_s))


def voltage(p_net_house_kw, q_house_kvar, cfg: FeederConfig):
    """由单户净注入(+倒送/-取电)与无功, 算并网点电压(pu)。"""
    p_feeder = cfg.n_houses * np.asarray(p_net_house_kw, float)
    q_feeder = cfg.n_houses * np.asarray(q_house_kvar, float)
    return cfg.v_ref_pu + cfg.dvdp_pu_per_kw * p_feeder + cfg.dvdq_pu_per_kvar * q_feeder


def voltvar_q(p_net_house_kw, v_no_q, s_rating_kw: float, cfg: FeederConfig):
    """Volt-VAR 下垂：电压超过(上限-死区)→吸收无功(Q<0)把电压压回; 偏低→发无功。

    返回每个时刻的无功设定 q (kvar, 单户)。
    """
    p = np.asarray(p_net_house_kw, float)
    v = np.asarray(v_no_q, float)
    hi = cfg.v_upper_pu - cfg.vv_deadband
    lo = cfg.v_lower_pu + cfg.vv_deadband
    q = np.zeros_like(v)
    # 需要把电压拉回的目标偏移量 → 反推所需馈线无功 → 单户无功
    over = v > hi
    under = v < lo
    need_dv = np.where(over, hi - v, np.where(under, lo - v, 0.0))   # 想要的电压变化
    q_feeder_need = need_dv / cfg.dvdq_pu_per_kvar
    q_need = q_feeder_need / cfg.n_houses
    # 受逆变器能力限制
    for i in range(len(q)):
        if need_dv[i] == 0.0:
            continue
        cap = _q_capability(p[i], s_rating_kw, cfg.pf_min)
        q[i] = float(np.clip(q_need[i], -cap, cap))
    return q


def evaluate(ts: pd.DataFrame, kwp: float, cfg: FeederConfig | None = None,
             apply_voltvar: bool = True, dt_h: float = 1.0) -> dict:
    """对一份调度结果(含 import_kw/export_kw)评估配网友好性。

    返回逐时电压/无功/变压器负载 + 越限/过载/爬坡指标。
    """
    cfg = cfg or FeederConfig()
    p_net = (ts["export_kw"] - ts["import_kw"]).to_numpy(float)   # 单户净注入(+倒送)

    v_noq = voltage(p_net, 0.0, cfg)
    if apply_voltvar:
        q = voltvar_q(p_net, v_noq, kwp, cfg)
    else:
        q = np.zeros_like(p_net)
    v = voltage(p_net, q, cfg)

    # 变压器视在功率负载率(台区)
    s_feeder = np.sqrt((cfg.n_houses * p_net) ** 2 + (cfg.n_houses * q) ** 2)
    transformer_loading = s_feeder / cfg.transformer_kva

    # 爬坡(馈线净功率每小时变化, 折算 kW/min)
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
