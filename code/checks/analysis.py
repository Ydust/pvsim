"""Extend existing conditional scenarios to decision and support endpoints.

No observational data are fitted. All original outputs remain immutable.
"""
from pathlib import Path
import sys, json, hashlib, os
sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(os.environ.get('PVSIM_ROOT', '.'))
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
from scripts.analyse_regional_policy import load, evaluate, winners
from pvsim.economics import perovskite_durability
from pvsim.economic_priors import CENTRAL_BREAKTHROUGH_YEAR, CENTRAL_POST_BREAKTHROUGH_LIFETIME_YR

D = Path('.')
Q = Path(os.environ.get('PVSIM_CHECK_DIR', str(D / 'reproduced')))
N = Q / 'data'
N.mkdir(parents=True, exist_ok=True)
CITY, Y, DEN, COST = load()
IDX = np.arange(len(CITY))
assert len(CITY) == CITY.adcode.nunique() == 337
DUR = perovskite_durability(2035, CENTRAL_BREAKTHROUGH_YEAR, CENTRAL_POST_BREAKTHROUGH_LIFETIME_YR)
PARAMS = [('Central', {}), ('Half replacement cost', {'replacement_factor': .5}),
          ('Remaining-life salvage', {'salvage': True})]

def save(df, name):
    df.to_csv(N / (name + '.csv'), index=False)

def energy(ev, context, scale):
    factor = scale if context == 'cap' else ev['density'] * ev['packing'] / 1000 * scale
    return ev['delivered_pv_kwh_kwp'] * factor / 1000

def selected(a, w):
    return np.where(w < 0, 0, a[IDX, np.maximum(w, 0)])

def ceiling(ev, context, kw):
    if context == 'area':
        return max(0., ev['initial_area'][2] - ev['initial_area'][0]) * 10000
    times = np.arange(DUR.lifetime_years, 25 - 1e-9, DUR.lifetime_years)
    return ev['initial_cap'][1] * np.sum(1.05 ** (-times)) * kw.get('replacement_factor', 1.) * 1000

def information(y, label, accounting, kw):
    ev = evaluate(CITY, y, DEN, COST, **kw)
    ratios = y / y[:, [0]]
    simplified = y[:, [0]] * ratios.mean(axis=0)[None, :]
    sm = evaluate(CITY, simplified, DEN, COST, **kw)
    summary, records = [], []
    for context, scale in [('cap', 1000.), ('area', 10000.)]:
        p = ev['npv_' + context] * scale
        w, v = winners(p), winners(sm['npv_' + context])
        best = np.maximum(0, p.max(axis=1))
        loss = best - selected(p, v)
        assert loss.min() >= -1e-7
        p0 = evaluate(CITY, Y, DEN, COST, **kw)['npv_' + context] * scale
        w0 = winners(p0)
        summary.append(dict(spatial_case=label, accounting=accounting, context=context,
            viable=int((w >= 0).sum()), csi=int((w == 0).sum()), single=int((w == 1).sum()), tandem=int((w == 2).sum()),
            choices_changed_from_primary=int((w != w0).sum()),
            uniform_ratio_choices_changed=int((w != v).sum()),
            reference_npv_usd=best.sum(), information_loss_usd=loss.sum(),
            information_loss_pct=100 * loss.sum() / best.sum() if best.sum() else np.nan))
        records.append(pd.DataFrame(dict(spatial_case=label, accounting=accounting, context=context,
            adcode=CITY.adcode, city=CITY.city, province=CITY.province, reference_choice=w,
            primary_choice=w0, uniform_ratio_choice=v, reference_npv_usd=best,
            selected_reference_npv_usd=selected(p, v), information_loss_usd=loss)))
    return ev, summary, records

