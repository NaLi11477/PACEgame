"""Independent exact oracles for the eleventh audit's three public defects."""
import unittest
import sympy as sp
import pacegame as pg
from pacegame.solve.feasible import check_point
from pacegame.solve._domains import BoundsPrecisionError
from pacegame.analyze import rank_strategies, verify
from pacegame.examples._audit_0210_fixtures import POINT, U, EPS, TINY, fixture, ComplexGame

def low(payoff=0, gross=0, **kwargs):
    return check_point(payoff, {U: 0}, {U: (0, 0)}, {}, gross=gross, **kwargs)

class TestMixedEndpointGeometry(unittest.TestCase):
    def test_collapsed_mixed_nonzero_is_not_fixed(self):
        domain = (sp.Float(1.), 1+EPS)
        g = fixture(domain)
        with self.assertRaises(BoundsPrecisionError): pg.solve(g, g.strategies[0], g.numeric(POINT))
        r = check_point(-U, {U: domain[0]}, {U: domain}, {}, gross=1)
        self.assertFalse(r.complete)
        self.assertTrue(any(f.check == 'bounds precision' and f.required for f in r.findings))

    def test_two_mixed_reversed_intervals_reject(self):
        for domain in [(sp.Float(1.), 1-EPS), (sp.Float(.1), sp.Rational(1,10)+EPS)]:
            with self.subTest(domain=domain):
                # Independent oracle retains actual Float atoms before arithmetic.
                retained = lambda v: sp.Rational(v) if isinstance(v, sp.Float) else v
                self.assertLess(retained(domain[1])-retained(domain[0]), 0)
                g = fixture(domain)
                with self.assertRaises(ValueError): pg.solve(g, g.strategies[0], g.numeric(POINT))
                r = check_point(-U, {U: domain[0]}, {U: domain}, {}, gross=1)
                self.assertFalse(r.ok)
                self.assertTrue(any(f.check == 'bounds' for f in r.violations()))

    def test_normal_mixed_interval_still_ranks(self):
        g = fixture((sp.Float(1.), sp.Rational(11,10)))
        o = rank_strategies(g, POINT)
        self.assertTrue(o.complete); self.assertEqual(o.best, 'RL')
        self.assertEqual(o.solutions['RL'].kind[U], 'lower corner')

    def test_true_mixed_singleton_is_fixed(self):
        g = fixture((sp.Float(1.), sp.Integer(1)))
        s = pg.solve(g, g.strategies[0], g.numeric(POINT))
        self.assertTrue(s.rankable); self.assertEqual(s.kind[U], 'fixed')

    def test_exact_collapsed_control_still_rejects(self):
        g = fixture((sp.Integer(1), 1+EPS))
        with self.assertRaises(BoundsPrecisionError): pg.solve(g, g.strategies[0], g.numeric(POINT))

    def test_representable_narrow_mixed_control_passes(self):
        g = fixture((sp.Float(1.), 1+sp.Rational(1,2**40)))
        s = pg.solve(g, g.strategies[0], g.numeric(POINT))
        self.assertTrue(s.rankable); self.assertEqual(s.kind[U], 'lower corner')

    def test_float_parameter_substitution_preserves_width(self):
        q = sp.Symbol('endpoint_parameter', real=True)
        r = check_point(0, {U:q}, {U:(q,q+EPS)}, {q:sp.Float(1.)}, gross=0)
        self.assertFalse(r.complete)
        self.assertTrue(any(f.check == 'bounds precision' for f in r.findings))

    def test_invalid_intervals_never_pass_rank_or_claims(self):
        for domain in [(sp.Float(1.),1+EPS),(sp.Float(1.),1-EPS),(sp.Float(.1),sp.Rational(1,10)+EPS)]:
            g = fixture(domain)
            with self.assertRaises(ValueError): rank_strategies(g, POINT)
            r = verify.check(g,[verify.Feasible(),verify.Bounded('RL')],over={},fixed=POINT)
            self.assertFalse(r.complete)
            self.assertTrue(all(x.passed==0 and x.errors==1 for x in r.results))

