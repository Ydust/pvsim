"""Constrained electrical-parameter stress test, never an empirical interval.

Seven single-junction and seven c-Si parameterizations are crossed. The existing
STC Pmax, Voc and 15--65 C Pmax slope are retained separately for each technology.
Hourly perturbation factors are anchored to the stored original hourly yields,
then propagated with the unchanged primary spatial operator.
"""
from pathlib import Path
import sys, json, time, os
from dataclasses import replace, asdict
sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(os.environ.get('PVSIM_ROOT', '.'))
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
from scipy.optimize import least_squares, brentq
from scipy.special import lambertw
from scipy.interpolate import RegularGridInterpolator
from pvsim.materials import CSI_MODERN, PEROVSKITE, K_B, Q as Q_E
from pvsim.cell import operating_point
from pvsim.system import inverter_ac, simulate, SystemConfig
from pvsim.optics import effective_poa
from pvsim.temperature import cell_temperature
from pvsim.spectral import spectral_factor_from_zenith
from pvsim.city_catalog import load_city_catalog
from pvsim.weather import from_pvgis_tmy
from scripts.silicon_baseline_sensitivity import _gamma_pmax
from scripts.analyse_regional_policy import load, evaluate, winners

D = Path('.')
OUT = Path(os.environ.get('PVSIM_CHECK_DIR', str(D / 'reproduced')))
N = OUT / 'data'
N.mkdir(parents=True, exist_ok=True)
GRID_G = np.arange(0., 1800.1, 5.)
GRID_T = np.arange(-50., 100.1, 1.)
TECHS = {'csi': CSI_MODERN, 'single': PEROVSKITE}

def save(df, name):
    df.to_csv(N / (name + '.csv'), index=False)

def variants(base):
    op0 = operating_point(base, 1000., 25.)
    gamma0 = _gamma_pmax(base)
    settings = [('Baseline', {}), ('Rs 0.8', {'R_s': base.R_s * .8}),
        ('Rs 1.2', {'R_s': base.R_s * 1.2}), ('Rsh 0.5', {'R_sh_ref': base.R_sh_ref * .5}),
        ('Rsh 2.0', {'R_sh_ref': base.R_sh_ref * 2}),
        ('Ideality low', {'n_ideality': max(1., base.n_ideality * .9)}),
        ('Ideality high', {'n_ideality': base.n_ideality * 1.1})]
    out, records = [], []
    for label, settings in settings:
        if not settings:
            t = base
        else:
            initial = replace(base, **settings)
            vth = initial.n_ideality * K_B * 298.15 / Q_E
            guess_io = (base.I_L_ref - op0.voc / initial.R_sh_ref) / np.expm1(op0.voc / vth)
            def candidate(x):
                il, io = np.exp(x)
                return replace(initial, I_L_ref=il, I_o_ref=io, alpha_sc=base.alpha_sc * il / base.I_L_ref)
            def residual(x):
                op = operating_point(candidate(x), 1000., 25.)
                return [(op.pmp / op0.pmp - 1), (op.voc / op0.voc - 1)]
            fit = least_squares(residual, np.log([base.I_L_ref, guess_io]),
                xtol=1e-13, ftol=1e-13, gtol=1e-13, max_nfev=250)
            assert fit.success and max(abs(np.array(residual(fit.x)))) < 1e-8
            t = candidate(fit.x)
            ea = brentq(lambda x: _gamma_pmax(replace(t, Ea_recomb=x)) - gamma0, .05, 3., xtol=1e-11)
            t = replace(t, Ea_recomb=ea)
        op = operating_point(t, 1000., 25.)
        actual_gamma = _gamma_pmax(t)
        assert abs(op.pmp / op0.pmp - 1) < 1e-8
        assert abs(op.voc / op0.voc - 1) < 1e-8
        assert abs(actual_gamma - gamma0) < 1e-7
        out.append((label, t))
        records.append(dict(technology=base.name, electrical_case=label, I_L_ref=t.I_L_ref, I_o_ref=t.I_o_ref,
            R_s=t.R_s, R_sh_ref=t.R_sh_ref, n_ideality=t.n_ideality, alpha_sc=t.alpha_sc, Ea_recomb=t.Ea_recomb,
            stc_cell_pmax_w=op.pmp, stc_cell_voc_v=op.voc, stc_cell_isc_a=op.isc, stc_ff=op.ff,
            pmax_error_pct=100 * (op.pmp / op0.pmp - 1), voc_error_pct=100 * (op.voc / op0.voc - 1),
            gamma_pct_c=actual_gamma, gamma_error_pp_c=actual_gamma - gamma0))
    return out, records

