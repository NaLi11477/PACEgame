"""v0.2.2 acceptance of the five third-audit counterexamples.

Usage: python -m pacegame.examples.validate_audit_022 --out results.json
Only public model extensions are used; assertions establish repaired behavior.
"""
from __future__ import annotations
import argparse, json, math, platform, sys
from dataclasses import dataclass, replace
from pathlib import Path
import sympy as sp
import pacegame as pg
from pacegame.analyze import derivative, verify
from pacegame.solve.feasible import check_point
from pacegame.core.lifecycle import TwoPhase, Segment

POINT = dict(sigma=.1, phi=.85, hatvarsigma=.3)

def strategy(game, name):
    return next(s for s in game.strategies if s.name == name)

def pack_solution(sol):
    return {'point': {str(k): float(v) for k, v in sol.point.items()},
            'kind': {str(k): v for k, v in sol.kind.items()}, 'payoffs': sol.payoffs,
            'rankable': sol.rankable, 'feasibility_ok': sol.feasibility.ok,
            'feasibility_complete': sol.feasibility.complete,
            'findings': [vars(f) for f in sol.feasibility.findings]}

def pack_report(rep):
    return {'ok': rep.ok, 'complete': rep.complete, 'points': rep.points,
            'results': [{'passed': r.passed, 'failed': r.failed, 'skipped': r.skipped,
                         'errors': r.errors, 'holds': r.holds,
                         'reasons': r.reasons, 'counterexamples': r.counterexamples} for r in rep.results]}

@dataclass(slots=True)
class SlottedTwoPhase(TwoPhase):
    gain: sp.Expr = sp.Integer(1)
    def segments(self, *args, **kw):
        return [Segment(s.lo, s.hi, self.gain * s.expr)
                for s in super(SlottedTwoPhase, self).segments(*args, **kw)]
    def capacity(self):
        return self.gain * super(SlottedTwoPhase, self).capacity()

@dataclass
class PlainTwoPhase(TwoPhase):
    gain: sp.Expr = sp.Integer(1)
    def segments(self, *args, **kw):
        return [Segment(s.lo, s.hi, self.gain * s.expr)
                for s in super().segments(*args, **kw)]
    def capacity(self):
        return self.gain * super().capacity()

class FixedZero(pg.Game):
    def bounds(self, st):
        b = super().bounds(st)
        b[self.entry] = (sp.Integer(0), sp.Integer(0))
        return b

class FixedTenth(pg.Game):
    def bounds(self, st):
        b = super().bounds(st)
        b[self.entry] = (sp.Rational(1, 10), sp.Rational(1, 10))
        return b

def silence(base, cls=pg.Game, **overrides):
    return cls(lifecycle=base.lifecycle, share_rule=base.share_rule, entry=base.entry,
               signal=base.signal, strategies=tuple(s for s in base.strategies if not s.signals),
               **overrides)

