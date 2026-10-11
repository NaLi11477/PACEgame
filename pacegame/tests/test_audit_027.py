"""Analytic regressions for parameter, candidate and derivative retention."""
import importlib
import unittest
from unittest.mock import patch
import sympy as sp
import pacegame as pg
from pacegame.analyze import rank_strategies, verify
from pacegame.solve.engine import _Evaluator
from pacegame.solve.feasible import check_point
from pacegame.examples._audit_027_fixtures import SCALES, NAMES, POINT, fixture, parameter_case


class RetainedValues(unittest.TestCase):
    pass


def add(name, function):
    setattr(RetainedValues, 'test_'+name, function)


for index, A in enumerate(SCALES):
    for name in NAMES:
        for power in (1, 2):
            for integer in (False, True):
                def test(self, A=A, name=name, power=power, integer=integer):
                    game, params = parameter_case(A, power, name, integer)
                    solution = pg.solve(game, game.strategies[0], params)
                    self.assertEqual(sp.Rational(solution.point[game.entry]), 1)
                    self.assertEqual(solution.payoffs[game.focal], 1)
                    self.assertTrue(solution.rankable)
                    low = check_point(game.objective, {game.entry: 0},
                                      {game.entry: (0, 1)}, params, gross=1)
                    self.assertFalse(low.ok)
                    expected = 'first order' if power == 1 else 'joint curvature'
                    self.assertTrue(any(f.check == expected and f.status == 'violation' for f in low.findings))
                    ranking = rank_strategies(game, {**POINT, 'sigma': float(A)})
                    self.assertEqual(ranking.payoffs['DF'], 1)
                    claim = verify.check(game, [verify.Feasible()], over={},
                                         fixed={**POINT, 'sigma': float(A)})
                    self.assertTrue(claim.ok and claim.complete)
                    self.assertEqual((claim.results[0].passed, claim.results[0].failed,
                                      claim.results[0].skipped, claim.results[0].errors), (1, 0, 0, 0))
                add(f'objective_{index}_{name}_{power}_{integer}', test)
        def candidate(self, A=A, name=name):
            u = sp.Symbol(name, real=True); offset = sp.Symbol('audit_offset', real=True)
            params = {offset: float(A)}
            expression = check_point(-u**2, {u: offset-A+1}, {u: (0, 1)}, params, gross=1)
            literal = check_point(-u**2, {u: 1}, {u: (0, 1)}, params, gross=1)
            self.assertFalse(expression.ok); self.assertEqual(expression.ok, literal.ok)
            self.assertTrue(any(f.check == 'first order' and '-2' in f.detail and f.status == 'violation'
                                for f in expression.findings))
            self.assertEqual([(f.check, f.status, f.detail) for f in expression.findings],
                             [(f.check, f.status, f.detail) for f in literal.findings])
        add(f'candidate_{index}_{name}', candidate)
        def interior(self, A=A, name=name):
            u = sp.Symbol(name, real=True); sigma = sp.Symbol('sigma', real=True)
            result = check_point((sigma-A+1)*u, {u: sp.Rational(1,2)},
                                 {u: (0,1)}, {sigma: float(A)}, gross=1)
            self.assertFalse(result.ok)
            self.assertTrue(any(f.check == 'stationarity' and f.status == 'violation'
                                and '1.0' in f.detail for f in result.findings))
        add(f'interior_gradient_{index}_{name}', interior)
        def polishing(self, A=A, name=name):
            game, params = parameter_case(A, 1, name)
            sigma = game.parameters()['sigma']; u = game.entry
            game.objective = (sigma-A+1)*(1-(u-sp.Rational(1,3))**2)
            solution = pg.solve(game, game.strategies[0], params)
            self.assertTrue(solution.rankable)
            self.assertAlmostEqual(float(solution.point[u]), 1/3, places=12)
            self.assertAlmostEqual(solution.payoffs[game.focal], 1, places=12)
        add(f'local_polishing_{index}_{name}', polishing)
    for mixed in (False, True):
        def hessian(self, A=A, mixed=mixed):
            u,v,sigma=sp.symbols('audit_u audit_v sigma', real=True)
            target = (sigma-A+1)*(u**2-v**2)
            bounds = {u:(0,1), v:(-1,1) if mixed else (0,1)}
            result = check_point(target, {u:0,v:0}, bounds, {sigma:float(A)}, gross=1)
            self.assertFalse(result.ok)
            self.assertTrue(any(f.check == 'joint curvature' and f.status == 'violation' for f in result.findings))
        add(f'critical_hessian_{index}_{mixed}', hessian)
    def fallback(self, A=A):
        u=sp.Symbol('audit_u',real=True)
        evaluator=_Evaluator(A+1-u,[u])
        value=evaluator._fn(2)(float(A))
        self.assertEqual(value,1)
    add(f'exact_fallback_{index}',fallback)


def binary_tenth(self):
    u=sp.Symbol('audit_u',real=True); c=sp.Symbol('sigma',real=True)
    value=sp.Float(.1); target=-(u-c)**2
    result=check_point(target,{u:value},{u:(0,1)},{c:value},gross=1)
    self.assertTrue(result.ok and result.complete)
    self.assertNotEqual(sp.Rational(value),sp.Rational(1,10))
add('actual_binary_tenth',binary_tenth)


def unknown(self):
    u,b=sp.symbols('audit_u missing',real=True)
    result=check_point(b*u,{u:0},{u:(0,1)},{},gross=1)
    self.assertFalse(result.complete)
    self.assertTrue(any(f.required and f.status=='warning' for f in result.findings))
add('unavailable_derivative_incomplete',unknown)


def validation(self):
    game=pg.models.preannounce_entry(); c=game.parameters()['sigma']; A=SCALES[0]
    game.signal_cost=c-A+1
    params=game.numeric({**POINT,'sigma':float(A)})
    self.assertEqual(sp.Rational(params[c]),A)
    game.validate(params)
add('model_coefficient_validation',validation)


def incomplete_symbolic(self):
    game,params=parameter_case(SCALES[0],1)
    from pacegame.core.numeric import exact_numeric
    original=exact_numeric
    def missing(expr,subs=None):
        if subs and game.entry in subs and sp.sympify(expr)==game.objective:
            raise ValueError('unavailable independent payoff route')
        return original(expr,subs)
    engine=importlib.import_module('pacegame.solve.engine')
    with patch.object(engine,'exact_numeric',side_effect=missing):
        solution=pg.solve(game,game.strategies[0],params)
    self.assertFalse(solution.rankable)
    self.assertFalse(solution.feasibility.complete)
    self.assertTrue(any(f.check=='evaluation' and f.required and f.status=='warning'
                        for f in solution.feasibility.findings))
add('unavailable_payoff_comparison_incomplete',incomplete_symbolic)


if __name__=='__main__': unittest.main()
