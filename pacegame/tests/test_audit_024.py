"""Fifth-audit counterexamples and normal controls, through public interfaces."""
from dataclasses import replace
import unittest
import sympy as sp
import pacegame as pg
from pacegame.analyze import rank_strategies, derivative
from pacegame.solve.feasible import check_point
from pacegame.core.lifecycle import TwoPhase, Logistic
from pacegame.core.share import Proportional, Logit, ShareRule
from pacegame.examples.validate_audit_022 import FixedTenth, silence

POINT = dict(sigma=.1, phi=.85, hatvarsigma=.3, **{'lambda':.1})


def silent(quality=None, phi=None, **names):
    base = pg.models.preannounce_entry(keep_stock=True, entry_floor=True)
    return replace(base, share_rule=Proportional(base.share_rule.phi if phi is None else phi, quality),
                   strategies=tuple(s for s in base.strategies if not s.signals), **names)


class CandidateMetadata(unittest.TestCase):
    def setUp(self): self.x, self.y = sp.symbols('x y')
    def report(self, kind=None, value=sp.Rational(1,2), interval=(0,1), **kw):
        return check_point(self.x, {self.x:value}, {self.x:interval}, {}, gross=self.x,
                           kinds=None if kind is None else {self.x:kind}, **kw)
    def test_unknown_kind_cannot_pass(self): self.assertFalse(self.report('upper').ok)
    def test_nonstring_kind_cannot_pass(self): self.assertFalse(self.report([]).ok)
    def test_upper_corner_at_interior_cannot_pass(self): self.assertFalse(self.report('upper corner').ok)
    def test_lower_corner_at_interior_cannot_pass(self): self.assertFalse(self.report('lower corner').ok)
    def test_fixed_on_nonzero_interval_cannot_pass(self): self.assertFalse(self.report('fixed').ok)
    def test_interior_at_upper_boundary_cannot_pass(self): self.assertFalse(self.report('interior',1).ok)
    def test_correct_interior_still_fails_stationarity(self):
        r=self.report('interior'); self.assertFalse(r.ok); self.assertTrue(r.complete)
        self.assertIn('stationarity',[f.check for f in r.violations()])
    def test_true_upper_corner_passes(self):
        r=self.report('upper corner',1); self.assertTrue(r.ok and r.complete)
    def test_singleton_passes_without_kkt(self):
        r=self.report('fixed',interval=(sp.Rational(1,2),sp.Rational(1,2)))
        self.assertTrue(r.ok and r.complete); self.assertIn('fixed variable',[f.check for f in r.findings])
    def test_legacy_singleton_corner_remains_fixed(self):
        r=self.report('lower corner',1,(1,1)); self.assertTrue(r.ok and r.complete)
    def test_missing_coordinate_rejects_and_checks_reversed_interval(self):
        r=check_point(0,{self.x:0},{self.x:(0,0),self.y:(2,1)},{},gross=0)
        self.assertFalse(r.ok); self.assertIn('bounds',[f.check for f in r.violations()])
    def test_missing_declared_bounds_rejects(self):
        r=check_point(0,{self.x:0},{},{},gross=0); self.assertFalse(r.ok)
    def test_missing_owned_coordinate_rejects(self):
        r=check_point(0,{self.x:0},{self.x:(0,0)},{},gross=0,payoff_for={self.y:0})
        self.assertFalse(r.ok)
    def test_extra_kind_coordinate_rejects(self):
        r=check_point(0,{self.x:0},{self.x:(0,0)},{},gross=0,kinds={self.y:'fixed'})
        self.assertFalse(r.ok)
    def test_skip_does_not_bypass_metadata(self): self.assertFalse(self.report('upper',skip_optimality={self.x}).ok)
    def test_narrow_nonzero_interval_preserves_interior(self):
        x=self.x; a=sp.Rational(1,2*10**10)
        r=check_point(1-(x-a)**2,{x:a},{x:(0,2*a)},{},gross=1-(x-a)**2,kinds={x:'interior'})
        self.assertTrue(r.ok and r.complete)
    def test_omitted_kind_infers_actual_corner(self):
        r=self.report(None,1); self.assertTrue(r.ok and r.complete)
    def test_search_limit_cannot_be_complete(self):
        r=self.report('search limit',1,(0,sp.oo)); self.assertFalse(r.complete)
        r=self.report('unbounded',1,(0,sp.oo),skip_optimality={self.x});self.assertFalse(r.ok)


