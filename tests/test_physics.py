"""pvsim 物理核心 pytest 单测 (为 SoftwareX 工具论文要求的 CI 测试)。

覆盖:
  - cell.operating_point: STC 数值正确性 + 温度/辐照行为
  - temperature.faiman: 边界条件
  - lcoe.lcoe: 现金流核算
  - degradation.retention: 保持率单调性
  - spectral.eqe: 截止波长

运行: pytest tests/ -v
"""

import numpy as np
import pytest

from pvsim.materials import CSI_EARLY, PEROVSKITE
from pvsim.cell import operating_point
from pvsim.temperature import faiman
from pvsim.lcoe import lcoe
from pvsim.degradation import retention, profile_for
from pvsim.spectral import eqe


# ============================================================
# cell.operating_point
# ============================================================

class TestCell:
    def test_csi_stc_within_tolerance(self):
        """晶硅 STC 应给文献值 (PERC/Al-BSF 15-16% 效率)"""
        op = operating_point(CSI_EARLY, 1000.0, 25.0, ns=60, npts=400)
        assert 220 < op.pmp < 230, f"晶硅 STC Pmp={op.pmp:.1f} 不在 220-230 W 范围"
        assert 36 < op.voc < 38, f"Voc={op.voc:.1f} 不在 36-38 V 范围"
        assert 8 < op.isc < 8.2, f"Isc={op.isc:.2f} 不在 8-8.2 A 范围"
        assert 0.74 < op.ff < 0.77, f"FF={op.ff:.3f} 不在 0.74-0.77 范围"
        assert 0.15 < op.efficiency < 0.16, f"η={op.efficiency:.3f} 不在 0.15-0.16 范围"

    def test_pero_stc_within_tolerance(self):
        """钙钛矿 STC ~19% 效率"""
        op = operating_point(PEROVSKITE, 1000.0, 25.0, ns=60, npts=400)
        assert 270 < op.pmp < 290, f"钙钛矿 STC Pmp={op.pmp:.1f} 越界"
        assert 65 < op.voc < 68, f"Voc={op.voc:.1f} 越界"
        assert 0.19 < op.efficiency < 0.20

    def test_power_decreases_with_temperature(self):
        """温度升 1°C 功率应下降; 晶硅降幅 > 钙钛矿"""
        opC25 = operating_point(CSI_EARLY, 1000.0, 25.0, ns=60)
        opC50 = operating_point(CSI_EARLY, 1000.0, 50.0, ns=60)
        opP25 = operating_point(PEROVSKITE, 1000.0, 25.0, ns=60)
        opP50 = operating_point(PEROVSKITE, 1000.0, 50.0, ns=60)
        drop_csi = (opC25.pmp - opC50.pmp) / opC25.pmp
        drop_pero = (opP25.pmp - opP50.pmp) / opP25.pmp
        assert drop_csi > drop_pero, "晶硅温度损失应大于钙钛矿"
        assert 0.08 < drop_csi < 0.13, f"晶硅 25°C→50°C 应损失 ~10%, 实际 {drop_csi*100:.1f}%"
        assert 0.02 < drop_pero < 0.06, f"钙钛矿应损失 ~3-4%, 实际 {drop_pero*100:.1f}%"

    def test_irradiance_linearity_low_light(self):
        """200 W/m^2 下 Pmax 应 ≈ STC × 0.2 (留点弱光余量)"""
        op_stc = operating_point(CSI_EARLY, 1000.0, 25.0, ns=60)
        op_lo = operating_point(CSI_EARLY, 200.0, 25.0, ns=60)
        ratio = op_lo.pmp / op_stc.pmp
        assert 0.18 < ratio < 0.21, f"弱光 Pmp/Pmp_stc={ratio:.3f} 越界"

    def test_isc_monotonic_irradiance(self):
        irradiances = [100, 300, 500, 800, 1000, 1200]
        iscs = [operating_point(CSI_EARLY, G, 25.0, ns=60).isc for G in irradiances]
        assert all(iscs[i] < iscs[i + 1] for i in range(len(iscs) - 1)), "Isc 应随辐照单调递增"

    def test_iv_curve_returned_arrays_consistent(self):
        op = operating_point(CSI_EARLY, 1000.0, 25.0, ns=60, npts=200)
        assert len(op.v) == len(op.i) == 200
        assert op.v[0] == 0
        assert op.v[-1] == pytest.approx(op.voc, rel=1e-4)