def policy(ev, label, accounting, kw):
    summaries, details, priorities, curves = [], [], [], []
    for context, j, scale in [('cap', 1, 1000.), ('area', 2, 10000.)]:
        p = ev['npv_' + context] * scale
        w = winners(p)
        before = np.maximum(0, p.max(axis=1))
        en = energy(ev, context, scale)
        eb = selected(en, w)
        full = ceiling(ev, context, kw)
        outside = np.maximum(0, np.delete(p, j, axis=1).max(axis=1))
        gap = np.maximum(0, outside - p[:, j])
        extra_target = en[:, j] - eb
        candidates = (w < 0) if context == 'cap' else ((w != j) & (extra_target > 0))
        candidates &= gap + 1 <= full + 1e-7
        ix = np.where(candidates)[0]
        ordering = gap[ix] + 1 if context == 'cap' else (gap[ix] + 1) / extra_target[ix]
        ix = ix[np.argsort(ordering, kind='stable')]
        for rank, i in enumerate(ix, 1):
            priorities.append(dict(spatial_case=label, accounting=accounting, context=context, rank=rank,
                adcode=CITY.adcode.iloc[i], transfer_usd=gap[i] + 1, extra_mwh=extra_target[i], ceiling_usd=full))
        for count in range(len(ix) + 1):
            chosen = ix[:count]
            curves.append(dict(spatial_case=label, accounting=accounting, context=context,
                strategy='Ranked additions', index=count, support_fraction=np.nan,
                public_cost_usd=float(np.sum(gap[chosen] + 1) * 1.05),
                new_viable=count if context == 'cap' else 0, switches=count,
                extra_mwh=float(extra_target[chosen].sum())))
        for share in [0., .25, .5, .75, 1.]:
            uniform_values = p.copy()
            uniform_values[:, j] += full * share
            v = winners(uniform_values)
            switched = (v == j) & (w != j)
            new_viable = (w < 0) & (v >= 0)
            objective = new_viable if context == 'cap' else switched
            if context == 'area':
                assert np.all(extra_target[switched] > 0)
            uniform = np.where(v == j, full * share, 0.)
            strict = np.where(switched, np.minimum(gap + 1., full * share), 0.)
            matched = np.where(objective, np.minimum(gap + 1., full * share), 0.)
            target_ids = set(np.where(objective)[0])
            is_prefix = target_ids == set(ix[:int(objective.sum())])
            for strategy, support in [('Uniform', uniform), ('Matched additions', matched), ('Strict selections', strict)]:
                pp = p.copy()
                pp[:, j] += support
                va = winners(pp)
                if strategy in ('Uniform', 'Strict selections'):
                    assert np.array_equal(v, va)
                if strategy == 'Matched additions':
                    assert np.array_equal((w < 0) & (va >= 0), new_viable)
                    if context == 'area':
                        assert np.array_equal(va, v)
                after = np.maximum(0, pp.max(axis=1))
                ea = selected(en, va)
                gain = after - before
                assert np.all(gain >= -1e-7) and np.all(gain <= support + 1e-7)
                paid = support > 0
                newly_selected = (va == j) & (w != j)
                newly_viable = (w < 0) & (va >= 0)
                obj = newly_viable if context == 'cap' else newly_selected
                use = np.select([paid & obj, paid & newly_selected & ~obj, paid & (w == j)],
                    ['Objective additions', 'Other switches', 'Baseline adopters'], default='None')
                assert not np.any(paid & (use == 'None'))
                rec = dict(spatial_case=label, accounting=accounting, context=context, strategy=strategy,
                    support_fraction=share, before_viable=int((w >= 0).sum()), after_viable=int((va >= 0).sum()),
                    new_viable=int(newly_viable.sum()), before_target=int((w == j).sum()),
                    after_target=int((va == j).sum()), new_target=int(newly_selected.sum()),
                    supported_projects=int(paid.sum()), baseline_adopters_paid=int((paid & (w == j)).sum()),
                    before_npv_usd=before.sum(), after_npv_usd=after.sum(), private_gain_usd=gain.sum(),
                    direct_support_usd=support.sum(), admin_usd=.05 * support.sum(),
                    public_cost_usd=1.05 * support.sum(), extra_mwh=(ea - eb).sum(),
                    full_instrument_ceiling_usd=full, matched_set_is_global_rank_prefix=int(is_prefix),
                    all_choices_match_uniform=int(np.array_equal(v, va)))
                for category, short in [('Objective additions', 'objective'), ('Other switches', 'other_switch'), ('Baseline adopters', 'baseline_adopter')]:
                    rec[short + '_support_usd'] = float(support[use == category].sum())
                summaries.append(rec)
                details.append(pd.DataFrame(dict(spatial_case=label, accounting=accounting, context=context,
                    strategy=strategy, support_fraction=share, adcode=CITY.adcode, city=CITY.city, province=CITY.province,
                    before_choice=w, after_choice=va, before_npv_usd=before, after_npv_usd=after,
                    transfer_usd=support, admin_usd=.05 * support, private_gain_usd=gain,
                    extra_mwh=ea - eb, spending_use=use, new_viable=newly_viable,
                    outside_option_npv_usd=outside, candidate_npv_usd=p[:, j], financing_gap_usd=gap,
                    full_instrument_ceiling_usd=full)))
            u = summaries[-3]
            curves.append(dict(spatial_case=label, accounting=accounting, context=context,
                strategy='Uniform', index=int(share * 100), support_fraction=share,
                public_cost_usd=u['public_cost_usd'], new_viable=u['new_viable'],
                switches=u['new_target'], extra_mwh=u['extra_mwh']))
    return summaries, details, priorities, curves

