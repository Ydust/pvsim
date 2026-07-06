"""运维诊断 —— 用物理孪生当"标准答案"，发现并**分清**多种故障。

思路：system.simulate 算的是"健康时本应发多少电"(孪生/基线)，与实测对比即诊断。
关键优势：孪生已含温度、光谱，"雾霾红移少发电"这种天气因素它本就预见、不误报；
普通"按辐照打固定折扣"的基线分不清天气和故障。

升级点 —— 用**物理特征**把故障分门别类：
    积灰     缓慢均匀下降(各时段/各辐照档损失相近)。
    遮挡     损失集中在特定小时(早/晚)。
    组串/硬件 突变台阶(某天起均匀掉一截)。
    逆变器限幅 损失只在大出力(中午/高辐照)时出现。
    加速衰减  极缓慢均匀下降(比积灰更慢, 且不会因下雨恢复)。
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .materials import CellTechnology
from .system import SystemConfig, simulate


def _day_counter(idx: pd.DatetimeIndex) -> np.ndarray:
    d0 = idx.normalize()
    return (d0 - d0[0]).days.to_numpy()


def daily_kwh(power_w: pd.Series, dt_h: float | None = None) -> pd.Series:
    idx = power_w.index
    if dt_h is None:
        dt_h = (idx[1] - idx[0]).total_seconds() / 3600.0 if len(idx) > 1 else 1.0
    return power_w.resample("D").sum() * dt_h / 1000.0


# ---------------- 故障注入 ----------------
def inject_soiling(ac, loss_final=0.18, start_day=120, ramp_days=60):
    """积灰: start_day 起 ramp_days 内线性爬升到 loss_final。"""
    day = _day_counter(ac.index)
    frac = np.clip((day - start_day) / max(ramp_days, 1), 0.0, 1.0)
    return ac * (1.0 - loss_final * frac)


def inject_string_failure(ac, frac=0.25, start_day=200):
    """组串/硬件故障: start_day 起功率台阶式掉 frac。"""
    day = _day_counter(ac.index)
    return ac * np.where(day >= start_day, 1.0 - frac, 1.0)


def inject_shading(ac, hours=(7, 10), loss=0.6, start_day=0):
    """局部遮挡: start_day 起每天 hours 时段损失 loss。"""
    h = ac.index.hour.to_numpy()
    day = _day_counter(ac.index)
    mask = (h >= hours[0]) & (h < hours[1]) & (day >= start_day)
    return ac * np.where(mask, 1.0 - loss, 1.0)


def inject_inverter_clip(ac, clip_frac=0.7, start_day=150):
    """逆变器限幅异常: start_day 起把功率削到峰值的 clip_frac 以下(只伤大出力时段)。"""
    day = _day_counter(ac.index)
    cap = clip_frac * float(ac.max())
    out = ac.copy()
    m = day >= start_day
    out[m] = np.minimum(ac[m], cap)
    return out


def inject_accelerated_degradation(ac, loss_per_year=0.06, start_day=0):
    """加速衰减: 从 start_day 起按 loss_per_year 极缓慢均匀下降。"""
    day = _day_counter(ac.index)
    frac = np.clip((day - start_day) / 365.0, 0.0, None) * loss_per_year
    return ac * (1.0 - frac)


def add_noise(ac, rel=0.02, seed=0):
    rng = np.random.default_rng(seed)
    return ac * (1.0 + rng.normal(0, rel, size=len(ac)))


# ---------------- 特征 + 检测 + 分类 ----------------
def _onset(pi: np.ndarray, threshold: float, persist: int):
    below = pi < threshold
    run = 0
    for i, b in enumerate(below):
        run = run + 1 if b else 0
        if run >= persist:
            return i - persist + 1
    return None


def _features(measured: pd.Series, expected: pd.Series, onset_day: int) -> dict:
    """提取物理特征(均在故障发生后的白天时段统计)。"""
    m = measured.to_numpy(float); e = expected.to_numpy(float)
    day = _day_counter(measured.index); h = measured.index.hour.to_numpy()
    post = (day >= onset_day) & (e > 1.0)          # 故障后、有出力的时刻

    # 按小时的保持率 → 集中度(遮挡特征)
    hourly = []
    for hr in range(5, 20):
        sel = post & (h == hr)
        if sel.sum() > 5:
            hourly.append((m[sel] / e[sel]).mean())
    hour_conc = (max(hourly) - min(hourly)) if hourly else 0.0

    # 按出力高低分档的损失 → 高档损失大=限幅特征
    epost = e[post]; mpost = m[post]
    if len(epost) > 30:
        q1, q2 = np.quantile(epost, [0.5, 0.85])
        lo = epost <= q1; hi = epost >= q2
        loss_lo = 1 - (mpost[lo] / epost[lo]).mean() if lo.sum() else 0.0
        loss_hi = 1 - (mpost[hi] / epost[hi]).mean() if hi.sum() else 0.0
    else:
        loss_lo = loss_hi = 0.0

    return {"hour_concentration": float(hour_conc),
            "loss_high_minus_low": float(loss_hi - loss_lo)}


def detect(measured: pd.Series, expected: pd.Series,
           threshold=0.94, persist_days=5) -> dict:
    """逐日性能指数 PI → 找异常起点、估损失、按物理特征分类。"""
    m_daily = daily_kwh(measured); e_daily = daily_kwh(expected)
    pi = (m_daily / e_daily.replace(0, np.nan)).to_numpy()
    pi = np.where(np.isfinite(pi), pi, 1.0)
    onset = _onset(pi, threshold, persist_days)

    if onset is None:
        return {"pi_daily": pd.Series(pi, index=m_daily.index, name="PI"),
                "onset_day": None, "onset_date": None, "est_loss": 0.0,
                "fault_type": "无明显故障", "confidence": "—",
                "false_alarm_free_days": int((pi >= threshold).sum())}

    est_loss = float(1.0 - np.median(pi[onset:]))
    pre = pi[max(0, onset - 4):onset]; post = pi[onset:onset + 4]
    jump = float((pre.mean() if len(pre) else 1.0) - (post.mean() if len(post) else 1.0))
    # 起点后 ~40 天的下降速率(每天损失增量)
    seg = pi[onset:onset + 40]
    ramp_rate = float((seg[0] - seg[-1]) / max(len(seg) - 1, 1)) if len(seg) > 5 else 0.0
    feat = _features(measured, expected, onset)

    kind, conf = _classify(jump, ramp_rate, feat)
    return {"pi_daily": pd.Series(pi, index=m_daily.index, name="PI"),
            "onset_day": int(onset), "onset_date": m_daily.index[onset].date(),
            "est_loss": est_loss, "fault_type": kind, "confidence": conf,
            "jump": jump, "ramp_rate": ramp_rate, **feat}


def _classify(jump, ramp_rate, feat) -> tuple[str, str]:
    hc = feat["hour_concentration"]; hl = feat["loss_high_minus_low"]
    if hc > 0.25:
        return "局部遮挡", "高" if hc > 0.4 else "中"
    if hl > 0.12:
        return "逆变器限幅/异常", "高" if hl > 0.2 else "中"
    if jump > 0.06:
        return "组串/硬件故障", "高" if jump > 0.12 else "中"
    if ramp_rate > 0.002:           # >0.2%/天 的下降 → 积灰
        return "积灰", "中"
    return "加速衰减", "低"          # 极缓慢均匀 → 衰减


# ---------------- 朴素基线 + 演示/评测 ----------------
def naive_baseline(twin_ts: pd.DataFrame, kwp: float, twin_energy_kwh: float,
                   dt_h: float) -> pd.Series:
    poa = twin_ts["poa_global"].to_numpy(float)
    ref = (poa / 1000.0).sum() * dt_h * kwp
    eta = twin_energy_kwh / ref if ref > 0 else 1.0
    return pd.Series(kwp * (poa / 1000.0) * eta * 1000.0,
                     index=twin_ts.index, name="naive_ac")


_FAULTS = {
    "积灰": lambda ac: inject_soiling(ac, 0.18, 120, 60),
    "局部遮挡": lambda ac: inject_shading(ac, (7, 10), 0.6, 120),
    "组串/硬件故障": lambda ac: inject_string_failure(ac, 0.25, 120),
    "逆变器限幅/异常": lambda ac: inject_inverter_clip(ac, 0.7, 120),
    "加速衰减": lambda ac: inject_accelerated_degradation(ac, 0.12, 1),
}


def evaluate_suite(tech: CellTechnology, weather: pd.DataFrame,
                   cfg: SystemConfig | None = None, seed=0) -> pd.DataFrame:
    """逐一注入5类故障, 用孪生诊断, 报告: 判定类型/是否判对/发现延迟/损失估计。"""
    cfg = cfg or SystemConfig(n_modules=20)
    twin = simulate(tech, weather, cfg, npts=100)["timeseries"]["ac_power"]
    rows = []
    for true_type, fn in _FAULTS.items():
        measured = add_noise(fn(twin), rel=0.02, seed=seed)
        dg = detect(measured, twin)
        true_onset = 1 if true_type == "加速衰减" else 120
        delay = (dg["onset_day"] - true_onset) if dg["onset_day"] is not None else None
        rows.append({
            "真实故障": true_type, "判定": dg["fault_type"],
            "判对": "✓" if dg["fault_type"] == true_type else "✗",
            "发现延迟天": delay, "估计损失%": round(dg["est_loss"] * 100, 1),
            "置信": dg["confidence"],
        })
    return pd.DataFrame(rows)


def run_diagnosis_demo(tech: CellTechnology, weather: pd.DataFrame,
                       cfg: SystemConfig | None = None,
                       soiling_start=120, soiling_loss=0.18, threshold=0.94) -> dict:
    """演示: 注入积灰 → 物理孪生 vs 朴素基线诊断 → 比误报。"""
    cfg = cfg or SystemConfig(n_modules=20)
    r = simulate(tech, weather, cfg, npts=100)
    twin = r["timeseries"]["ac_power"]
    dt_h = (twin.index[1] - twin.index[0]).total_seconds() / 3600.0
    measured = add_noise(inject_soiling(twin, soiling_loss, soiling_start), rel=0.02)
    naive = naive_baseline(r["timeseries"], r["kwp"], r["energy_ac_kwh"], dt_h)

    diag_twin = detect(measured, twin, threshold=threshold)
    diag_naive = detect(measured, naive, threshold=threshold)
    pi_t = diag_twin["pi_daily"].to_numpy(); pi_n = diag_naive["pi_daily"].to_numpy()
    pre = np.arange(len(pi_t)) < soiling_start
    return {"twin": diag_twin, "naive": diag_naive,
            "false_alarms_twin": int((pi_t[pre] < threshold).sum()),
            "false_alarms_naive": int((pi_n[pre] < threshold).sum()),
            "pre_fault_days": int(pre.sum())}
