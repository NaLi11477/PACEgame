"""Fourth-audit public-state, target binding and iterable sweep regressions."""
import math
import unittest
from dataclasses import dataclass, replace
from unittest.mock import patch
import sympy as sp
import pacegame as pg
from pacegame.analyze import derivative, rank_strategies, sign_map, sweep, verify
from pacegame.core.lifecycle import Segment
from pacegame.examples.validate_audit_022 import POINT, FixedTenth, silence, strategy
from pacegame.examples.validate_audit_023 import keyed, solve_df, Once, brief, KeyedTwoPhase

class Audit023(unittest.TestCase):
    def fixed(self):return silence(pg.models.preannounce_entry(keep_stock=True),FixedTenth)
    def report(self,g,target,relation):
        return verify.check(g,[verify.Sign(f'd {target} / d phi',relation,strategy='DF')],over={},fixed=POINT)
    def cache_change(self,g,weights):
        old=solve_df(g);fp=g._fingerprint();g.lifecycle.weights=weights
        new=solve_df(g);fresh=solve_df(replace(g));g.invalidate();explicit=solve_df(g)
        self.assertNotEqual(fp,g._fingerprint());self.assertNotEqual(old.payoffs,new.payoffs)
        self.assertEqual(new.payoffs,fresh.payoffs);self.assertEqual(new.payoffs,explicit.payoffs)
        self.assertTrue(new.rankable);self.assertAlmostEqual(new.payoffs['x'],51/16000,places=15)

    def test_integer_and_string_keys_match_fresh_and_analytic(self):
        self.cache_change(keyed(),{'1':sp.Integer(2)})
    def test_same_named_symbol_assumptions_are_distinct(self):
        k=sp.Symbol('gain');self.cache_change(keyed({k:sp.Integer(2)},k),{sp.Symbol('gain',positive=True):sp.Integer(2)})
    def test_nested_dictionary_key_change_recomputes(self):
        self.cache_change(keyed({'phase':{1:sp.Integer(2)}}),{'phase':{'1':sp.Integer(2)}})
    def test_dictionary_order_is_semantically_irrelevant(self):
        g=keyed({1:sp.Integer(2),'unused':3});s=solve_df(g);fp=g._fingerprint()
        g.lifecycle.weights={'unused':3,1:sp.Integer(2)}
        self.assertEqual(fp,g._fingerprint());self.assertEqual(s.payoffs,solve_df(g).payoffs)
    def test_key_mutation_roundtrip(self):
        g=keyed();a=solve_df(g);g.lifecycle.weights={'1':sp.Integer(2)};b=solve_df(g)
        g.lifecycle.weights={1:sp.Integer(2)};c=solve_df(g)
        self.assertNotEqual(a.payoffs,b.payoffs);self.assertEqual(a.payoffs,c.payoffs)
    def test_numeric_public_value_types_can_change_semantics(self):
        @dataclass
        class Typed(KeyedTwoPhase):
            marker:object=1
            @property
            def gain(self):return sp.Integer(2) if type(self.marker) is int else sp.Integer(1)
        b=pg.models.preannounce_entry();l=b.lifecycle
        g=replace(b,lifecycle=Typed(l.sigma,l.growth_end,l.horizon,l.keep_stock))
        a=solve_df(g);g.lifecycle.marker=True;b=solve_df(g)
        self.assertAlmostEqual(a.payoffs['x'],2*b.payoffs['x'],places=15)
    def test_sequence_order_is_preserved_and_container_type_is_seen(self):
        g=keyed();g.lifecycle.extra=[1,2];a=g._fingerprint();g.lifecycle.extra=[2,1]
        self.assertNotEqual(a,g._fingerprint());b=g._fingerprint();g.lifecycle.extra=(2,1)
        self.assertNotEqual(b,g._fingerprint())
    def test_set_order_ignored_and_set_type_seen(self):
        g=keyed();g.lifecycle.extra={1,'1'};a=g._fingerprint();g.lifecycle.extra={'1',1}
        self.assertEqual(a,g._fingerprint());g.lifecycle.extra=frozenset({1,'1'})
        self.assertNotEqual(a,g._fingerprint())

    def test_focal_positive_and_rival_negative_claims(self):
        g=self.fixed()
        for target,relation,expected in [('pi_x','>',True),('pi_y','>',False),('pi_y','<',True),('pi_x','<',False)]:
            r=self.report(g,target,relation);self.assertTrue(r.complete)
            self.assertEqual(r.results[0].passed,int(expected));self.assertEqual(r.results[0].failed,int(not expected))
    def test_both_derivatives_match_exact_analytic_reference(self):
        g=self.fixed()
        for quantity,sign in [('pi_x',1),('pi_y',-1)]:
            r=derivative(g,'DF','phi',POINT,quantity=quantity)
            self.assertAlmostEqual(r.slope,sign*160/16136289,places=12)
            self.assertEqual(r.target,quantity+'[DF]')
    def test_legacy_focal_alias_is_unchanged(self):
        g=self.fixed()
        self.assertEqual(derivative(g,'DF','phi',POINT).slope,
                         derivative(g,'DF','phi',POINT,quantity='pi_x').slope)
    def test_unknown_payoff_target_rejected_before_evaluation(self):
        with patch('pacegame.analyze.statics.derivative',side_effect=AssertionError('must not run')):
            with self.assertRaisesRegex(ValueError,'unknown payoff target'):
                self.report(self.fixed(),'pi_UNKNOWN','>')
    def test_malformed_or_decision_targets_rejected(self):
        for expr in ['d varsigma / d phi','d banana / d phi','d pi_x / d phi / d sigma','pi_x/phi','d pi_x/dphi','d pi_ / d phi','',None]:
            with self.subTest(expr=expr),self.assertRaises(ValueError):verify.Sign(expr,'>')
    def test_unknown_derivative_parameter_rejected_early(self):
        with self.assertRaisesRegex(ValueError,'unknown derivative parameter'):
            verify.check(self.fixed(),[verify.Sign('d pi_x / d TYPO','>',strategy='DF')],over={},fixed=POINT)
    def test_custom_player_names_bind_actual_payoff(self):
        g=replace(self.fixed(),focal='alpha',rival='beta')
        self.assertEqual(self.report(g,'pi_beta','<').results[0].passed,1)
        with self.assertRaises(ValueError):self.report(g,'pi_y','<')
    def test_whitespace_grammar_keeps_correct_label(self):
        c=verify.Sign('  d   pi_y / d  phi  ','<',strategy='DF')
        r=verify.check(self.fixed(),[c],over={},fixed=POINT)
        self.assertEqual(r.results[0].passed,1);self.assertEqual(r.results[0].claim,'d pi_y / d phi < 0  under DF')
    def test_fixed_decision_response_stays_on_derivative_interface(self):
        g=self.fixed();r=derivative(g,'DF','phi',POINT,quantity='varsigma')
        self.assertEqual(r.slope,0);self.assertEqual(r.target,'varsigma*[DF]')
    def test_rival_statics_map_keeps_payoff_target(self):
        r=sign_map(self.fixed(),'DF','phi',{'phi':(.8,.9)},{'sigma':.1,'hatvarsigma':.3},n=3,quantity='pi_y')
        self.assertEqual(r.target,'pi_y[DF]');self.assertEqual(r.signs,{'-'})
    def test_flat_payoff_is_not_a_strict_sign(self):
        g=self.fixed();r=verify.check(g,[verify.Sign('d pi_y / d phi','<',strategy='DF',flat=1)],over={},fixed=POINT)
        self.assertEqual(r.results[0].failed,1);self.assertTrue(r.complete)
    def test_rival_overflow_retains_numerical_range_error(self):
        p={'sigma':1e308,'phi':1e-308,'hatvarsigma':.3}
        with self.assertRaisesRegex(ValueError,'numerical range'):
            derivative(self.fixed(),'DF','phi',p,quantity='pi_y',step=1e-309)
    def test_unknown_strategy_rejected_before_sign_samples(self):
        with self.assertRaisesRegex(ValueError,'unknown strategy'):
            verify.check(self.fixed(),[verify.Sign('d pi_x / d phi','>',strategy='TYPO')],over={},fixed=POINT)
    def test_gap_interface_does_not_ignore_explicit_target(self):
        with self.assertRaisesRegex(ValueError,'payoff gaps'):
            derivative(self.fixed(),('DF','DL'),'phi',POINT,quantity='pi_y')

    def test_sweep_all_iterable_types_equal_over_multiple_points(self):
        g=self.fixed();pool=list(g.strategies);fixed={'sigma':.1,'hatvarsigma':.3}
        expected=[brief(o) for o in sweep(g,'phi',[.8,.85,.9],fixed,pool)]
        for factory in [tuple,iter,lambda xs:(s for s in xs),Once]:
            actual=[brief(o) for o in sweep(g,'phi',[.8,.85,.9],fixed,factory(pool))]
            self.assertEqual(actual,expected)
    def test_once_strategy_pool_is_consumed_once(self):
        g=self.fixed();selected=Once(list(g.strategies))
        self.assertEqual(len(sweep(g,'phi',[.8,.9],{'sigma':.1,'hatvarsigma':.3},selected)),2)
        self.assertEqual(selected.iterations,1)
    def test_invalid_pools_rejected_before_solves(self):
        g=self.fixed();st=strategy(g,'DF')
        with patch('pacegame.analyze.equilibrium.solve',side_effect=AssertionError('must not solve')):
            for pool in [[],[st,st],[pg.Strategy('TYPO',False,True)],['DF']]:
                with self.subTest(pool=pool),self.assertRaises(ValueError):
                    sweep(g,'phi',[.8,.9],{'sigma':.1,'hatvarsigma':.3},pool)
    def test_same_name_wrong_flags_is_not_admitted(self):
        g=self.fixed()
        with self.assertRaisesRegex(ValueError,'not admitted'):
            sweep(g,'phi',[.8],{'sigma':.1,'hatvarsigma':.3},[pg.Strategy('DF',True,True)])
    def test_empty_values_validate_pool_then_return_empty(self):
        g=self.fixed();self.assertEqual(sweep(g,'phi',[],POINT,list(g.strategies)),[])
        with self.assertRaises(ValueError):sweep(g,'phi',[],POINT,[])
    def test_values_generator_is_consumed_once(self):
        g=self.fixed();values=Once([.8,.9])
        self.assertEqual(len(sweep(g,'phi',values,{'sigma':.1,'hatvarsigma':.3})),2)
        self.assertEqual(values.iterations,1)
    def test_default_pool_matches_explicit_pool(self):
        g=self.fixed();fixed={'sigma':.1,'hatvarsigma':.3}
        self.assertEqual([brief(o) for o in sweep(g,'phi',[.8,.9],fixed)],
                         [brief(o) for o in sweep(g,'phi',[.8,.9],fixed,g.strategies)])
    def test_single_point_generator_still_supported(self):
        g=self.fixed();o=rank_strategies(g,POINT,(s for s in g.strategies));self.assertTrue(o.complete)

if __name__=='__main__':unittest.main()
