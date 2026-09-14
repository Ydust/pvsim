from pvsim.labels import label as _text_label
import sys
import numpy as np
import pvlib

from pvsim.materials import CSI_EARLY, PEROVSKITE
from pvsim.cell import operating_point

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

KB = 1.380649e-23
Q = 1.602176634e-19
TREF = 298.15


def compare(tech, label):
    ns = tech.cells_in_series
    a_ref = tech.n_ideality * ns * KB * TREF / Q

    conditions = [
        ("STC",       1000.0, 25.0),
        (_text_label('hot_high_irradiance'),   1000.0, 60.0),
        (_text_label('low_irradiance'),        200.0, 25.0),
        (_text_label('cold_high_irradiance'),   1200.0, -5.0),
    ]

    print(f"\n========== {label} (Ns={ns}, Ea_recomb={tech.Ea_recomb:.3f} eV) ==========")
    print(f"{_text_label('operating_condition'):<10}{_text_label('metric'):<6}{'pvsim':>12}{'pvlib':>12}{_text_label('validate_against_pvlib_text'):>12}")
    print("-" * 56)

    max_abs_pct = 0.0
    for cond, G, T in conditions:
        # pvsim
        op = operating_point(tech, G, T, effective_irradiance=G, ns=ns, npts=400)


        IL, I0, Rs, Rsh, nNsVth = pvlib.pvsystem.calcparams_desoto(
            effective_irradiance=G, temp_cell=T,
            alpha_sc=tech.alpha_sc,
            a_ref=a_ref,
            I_L_ref=tech.I_L_ref,
            I_o_ref=tech.I_o_ref,
            R_sh_ref=tech.R_sh_ref * ns,
            R_s=tech.R_s * ns,
            EgRef=tech.Ea_recomb,
            dEgdT=0.0,
        )
        sd = pvlib.pvsystem.singlediode(
            photocurrent=IL, saturation_current=I0,
            resistance_series=Rs, resistance_shunt=Rsh, nNsVth=nNsVth,
        )

        for metric, ps, pl, unit in [
            ("Pmp", op.pmp, float(sd["p_mp"]), "W"),
            ("Voc", op.voc, float(sd["v_oc"]), "V"),
            ("Isc", op.isc, float(sd["i_sc"]), "A"),
            ("FF",  op.ff,  float(sd["p_mp"] / (sd["v_oc"] * sd["i_sc"])
                                 if sd["v_oc"] * sd["i_sc"] > 0 else 0), ""),
        ]:
            pct = (ps - pl) / pl * 100 if pl != 0 else 0
            max_abs_pct = max(max_abs_pct, abs(pct))
            print(f"{cond:<10}{metric:<6}{ps:>11.4f}{unit}{pl:>11.4f}{unit}{pct:>+11.4f}")
        print()

    print(f'>>> {label} Maximum absolute deviation: {max_abs_pct:.4f} %')
    return max_abs_pct


def main():
    err1 = compare(CSI_EARLY, _text_label('tech_early_csi'))
    err2 = compare(PEROVSKITE, _text_label('tech_perovskite'))
    print('\n========== Validation result ==========')
    print(f'Maximum c-Si deviation   : {err1:.4f} %')
    print(f'Maximum perovskite deviation : {err2:.4f} %')
    overall = max(err1, err2)
    print(f'Maximum overall deviation   : {overall:.4f} %')
    if overall < 0.1:
        print('✓ PASS (< 0.1%): pvsim and pvlib Numerically consistent, Lambert W and De Soto translation shows no material discrepancy')
    else:
        print('✗ FAIL, Check nNsVth scaling or I0(T) law alignment')


if __name__ == "__main__":
    main()
