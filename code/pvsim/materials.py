"""Representative photovoltaic device parameters."""

from __future__ import annotations

from pvsim.labels import label as _text_label

from dataclasses import dataclass, field


Q = 1.602176634e-19
K_B = 1.380649e-23
T_REF = 298.15
G_REF = 1000.0


@dataclass
class SpectralResponse:

    lambda_min: float
    lambda_gap: float
    eqe_peak: float
    edge_width: float = 40.0
    blue_rolloff: float = 60.0


@dataclass
class CellTechnology:

    name: str
    name_cn: str


    area_cm2: float
    cells_in_series: int


    I_L_ref: float
    I_o_ref: float
    R_s: float
    R_sh_ref: float
    n_ideality: float
    alpha_sc: float
    EgRef: float
    dEgdT: float
    Ea_recomb: float


    gamma_pmax_lit: float
    beta_voc_lit: float
    alpha_isc_lit: float


    noct: float


    spectral: SpectralResponse


    degradation_rate: float
    burn_in_loss: float
    burn_in_years: float


    hysteresis_index: float


    bifaciality: float


    capex_per_wp: float
    lifetime_years: float

    notes: str = ""


# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
CSI_EARLY = CellTechnology(
    name="c-Si",
    name_cn=_text_label('tech_early_csi'),
    area_cm2=243.36,
    cells_in_series=60,
    I_L_ref=8.05,
    I_o_ref=2.7e-9,
    R_s=0.0052,
    R_sh_ref=8.0,
    n_ideality=1.10,
    alpha_sc=8.05 * 0.0005,    # +0.05 %/°C × Isc
    EgRef=1.121,
    dEgdT=-0.0002677,
    Ea_recomb=1.0816,
    gamma_pmax_lit=-0.45,
    beta_voc_lit=-0.33,
    alpha_isc_lit=+0.05,
    noct=45.0,
    spectral=SpectralResponse(
        lambda_min=350.0, lambda_gap=1110.0, eqe_peak=0.92,
        edge_width=50.0, blue_rolloff=80.0,
    ),
    degradation_rate=0.007,
    burn_in_loss=0.02,
    burn_in_years=1.0,
    hysteresis_index=0.0,
    bifaciality=0.0,
    capex_per_wp=1.0,
    lifetime_years=25.0,
    notes=_text_label('materials_text'),
)


# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
PEROVSKITE = CellTechnology(
    name="perovskite",
    name_cn=_text_label('tech_perovskite'),
    area_cm2=243.36,
    cells_in_series=60,
    I_L_ref=5.48,
    I_o_ref=9.5e-12,
    R_s=0.016,
    R_sh_ref=30.0,
    n_ideality=1.60,
    alpha_sc=5.48 * 0.0002,   # +0.02 %/°C
    EgRef=1.55,
    dEgdT=+0.0003,
    Ea_recomb=0.8258,

    gamma_pmax_lit=-0.15,
    beta_voc_lit=-0.15,
    alpha_isc_lit=+0.02,
    noct=44.0,
    spectral=SpectralResponse(
        lambda_min=350.0, lambda_gap=800.0, eqe_peak=0.90,
        edge_width=25.0, blue_rolloff=60.0,
    ),
    degradation_rate=0.030,
    burn_in_loss=0.10,
    burn_in_years=1.0,
    hysteresis_index=0.04,
    bifaciality=0.0,
    capex_per_wp=0.8,
    lifetime_years=15.0,
    notes=_text_label('single_junction_perovskite_approximately_20_efficiency_favorable_'),
)


# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
TANDEM_2T = CellTechnology(
    name="tandem",
    name_cn=_text_label('tech_tandem'),
    area_cm2=243.36,
    cells_in_series=60,
    I_L_ref=4.62,              # j_matched ~19 mA/cm² × 243 cm² (current-matched)
    I_o_ref=1.3e-15,
    R_s=0.025,
    R_sh_ref=50.0,
    n_ideality=2.0,
    alpha_sc=4.62 * 0.00025,
    EgRef=1.68,
    dEgdT=+0.0001,
    Ea_recomb=1.5087,
    gamma_pmax_lit=-0.30,      # Babics 2023 ACS Energy Lett.
    beta_voc_lit=-0.24,
    alpha_isc_lit=+0.025,
    noct=45.0,
    spectral=SpectralResponse(
        lambda_min=350.0, lambda_gap=1110.0, eqe_peak=0.85,
        edge_width=50.0, blue_rolloff=70.0,
    ),
    degradation_rate=0.012,
    burn_in_loss=0.04,
    burn_in_years=1.0,
    hysteresis_index=0.01,
    bifaciality=0.0,
    capex_per_wp=1.13,         # Scenario system cost: Cordell MODULE MSP $0.428/WDC
                              # (US, 25%, 3 GW/yr) + assumed ~0.70 system add-on.
                              # The add-on is not verified as a Cordell result;
                              # current economics uses economic_priors.py instead.
    lifetime_years=25.0,
    notes=_text_label('perovskite_c_si_2t_tandem_approximately_28_efficiency_explicit_to'),
)


# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
CSI_MODERN = CellTechnology(
    name="c-Si-modern",
    name_cn=_text_label('tech_modern_csi'),
    area_cm2=243.36,
    cells_in_series=60,
    I_L_ref=11.0962,
    I_o_ref=4.0e-10,
    R_s=0.0040,
    R_sh_ref=15.0,
    n_ideality=1.02,
    alpha_sc=11.0962 * 0.000363,
    EgRef=1.121,
    dEgdT=-0.0002677,
    Ea_recomb=0.9957,
    gamma_pmax_lit=-0.32,
    beta_voc_lit=-0.27,
    alpha_isc_lit=+0.04,
    noct=44.0,
    spectral=SpectralResponse(
        lambda_min=350.0, lambda_gap=1110.0, eqe_peak=0.95,
        edge_width=50.0, blue_rolloff=70.0,
    ),
    degradation_rate=0.005,
    burn_in_loss=0.01,
    burn_in_years=1.0,
    hysteresis_index=0.0,
    bifaciality=0.0,
    capex_per_wp=1.0,
    lifetime_years=25.0,
    notes=_text_label('modern_topcon_perc_c_si_approximately_22_module_efficiency_and_ga'),
)


TECHNOLOGIES = {
    CSI_EARLY.name: CSI_EARLY,
    CSI_MODERN.name: CSI_MODERN,
    PEROVSKITE.name: PEROVSKITE,
    TANDEM_2T.name: TANDEM_2T,
}


def get_technology(name: str) -> CellTechnology:
    if name not in TECHNOLOGIES:
        raise KeyError(f"Unknown technology '{name}', optional: {list(TECHNOLOGIES)}")
    return TECHNOLOGIES[name]
