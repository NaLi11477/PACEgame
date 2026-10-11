"""Regression controls for all five sixth-audit findings; old tests retained."""
from dataclasses import replace
from contextlib import redirect_stderr,redirect_stdout
import io,json,unittest
from pathlib import Path
from unittest.mock import patch
import sympy as sp
import pacegame as pg
from pacegame.analyze import rank_strategies,verify
from pacegame.solve.feasible import check_point
from pacegame.examples._audit_025_fixtures import A,U,V,W,POINT,fixture,silent,FixedTenth,JointFixture,solve_fixture

class ExactDomainTests(unittest.TestCase):
    def check(self,kind):
        kwargs={} if kind is None else {'kinds':{U:kind}}
        return check_point(U-A,{U:A},{U:(A,A+1)},{},gross=U-A,**kwargs)
    def test_collapsed_domain_is_not_fixed(self):
        r=self.check('fixed');self.assertFalse(r.complete)
        self.assertTrue(any(f.check=='bounds precision' and f.required for f in r.findings))
        self.assertFalse(any(f.check=='fixed variable' for f in r.findings))
    def test_collapsed_domain_lower_label_incomplete(self):self.assertFalse(self.check('lower corner').complete)
    def test_collapsed_domain_inferred_label_incomplete(self):self.assertFalse(self.check(None).complete)
    def test_solver_raises_typed_precision_error(self):
        g=fixture();g.domain=(A,A+1);g.objective=U-A
        with self.assertRaises(pg.BoundsPrecisionError):solve_fixture(g)
    def test_ranking_cannot_return_precision_invalid_candidate(self):
        g=fixture();g.domain=(A,A+1);g.objective=U-A
        with self.assertRaises(pg.BoundsPrecisionError):rank_strategies(g,POINT)
    def test_precision_failure_cannot_establish_claim(self):
        g=fixture();g.domain=(A,A+1);g.objective=U-A
        r=verify.check(g,[verify.Feasible()],over={},fixed=POINT)
        self.assertEqual(r.results[0].errors,1);self.assertFalse(r.ok)
    def test_reversed_exact_interval_detected_before_float(self):
        r=check_point(U-A,{U:A},{U:(A+1,A)},{},gross=U-A)
        self.assertFalse(r.ok);self.assertTrue(any('lower bound exceeds' in f.detail for f in r.findings))
    def test_reversed_exact_interval_solver_rejected(self):
        g=fixture();g.domain=(A+1,A);g.objective=U-A
        with self.assertRaises(ValueError):solve_fixture(g)
    def test_symbolic_width_survives_float_parameter_substitution(self):
        a=sp.Symbol('offset',real=True)
        r=check_point(U-a,{U:A},{U:(a,a+1)},{a:sp.Float(A)},gross=U-a,kinds={U:'fixed'})
        self.assertFalse(r.complete);self.assertTrue(any(f.check=='bounds precision' for f in r.findings))
    def test_true_exact_large_singleton_preserved(self):
        g=fixture();g.domain=(A,A);g.objective=U-A;s=solve_fixture(g)
        self.assertTrue(s.rankable);self.assertEqual(s.kind[U],'fixed');self.assertEqual(s.payoffs['x'],0)
    def test_narrow_nonzero_domain_preserved(self):
        half=sp.Rational(1,2*10**10)
        r=check_point(1-(U-half)**2,{U:half},{U:(0,2*half)},{},gross=1-(U-half)**2,kinds={U:'interior'})
        self.assertTrue(r.ok and r.complete)
    def test_rescaled_linear_control_returns_upper(self):
        g=fixture();g.objective=U;s=solve_fixture(g)
        self.assertTrue(s.rankable);self.assertEqual(s.kind[U],'upper corner');self.assertEqual(s.payoffs['x'],1)
    def test_cli_precision_unavailable_is_unresolved_exit(self):
        from pacegame import cli
        g=fixture();g.domain=(A,A+1);g.objective=U-A;err=io.StringIO()
        with patch.dict(pg.models.REGISTRY,{'preannounce_entry':lambda **kwargs:g}),redirect_stdout(io.StringIO()),redirect_stderr(err):
            code=cli.main(['solve','preannounce_entry'])
        self.assertEqual(code,1);self.assertIn('unresolved: bounds precision unavailable',err.getvalue())