def main():
    old = pd.read_csv(ROOT / 'outputs/prefecture_area_weighted_physics_summary.csv', dtype={'adcode': str}).set_index('adcode').loc[CITY.adcode]
    alt = np.column_stack([old[f'{k}_yield_kwh_per_kwp'].to_numpy() for k in ['csi', 'perovskite', 'tandem']])
    # Keep paired technology fields; ratio-only control isolates their regional response.
    variants = [('Primary', Y), ('Alternative area estimator', alt),
                ('Alternative ratios with primary c-Si', Y[:, [0]] * (alt / alt[:, [0]]))]
    inf, infcity, pol, polcity, pri, cur = [], [], [], [], [], []
    yr = []
    for label, y in variants:
        assert np.isfinite(y).all() and (y > 0).all()
        for i in range(337):
            yr.append(dict(spatial_case=label, adcode=CITY.adcode.iloc[i], city=CITY.city.iloc[i],
                csi_yield_kwh_kwp=y[i, 0], single_yield_kwh_kwp=y[i, 1], tandem_yield_kwh_kwp=y[i, 2]))
        for accounting, kw in PARAMS:
            ev, a, b = information(y, label, accounting, kw)
            inf.extend(a); infcity.extend(b)
            a, b, c, d = policy(ev, label, accounting, kw)
            pol.extend(a); polcity.extend(b); pri.extend(c); cur.extend(d)
            print(label, accounting, 'completed', flush=True)
    inf, pol = pd.DataFrame(inf), pd.DataFrame(pol)
    save(inf, 'information_summary')
    save(pd.concat(infcity, ignore_index=True), 'information_city')
    save(pol, 'policy_summary')
    pd.concat(polcity, ignore_index=True).to_csv(N / 'policy_city.csv.gz', index=False, compression='gzip')
    save(pd.DataFrame(pri), 'priority_city')
    save(pd.DataFrame(cur), 'budget_curves')
    save(pd.DataFrame(yr), 'spatial_yields')
    match = pol.merge(pol[pol.strategy.eq('Uniform')][['spatial_case', 'accounting', 'context', 'support_fraction', 'public_cost_usd']],
        on=['spatial_case', 'accounting', 'context', 'support_fraction'], suffixes=('', '_uniform'), validate='many_to_one')
    match['saving_pct'] = np.where(match.public_cost_usd_uniform > 0,
        100 * (1 - match.public_cost_usd / match.public_cost_usd_uniform), np.nan)
    save(match[match.support_fraction.eq(.5)], 'matched_50pct_summary')
    reg = []
    for label, kw in PARAMS:
        reg.append(dict(accounting=label, replacement_cost_multiplier=kw.get('replacement_factor', 1.),
            remaining_life_salvage=int(kw.get('salvage', False)), project_horizon_years=25,
            single_lifetime_years=DUR.lifetime_years, discount_rate=.05, administration_fraction=.05,
            capacity_scale_kwp=1000, area_scale_m2=10000,
            ceiling_definition='Discounted gross replacement outlay after replacement multiplier; terminal credit fixed at gross asset remaining value'))
    save(pd.DataFrame(reg), 'accounting_case_register')
    central = inf[inf.spatial_case.eq('Primary') & inf.accounting.eq('Central')].set_index('context')
    assert central.loc['cap', 'uniform_ratio_choices_changed'] == 59
    assert central.loc['area', 'uniform_ratio_choices_changed'] == 14
    primary = inf[inf.spatial_case.eq('Primary') & inf.context.eq('cap')].set_index('accounting')
    assert np.array_equal(337 - primary.loc[[p[0] for p in PARAMS], 'viable'].to_numpy(), [79, 31, 14])
    c = match[match.spatial_case.eq('Primary') & match.accounting.eq('Central') & match.support_fraction.eq(.5)]
    for context, new, expected in [('cap', 48, 94.1), ('area', 0, 79.9)]:
        z = c[c.context.eq(context) & c.strategy.eq('Matched additions')].iloc[0]
        assert z.new_viable == new and abs(z.saving_pct - expected) < .05
    report = dict(cities=337, spatial_cases=len(variants), accounting_cases=3,
        information_rows=len(inf), policy_summary_rows=len(pol), policy_city_rows=sum(len(v) for v in polcity),
        original_central_information_counts_reproduced=True, original_nonviable_sensitivity_reproduced=True,
        original_headline_savings_reproduced=True, primary_50pct=c.to_dict('records'),
        accounting_information=inf[inf.spatial_case.eq('Primary')].to_dict('records'),
        all_primary_accounting_matched=match[match.spatial_case.eq('Primary') & match.support_fraction.eq(.5)].to_dict('records'))
    (Q / 'economic_checks.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=True), encoding='utf-8')
    print(inf.to_string(index=False), flush=True)

if __name__ == '__main__':
    main()
