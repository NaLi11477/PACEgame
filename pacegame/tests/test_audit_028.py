"""Analytic curvature counterexamples, owner/stage/domain scope controls."""
import unittest
from unittest.mock import patch
import sympy as sp
import pacegame as pg
from pacegame.solve.feasible import check_point
from pacegame.analyze import rank_strategies,verify
from pacegame.examples._audit_028_fixtures import POINT,SCALES,NAMES,fixture,expressions

U,V,W=sp.symbols('audit_u audit_v audit_w',real=True)
def low(f, point=None, bounds=None, **kwargs):
    return check_point(f,point if point is not None else {U:0,V:0},
                       bounds if bounds is not None else {U:(0,1),V:(0,1)}, {},gross=3,**kwargs)
def joint_fail(r):
    return any(f.check=='joint curvature' and f.status=='violation' for f in r.findings)

class RetainedBoundary(unittest.TestCase): pass

def boundary_case(A,name):
    def test(self):
        game=fixture(name);u,v=game.entry,game.signal;f=expressions(game,A)[1]
        self.assertEqual(sp.hessian(f,[u,v]).eigenvals(),{sp.Integer(2):1,-4*sp.Integer(A)-2:1})
        self.assertEqual(f.subs({u:sp.Rational(1,10),v:sp.Rational(1,10)}),sp.Rational(1,50))
        r=check_point(f,{u:0,v:0},{u:(0,1),v:(0,1)},{},gross=3)
        self.assertFalse(r.ok);self.assertTrue(r.complete);self.assertTrue(joint_fail(r))
    return test

def solver_case(A,name):
    def test(self):
        game=fixture(name);params=game.numeric(POINT)
        for f in expressions(game,A):
            game.objective=f;s=pg.solve(game,game.strategies[0],params)
            if s.rankable:
                self.assertEqual(s.payoffs[game.focal],2)
                self.assertEqual([sp.Rational(s.point[v]) for v in (game.entry,game.signal)],[1,1])
            else:
                self.assertFalse(s.feasibility.ok and s.feasibility.complete)
        game.objective=expressions(game,A)[0]
        self.assertTrue(pg.solve(game,game.strategies[0],params).rankable)
    return test
for A in SCALES:
    for name in NAMES:
        setattr(RetainedBoundary,f'test_wrong_origin_{A}_{name}',boundary_case(A,name))
        setattr(RetainedBoundary,f'test_solve_correct_or_excluded_{A}_{name}',solver_case(A,name))

class JointScope(unittest.TestCase):
    def test_precision_beyond_fixed_80_digits(self):
        r=low(sp.expand(-10**120*(U-V)**2+2*U*V));self.assertFalse(r.ok);self.assertTrue(joint_fail(r))
    def test_huge_concave_boundary(self):
        r=low(-10**120*(U+V)**2-2*U*V);self.assertTrue(r.ok and r.complete)
    def test_positive_cross_below_envelope(self):
        self.assertTrue(low(-U**2-V**2+U*V).ok)
    def test_negative_cross_positive_eigenvalue_outside_cone(self):
        r=low(-U**2-V**2-3*U*V);self.assertTrue(r.ok and r.complete)
    def test_upper_lower_orientation(self):
        a,b=1-U,V;r=low(-a*a-b*b+3*a*b,{U:1,V:0});self.assertTrue(joint_fail(r))
    def test_upper_upper_orientation(self):
        a,b=1-U,1-V;r=low(-a*a-b*b+3*a*b,{U:1,V:1});self.assertTrue(joint_fail(r))
    def test_mixed_huge_retained_spectrum(self):
        r=low(sp.expand(-2**60*(U-V)**2+2*U*V),bounds={U:(0,1),V:(-1,1)})
        self.assertTrue(joint_fail(r));self.assertTrue(r.complete)
    def test_interior_automatic_saddle(self):
        a,b=U-sp.Rational(1,2),V-sp.Rational(1,2)
        r=low(-a*a-b*b+3*a*b,{U:sp.Rational(1,2),V:sp.Rational(1,2)})
        self.assertFalse(r.ok);self.assertTrue(joint_fail(r) and r.complete)
    def test_interior_explicit_saddle(self):
        f=-U**2-V**2+3*U*V;r=low(f,bounds={U:(-1,1),V:(-1,1)},
             kinds={U:'interior',V:'interior'},payoff_for={U:f,V:f})
        self.assertTrue(joint_fail(r) and r.complete)
    def test_interior_huge_retained_spectrum(self):
        r=low(sp.expand(-10**120*(U-V)**2+2*U*V),bounds={U:(-1,1),V:(-1,1)})
        self.assertTrue(joint_fail(r) and r.complete)
    def test_interior_concave(self):
        r=low(-U**2-V**2,bounds={U:(-1,1),V:(-1,1)})
        self.assertTrue(r.ok and r.complete);self.assertTrue(any(f.check=='joint curvature' for f in r.findings))
    def test_interior_three_dimensions(self):
        r=low(-U**2-V**2-W**2+3*U*V,{U:0,V:0,W:0},{U:(-1,1),V:(-1,1),W:(-1,1)})
        self.assertTrue(joint_fail(r) and r.complete)
    def test_distinct_objectives_not_combined(self):
        r=low(-U**2-V**2+3*U*V,bounds={U:(-1,1),V:(-1,1)},payoff_for={U:-U**2+3*U*V,V:-V**2})
        self.assertTrue(r.ok and r.complete);self.assertFalse(any(f.check=='joint curvature' for f in r.findings))
    def test_skipped_earlier_stage(self):
        r=low(-U**2-V**2+3*U*V,bounds={U:(-1,1),V:(-1,1)},skip_optimality={U})
        self.assertTrue(r.ok and r.complete);self.assertFalse(joint_fail(r))
    def test_fixed_coordinate_excluded(self):
        r=low(-U**2-V**2+3*U*V,bounds={U:(0,0),V:(-1,1)})
        self.assertTrue(r.ok and r.complete)
    def test_unavailable_joint_hessian_blocks_completion(self):
        with patch('pacegame.solve.feasible.sp.hessian',side_effect=ValueError('unavailable')):
            r=low(-U**2-V**2,bounds={U:(-1,1),V:(-1,1)})
        self.assertFalse(r.complete);self.assertTrue(any(f.check=='joint curvature' and f.required and f.status=='warning' for f in r.findings))
    def test_rank_and_feasible_do_not_accept_wrong_origin(self):
        g=fixture();g.objective=expressions(g,2**60)[1]
        ranking=rank_strategies(g,POINT);claim=verify.check(g,[verify.Feasible()],over={},fixed=POINT)
        self.assertTrue(not ranking.complete or ranking.payoffs.get('RL')==2)
        if ranking.payoffs.get('RL')!=2:self.assertEqual(claim.results[0].passed,0)
    def test_main_interior_control_still_rankable(self):
        g=fixture();u,v=g.entry,g.signal;a,b=u-sp.Rational(1,2),v-sp.Rational(1,2);g.objective=-a*a-b*b+3*a*b
        s=pg.solve(g,g.strategies[0],g.numeric(POINT));self.assertTrue(s.rankable);self.assertEqual(s.payoffs[g.focal],.25)

if __name__=='__main__':unittest.main()
