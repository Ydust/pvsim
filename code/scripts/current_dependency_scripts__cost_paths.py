"""Author-defined exogenous cost paths. No historical fitting or adoption allocation."""
import numpy as np
from pvsim.economic_priors import *
from pvsim.economics import MODERN_CSI_DURABILITY,TANDEM_DURABILITY,discounted_lcoe,perovskite_durability
YEARS=np.arange(2025,2051)
NY=len(YEARS)
TECHS=[TECH_CSI,TECH_PEROVSKITE,TECH_TANDEM]
CAPEX_0=dict(INITIAL_SYSTEM_CAPEX_USD_W)
Q_0=dict(INITIAL_GLOBAL_DEPLOYMENT_GW)
ROW=0.4

def global_new_schedule():
    a = np.arange(NY)
    return {"晶硅": np.linspace(80, 30, NY) + np.linspace(0, 20, NY),
            "钙钛矿": np.minimum(a*4+5, 100.0),
            "叠层": np.maximum(0, np.minimum(a*3-12, 80.0))}

def capex_and_lcoe(
    yields,
    LR,
    floor,
    breakthrough,
    life_final=25.0,
    *,
    return_capex=False,
):
    """外生学习: capex 由全球部署轨迹驱动. 钙钛矿寿命阶跃突破到 life_final.

    life_final < 25 表示寿命问题未完全解决 (真实不确定性核心).
    """
    B = {k: -np.log2(1-v) for k, v in LR.items()}
    sched = global_new_schedule()
    cum = {k: Q_0[k] for k in TECHS}; cap = dict(CAPEX_0)
    lcoe = {k: np.zeros(NY) for k in TECHS}
    capex = {k: np.zeros(NY) for k in TECHS}
    for i, yr in enumerate(YEARS):
        for k in TECHS:
            raw = max(floor[k], CAPEX_0[k]*(max(cum[k],0.1)/Q_0[k])**(-B[k]))
            cap[k] = raw if i == 0 else max(cap[k]*0.88, raw, floor[k])
            capex[k][i] = cap[k]
            if k == TECH_PEROVSKITE:
                durability = perovskite_durability(yr, breakthrough, life_final)
            elif k == TECH_CSI:
                durability = MODERN_CSI_DURABILITY
            else:
                durability = TANDEM_DURABILITY
            lcoe[k][i] = discounted_lcoe(
                cap[k],
                yields[k],
                durability.lifetime_years,
                durability.degradation_rate,
                durability.burn_in_loss,
            ) * 100.0
        for k in TECHS:
            cum[k] += sched[k][i]*(1+ROW)
    return (lcoe, capex) if return_capex else lcoe