# ============================================================
# temperature.faiman
# ============================================================

class TestTemperature:
    def test_zero_irradiance_gives_ambient(self):
        assert faiman(0, 25.0, 1.0) == pytest.approx(25.0)

    def test_higher_wind_cools_panel(self):
        t1 = faiman(800, 25.0, 0.5)
        t2 = faiman(800, 25.0, 5.0)
        assert t2 < t1, "更大风速应让电池更凉"

    def test_typical_noon_panel_around_40_60c(self):
        t = float(faiman(800, 25.0, 1.0))
        assert 40 < t < 60, f"800 W/m^2 + 25°C 气温下电池温应在 40-60, 实际 {t}"


# ============================================================
# lcoe
# ============================================================

class TestLCOE:
    def test_lcoe_positive_and_reasonable(self):
        r = lcoe(CSI_EARLY, kwp=5.0, year1_energy_kwh=7000)
        assert 0.02 < r["lcoe"] < 0.15, f"晶硅 LCOE 应在 2-15 分/kWh, 实际 {r['lcoe']*100:.2f}"
        assert r["lifetime_energy_kwh"] > 0
        assert r["capex"] == 5.0 * 1000 * CSI_EARLY.capex_per_wp

    def test_pero_repr_higher_lcoe_than_csi(self):
        r_c = lcoe(CSI_EARLY, kwp=5.0, year1_energy_kwh=7000)
        r_p = lcoe(PEROVSKITE, kwp=5.0, year1_energy_kwh=7400, scenario="代表性")
        assert r_p["lcoe"] > r_c["lcoe"], "代表性钙钛矿 LCOE 应高于晶硅 (寿命短主导)"


# ============================================================
# degradation
# ============================================================

class TestDegradation:
    def test_retention_monotonic_decreasing(self):
        prof = profile_for(CSI_EARLY)
        years = np.linspace(0, 25, 50)
        rets = retention(prof, years)
        # 允许早期 burn-in 后再单调
        assert rets[0] >= 0.99
        assert rets[-1] < rets[0]
        assert (np.diff(rets) <= 1e-9).all(), "应单调不增"

    def test_pero_repr_drops_faster(self):
        prof_c = profile_for(CSI_EARLY)
        prof_p = profile_for(PEROVSKITE, "代表性")
        # 第 5 年钙钛矿保持率应低于晶硅
        r_c = float(retention(prof_c, 5.0))
        r_p = float(retention(prof_p, 5.0))
        assert r_p < r_c

    def test_pero_optimistic_better_than_repr(self):
        prof_repr = profile_for(PEROVSKITE, "代表性")
        prof_opt = profile_for(PEROVSKITE, "乐观(改进封装)")
        r_repr = float(retention(prof_repr, 10.0))
        r_opt = float(retention(prof_opt, 10.0))
        assert r_opt > r_repr, "乐观情景第10年应高于代表"


# ============================================================
# spectral.eqe
# ============================================================

class TestSpectral:
    def test_csi_cuts_at_silicon_bandgap(self):
        # 晶硅 1100 nm 附近应有 EQE; 1200 nm 应接近 0
        val_900 = float(eqe(CSI_EARLY, np.array([900.0]))[0])
        val_1200 = float(eqe(CSI_EARLY, np.array([1200.0]))[0])
        assert val_900 > 0.7
        assert val_1200 < 0.05

    def test_pero_cuts_at_perovskite_bandgap(self):
        # 钙钛矿 700 nm 有效, 900 nm 截止
        val_700 = float(eqe(PEROVSKITE, np.array([700.0]))[0])
        val_900 = float(eqe(PEROVSKITE, np.array([900.0]))[0])
        assert val_700 > 0.7
        assert val_900 < 0.05