class SymbolContractTests(unittest.TestCase):
    def test_constructor_rejects_time_as_rate(self):
        g=pg.models.preannounce_entry()
        with self.assertRaisesRegex(ValueError,'independent'):
            replace(g,lifecycle=pg.TwoPhase(g.time,g.lifecycle.growth_end,1,True))
    def test_constructor_rejects_decision_as_parameter(self):
        g=pg.models.preannounce_entry()
        with self.assertRaisesRegex(ValueError,'independent'):replace(g,share_rule=pg.Proportional(g.entry))
    def test_constructor_rejects_signal_entry_identity(self):
        g=pg.models.preannounce_entry()
        with self.assertRaisesRegex(ValueError,'distinct'):replace(g,signal=g.entry)
    def test_constructor_rejects_time_entry_identity(self):
        g=pg.models.preannounce_entry()
        with self.assertRaisesRegex(ValueError,'distinct'):replace(g,time=g.entry)
    def test_structural_symbols_must_be_scalar(self):
        g=pg.models.preannounce_entry()
        for value in (1,g.entry+1,sp.MatrixSymbol('m',1,1)):
            with self.subTest(value=value),self.assertRaisesRegex(ValueError,'scalar Symbols'):replace(g,signal=value)
    def test_same_named_distinct_structural_symbols_rejected(self):
        g=pg.models.preannounce_entry()
        with self.assertRaisesRegex(ValueError,'distinct names'):replace(g,signal=sp.Symbol(str(g.entry),positive=True))
    def test_same_named_parameter_structural_symbols_rejected(self):
        g=pg.models.preannounce_entry()
        with self.assertRaisesRegex(ValueError,'independent'):
            replace(g,share_rule=pg.Proportional(sp.Symbol(str(g.entry),positive=True)))
    def test_mutated_time_rate_rejected_before_public_work(self):
        g=silent();g.lifecycle.sigma=g.time
        actions=[lambda:g.parameters(),lambda:g.numeric(dict(POINT,t=1)),lambda:g.payoffs(g.strategies[0]),
                 lambda:g.stocks(g.strategies[0]),lambda:g.demand_ceiling(g.strategies[0]),
                 lambda:pg.solve_symbolic(g,g.strategies[0])]
        for action in actions:
            with self.assertRaisesRegex(ValueError,'independent'):action()
    def test_mutated_signal_alias_rejected_by_solver(self):
        g=pg.models.preannounce_entry(keep_stock=True,signal_ceiling=True);params=g.numeric(POINT);g.signal=g.entry
        with self.assertRaisesRegex(ValueError,'distinct'):pg.solve(g,g.strategies[1],params)
    def test_mutated_decision_coefficient_rejected(self):
        g=silent();g.share_rule.phi=g.entry
        with self.assertRaisesRegex(ValueError,'independent'):g.numeric(dict(POINT,varsigma=.1))
    def test_independent_rate_expression_matches_constant(self):
        base=silent(cls=FixedTenth);alpha=sp.Symbol('alpha',positive=True)
        a=replace(base,lifecycle=pg.TwoPhase(alpha,base.lifecycle.growth_end,1,True))
        b=replace(base,lifecycle=pg.TwoPhase(sp.Integer(1),base.lifecycle.growth_end,1,True))
        oa=rank_strategies(a,dict(POINT,alpha=1));ob=rank_strategies(b,POINT)
        self.assertEqual(oa.payoffs,ob.payoffs);self.assertTrue(oa.complete and ob.complete)

