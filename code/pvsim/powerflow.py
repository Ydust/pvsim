"""Balanced radial-feeder backward/forward sweep power flow."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Feeder:
    parent: np.ndarray
    Z: np.ndarray
    v_base: float = 230.0
    s_rated_va: float = 250e3
    length_m: np.ndarray | None = None

    @property
    def n_bus(self) -> int:
        return len(self.parent)

    def order(self) -> np.ndarray:

        order = []
        seen = {0}
        stack = [0]

        children = {i: [] for i in range(self.n_bus)}
        for i in range(1, self.n_bus):
            children[int(self.parent[i])].append(i)
        q = [0]
        while q:
            b = q.pop(0)
            order.append(b)
            q.extend(children[b])
        return np.array(order)


def build_lv_feeder(n_houses: int = 20, span_m: float = 400.0,
                    r_ohm_per_km: float = 0.32, x_ohm_per_km: float = 0.08,
                    s_rated_kva: float = 250.0,
                    trafo_uk: float = 0.04, trafo_xr: float = 3.0) -> Feeder:

    n = n_houses + 1
    parent = np.array([-1] + list(range(0, n_houses)))
    seg = span_m / n_houses / 1000.0
    z_line = (r_ohm_per_km + 1j * x_ohm_per_km) * seg
    Z = np.array([0 + 0j] + [z_line] * n_houses)

    v_base = 230.0
    z_t_mag = trafo_uk * v_base**2 / (s_rated_kva * 1e3 / 3.0)
    r_t = z_t_mag / np.sqrt(1 + trafo_xr**2)
    x_t = r_t * trafo_xr
    Z[1] = Z[1] + (r_t + 1j * x_t)
    length = np.array([0.0] + [span_m / n_houses] * n_houses)
    return Feeder(parent=parent, Z=Z, v_base=v_base, s_rated_va=s_rated_kva * 1e3,
                  length_m=length)


def solve(feeder: Feeder, p_w, q_var, v_slack_pu: float = 1.02,
          tol: float = 1e-8, max_iter: int = 100) -> dict:

    n = feeder.n_bus
    p = np.asarray(p_w, float).copy(); q = np.asarray(q_var, float).copy()
    p[0] = q[0] = 0.0
    order = feeder.order()
    rev = order[::-1]
    parent = feeder.parent; Z = feeder.Z
    children = {i: [] for i in range(n)}
    for i in range(1, n):
        children[int(parent[i])].append(i)

    v_slack = v_slack_pu * feeder.v_base
    V = np.full(n, complex(v_slack, 0.0))
    it = 0
    for it in range(1, max_iter + 1):
        S = p + 1j * q
        I_bus = np.conj(S / V)
        I_branch = np.zeros(n, complex)
        for b in rev:
            if b == 0:
                continue
            I_branch[b] = I_bus[b] + sum(I_branch[c] for c in children[b])
        Vnew = V.copy(); Vnew[0] = complex(v_slack, 0.0)
        for b in order:
            if b == 0:
                continue
            Vnew[b] = Vnew[int(parent[b])] - Z[b] * I_branch[b]
        diff = np.max(np.abs(Vnew - V))
        V = Vnew
        if diff < tol * feeder.v_base:
            break


    i_root = sum(I_branch[c] for c in children[0])
    s_trafo_3ph = 3.0 * V[0] * np.conj(i_root)
    return {
        "v_pu": np.abs(V) / feeder.v_base,
        "v_complex": V,
        "transformer_loading": float(np.abs(s_trafo_3ph) / feeder.s_rated_va),
        "max_branch_current_a": float(np.max(np.abs(I_branch))),
        "converged": bool(diff < tol * feeder.v_base),
        "iters": it,
    }


def build_sensitivity(feeder: Feeder):

    n = feeder.n_bus; parent = feeder.parent
    R = feeder.Z.real; X = feeder.Z.imag
    paths = [set() for _ in range(n)]
    for i in range(1, n):
        b = i
        while b != 0:
            paths[i].add(b); b = int(parent[b])
    Rc = np.zeros((n, n)); Xc = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            common = paths[i] & paths[j]
            Rc[i, j] = sum(R[b] for b in common)
            Xc[i, j] = sum(X[b] for b in common)
    return Rc, Xc


def fast_voltage_pu(feeder: Feeder, P_w, Q_var, v_slack_pu: float = 1.02,
                    Rc=None, Xc=None):

    if Rc is None:
        Rc, Xc = build_sensitivity(feeder)
    Vn = feeder.v_base
    dV = -(Rc @ np.asarray(P_w, float) + Xc @ np.asarray(Q_var, float)) / Vn
    return (v_slack_pu * Vn + dV) / Vn


def validate_fast() -> dict:

    fd = build_lv_feeder(n_houses=20, span_m=400.0, s_rated_kva=250.0)
    n = fd.n_bus
    P = np.array([0.0] + [-5000.0 / 3] * 20)
    exact = solve(fd, P, np.zeros(n), v_slack_pu=1.02)["v_pu"]
    lin = fast_voltage_pu(fd, P, np.zeros(n), v_slack_pu=1.02)
    return {"v_end_exact": float(exact[-1]), "v_end_linear": float(lin[-1]),
            "max_abs_diff_pu": float(np.max(np.abs(exact - lin)))}


def hosting_capacity(feeder: Feeder, pv_perkwp_w, load_kw_house,
                     v_limit: float = 1.05, v_slack_pu: float = 1.02,
                     n_worst: int = 30, k_max: float = 40.0) -> dict:

    n = feeder.n_bus; nh = n - 1
    pvkw = np.asarray(pv_perkwp_w, float) / 1000.0      # kW per kWp
    load = np.asarray(load_kw_house, float)

    def worst_metrics(K):
        net = K * pvkw - load
        worst = np.argsort(net)[-n_worst:]
        vmax, tmax = 0.0, 0.0
        for t in worst:
            if net[t] <= 0:
                continue
            p_phase = -net[t] * 1000.0 / 3.0
            p = np.array([0.0] + [p_phase] * nh)
            r = solve(feeder, p, np.zeros(n), v_slack_pu)
            vmax = max(vmax, float(r["v_pu"].max()))
            tmax = max(tmax, r["transformer_loading"])
        return vmax, tmax

    def violates(K):
        v, t = worst_metrics(K)
        return (v > v_limit) or (t > 1.0)

    if not violates(k_max):
        return {"kwp_per_house": k_max, "total_kwp": k_max * nh, "binding": "none"}
    lo, hi = 0.0, k_max
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if violates(mid):
            hi = mid
        else:
            lo = mid
    v, t = worst_metrics(lo)
    binding = "voltage" if v > v_limit - 1e-3 else ("transformer" if t > 0.99 else "voltage")
    return {"kwp_per_house": lo, "total_kwp": lo * nh, "binding": binding}


def annual_curtailment(feeder: Feeder, pv_perkwp_w, load_kw_house, kwp_per_house: float,
                       v_limit: float = 1.05, v_slack_pu: float = 1.02,
                       dt_h: float = 1.0) -> dict:

    n = feeder.n_bus; nh = n - 1
    pvkw = np.asarray(pv_perkwp_w, float) / 1000.0
    load = np.asarray(load_kw_house, float)
    net = kwp_per_house * pvkw - load
    curt = exp = 0.0; vh = 0
    for t in range(len(net)):
        if net[t] <= 0:
            continue
        exp += net[t] * dt_h
        p = np.array([0.0] + [-net[t] * 1000.0 / 3.0] * nh)
        vmax = float(solve(feeder, p, np.zeros(n), v_slack_pu)["v_pu"].max())
        if vmax > v_limit:
            vh += 1
            frac = min(max((vmax - v_limit) / (vmax - v_slack_pu), 0.0), 1.0)
            curt += net[t] * frac * dt_h
    return {"curtail_kwh": curt, "export_kwh": exp,
            "curtail_frac": (curt / exp if exp > 0 else 0.0), "violation_hours": vh}


def validate_2bus() -> dict:

    Z = 0.5 + 0.2j                              # Ω
    feeder = Feeder(parent=np.array([-1, 0]), Z=np.array([0 + 0j, Z]),
                    v_base=230.0, s_rated_va=100e3)
    P, Q = 5000.0, 1000.0
    res = solve(feeder, [0.0, P], [0.0, Q], v_slack_pu=1.0)
    v_num = res["v_pu"][1] * 230.0
    dv_analytic = (P * Z.real + Q * Z.imag) / 230.0
    v_approx = 230.0 - dv_analytic
    return {"v_solver": v_num, "v_analytic_approx": v_approx,
            "diff_volt": abs(v_num - v_approx), "iters": res["iters"]}