class TestToleranceAdmission(unittest.TestCase):
    def test_negative_underflow_rejects_before_conversion(self):
        for value in [-TINY, sp.Float('-1e-400')]:
            with self.subTest(value=value), self.assertRaisesRegex(ValueError,'finite nonnegative'):
                low(tol=value)

    def test_positive_underflow_has_explicit_range_error(self):
        for value in [TINY,sp.Float('1e-400')]:
            with self.subTest(value=value), self.assertRaisesRegex(ValueError,'binary64 range'):
                low(TINY/2,TINY/2,upper_bound=0,tol=value)

    def test_overflow_has_explicit_range_error(self):
        with self.assertRaisesRegex(ValueError,'binary64 range'): low(tol=sp.Integer(10)**400)

    def test_nonreal_nonfinite_and_unresolved_reject(self):
        for value in [-sp.Rational(1,10**12),sp.I*TINY,sp.nan,sp.oo,-sp.oo,sp.Symbol('tol',positive=True)]:
            with self.subTest(value=value), self.assertRaisesRegex(ValueError,'tol must'):
                low(tol=value)

    def test_zero_and_normal_inside_outside_controls(self):
        self.assertTrue(low(tol=0).ok)
        t=sp.Rational(1,10**9)
        self.assertTrue(low(t/2,t/2,upper_bound=0,tol=t).ok)
        self.assertFalse(low(2*t,2*t,upper_bound=0,tol=t).ok)

    def test_original_rational_ceiling_tolerance_is_preserved(self):
        t=sp.Rational(1,10)
        self.assertTrue(low(t,t,upper_bound=0,tol=t).ok)
        self.assertFalse(low(t+EPS,t+EPS,upper_bound=0,tol=t).ok)

    def test_original_rational_gross_tolerance_is_preserved(self):
        t=sp.Rational(1,10)
        self.assertTrue(low(-1,-t,tol=t).ok)
        r=low(-1,-t-EPS,tol=t)
        self.assertTrue(any(f.check=='payoff sign' for f in r.violations()))

class TestPayoffAdmission(unittest.TestCase):
    def test_small_and_underflow_nonreal_net_reject_with_or_without_ceiling(self):
        for imag in [TINY,sp.Rational(1,10**10),sp.Rational(1,10**6)]:
            for ceiling in [None,2]:
                r=low(1+sp.I*imag,1,upper_bound=ceiling)
                self.assertFalse(r.ok)
                self.assertTrue(any(f.check=='payoff' for f in r.violations()))

    def test_small_and_underflow_nonreal_gross_reject_with_or_without_ceiling(self):
        for imag in [TINY,sp.Rational(1,10**10)]:
            for ceiling in [None,2]:
                r=low(1,1+sp.I*imag,upper_bound=ceiling)
                self.assertFalse(r.ok)
                self.assertTrue(any(f.check=='payoff sign' for f in r.violations()))

    def test_nonreal_realised_payoff_is_not_silently_projected(self):
        r=low(1,1,realised={'x':1+sp.I*TINY})
        self.assertFalse(r.ok)
        self.assertTrue(any(f.check=='payoff finite' for f in r.violations()))

    def test_unresolved_net_admission_is_required_unavailable(self):
        r=low(sp.Symbol('unresolved_payoff',real=True),1)
        self.assertFalse(r.complete)
        self.assertTrue(any(f.check=='payoff' and f.required and f.status=='warning' for f in r.findings))

    def test_unresolved_gross_admission_is_required_unavailable(self):
        r=low(1,sp.Symbol('unresolved_gross',real=True))
        self.assertFalse(r.complete)

    def test_nonfinite_net_and_gross_reject(self):
        for value in [sp.nan,sp.zoo,sp.oo,-sp.oo]:
            self.assertFalse(low(value,1).ok)
            self.assertFalse(low(1,value).ok)

    def test_negative_net_with_omitted_gross_is_legal(self):
        r=low(-1,None)
        self.assertTrue(r.ok and r.complete)
        self.assertTrue(any(f.check=='payoff sign' and not f.required for f in r.findings))

    def test_negative_net_with_positive_gross_is_legal(self):
        r=low(-1,1)
        self.assertTrue(r.ok and r.complete)

    def test_real_numeric_controls_pass(self):
        for value in [sp.Integer(1),sp.Rational(1,10),sp.Float(.1)]:
            r=low(value,value,upper_bound=2)
            self.assertTrue(r.ok and r.complete)

    def test_admission_occurs_after_retained_substitution(self):
        q=sp.Symbol('payoff_parameter',real=True)
        r=check_point(q,{U:0},{U:(0,0)},{q:1+sp.I*TINY},gross=1)
        self.assertFalse(r.ok)

    def test_main_solver_nonreal_guard_stays_effective(self):
        g=fixture((0,0),ComplexGame)
        s=pg.solve(g,g.strategies[0],g.numeric(POINT))
        self.assertFalse(s.rankable)

if __name__=='__main__': unittest.main()