def vector_pmax(tech, geff, temp, npts=120):
    shape = np.broadcast_shapes(np.shape(geff), np.shape(temp))
    g = np.maximum(np.broadcast_to(geff, shape).ravel(), 1e-6)
    tc = np.broadcast_to(temp, shape).ravel() + 273.15
    result = np.empty_like(g)
    for start in range(0, len(g), 1600):
        sl = slice(start, start + 1600)
        gg, tt = g[sl], tc[sl]
        il = gg / 1000 * (tech.I_L_ref + tech.alpha_sc * (tt - 298.15))
        io = tech.I_o_ref * (tt / 298.15) ** 3 * np.exp(tech.Ea_recomb / 8.617333262e-5 * (1 / 298.15 - 1 / tt))
        sh = gg / (tech.R_sh_ref * 1000)
        a = tech.n_ideality * K_B * tt / Q_E
        rs = tech.R_s
        aa = 1 + rs * sh
        voc = a * np.log1p(il / io)
        for _ in range(8):
            ex = io * np.exp(np.clip(voc / a, -700, 700))
            voc -= (il + io - ex - sh * voc) / (-ex / a - sh)
        def current(v):
            vv = np.asarray(v)
            expand = vv.ndim == 2
            ll, ii, ss, av, avv = (x[:, None] for x in (il, io, sh, a, aa)) if expand else (il, io, sh, a, aa)
            arg = rs * ii / (avv * av) * np.exp(np.clip((rs * (ll + ii) + vv) / (avv * av), -700, 700))
            return (ll + ii - ss * vv) / avv - av / rs * np.real(lambertw(arg))
        vv = voc[:, None] * np.linspace(0, 1, npts)[None, :]
        pp = vv * np.maximum(0, current(vv))
        k = np.clip(pp.argmax(axis=1), 1, npts - 2)
        ii = np.arange(len(k))
        p0, p1, p2 = pp[ii, k - 1], pp[ii, k], pp[ii, k + 1]
        denom = p0 - 2 * p1 + p2
        vm = vv[ii, k] - .5 * (voc / (npts - 1)) * np.divide(p2 - p0, denom, out=np.zeros_like(p0), where=denom != 0)
        result[sl] = vm * current(vm)
    return result.reshape(shape)

def weather_inputs(anchors):
    cache = OUT / 'electrical_hourly_inputs.npz'
    if cache.exists():
        return dict(np.load(cache))
    arrays = {'poa': [], 'tcell': [], 'csi_eff': [], 'single_eff': []}
    for i, a in enumerate(anchors):
        w = from_pvgis_tmy(a.lat, a.lon, altitude=a.altitude_m, name=a.cache_key,
            cache_dir=str(ROOT / 'data/tmy_cache'), allow_download=False)
        poa = w.poa_global.to_numpy(float)
        tc = cell_temperature(poa, w.temp_air.to_numpy(float), w.wind_speed.to_numpy(float), model='faiman', u0=25., u1=6.84)
        eff = effective_poa(w.poa_direct.to_numpy(float), w.poa_diffuse.to_numpy(float), w.aoi.to_numpy(float))
        arrays['poa'].append(poa); arrays['tcell'].append(tc)
        for tech, t in TECHS.items():
            arrays[tech + '_eff'].append(eff * spectral_factor_from_zenith(t, w.solar_zenith.to_numpy(float), tcell_C=tc))
        if (i + 1) % 70 == 0:
            print('Prepared hourly conditions', i + 1, flush=True)
    arrays = {k: np.asarray(v) for k, v in arrays.items()}
    assert all(v.shape == (337, 8760) for v in arrays.values())
    np.savez_compressed(cache, **arrays)
    return arrays

def yields(t, g, tc, poa, coarse=False):
    gg, tt = np.meshgrid(GRID_G, GRID_T, indexing='ij')
    pm = vector_pmax(t, gg, tt)
    pm[0] = 0
    step = 2 if coarse else 1
    lookup = RegularGridInterpolator((GRID_G[::step], GRID_T[::step]), pm[::step, ::step], bounds_error=True)
    if (np.nanmin(g) < 0) or (np.nanmax(g) > GRID_G[-1]) or (np.min(tc) < GRID_T[0]) or (np.max(tc) > GRID_T[-1]):
        raise ValueError('Hourly conditions outside declared interpolation grid')
    power = lookup((g, tc)) * t.cells_in_series
    power[poa <= 1.] = 0
    rated = operating_point(t, 1000., 25., ns=t.cells_in_series).pmp
    ac = inverter_ac(power * .98 * .95, rated / 1.2, .96)
    result = np.sum(ac, axis=1) / rated
    return result

