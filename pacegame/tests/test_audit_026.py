"""Independent exact membership and feasible-direction regression controls."""
import unittest,io
from unittest.mock import patch
import sympy as sp
import pacegame as pg
from pacegame.solve.feasible import check_point
from pacegame.analyze import rank_strategies,verify
from pacegame.examples._audit_026_fixtures import (
    A,U,V,POINT,NetFixture,FixedNeighbor,fixture,solve_fixture,offset_model)

class CandidatePrecision(unittest.TestCase):
    def low(self,value,domain=None,tol=1e-9):
        return check_point(A-U,{U:value},{U:domain or (A+1,A+32769)},{},gross=1,tol=tol)
    def test_exact_lower_outside(self):
        r=self.low(A);self.assertFalse(r.ok);self.assertFalse(r.complete)
    def test_exact_upper_outside(self):
        r=self.low(A+32770);self.assertFalse(r.ok);self.assertFalse(r.complete)
    def test_binary_candidate_outside(self):
        self.assertFalse(self.low(sp.Float(A)).ok)
    def test_high_precision_candidate_outside(self):
        self.assertFalse(self.low(sp.Float(A,80)).ok)
    def test_unrepresentable_singleton_solver(self):
        with self.assertRaises(pg.BoundsPrecisionError):solve_fixture(offset_model((A+1,A+1)))
    def test_noncollapsed_domain_solver(self):
        self.assertNotEqual(float(A+1),float(A+32769))
        with self.assertRaises(pg.BoundsPrecisionError):solve_fixture(offset_model())
    def test_low_exact_legal_but_unavailable_coordinates(self):
        r=self.low(A+1);self.assertTrue(r.ok);self.assertFalse(r.complete)
    def test_low_unrepresentable_singleton(self):
        r=self.low(A,(A+1,A+1));self.assertFalse(r.ok);self.assertFalse(r.complete)
    def test_ranking_rejected(self):
        with self.assertRaises(pg.BoundsPrecisionError):rank_strategies(offset_model(),POINT)
    def test_dependent_claim_error(self):
        r=verify.check(offset_model(),[verify.Feasible()],over={},fixed=POINT)
        self.assertEqual(r.results[0].errors,1);self.assertFalse(r.ok)
    def test_shifted_equivalent_negative_net(self):
        g=fixture(NetFixture);g.objective=-U;g.domain=(1,32769);s=solve_fixture(g)
        self.assertTrue(s.rankable);self.assertEqual(sp.Rational(s.point[U]),1)
        self.assertEqual(s.payoffs['x'],-1)
    def test_representable_large_interval(self):
        s=solve_fixture(offset_model((A,A+32768)));self.assertTrue(s.rankable)
        self.assertEqual(sp.Rational(s.point[U]),A);self.assertEqual(s.payoffs['x'],0)
    def test_representable_large_singleton(self):
        s=solve_fixture(offset_model((A,A)));self.assertTrue(s.rankable)
        self.assertEqual(s.kind[U],'fixed');self.assertEqual(s.payoffs['x'],0)
    def test_payoff_cancellation_cannot_silently_agree(self):
        g=offset_model((A,A+32768));g.objective=A+1-U;s=solve_fixture(g)
        self.assertFalse(s.rankable)
        self.assertTrue(any(f.check=='evaluation' and f.status=='violation' for f in s.feasibility.findings))
    def test_rational_tenth_singleton(self):
        g=fixture(NetFixture);g.domain=(sp.Rational(1,10),)*2;g.objective=-U
        s=solve_fixture(g);self.assertTrue(s.rankable);self.assertAlmostEqual(s.payoffs['x'],-.1)
    def test_parameter_offset_not_rounded_before_guard(self):
        b=sp.Symbol('b',real=True)
        r=check_point(0,{U:A},{U:(b+1,b+32769)},{b:sp.Float(A)},gross=1)
        self.assertFalse(r.ok);self.assertFalse(r.complete)
    def test_exact_tolerance_threshold(self):
        delta=sp.Rational(1,10**9)
        at=check_point(0,{U:-delta},{U:(0,1)},{},gross=0,tol=sp.Rational(1,10**9))
        beyond=check_point(0,{U:-2*delta},{U:(0,1)},{},gross=0,tol=sp.Rational(1,10**9))
        self.assertTrue(at.ok);self.assertFalse(beyond.ok)
    def test_collapsed_r6_control(self):
        with self.assertRaises(pg.BoundsPrecisionError):solve_fixture(offset_model((A,A+1)))
    def test_cli_precision_exit(self):
        from pacegame.cli import main
        with patch.dict(pg.models.REGISTRY,{'preannounce_entry':lambda **kwargs:offset_model()}),patch('sys.stderr',new_callable=io.StringIO) as err:
            code=main(['solve','preannounce_entry'])
        self.assertEqual(code,1);self.assertIn('bounds precision unavailable',err.getvalue())

class ScalarBoundaryCurvature(unittest.TestCase):
    def low(self,f,point=None,bounds=None):
        return check_point(f,point or {U:0,V:0},bounds or {U:(0,1),V:(0,0)},{},gross=1)
    def test_fixed_neighbor_positive_curvature(self):
        r=self.low(U**2-10**8*U**4-V**2);self.assertFalse(r.ok)
        self.assertTrue(any(f.check=='joint curvature' and f.status=='violation' for f in r.findings))
    def test_single_scalar_positive_curvature(self):
        self.assertFalse(self.low(U**2,point={U:0},bounds={U:(0,1)}).ok)
    def test_concave_lower_passes(self):
        r=self.low(-U**2-V**2);self.assertTrue(r.ok and r.complete)
    def test_concave_upper_passes(self):
        r=self.low(-(U-1)**2-V**2,{U:1,V:0});self.assertTrue(r.ok and r.complete)
    def test_strict_inward_gradient_removes_direction(self):
        r=self.low(-U+100*U**2-V**2);self.assertTrue(r.ok and r.complete)
    def test_flat_higher_order_scope(self):
        r=self.low(U**4-V**2);self.assertTrue(any(f.check=='joint curvature scope' and f.status=='warning' for f in r.findings))
    def test_fixed_only_has_no_direction(self):
        r=self.low(U**2-V**2,bounds={U:(0,0),V:(0,0)});self.assertTrue(r.ok and r.complete)
        self.assertFalse(any(f.check=='joint curvature' for f in r.findings))
    def test_solver_positive_interior_control(self):
        g=fixture(FixedNeighbor);g.objective=U**2-10**8*U**4-V**2
        s=solve_fixture(g);self.assertTrue(s.rankable)
        self.assertAlmostEqual(float(s.point[U]),float(1/sp.sqrt(2*10**8)),places=10)
        self.assertAlmostEqual(s.payoffs['x'],2.5e-9,places=15)

if __name__=='__main__':unittest.main()
