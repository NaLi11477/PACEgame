"""Tenth-audit numeric guards through low-level and public interfaces."""
import unittest
from dataclasses import replace
import sympy as sp
import pacegame as pg
from pacegame.solve.feasible import check_point
from pacegame.analyze import rank_strategies, verify
from pacegame.examples._audit_029_fixtures import POINT, NEGATIVE, injection

U = sp.Symbol('audit_r10_test_u', real=True)

def ceiling(amount, limit, **kw):
    return check_point(sp.sympify(amount), {U: 0}, {U: (0, 0)}, {},
                       gross=sp.Abs(amount), upper_bound=limit, **kw)

def silent(g):
    return next(s for s in g.strategies if s.name == 'DF')

class TestRetainedCeiling(unittest.TestCase):
    def test_three_original_over_ceiling_outputs_fail(self):
        for A, delta in ((2**53, 1), (2**60, 128), (10**20, 4096)):
            with self.subTest(A=A):
                r = ceiling(sp.Integer(A)+delta, sp.Integer(A))
                self.assertFalse(r.ok)
                self.assertTrue(r.complete)
                self.assertTrue(any(f.check=='payoff magnitude' for f in r.violations()))

    def test_visible_large_excess_controls_still_fail(self):
        for A, delta in ((2**40, 1), (2**60, 256)):
            self.assertFalse(ceiling(sp.Integer(A)+delta, sp.Integer(A)).ok)

    def test_equal_and_below_ceiling_controls_pass(self):
        for delta in (0, -256):
            r = ceiling(sp.Integer(2**60)+delta, sp.Integer(2**60))
            self.assertTrue(r.ok and r.complete)

    def test_absolute_tolerance_is_preserved_at_large_scale(self):
        A = sp.Integer(2**60)
        t = sp.Rational(1e-9)
        for factor, good in ((sp.Rational(1,2), True), (1, True), (2, False)):
            self.assertEqual(ceiling(A+t*factor, A).ok, good)

    def test_negative_ceiling_uses_retained_difference(self):
        self.assertFalse(ceiling(-sp.Integer(2**60)+128, -sp.Integer(2**60)).ok)

    def test_symbolic_ceiling_is_required_unavailable(self):
        r = ceiling(1, sp.Symbol('missing', real=True))
        self.assertFalse(r.complete)
        self.assertTrue(any(f.check=='payoff magnitude' and f.required and f.status=='warning' for f in r.findings))

    def test_nonreal_and_nonfinite_ceilings_are_unavailable(self):
        for x in (sp.I*sp.Rational(1,10**400), sp.nan, -sp.oo):
            with self.subTest(x=x):
                self.assertFalse(ceiling(1,x).complete)

    def test_explicit_positive_infinity_stays_uninformative(self):
        r = ceiling(1, sp.oo)
        self.assertTrue(r.ok and r.complete)
        self.assertTrue(any(f.check=='payoff magnitude' and f.status=='warning' and not f.required for f in r.findings))

    def test_public_rank_and_claims_exclude_original_counterexamples(self):
        for A, delta in ((2**53,1),(2**60,128),(10**20,4096)):
            with self.subTest(A=A):
                g = injection(sp.Integer(A)+delta, sp.Integer(A))
                o = rank_strategies(g, POINT)
                self.assertIsNone(o.best)
                self.assertFalse(o.complete)
                self.assertEqual(o.excluded, ['RL'])
                r = verify.check(g,[verify.Feasible(),verify.Bounded('RL')],over={},n=1,fixed=POINT)
                self.assertEqual(r.results[0].failed,1)
                self.assertEqual(r.results[1].skipped,1)
                self.assertTrue(all(x.passed==0 and x.errors==0 for x in r.results))

    def test_public_equal_and_below_controls_pass(self):
        for delta in (0,-256):
            g = injection(sp.Integer(2**60)+delta,sp.Integer(2**60))
            self.assertEqual(rank_strategies(g,POINT).best,'RL')
            r = verify.check(g,[verify.Feasible(),verify.Bounded('RL')],over={},fixed=POINT)
            self.assertTrue(all(x.passed==1 and x.errors==0 for x in r.results))

    def test_bounded_uses_retained_payoff_with_its_existing_stricter_tolerance(self):
        A = sp.Integer(10**6)
        g = injection(A+sp.Rational(1,10**11),A)
        self.assertTrue(rank_strategies(g,POINT).complete)
        r = verify.check(g,[verify.Feasible(),verify.Bounded('RL')],over={},fixed=POINT)
        self.assertEqual(r.results[0].passed,1)
        self.assertEqual(r.results[1].failed,1)
        self.assertEqual(r.results[1].errors,0)