def main(out):
    data = {'environment': {'pacegame': pg.__version__, 'import_path': pg.__file__,
            'python': sys.version, 'sympy': sp.__version__, 'platform': platform.platform()}, 'groups': {}}
    assert pg.__version__ == '0.2.11'

    # Public dataclass(slots=True) mutation must invalidate cached expressions.
    base = pg.models.preannounce_entry()
    life = SlottedTwoPhase(base.lifecycle.sigma, base.lifecycle.growth_end,
                          base.lifecycle.horizon, base.lifecycle.keep_stock)
    game = replace(base, lifecycle=life)
    st = strategy(game, 'DF')
    before = pg.solve(game, st, game.numeric(POINT))
    fingerprint = game._fingerprint()
    life.gain = sp.Integer(2)
    after = pg.solve(game, st, game.numeric(POINT))
    equal = fingerprint == game._fingerprint()
    fresh = pg.solve(replace(game), st, game.numeric(POINT))
    game.invalidate()
    invalidated = pg.solve(game, st, game.numeric(POINT))
    plain = replace(base, lifecycle=PlainTwoPhase(base.lifecycle.sigma, base.lifecycle.growth_end,
                                                base.lifecycle.horizon, base.lifecycle.keep_stock))
    plain_before = pg.solve(plain, st, plain.numeric(POINT))
    plain.lifecycle.gain = sp.Integer(2)
    plain_after = pg.solve(plain, st, plain.numeric(POINT))
    assert not equal and after.payoffs != before.payoffs and after.rankable
    assert abs(fresh.payoffs['x'] - 2 * before.payoffs['x']) < 1e-15
    # At simultaneous silent entry both shares are 1/2. Integrating the
    # two-phase path gives gain*sigma*(growth-growth**2/2)/8 per player.
    analytic_before = sp.Rational(1, 10) * (sp.Rational(3, 10) - sp.Rational(3, 10)**2 / 2) / 8
    analytic_after = 2 * analytic_before
    assert abs(fresh.payoffs['x'] - float(analytic_after)) < 1e-15
    assert after.payoffs == invalidated.payoffs == fresh.payoffs == plain_after.payoffs
    assert plain_after.payoffs['x'] == 2 * plain_before.payoffs['x']
    data['groups']['R3-01'] = {'fingerprint_unchanged': equal, 'slots': list(life.__slots__),
        'analytic_reference_before': str(analytic_before), 'analytic_reference_after': str(analytic_after),
        'before': pack_solution(before), 'after_public_mutation': pack_solution(after),
        'fresh_same_model': pack_solution(fresh), 'after_explicit_invalidate': pack_solution(invalidated),
        'plain_dataclass_after_mutation': pack_solution(plain_after),
        'accepted': True}

    # A cost-only response must not establish share-channel activity.
    base = pg.models.preannounce_entry()
    game = silence(base, FixedZero, timing_cost=base.share_rule.phi)
    st = strategy(game, 'DF')
    sub = game.numeric(POINT); sub[game.entry] = sp.Integer(0)
    shares = {k: sp.simplify(v.subs({game.entry: 0})) for k, v in game.shares(st).items()}
    share_derivatives = {k: str(sp.diff(v, base.share_rule.phi)) for k, v in shares.items()}
    gross_derivative = sp.simplify(sp.diff(game.gross_payoffs(st)['x'], base.share_rule.phi).subs(sub))
    net_derivative = sp.simplify(sp.diff(game.payoffs(st)['x'], base.share_rule.phi).subs(sub))
    confounded = verify.check(game, [verify.Competitive('DF')], over={'phi': (.8, .9)}, n=3,
                              fixed={'sigma': .1, 'hatvarsigma': .3})
    costless = silence(base, FixedZero)
    zero = verify.check(costless, [verify.Competitive('DF')], over={'phi': (.8, .9)}, n=3,
                        fixed={'sigma': .1, 'hatvarsigma': .3})
    active = silence(base, FixedTenth)
    genuine = verify.check(active, [verify.Competitive('DF')], over={'phi': (.8, .9)}, n=3,
                           fixed={'sigma': .1, 'hatvarsigma': .3})
    assert all(v == sp.Rational(1, 2) for v in shares.values())
    assert gross_derivative == 0 and net_derivative == -1
    assert confounded.results[0].failed == 3 and confounded.results[0].passed == 0 and confounded.complete
    assert zero.results[0].failed == 3 and genuine.results[0].passed == 3
    data['groups']['R3-02'] = {'shares_at_fixed_entry': {k: str(v) for k, v in shares.items()},
        'share_derivatives': share_derivatives, 'gross_phi_derivative': str(gross_derivative),
        'net_phi_derivative': str(net_derivative), 'confounded_report': pack_report(confounded),
        'costless_control': pack_report(zero), 'genuine_share_control': pack_report(genuine),
        'accepted': True}

    # One-shot claim iterables must receive exactly the same evaluations as lists.
    game = pg.models.preannounce_entry(keep_stock=True, signal_accrues=True, signal_cost=True)
    fixed = dict(sigma=.1, hatvarsigma=.3, kappa_d=.05)
    reports = {}
    for name, claims in [('list', [verify.Dominates('DF', 'DL')]),
                         ('tuple', (verify.Dominates('DF', 'DL'),)),
                         ('iterator', iter([verify.Dominates('DF', 'DL')])),
                         ('generator', (c for c in [verify.Dominates('DF', 'DL')]))]:
        reports[name] = pack_report(verify.check(game, claims, over={'phi': (.8, .9)}, n=3, fixed=fixed))
    for name in ['list', 'tuple']:
        assert reports[name]['results'][0]['failed'] == 3 and not reports[name]['ok']
    for name in ['iterator', 'generator']:
        assert not reports[name]['ok'] and reports[name]['complete']
        assert reports[name]['results'][0]['failed'] == 3
    data['groups']['R3-03'] = {'reports': reports, 'accepted': True}

    # Required checks reject invalid tolerance before evaluating the point.
    x = sp.Symbol('x', real=True)
    normal = check_point(-1, {x: 2}, {x: (0, 1)}, {}, gross=-1,
                         upper_bound=-2, kinds={x: 'lower corner'})
    assert not normal.ok and normal.complete
    rejected = {}
    for name, tol in [('nan', float('nan')), ('positive_infinity', float('inf')),
                      ('negative_infinity', -float('inf')), ('negative', -1), ('complex', 1j)]:
        try:
            check_point(-1, {x: 2}, {x: (0, 1)}, {}, gross=-1, upper_bound=-2, tol=tol)
        except ValueError as exc:
            rejected[name] = str(exc)
        else:
            raise AssertionError(name)
    data['groups']['R3-04'] = {'normal_violations': [vars(f) for f in normal.violations()],
                              'invalid_tolerances_rejected': rejected, 'accepted': True}

    # Legal finite inputs, finite resolved payoffs, overflow in the final quotient.
    base = pg.models.preannounce_entry(keep_stock=True)
    game = silence(base, FixedTenth)
    extreme = dict(sigma=1e308, phi=1e-308, hatvarsigma=.3)
    st = strategy(game, 'DF')
    sol = pg.solve(game, st, game.numeric(extreme))
    try:
        derivative(game, 'DF', 'phi', extreme, step=1e-309)
    except ValueError as exc:
        response_error = str(exc)
    else:
        raise AssertionError('overflow not rejected')
    report = verify.check(game, [verify.Sign('d pi_x / d phi', '>', strategy='DF', step=1e-309)],
                          over={'phi': [1e-308]}, fixed={'sigma': 1e308, 'hatvarsigma': .3})
    at = game.numeric(extreme); at.update(sol.point)
    exact = sp.N(sp.diff(game.payoffs(st)['x'], game.share_rule.phi).subs(at), 50)
    ordinary = derivative(game, 'DF', 'phi', POINT)
    assert sol.rankable and all(math.isfinite(v) for v in sol.payoffs.values())
    assert 'numerical range' in response_error
    assert report.results[0].passed == 0 and report.results[0].errors == 1 and not report.complete
    assert exact.is_finite is True and math.isfinite(ordinary.slope)
    data['groups']['R3-05'] = {'parameters': extreme, 'step': 1e-309, 'solution': pack_solution(sol),
        'response_error': response_error, 'analytic_derivative_50_digits': str(exact),
        'sign_report': pack_report(report), 'ordinary_control_slope': ordinary.slope,
        'accepted': True}

    data['all_accepted'] = all(c['accepted'] for c in data['groups'].values())
    Path(out).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    print(out)
    return 0

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', nargs='?', default=None)
    parser.add_argument('--out', default='audit_022_acceptance.json')
    args=parser.parse_args()
    if args.directory:
        Path(args.directory).mkdir(parents=True, exist_ok=True)
        args.out=str(Path(args.directory)/'audit_022_acceptance.json')
    raise SystemExit(main(args.out))
