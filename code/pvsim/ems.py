"""Energy management and dispatch."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .storage import Battery, BatteryState, request, equivalent_full_cycles
from .tariff import Tariff, buy_price_series, period_series


@dataclass
class GridConfig:
    export_limit_kw: float = np.inf
    import_limit_kw: float = np.inf


def _dt_hours(idx: pd.DatetimeIndex) -> float:
    return (idx[1] - idx[0]).total_seconds() / 3600.0 if len(idx) > 1 else 1.0


# =====================================================================

# =====================================================================
def dispatch(pv_kw: pd.Series, load_kw: pd.Series, ev_kw: pd.Series | None,
             bat: Battery, tariff: Tariff | None = None,
             grid: GridConfig | None = None,
             strategy: str = "self_consumption",
             soc_init_frac: float = 0.5) -> dict:
    tariff = tariff or Tariff()
    grid = grid or GridConfig()
    idx = pv_kw.index
    dt = _dt_hours(idx)
    n = len(idx)
    pv = pv_kw.to_numpy(float)
    base = load_kw.to_numpy(float)
    ev = (ev_kw.to_numpy(float) if ev_kw is not None else np.zeros(n))
    dem = base + ev
    period = period_series(idx, tariff).to_numpy()
    buy = buy_price_series(idx, tariff).to_numpy()
    st = BatteryState(soc_kwh=soc_init_frac * bat.capacity_kwh)

    imp = np.zeros(n); exp = np.zeros(n); curt = np.zeros(n)
    batt = np.zeros(n); soc = np.zeros(n)
    pv2load = np.zeros(n); pv2batt = np.zeros(n)
    batt2load = np.zeros(n); grid2load = np.zeros(n)

    for t in range(n):
        b = 0.0
        pl = min(pv[t], dem[t]); rem_pv = pv[t] - pl; rem_dem = dem[t] - pl
        e_exp = e_imp = e_curt = 0.0
        g2l = p2b = b2l = 0.0
        if rem_pv > 1e-12:
            chg = request(bat, st, +rem_pv, dt); b += chg; p2b = chg
            e_exp = rem_pv - chg
        elif rem_dem > 1e-12:
            if strategy == "tou_arbitrage" and period[t] == "valley":
                g2l = rem_dem
                head = bat.power_kw - abs(b)
                if head > 1e-9:
                    extra = request(bat, st, +head, dt); b += extra; e_imp = g2l + extra
                else:
                    e_imp = g2l
            else:
                dis = request(bat, st, -rem_dem, dt); b += dis; b2l = -dis
                g2l = rem_dem - b2l; e_imp = g2l
        if e_exp > grid.export_limit_kw:
            excess = e_exp - grid.export_limit_kw
            head = bat.power_kw - abs(b)
            absorbed = request(bat, st, +min(excess, max(head, 0.0)), dt) if head > 1e-9 else 0.0
            b += absorbed; p2b += absorbed
            e_curt = max(excess - absorbed, 0.0); e_exp = e_exp - absorbed - e_curt
        if e_imp > grid.import_limit_kw:
            e_imp = grid.import_limit_kw
        imp[t] = e_imp; exp[t] = e_exp; curt[t] = e_curt
        batt[t] = b; soc[t] = st.soc_kwh
        pv2load[t] = pl; pv2batt[t] = p2b; batt2load[t] = b2l; grid2load[t] = g2l

    ts = pd.DataFrame({
        "pv_kw": pv, "load_kw": base, "ev_kw": ev, "demand_kw": dem,
        "batt_kw": batt, "soc_kwh": soc, "import_kw": imp, "export_kw": exp,
        "curtail_kw": curt, "buy_price": buy, "period": period,
        "pv_to_load": pv2load, "pv_to_batt": pv2batt, "batt_to_load": batt2load,
        "grid_to_load": grid2load,
    }, index=idx)
    return {"timeseries": ts,
            "summary": _summarize(ts, bat, st, tariff, dt, f"rule:{strategy}")}


def _summarize(ts, bat, st, tariff, dt, label) -> dict:
    pv = ts["pv_kw"].to_numpy(); imp = ts["import_kw"].to_numpy()
    exp = ts["export_kw"].to_numpy(); curt = ts["curtail_kw"].to_numpy()
    dem = ts["demand_kw"].to_numpy()
    pv_pot = pv.sum() * dt
    consumption = dem.sum() * dt
    exported = exp.sum() * dt; curtailed = curt.sum() * dt; imported = imp.sum() * dt
    pv_onsite = pv_pot - exported - curtailed
    bill = float((imp * ts["buy_price"].to_numpy()).sum() * dt - exported * tariff.feed_in_price)
    wear = st.throughput_kwh * bat.wear_cost_per_kwh
    return {
        "strategy": label,
        "pv_potential_kwh": float(pv_pot), "demand_kwh": float(consumption),
        "self_consumption_rate": float(pv_onsite / pv_pot) if pv_pot > 0 else 0.0,
        "self_sufficiency_rate": float(max(0.0, (consumption - imported) / consumption))
        if consumption > 0 else 0.0,
        "imported_kwh": float(imported), "exported_kwh": float(exported),
        "curtailed_kwh": float(curtailed), "annual_bill_yuan": bill,
        "battery_wear_yuan": float(wear),
        "total_cost_yuan": float(bill + wear),
        "max_import_kw": float(imp.max()), "max_export_kw": float(exp.max()),
        "export_hours": int((exp > 1e-6).sum()),
        "battery_cycles": float(equivalent_full_cycles(bat, st)),
        "battery_throughput_kwh": float(st.throughput_kwh),
    }


def pv_surplus_preference(pv_kw: pd.Series, load_kw: pd.Series,
                          tariff: Tariff | None = None) -> np.ndarray:
    tariff = tariff or Tariff()
    surplus = pv_kw.to_numpy(float) - load_kw.to_numpy(float)
    period = period_series(pv_kw.index, tariff).to_numpy()
    return (surplus + 3.0 * (period == "valley") - 2.0 * (period == "peak")).astype(float)


# =====================================================================

# =====================================================================
def dispatch_optimal(pv_kw: pd.Series, load_kw: pd.Series, bat: Battery,
                     ev_aggregate: dict | None = None,
                     tariff: Tariff | None = None, grid: GridConfig | None = None,
                     soc_init_frac: float = 0.3, eta_ev: float = 0.92) -> dict:

    from scipy.optimize import linprog
    from scipy.sparse import coo_matrix
    tariff = tariff or Tariff()
    grid = grid or GridConfig()
    ev_aggregate = ev_aggregate or {}
    idx = pv_kw.index
    dt = _dt_hours(idx)
    n = len(idx)
    pv = pv_kw.to_numpy(float); load = load_kw.to_numpy(float)
    buy = buy_price_series(idx, tariff).to_numpy()
    feed = tariff.feed_in_price
    smin, smax = bat.soc_min_kwh, bat.soc_max_kwh
    soc_init = soc_init_frac * bat.capacity_kwh
    ech, edis = bat.eta_chg, bat.eta_dis

    GI, GE, BC, BD, CU, EC, SOC = (i * n for i in range(7))
    nv = 7 * n


    pc = np.zeros(n)
    day_need = []
    for d, rec in ev_aggregate.items():
        ix = rec["idx"]
        pc[ix] = np.maximum(pc[ix], rec["p_charge_cap"])
        if rec["energy_need"] > 0:
            day_need.append((ix, rec["energy_need"]))


    c = np.zeros(nv)
    c[GI:GI + n] = buy * dt
    c[GE:GE + n] = -feed * dt
    c[BC:BC + n] = bat.wear_cost_per_kwh * dt
    c[BD:BD + n] = bat.wear_cost_per_kwh * dt
    c[CU:CU + n] = 1e-4
    c[EC:EC + n] = 1e-4


    rows, cols, data, beq = [], [], [], []
    r = 0

    for t in range(n):
        for blk, val in ((GI, 1), (GE, -1), (BC, -1), (BD, 1), (CU, -1), (EC, -1)):
            rows.append(r); cols.append(blk + t); data.append(val)
        beq.append(load[t] - pv[t]); r += 1

    for t in range(n):
        rows += [r, r, r]; cols += [SOC + t, BC + t, BD + t]
        data += [1.0, -dt * ech, dt / edis]
        if t == 0:
            beq.append(soc_init)
        else:
            rows.append(r); cols.append(SOC + t - 1); data.append(-1.0)
            beq.append(0.0)
        r += 1

    for ix, need in day_need:
        for t in ix:
            rows.append(r); cols.append(EC + int(t)); data.append(dt * eta_ev)
        beq.append(need); r += 1
    A_eq = coo_matrix((data, (rows, cols)), shape=(r, nv)).tocsr()
    b_eq = np.array(beq)


    lb = np.zeros(nv); ub = np.full(nv, np.inf)
    ub[GI:GI + n] = grid.import_limit_kw
    ub[GE:GE + n] = grid.export_limit_kw
    ub[BC:BC + n] = bat.power_kw
    ub[BD:BD + n] = bat.power_kw
    ub[CU:CU + n] = np.maximum(pv, 0.0)
    ub[EC:EC + n] = pc
    lb[SOC:SOC + n] = smin; ub[SOC:SOC + n] = smax
    lb[SOC + n - 1] = max(smin, soc_init)
    bounds = list(zip(lb, ub))

    res = linprog(c, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")
    if not res.success:
        raise RuntimeError(f'LP Solver failed: {res.message}')
    x = res.x
    gi = x[GI:GI + n]; ge = x[GE:GE + n]; bc = x[BC:BC + n]; bd = x[BD:BD + n]
    cu = x[CU:CU + n]; ec = x[EC:EC + n]; soc = x[SOC:SOC + n]
    batt_ac = bc - bd

    ts = pd.DataFrame({
        "pv_kw": pv, "load_kw": load, "ev_kw": ec, "demand_kw": load + ec,
        "batt_kw": batt_ac, "soc_kwh": soc, "import_kw": gi, "export_kw": ge,
        "curtail_kw": cu, "buy_price": buy, "period": period_series(idx, tariff).to_numpy(),
    }, index=idx)
    throughput = float((bc * ech * dt).sum())
    st = BatteryState(soc_kwh=float(soc[-1]), throughput_kwh=throughput)
    summ = _summarize(ts, bat, st, tariff, dt, "optimal(LP)")
    summ["ev_delivered_kwh"] = float((ec * eta_ev * dt).sum())
    return {"timeseries": ts, "summary": summ}