class TestStrictInputSigns(unittest.TestCase):
    def test_both_original_negative_parameters_are_rejected(self):
        for field, name in (('signal_cost','kappa_d'),('timing_cost','kappa_t')):
            with self.subTest(field=field):
                g = pg.models.preannounce_entry(**{field:True})
                with self.assertRaisesRegex(ValueError,'nonnegative'):
                    g.numeric(dict(POINT,**{name:NEGATIVE}))

    def test_direct_solve_rejects_both_negative_parameters(self):
        for field, name in (('signal_cost','kappa_d'),('timing_cost','kappa_t')):
            g = pg.models.preannounce_entry(**{field:True})
            params = {sym:(NEGATIVE if n==name else sp.Float(POINT[n])) for n,sym in g.parameters().items()}
            with self.assertRaisesRegex(ValueError,'nonnegative'):
                pg.solve(g,silent(g),params)

    def test_three_original_public_mutations_reject_on_numeric_boundary(self):
        for field in ('signal_cost','timing_cost','phi_coefficient'):
            g = pg.models.preannounce_entry()
            if field=='phi_coefficient':g.share_rule.phi=NEGATIVE
            else:setattr(g,field,NEGATIVE)
            with self.assertRaisesRegex(ValueError,'nonnegative'):
                g.numeric(POINT)

    def test_public_mutations_reject_on_direct_solve_boundary(self):
        for field in ('signal_cost','timing_cost','phi_coefficient'):
            g = pg.models.preannounce_entry()
            params = g.numeric(POINT)
            if field=='phi_coefficient':g.share_rule.phi=NEGATIVE
            else:setattr(g,field,NEGATIVE)
            with self.assertRaisesRegex(ValueError,'nonnegative'):
                pg.solve(g,silent(g),params)

    def test_zero_and_ordinary_positive_costs_remain_valid(self):
        for field,name in (('signal_cost','kappa_d'),('timing_cost','kappa_t')):
            for value in (sp.Integer(0),sp.Rational(1,10**6)):
                g = pg.models.preannounce_entry(**{field:True})
                p = dict(POINT,**{name:value})
                self.assertTrue(rank_strategies(g,p,[silent(g)]).complete)

    def test_ordinary_negative_costs_continue_to_reject(self):
        for field,name in (('signal_cost','kappa_d'),('timing_cost','kappa_t')):
            g = pg.models.preannounce_entry(**{field:True})
            with self.assertRaisesRegex(ValueError,'nonnegative'):
                g.numeric(dict(POINT,**{name:-sp.Rational(1,10**6)}))

    def test_positive_underflow_parameters_have_explicit_range_error(self):
        for field,name in (('signal_cost','kappa_d'),('timing_cost','kappa_t')):
            g = pg.models.preannounce_entry(**{field:True})
            with self.assertRaisesRegex(ValueError,'binary64 range'):
                g.numeric(dict(POINT,**{name:-NEGATIVE}))

    def test_positive_underflow_constant_coefficients_have_range_error(self):
        g = pg.models.preannounce_entry()
        g.signal_cost = -NEGATIVE
        with self.assertRaisesRegex(ValueError,'binary64 range'):
            g.numeric(POINT)

    def test_nonfinite_and_complex_parameters_are_rejected(self):
        for x in (sp.nan,sp.oo,-sp.oo,sp.I*sp.Rational(1,10**400)):
            g = pg.models.preannounce_entry(signal_cost=True)
            with self.assertRaisesRegex(ValueError,'finite real'):
                g.numeric(dict(POINT,kappa_d=x))

    def test_nonfinite_and_complex_constant_costs_are_rejected(self):
        for x in (sp.nan,sp.oo,-sp.oo,sp.I*sp.Rational(1,10**400)):
            g = pg.models.preannounce_entry()
            g.signal_cost = x
            with self.assertRaisesRegex(ValueError,'finite real'):
                g.numeric(POINT)

    def test_positive_symbol_zero_and_negative_are_rejected(self):
        for value in (0,NEGATIVE):
            with self.assertRaisesRegex(ValueError,'positive'):
                pg.models.preannounce_entry().numeric(dict(POINT,phi=value))

    def test_underflow_cannot_hide_negative_cost_expression(self):
        q = sp.Symbol('audit_cost_factor',real=True)
        g = pg.models.preannounce_entry()
        g.signal_cost = q-1
        with self.assertRaisesRegex(ValueError,'signal_cost must be nonnegative'):
            g.numeric(dict(POINT,audit_cost_factor=1+NEGATIVE))

    def test_legal_small_positive_expression_that_underflows_is_rejected(self):
        q = sp.Symbol('audit_cost_factor',real=True)
        g = pg.models.preannounce_entry()
        g.signal_cost = q-1
        with self.assertRaisesRegex(ValueError,'signal_cost is outside the supported binary64 range'):
            g.numeric(dict(POINT,audit_cost_factor=1-NEGATIVE))

    def test_numeric_preserves_supplied_rational_before_substitution(self):
        g = pg.models.preannounce_entry()
        value = sp.Rational(17,20)
        self.assertEqual(g.numeric(dict(POINT,phi=value))[g.parameters()['phi']],value)

if __name__=='__main__':
    unittest.main()