def main():
    began = time.time()
    anchors = sorted(load_city_catalog(), key=lambda x: x.adcode)
    city, y0, den, cost = load()
    assert [a.adcode for a in anchors] == city.adcode.tolist()
    all_variants, reg = {}, []
    for key, tech in TECHS.items():
        vs, rr = variants(tech)
        all_variants[key] = vs; reg.extend(rr)
    save(pd.DataFrame(reg), 'electrical_parameter_register')
    print('Fourteen constrained parameterizations fitted', flush=True)
    wx = weather_inputs(anchors)
    raw = pd.read_csv(ROOT / 'outputs/city_mechanism_attribution.csv', dtype={'adcode': str}).set_index('adcode').loc[city.adcode]
    op = np.load(ROOT / '.work/figures234_submission_20260907/spatial_operator.npy')
    assert op.shape == (337, 337)
    response, checks, normalized = [], [], []
    mapped = {}
    mapped_coarse = {}
    sample_g, sample_t = np.meshgrid([50., 100., 200., 400., 800., 1000., 1200.], [-10., 15., 25., 45., 65.], indexing='ij')
    for key, vs in all_variants.items():
        prefix = 'perovskite' if key == 'single' else 'csi'
        base_lookup = {}
        base_coarse = {}
        for case_index, (label, tech) in enumerate(vs):
            for mask in [0, 7]:
                tc = wx['tcell'] if mask == 7 else np.full_like(wx['tcell'], 25.)
                ge = wx[key + '_eff'] if mask == 7 else wx['poa']
                yy = yields(tech, ge, tc, wx['poa'])
                coarse = yields(tech, ge, tc, wx['poa'], coarse=True)
                if case_index == 0:
                    base_lookup[mask] = yy.copy()
                    base_coarse[mask] = coarse.copy()
                factor = yy / base_lookup[mask]
                suffix = 't1_s1_i1' if mask == 7 else 't0_s0_i0'
                stored = raw[f'{prefix}_yield_{suffix}_kwh_per_kwp'].to_numpy()
                annual = stored * factor
                area = op @ annual
                assert (annual > 0).all() and (area > 0).all()
                mapped[key, label, mask] = area
                mapped_coarse[key, label, mask] = op @ (stored * coarse / base_coarse[mask])
                checks.append(dict(technology=key, electrical_case=label, mask=mask,
                    max_coarse_vs_fine_yield_pct=float(np.max(abs(coarse / yy - 1)) * 100),
                    min_hourly_geff=float(ge.min()), max_hourly_geff=float(ge.max()),
                    min_temperature=float(tc.min()), max_temperature=float(tc.max())))
                response.append(pd.DataFrame(dict(technology=key, electrical_case=label, mask=mask,
                    adcode=city.adcode, raw_lookup_yield_kwh_kwp=yy, original_anchor_yield_kwh_kwp=stored,
                    relative_hourly_response_factor=factor, anchored_yield_kwh_kwp=annual,
                    primary_area_yield_kwh_kwp=area)))
            pm = vector_pmax(tech, sample_g, sample_t)
            rating = operating_point(tech, 1000., 25.).pmp
            for g, tt, val in zip(sample_g.ravel(), sample_t.ravel(), pm.ravel()):
                normalized.append(dict(technology=key, electrical_case=label, effective_irradiance_w_m2=g,
                    cell_temperature_c=tt, normalized_pmax=val / rating, pmax_per_relative_irradiance=val / rating / (g / 1000)))
            print(key, label, 'hourly propagation complete', flush=True)
    save(pd.concat(response, ignore_index=True), 'electrical_anchor_responses')
    save(pd.DataFrame(checks), 'electrical_numerical_convergence')
    save(pd.DataFrame(normalized), 'electrical_response_matrix')
    # Every crossed case is retained, including sign changes; no probability weights.
    summaries, detail, economic = [], [], []
    idx = np.arange(337)
    for clabel, _ in all_variants['csi']:
        for slabel, _ in all_variants['single']:
            ys, yp = mapped['csi', clabel, 7], mapped['single', slabel, 7]
            full = 100 * (yp / ys - 1)
            off = 100 * (mapped['single', slabel, 0] / mapped['csi', clabel, 0] - 1)
            need = 1 / (den[1] / den[0] * (1 + full / 100))
            full_coarse = 100 * (mapped_coarse['single', slabel, 7] / mapped_coarse['csi', clabel, 7] - 1)
            off_coarse = 100 * (mapped_coarse['single', slabel, 0] / mapped_coarse['csi', clabel, 0] - 1)
            q1, q4 = city.ghi_quartile.eq('Q1').to_numpy(), city.ghi_quartile.eq('Q4').to_numpy()
            summaries.append(dict(csi_case=clabel, single_case=slabel, cities=337,
                positive_all_on=int((full > 0).sum()), min_all_on_pct=full.min(), mean_all_on_pct=full.mean(), max_all_on_pct=full.max(),
                q1_q4_pp=full[q1].mean() - full[q4].mean(), positive_all_off=int((off > 0).sum()),
                min_all_off_pct=off.min(), mean_all_off_pct=off.mean(), max_all_off_pct=off.max(),
                density_50pct_target_multiplier=np.sort(need)[168], density_90pct_target_multiplier=np.sort(need)[303],
                all_on_sign_disagreements_grid=int(((full > 0) != (full_coarse > 0)).sum()),
                all_off_sign_disagreements_grid=int(((off > 0) != (off_coarse > 0)).sum()),
                max_all_on_grid_difference_pp=float(np.max(abs(full - full_coarse)))))
            detail.append(pd.DataFrame(dict(csi_case=clabel, single_case=slabel, adcode=city.adcode,
                full_capacity_gain_pct=full, electrical_baseline_gain_pct=off, aperture_parity_density_multiplier=need,
                coarse_grid_full_gain_pct=full_coarse, coarse_grid_electrical_gain_pct=off_coarse)))
            y = np.column_stack([ys, yp, y0[:, 2]])
            ev = evaluate(city, y, den, cost)
            ratio = y / y[:, [0]]
            evs = evaluate(city, y[:, [0]] * ratio.mean(axis=0), den, cost)
            for ctx, scale in [('cap', 1000.), ('area', 10000.)]:
                p = ev['npv_' + ctx] * scale
                w, v = winners(p), winners(evs['npv_' + ctx])
                best = np.maximum(0, p.max(axis=1))
                selected = np.where(v < 0, 0, p[idx, np.maximum(v, 0)])
                loss = best - selected
                assert min(loss) >= -1e-7
                economic.append(dict(csi_case=clabel, single_case=slabel, context=ctx,
                    viable=int((w >= 0).sum()), single_selected=int((w == 1).sum()), tandem_selected=int((w == 2).sum()),
                    uniform_ratio_choices_changed=int((w != v).sum()), information_loss_usd=loss.sum(),
                    reference_npv_usd=best.sum(), information_loss_pct=100 * loss.sum() / best.sum()))
    save(pd.DataFrame(summaries), 'electrical_pair_summary')
    save(pd.concat(detail, ignore_index=True), 'electrical_pair_city')
    save(pd.DataFrame(economic), 'electrical_economic_summary')
    baseline = pd.DataFrame(summaries).query("csi_case == 'Baseline' and single_case == 'Baseline'").iloc[0]
    assert baseline.positive_all_on == baseline.positive_all_off == 337
    assert np.max(abs(mapped['csi', 'Baseline', 7] - y0[:, 0])) < 1e-8
    assert np.max(abs(mapped['single', 'Baseline', 7] - y0[:, 1])) < 1e-8
    # Independent scalar operating-point check at declared conditions.
    scalar = []
    for key, vs in all_variants.items():
        for label, tech in vs:
            fast = vector_pmax(tech, sample_g, sample_t)
            exact = np.array([operating_point(tech, float(g), float(t), npts=400).pmp for g, t in zip(sample_g.ravel(), sample_t.ravel())]).reshape(sample_g.shape)
            scalar.append(dict(technology=key, electrical_case=label,
                maximum_scalar_relative_pmax_error_pct=float(np.max(abs(fast / exact - 1)) * 100)))
    save(pd.DataFrame(scalar), 'electrical_solver_check')
    report = dict(crossed_parameter_pairs=49, primary_city_pair_records=49 * 337, states_per_pair=2,
        empirical_probabilities=False, new_device_validation=False, constrained_targets=['STC Pmax', 'STC Voc', '15--65 C Pmax slope'],
        unstressed_physical_inputs=['Tandem parameters', 'thermal model', 'spectrum', 'IAM', 'inverter', 'spatial operator', 'capacity density'],
        max_scalar_pmax_error_pct=max(v['maximum_scalar_relative_pmax_error_pct'] for v in scalar),
        max_grid_convergence_yield_pct=max(v['max_coarse_vs_fine_yield_pct'] for v in checks),
        runtime_seconds=time.time() - began)
    (OUT / 'electrical_checks.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)
    print(pd.DataFrame(summaries).describe().to_string(), flush=True)

if __name__ == '__main__':
    main()
