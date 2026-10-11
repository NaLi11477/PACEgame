"""Regression controls for the five v0.2.1 third-audit findings."""
import math
import unittest
from dataclasses import replace
from unittest.mock import patch
import sympy as sp
import pacegame as pg
from pacegame.analyze import derivative, verify
from pacegame.analyze.statics import Response
from pacegame.core.share import Proportional
from pacegame.solve.feasible import check_point
from pacegame.examples.validate_audit_022 import (POINT, SlottedTwoPhase,
    PlainTwoPhase, FixedZero, FixedTenth, silence, strategy)

class Audit022(unittest.TestCase):
    def fixed(self, cls=FixedZero, **kwargs):
        return silence(pg.models.preannounce_entry(), cls, **kwargs)

    def competitive(self,g):
        return verify.check(g,[verify.Competitive('DF')],over={'phi':(.8,.9)},n=3,
            fixed={'sigma':.1,'hatvarsigma':.3})

    def test_slots_mutation_roundtrip_matches_integral_and_fresh_model(self):
        b=pg.models.preannounce_entry();l=b.lifecycle
        g=replace(b,lifecycle=SlottedTwoPhase(l.sigma,l.growth_end,l.horizon,l.keep_stock))
        for gain in [1,2,1]:
            g.lifecycle.gain=sp.Integer(gain)
            sol=pg.solve(g,strategy(g,'DF'),g.numeric(POINT))
            fresh=pg.solve(replace(g),strategy(g,'DF'),g.numeric(POINT))
            self.assertTrue(sol.rankable);self.assertEqual(sol.payoffs,fresh.payoffs)
            self.assertAlmostEqual(sol.payoffs['x'],gain*51/16000,places=15)

    def test_inherited_string_slot_is_seen(self):
        class Gain(PlainTwoPhase):
            __slots__='gain'
        b=pg.models.preannounce_entry();l=b.lifecycle
        life=Gain(l.sigma,l.growth_end,l.horizon,l.keep_stock)
        g=replace(b,lifecycle=life)
        first=g.gross_payoffs(strategy(g,'DF'))
        life.gain=2
        self.assertEqual(g.gross_payoffs(strategy(g,'DF'))['x'],2*first['x'])

    def test_slotted_share_state_mutation_changes_payoff(self):
        class Quality(Proportional):
            __slots__='weight'
            def shares(self,stocks):
                return {k: self.weight if k=='x' else 1-self.weight for k in stocks}
        b=pg.models.preannounce_entry();rule=Quality(b.share_rule.phi);rule.weight=sp.Rational(1,2)
        g=replace(b,share_rule=rule);st=strategy(g,'DF')
        first=g.payoffs(st)['x'];rule.weight=sp.Rational(3,4)
        self.assertEqual(sp.simplify(g.payoffs(st)['x'].subs({g.entry:0})-sp.Rational(3,2)*first.subs({g.entry:0})),0)

    def test_same_named_classes_do_not_share_cache(self):
        def make(mult):
            class Variant(PlainTwoPhase):
                def segments(self,*a,**kw):
                    from pacegame.core.lifecycle import Segment
                    return [Segment(s.lo,s.hi,mult*s.expr) for s in super().segments(*a,**kw)]
            return Variant
        b=pg.models.preannounce_entry();l=b.lifecycle;A,B=make(1),make(2)
        g=replace(b,lifecycle=A(l.sigma,l.growth_end,l.horizon,l.keep_stock));st=strategy(g,'DF')
        first=g.payoffs(st)['x'];g.lifecycle=B(l.sigma,l.growth_end,l.horizon,l.keep_stock)
        self.assertEqual(g.payoffs(st)['x'],2*first)

    def test_explicit_invalidate_recomputes(self):
        g=pg.models.preannounce_entry();st=strategy(g,'DF');p=g.payoffs(st)
        g.invalidate();self.assertEqual(g.payoffs(st),p)

    def test_cost_only_parameter_cannot_establish_competition(self):
        g=self.fixed(timing_cost=pg.models.preannounce_entry().share_rule.phi)
        r=self.competitive(g);self.assertEqual(r.results[0].failed,3)
        self.assertEqual(r.results[0].passed,0);self.assertTrue(r.complete)

    def test_signal_cost_path_excluded(self):
        b=pg.models.preannounce_entry();g=FixedZero(b.lifecycle,b.share_rule,b.entry,b.signal,
            signal_cost=b.share_rule.phi,signal_ceiling=1)
        st=strategy(g,'RL')
        self.assertEqual(g.share_sensitivity(st,g.share_rule.phi).subs({g.entry:0,g.signal:0}),0)

    def test_genuine_share_channel_with_cost_still_active(self):
        b=pg.models.preannounce_entry();g=silence(b,FixedTenth,timing_cost=b.share_rule.phi)
        r=self.competitive(g);self.assertEqual(r.results[0].passed,3)
        self.assertTrue(r.complete)

    def test_lifecycle_overlap_is_held_fixed(self):
        b=pg.models.preannounce_entry();g=silence(b,FixedZero)
        g.lifecycle=replace(g.lifecycle,sigma=g.share_rule.phi)
        r=verify.check(g,[verify.Competitive('DF')],over={'phi':(.8,.9)},fixed={'hatvarsigma':.3})
        self.assertEqual(r.results[0].failed,3);self.assertEqual(r.results[0].passed,0)

    def test_analytic_share_response_at_positive_stock(self):
        g=self.fixed(FixedTenth);st=strategy(g,'DF');p=g.share_rule.phi
        # Here p enters only the explicit share rule: isolated and net partial agree.
        self.assertEqual(sp.simplify(g.share_sensitivity(st,p)-sp.diff(g.payoffs(st)['x'],p)),0)

    def test_custom_payoff_without_channel_contract_is_unknown(self):
        b=pg.models.preannounce_entry();p=b.share_rule.phi
        class Custom(FixedZero):
            def payoffs(self,st):return {'x':p/1000,'y':p/1000}
        g=silence(b,Custom);r=self.competitive(g)
        self.assertEqual(r.results[0].skipped,3);self.assertEqual(r.results[0].passed,0)
        self.assertFalse(r.complete)

    def test_custom_explicit_channel_hook_is_used(self):
        b=pg.models.preannounce_entry();p=b.share_rule.phi
        class Custom(FixedZero):
            def payoffs(self,st):return {'x':p/1000,'y':p/1000}
            def share_sensitivity(self,st,parameter):return sp.Rational(1,1000)
        r=self.competitive(silence(b,Custom));self.assertEqual(r.results[0].passed,3)

    def test_one_shot_claims_match_list_for_true_and_false(self):
        g=self.fixed()
        factories=[list,tuple,iter,lambda xs:(x for x in xs)]
        for factory in factories:
            r=verify.check(g,factory([verify.Dominates('DF','DL',strict=False),
                verify.Dominates('DF','DL')]),over={'phi':(.8,.9)},fixed={'sigma':.1,'hatvarsigma':.3})
            self.assertEqual(r.results[0].passed,3);self.assertEqual(r.results[1].failed,3)
            self.assertFalse(r.ok);self.assertTrue(r.complete)

    def test_empty_claim_iterables_rejected(self):
        for cs in [[],(),iter([]),(c for c in [])]:
            with self.assertRaisesRegex(ValueError,'at least one'):
                verify.check(self.fixed(),cs,over={},fixed=POINT)

    def test_invalid_claim_type_rejected_before_sweep(self):
        with self.assertRaisesRegex(TypeError,'Claim'):
            verify.check(self.fixed(),iter([object()]),over={},fixed=POINT)

    def test_zero_and_partial_accounting_are_incomplete(self):
        for result in [verify.Result('x'),verify.Result('x',passed=2),verify.Result('x',passed=4)]:
            self.assertFalse(verify.Report([result],points=3).complete)
        self.assertTrue(verify.Report([verify.Result('x',passed=1,failed=2)],points=3).complete)

    def test_skips_and_errors_remain_distinct_for_generators(self):
        class Unknown(verify.Claim):
            def evaluate(self,*a):return None,'unknown'
        class Error(verify.Claim):
            def evaluate(self,*a):raise ValueError('failure')
        r=verify.check(self.fixed(),(c for c in [Unknown(),Error()]),over={},fixed=POINT)
        self.assertEqual(r.results[0].skipped,1);self.assertEqual(r.results[1].errors,1)
        self.assertFalse(r.complete)

    def test_nonfinite_negative_complex_tolerances_rejected(self):
        x=sp.Symbol('x')
        for tol in [math.nan,math.inf,-math.inf,-1,1j,sp.I,sp.Symbol('tol')]:
            with self.subTest(tol=str(tol)),self.assertRaisesRegex(ValueError,'tol must'):
                check_point(-1,{x:2},{x:(0,1)},{},gross=-1,upper_bound=-2,tol=tol)

    def test_zero_and_default_tolerance_preserve_violations(self):
        x=sp.Symbol('x')
        for tol in [0,1e-9,sp.Rational(1,10**9)]:
            r=check_point(-1,{x:2},{x:(0,1)},{},gross=-1,upper_bound=-2,tol=tol,kinds={x:'lower corner'})
            self.assertFalse(r.ok);self.assertTrue(r.complete)
            self.assertEqual({f.check for f in r.violations()},{'bounds','payoff sign','payoff magnitude'})

    def test_extreme_finite_payoffs_overflow_has_no_sign_verdict(self):
        g=silence(pg.models.preannounce_entry(keep_stock=True),FixedTenth)
        p=dict(sigma=1e308,phi=1e-308,hatvarsigma=.3)
        s=pg.solve(g,strategy(g,'DF'),g.numeric(p))
        self.assertTrue(s.rankable);self.assertTrue(all(math.isfinite(v) for v in s.payoffs.values()))
        with self.assertRaisesRegex(ValueError,'numerical range'):
            derivative(g,'DF','phi',p,step=1e-309)
        r=verify.check(g,[verify.Sign('d pi_x / d phi','>',strategy='DF',step=1e-309)],
            over={'phi':[1e-308]},fixed={'sigma':1e308,'hatvarsigma':.3})
        self.assertEqual(r.results[0].passed,0);self.assertEqual(r.results[0].errors,1)
        self.assertFalse(r.complete)

    def test_ordinary_derivative_remains_finite_positive(self):
        g=silence(pg.models.preannounce_entry(keep_stock=True),FixedTenth)
        r=derivative(g,'DF','phi',POINT)
        self.assertTrue(math.isfinite(r.slope));self.assertGreater(r.slope,0);self.assertEqual(r.sign,'+')

    def test_response_sign_rejects_nonfinite_values(self):
        for slope in [math.nan,math.inf,-math.inf]:
            with self.assertRaisesRegex(ValueError,'no sign verdict'):
                _=Response('DF','phi',{},slope).sign

    def test_sign_claim_rejects_nonfinite_external_response(self):
        g=self.fixed();claim=verify.Sign('d pi_x / d phi','>',strategy='DF')
        with patch('pacegame.analyze.statics.derivative',return_value=Response('DF','phi',{},math.inf)):
            r=verify.check(g,[claim],over={},fixed=POINT)
        self.assertEqual(r.results[0].errors,1);self.assertEqual(r.results[0].passed,0)

    def test_invalid_flat_tolerances_rejected(self):
        for flat in [math.nan,math.inf,-1]:
            with self.assertRaisesRegex(ValueError,'flat'):
                verify.Sign('d pi_x / d phi','>',flat=flat)

    def test_overflow_numerator_rejected(self):
        g=self.fixed()
        with patch('pacegame.analyze.statics._read',side_effect=[-1e308,1e308]):
            with self.assertRaisesRegex(ValueError,'numerator'):
                derivative(g,'DF','phi',POINT)

if __name__=='__main__':unittest.main()