class PlayerQuality(unittest.TestCase):
    def test_unrelated_quality_player_rejected_at_game_boundary(self):
        with self.assertRaisesRegex(ValueError,'unknown player'): silent({'x':2,'z':2})
    def test_mutated_unknown_player_rejected(self):
        g=silent({'x':2});g.share_rule.quality['z']=2
        with self.assertRaisesRegex(ValueError,'unknown player'):g.numeric(POINT)
        with self.assertRaisesRegex(ValueError,'unknown player'):g.players_alike(g.strategies[0])
    def test_partial_dictionary_uses_actual_default_and_no_role_gap(self):
        a,b=silent({'x':2}),silent({'x':2,'y':1})
        oa,ob=rank_strategies(a,POINT),rank_strategies(b,POINT)
        self.assertFalse(a.share_rule.is_symmetric());self.assertEqual(oa.payoffs,ob.payoffs)
        self.assertIsNone(oa.role_conflict());self.assertIsNone(ob.role_conflict())
        self.assertEqual(a.share_rule.shares({'x':0,'y':0}),{'x':sp.Rational(2,3),'y':sp.Rational(1,3)})
    def test_equal_actual_quality_is_interchangeable(self):
        g=silent({'x':2,'y':2});self.assertTrue(g.share_rule.is_symmetric())
        self.assertTrue(all(g.players_alike(s) for s in g.strategies))
        self.assertIsNotNone(rank_strategies(g,POINT).role_conflict())
    def test_custom_player_names_bind_quality(self):
        g=silent({'alpha':2},focal='alpha',rival='beta')
        self.assertFalse(g.share_rule.is_symmetric_for(('alpha','beta')))
        self.assertIsNone(rank_strategies(g,POINT).role_conflict())
        self.assertTrue(silent({'alpha':2,'beta':2},focal='alpha',rival='beta').players_alike(g.strategies[0]))
    def test_symbolic_quality_uses_identity_and_default(self):
        q=sp.Symbol('quality',positive=True);g=silent({'x':q,'y':q})
        self.assertTrue(g.players_alike(g.strategies[0]));self.assertIn('quality',g.parameters())
        self.assertFalse(silent({'x':q}).players_alike(g.strategies[0]))
    def test_custom_no_argument_symmetry_hook_preserved(self):
        class Custom(ShareRule):
            def is_symmetric(self):return False
        g=replace(silent(),share_rule=Custom());self.assertFalse(g.players_alike(g.strategies[0]))
        class CustomProportional(Proportional):
            def is_symmetric(self):return False
        g=replace(silent(),share_rule=CustomProportional(sp.Rational(17,20)))
        self.assertFalse(g.players_alike(g.strategies[0]))


class ExpressionParameters(unittest.TestCase):
    def test_constant_share_has_no_external_phi(self):
        g=silent(phi=sp.Rational(17,20));self.assertEqual(g.share_rule.params,())
        self.assertNotIn('phi',g.parameters());self.assertNotIn('17/20',g.parameters())
        p={k:v for k,v in POINT.items() if k!='phi'}
        actual=rank_strategies(g,p).payoffs;reference=rank_strategies(silent(),POINT).payoffs
        for name in reference:self.assertAlmostEqual(actual[name],reference[name],places=15)
    def test_compound_share_requires_only_free_symbol(self):
        a=sp.Symbol('alpha',positive=True);g=silent(phi=2*a)
        self.assertEqual(g.share_rule.params,(a,));self.assertIn('alpha',g.parameters())
        self.assertNotIn('2*alpha',g.parameters())
        p={k:v for k,v in POINT.items() if k!='phi'};p['alpha']=.85
        self.assertEqual(rank_strategies(g,p).payoffs,rank_strategies(silent(),dict(POINT,phi=1.7)).payoffs)
    def test_missing_free_symbol_rejected(self):
        with self.assertRaisesRegex(KeyError,'alpha'):silent(phi=2*sp.Symbol('alpha',positive=True)).numeric(POINT)
    def test_expression_domain_rejected(self):
        a=sp.Symbol('alpha');g=silent(phi=2*a)
        with self.assertRaisesRegex(ValueError,'phi coefficient'):g.numeric(dict(POINT,alpha=-1))
    def test_nonfinite_constant_coefficient_rejected(self):
        with self.assertRaisesRegex(ValueError,'phi coefficient'):silent(phi=sp.oo).numeric(POINT)
    def test_compound_coefficient_statics_selects_either_player(self):
        a=sp.Symbol('alpha',positive=True);g=silence(silent(phi=2*a),FixedTenth)
        reference=silence(silent(),FixedTenth);p=dict(POINT,alpha=.85)
        for player in ['x','y']:
            actual=derivative(g,'DF','alpha',p,quantity='pi_'+player).slope
            expected=2*derivative(reference,'DF','phi',dict(POINT,phi=1.7),quantity='pi_'+player,step=2e-4).slope
            self.assertAlmostEqual(actual,expected,places=11)
    def test_other_builtin_expression_inventories(self):
        a,b=sp.symbols('a b',positive=True)
        self.assertEqual(Logit(2*a).params,(a,));self.assertEqual(Logit(1).all_params(),())
        self.assertEqual(TwoPhase(2*a,sp.Rational(3,10),b).params,(a,b))
        self.assertEqual(Logistic(2*a,8,sp.Rational(1,2),b).params,(a,b))
    def test_mutated_expression_inventory_tracks_current_coefficient(self):
        g=silent();a=sp.Symbol('alpha',positive=True);g.share_rule.phi=2*a
        self.assertIn('alpha',g.parameters());self.assertNotIn('phi',g.parameters())
        self.assertEqual(g.share_rule.all_params(),(a,))
    def test_same_named_distinct_symbols_rejected(self):
        a=sp.Symbol('alpha',positive=True);b=sp.Symbol('alpha',nonnegative=True)
        with self.assertRaisesRegex(ValueError,'ambiguous parameter'):silent(phi=a+b).parameters()


if __name__=='__main__':unittest.main()