class PlayerIdentityTests(unittest.TestCase):
    def test_duplicate_constructor_rejected(self):
        with self.assertRaisesRegex(ValueError,'distinct player'):replace(silent(),focal='x',rival='x')
    def test_duplicate_mutation_rejected_at_public_boundaries(self):
        g=silent();g.rival=g.focal
        actions=[lambda:g.stocks(g.strategies[0]),lambda:g.shares(g.strategies[0]),lambda:g.payoffs(g.strategies[0]),
                 lambda:g.numeric(POINT),lambda:g.players_alike(g.strategies[0]),lambda:rank_strategies(g,POINT)]
        for action in actions:
            with self.assertRaisesRegex(ValueError,'distinct player'):action()
    def test_custom_players_keep_two_payoff_keys(self):
        g=replace(silent(),focal='alpha',rival='beta',share_rule=pg.Proportional(sp.Rational(17,20),{'alpha':2,'beta':2}))
        o=rank_strategies(g,POINT);self.assertTrue(o.complete)
        for s in o.solutions.values():self.assertEqual(set(s.payoffs),{'alpha','beta'})
    def test_default_players_keep_two_payoff_keys(self):
        o=rank_strategies(silent(),POINT);self.assertTrue(o.complete)
        for s in o.solutions.values():self.assertEqual(set(s.payoffs),{'x','y'})

class BoundaryCurvatureTests(unittest.TestCase):
    def check(self,f,point=None,bounds=None,kinds=None):
        return check_point(f,point or {U:0,V:0},bounds or {U:(0,1),V:(0,1)},{},gross=f,
                           kinds=kinds or {U:'lower corner',V:'lower corner'},payoff_for={U:f,V:f})
    def test_audited_joint_corner_is_rejected(self):
        f=-U**2-V**2+3*U*V-10**8*(U+V)**4;r=self.check(f)
        self.assertFalse(r.ok);self.assertTrue(any(x.check=='joint curvature' and x.status=='violation' for x in r.findings))
    def test_solver_corner_cannot_rank(self):
        g=fixture(JointFixture);g.objective=-U**2-V**2+3*U*V-10**8*(U+V)**4
        s=solve_fixture(g);self.assertFalse(s.rankable);self.assertFalse(s.feasibility.ok)
    def test_concave_corner_remains_valid(self):
        r=self.check(-U**2-V**2);self.assertTrue(r.ok and r.complete)
    def test_positive_eigenvalue_in_infeasible_direction_not_false_failure(self):
        r=self.check(-U**2-V**2-3*U*V);self.assertTrue(r.ok and r.complete)
    def test_mixed_boundary_interior_positive_curvature_rejected(self):
        r=self.check(-U**2-V**2+3*U*V,bounds={U:(0,1),V:(-1,1)},kinds={U:'lower corner',V:'interior'})
        self.assertFalse(r.ok)
    def test_upper_lower_orientation_is_checked(self):
        f=-U**2-(V-1)**2-3*U*(V-1)
        r=self.check(f,point={U:0,V:1},kinds={U:'lower corner',V:'upper corner'});self.assertFalse(r.ok)
    def test_strict_boundary_gradient_removes_noncritical_direction(self):
        r=self.check(-U-V**2+100*U*V);self.assertTrue(r.ok and r.complete)
    def test_flat_curvature_discloses_higher_order_limit(self):
        r=self.check((U+V)**4);self.assertTrue(any(x.check=='joint curvature scope' and x.status=='warning' for x in r.findings))
    def test_three_dimensional_boundary_cone_is_explicitly_incomplete(self):
        f=-U**2-V**2-W**2
        r=check_point(f,{U:0,V:0,W:0},{x:(0,1) for x in (U,V,W)},{},gross=f,kinds={x:'lower corner' for x in (U,V,W)})
        self.assertFalse(r.complete);self.assertTrue(any(x.check=='joint curvature' and x.required and x.status=='warning' for x in r.findings))
    def test_interior_hessian_solver_control_preserved(self):
        g=fixture(JointFixture);g.objective=1-(U-sp.Rational(1,2))**2-(V-sp.Rational(1,2))**2
        s=solve_fixture(g);self.assertTrue(s.rankable);self.assertTrue(any(x.check=='joint curvature' for x in s.feasibility.findings))

if __name__=='__main__':unittest.main()
