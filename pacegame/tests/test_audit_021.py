"""Acceptance tests for the seven groups in the second independent audit."""
import contextlib
import io
import math
import unittest
import sympy as sp
import pacegame as pg
from pacegame.cli import main
from pacegame.analyze import threshold, critical_value, rank_strategies, verify
from pacegame.analyze._crossing import scan_crossing
from pacegame.solve import FIXED, INTERIOR, LOWER, UPPER, Solution
from pacegame.solve.feasible import check_point

P={'sigma':.1,'phi':.85,'hatvarsigma':.3}
def st(g,name): return next(s for s in g.strategies if s.name==name)
def repaired(**kw):
    return pg.models.preannounce_entry(keep_stock=True,signal_accrues=True,
                                      signal_cost=True,**kw)
def cli(args):
    out=io.StringIO()
    with contextlib.redirect_stdout(out),contextlib.redirect_stderr(out):
        code=main(args)
    return code,out.getvalue()

class Audit021(unittest.TestCase):
    def test_sweep_unresolved_exit_is_one(self):
        code,out=cli(['sweep','preannounce_entry','--wrt','sigma','--from','.1','--to','.2','--steps','1'])
        self.assertEqual(code,1);self.assertIn('unresolved',out)

    def test_sweep_complete_exit_is_zero(self):
        code,out=cli(['sweep','preannounce_entry','--repair','--wrt','sigma','--from','.1','--to','.2','--steps','1'])
        self.assertEqual(code,0);self.assertNotIn('unresolved',out)

    def test_sweep_malformed_exit_is_two(self):
        self.assertEqual(cli(['sweep','preannounce_entry','--wrt','TYPO','--from','.1','--to','.2'])[0],2)

    def test_both_public_crossing_apis_keep_sampled_root(self):
        b=pg.models.preannounce_entry();e,d=b.entry,b.signal
        phi,sigma=b.share_rule.phi,b.lifecycle.sigma
        class Gap(pg.Game):
            def payoffs(self,s):
                q=sp.Rational(1,1000)*(phi if s.name=='DF' else 1)
                return {'x':q,'y':q}
        class Slope(pg.Game):
            def payoffs(self,s):
                q=sp.Rational(1,1000)*(1+sigma*(phi-1))
                return {'x':q,'y':q}
        kwargs=dict(strategies=tuple(s for s in b.strategies if not s.signals))
        g=Gap(b.lifecycle,b.share_rule,e,d,**kwargs)
        h=Slope(b.lifecycle,b.share_rule,e,d,**kwargs)
        for scan in [2,3,12]:
            with self.subTest(scan=scan):
                self.assertAlmostEqual(threshold(g,'phi',.5,1.5,P,'DF','DL',scan=scan),1)
                self.assertAlmostEqual(critical_value(h,'DL','sigma','phi',.5,1.5,P,scan=scan),1)

    def test_unsampled_simple_root_is_refined(self):
        self.assertAlmostEqual(scan_crossing(lambda x:x-.37,0,1,4,50,1e-12),.37,places=9)

    def test_touching_zero_is_not_a_strict_reversal(self):
        self.assertIsNone(scan_crossing(lambda x:(x-.5)**2,0,1,4,30,1e-12))

    def test_endpoint_tie_is_not_a_strict_reversal(self):
        self.assertIsNone(scan_crossing(lambda x:x,0,1,4,30,1e-12))

    def test_all_zero_is_not_a_strict_reversal(self):
        self.assertIsNone(scan_crossing(lambda x:0,0,1,4,30,1e-12))

    def test_zero_plateau_returns_sampled_representative(self):
        f=lambda x:-1 if x<.25 else 1 if x>.75 else 0
        root=scan_crossing(f,0,1,8,30,1e-12)
        self.assertEqual(f(root),0);self.assertIn(root,[i/8 for i in range(9)])

    def test_same_sign_around_zero_run_is_not_reversal(self):
        f=lambda x:0 if .25<=x<=.75 else 1
        self.assertIsNone(scan_crossing(f,0,1,8,30,1e-12))

    def test_invalid_tolerance_and_nonfinite_scan_are_rejected(self):
        for tol in [-1,float('nan'),float('inf')]:
            with self.subTest(tol=tol),self.assertRaises(ValueError):scan_crossing(lambda x:x-.5,0,1,2,10,tol)
        with self.assertRaises(ValueError):scan_crossing(lambda x:float('nan'),0,1,2,10,0)

    def test_fixed_entry_has_analytic_signal_and_no_false_kkt(self):
        g=repaired(entry_floor=True);p=dict(P,kappa_d=.05,**{'lambda':.3})
        s=pg.solve(g,st(g,'RL'),g.numeric(p))
        self.assertEqual(s.kind[g.entry],FIXED);self.assertTrue(s.rankable,str(s.feasibility))
        self.assertAlmostEqual(float(s.point[g.signal]),1.05,places=10)
        self.assertAlmostEqual(s.payoffs['x'],.0275625,places=12)

    def test_fixed_signal_is_not_a_lower_corner(self):
        g=repaired();g.signal_ceiling=sp.Integer(0)
        s=pg.solve(g,st(g,'RL'),g.numeric(dict(P,kappa_d=.05)))
        self.assertEqual(s.kind[g.signal],FIXED);self.assertTrue(s.rankable)

    def test_both_decisions_fixed_have_no_feasible_kkt_direction(self):
        g=repaired(entry_floor=True);g.signal_ceiling=sp.Integer(0)
        s=pg.solve(g,st(g,'RL'),g.numeric(dict(P,kappa_d=.05,**{'lambda':.3})))
        self.assertEqual(set(s.kind.values()),{FIXED});self.assertTrue(s.rankable,str(s.feasibility))

    def test_narrow_nonzero_intervals_keep_interior_and_corners(self):
        b=pg.models.preannounce_entry();e,d=b.entry,b.signal
        for label,expr in [(INTERIOR,sp.Rational(1,1000)-(e-sp.Rational(1,200000000))**2),
                           (UPPER,sp.Rational(1,1000)+e),(LOWER,sp.Rational(1,1000)-e)]:
            class Narrow(pg.Game):
                def bounds(self,s):return {e:(0,sp.Rational(1,100000000))}
                def payoffs(self,s):return {'x':expr,'y':expr}
            g=Narrow(b.lifecycle,b.share_rule,e,d,strategies=(st(b,'DL'),))
            s=pg.solve(g,st(g,'DL'),g.numeric(P))
            with self.subTest(label=label):self.assertEqual(s.kind[e],label);self.assertTrue(s.rankable)

    def test_fixed_low_level_point_skips_one_sided_test(self):
        x=sp.Symbol('x')
        r=check_point(x,{x:1},{x:(1,1)},{},gross=x,kinds={x:LOWER})
        self.assertTrue(r.ok and r.complete);self.assertTrue(any(f.check=='fixed variable' for f in r.findings))

    def test_sensitivity_unknown_does_not_pass(self):
        g=pg.models.preannounce_entry();phi=g.share_rule.phi
        g.share_rule.quality={'x':1,'y':1+sp.floor(phi)}
        s=pg.solve(g,st(g,'DL'),g.numeric(P));self.assertTrue(s.rankable)
        note=next(f for f in s.feasibility.findings if f.check=='competition')
        self.assertIsNone(note.verdict);self.assertIn('unavailable',note.detail)
        r=verify.check(g,[verify.Competitive('DL')],over={},fixed=P)
        self.assertEqual(r.results[0].skipped,1);self.assertEqual(r.results[0].passed,0)
        self.assertFalse(r.complete);self.assertFalse(r.results[0].holds)

    def test_sensitivity_finite_active_has_evidence(self):
        g=pg.models.logistic_entry();s=pg.solve(g,st(g,'DF'),g.numeric(pg.models.LOGISTIC_POINT))
        note=next(f for f in s.feasibility.findings if f.check=='competition')
        self.assertTrue(note.verdict);self.assertIn('nonzero',note.detail)

    def test_sensitivity_all_zero_is_false_but_not_invalid_payoff(self):
        g=repaired();p=dict(P,kappa_d=.05)
        s=pg.solve(g,st(g,'RL'),g.numeric(p));self.assertTrue(s.rankable)
        self.assertIs(next(f for f in s.feasibility.findings if f.check=='competition').verdict,False)
        r=verify.check(g,[verify.Competitive('RL')],over={},fixed=p)
        self.assertEqual(r.results[0].failed,1)

    def test_partial_unknown_plus_active_is_evidenced_activity(self):
        g=pg.models.preannounce_entry();phi=g.share_rule.phi;w=sp.Symbol('omega',positive=True)
        g.share_rule.quality={'x':1,'y':w+sp.floor(phi)}
        s=pg.solve(g,st(g,'DL'),g.numeric(dict(P,omega=2)))
        note=next(f for f in s.feasibility.findings if f.check=='competition')
        self.assertTrue(s.rankable);self.assertIs(note.verdict,True)
        self.assertIn('omega',note.detail);self.assertIn('unavailable',note.detail)

    def test_partial_unknown_plus_zero_remains_unknown(self):
        b=pg.models.preannounce_entry();phi=b.share_rule.phi;w=sp.Symbol('omega',positive=True)
        b.share_rule.quality={'x':1,'y':w}
        e,d=b.entry,b.signal
        class Partial(pg.Game):
            def payoffs(self,s):
                q=(1+sp.floor(phi)+(w-1)**2)/1000-e**2
                return {'x':q,'y':q}
        g=Partial(b.lifecycle,b.share_rule,e,d,strategies=(st(b,'DL'),))
        s=pg.solve(g,st(g,'DL'),g.numeric(dict(P,omega=1)))
        self.assertTrue(s.rankable);self.assertIsNone(next(f for f in s.feasibility.findings if f.check=='competition').verdict)

    def test_no_share_parameters_is_skipped(self):
        g=pg.models.preannounce_entry()
        class Constant(pg.core.share.ShareRule):
            def shares(self,stocks):return {k:sp.Rational(1,2) for k in stocks}
        g.share_rule=Constant()
        r=verify.check(g,[verify.Competitive('DL')],over={},fixed=P)
        self.assertEqual(r.results[0].skipped,1)

    def test_logistic_horizon_is_entry_upper_bound(self):
        for T in [sp.Rational(1,2),sp.Integer(1),sp.Integer(2)]:
            g=pg.models.logistic_entry();g.lifecycle.horizon=T
            p=g.numeric(pg.models.LOGISTIC_POINT)
            for name in ['DF','DL']:
                s=pg.solve(g,st(g,name),p)
                with self.subTest(T=T,name=name):
                    self.assertEqual(g.bounds(st(g,name))[g.entry][1],T)
                    self.assertLessEqual(float(s.point[g.entry]),float(T))
                    self.assertTrue(s.rankable,str(s.feasibility))
                    at=dict(p);at.update(s.point)
                    roles=g.roles(st(g,name));stocks=g.stocks(st(g,name));shares=g.shares(st(g,name))
                    for player in [g.focal,g.rival]:
                        pioneer=player==roles.pioneer
                        segs=g.lifecycle.segments(g.time,entry=0 if pioneer else g.entry,
                            rivals_entry=g.entry if pioneer else 0,share=shares[player],stock=stocks[player],is_pioneer=pioneer)
                        for seg in segs:self.assertLessEqual(float(sp.sympify(seg.lo).subs(at)),float(sp.sympify(seg.hi).subs(at)))

    def test_two_phase_nonunit_horizon_respects_analytic_integral(self):
        for T,growth in [(sp.Rational(1,2),.3),(sp.Integer(1),.3),(sp.Integer(4),3)]:
            g=pg.models.preannounce_entry(entry_floor=True);g.lifecycle.horizon=T
            p=dict(P,hatvarsigma=growth,**{'lambda':growth})
            s=pg.solve(g,st(g,'DF'),g.numeric(p));at=g.numeric(p);at.update(s.point)
            expected=.1*(growth**2/2+growth*(float(T)-growth))/4
            with self.subTest(T=T):
                self.assertTrue(s.rankable,str(s.feasibility))
                self.assertAlmostEqual(s.payoffs['x'],expected,places=12)
                self.assertGreaterEqual(float(g.demand_ceiling(st(g,'DF'),at).subs(at))+1e-12,expected)

    def test_timing_cost_stays_nonnegative_over_general_horizon(self):
        g=pg.models.preannounce_entry(timing_cost=True);g.lifecycle.horizon=sp.Integer(4)
        p=g.numeric(dict(P,hatvarsigma=3,kappa_t=.2))
        for name in ['DF','DL']:
            for entry in [0,1,3]:
                at=dict(p);at[g.entry]=entry
                for cost in g.costs(st(g,name)).values():self.assertGreaterEqual(float(cost.subs(at)),0)

    def test_chosen_signal_bound_is_preserved_when_capacity_contract_changes(self):
        g=repaired(signal_ceiling=True);p=g.numeric(dict(P,kappa_d=.05))
        self.assertAlmostEqual(float(g.signal_ceiling.subs(p)),.1)
        s=pg.solve(g,st(g,'RL'),p);self.assertAlmostEqual(s.payoffs['x'],.005,places=12)

    def test_missing_bounds_are_incomplete_not_in_range(self):
        x,b=sp.symbols('x b')
        r=check_point(1-x*x,{x:0},{x:(b,b+1)},{},gross=1-x*x)
        self.assertTrue(r.ok);self.assertFalse(r.complete)
        self.assertFalse(any(f.check=='bounds' and f.status=='ok' for f in r.findings))
        self.assertIn('INCOMPLETE',str(r))

    def test_missing_requested_ceiling_is_recorded_incomplete(self):
        x,u=sp.symbols('x u')
        r=check_point(1-x*x,{x:0},{x:(-1,1)},{},upper_bound=u,gross=1-x*x)
        self.assertFalse(r.complete);self.assertTrue(any(f.check=='payoff magnitude' and f.required for f in r.findings))

    def test_invalid_numeric_bounds_cannot_report_complete_feasibility(self):
        x=sp.Symbol('x')
        for lo,hi in [(sp.nan,1),(0,sp.I),(sp.oo,1),(2,1)]:
            with self.subTest(lo=lo,hi=hi):
                r=check_point(1-x*x,{x:0},{x:(lo,hi)},{},gross=1-x*x)
                self.assertFalse(r.ok and r.complete)

    def test_explicit_infinite_domain_is_not_unknown_bounds(self):
        x=sp.Symbol('x')
        r=check_point(1-x*x,{x:0},{x:(-sp.oo,sp.oo)},{},gross=1-x*x)
        self.assertTrue(r.ok and r.complete)

    def test_negative_net_with_omitted_gross_is_not_negative_demand(self):
        x=sp.Symbol('x')
        r=check_point(-1-x*x,{x:0},{x:(-1,1)},{})
        self.assertTrue(r.ok and r.complete)
        self.assertIn('sign test skipped',str(r))

    def test_negative_net_positive_gross_is_legal(self):
        x=sp.Symbol('x')
        self.assertTrue(check_point(-1-x*x,{x:0},{x:(-1,1)},{},gross=1-x*x).ok)

    def test_unknown_supplied_gross_makes_required_check_incomplete(self):
        x,u=sp.symbols('x u')
        r=check_point(1-x*x,{x:0},{x:(-1,1)},{},gross=u)
        self.assertFalse(r.complete)

    def test_zero_ceiling_violation_does_not_divide_by_zero(self):
        x=sp.Symbol('x')
        r=check_point(1-x*x,{x:0},{x:(-1,1)},{},upper_bound=0,gross=1-x*x)
        self.assertFalse(r.ok)

    def test_incomplete_required_checks_exclude_ranking_and_feasible_pass(self):
        g=pg.models.preannounce_entry();g.lifecycle.capacity=lambda:sp.Symbol('missing_capacity')
        s=pg.solve(g,st(g,'DL'),g.numeric(P));self.assertFalse(s.rankable)
        r=verify.check(g,[verify.Feasible(('DL',))],over={},fixed=P)
        self.assertEqual(r.results[0].skipped,1);self.assertFalse(r.results[0].holds)

    def test_interior_skips_unresolved_parent(self):
        b=pg.models.preannounce_entry();e,d=b.entry,b.signal
        class Open(pg.Game):
            def payoffs(self,s):return {'x':sp.log(1+d)/1000,'y':-(e-sp.Rational(3,20))**2}
        g=Open(b.lifecycle,b.share_rule,e,d,strategies=(st(b,'RF'),))
        r=verify.check(g,[verify.Interior('varsigma',strategy='RF')],over={},fixed=P)
        self.assertEqual(r.results[0].skipped,1);self.assertFalse(r.complete)

    def test_interior_skips_invalid_parent(self):
        b=pg.models.preannounce_entry();e,d=b.entry,b.signal
        class Invalid(pg.Game):
            def payoffs(self,s):return {'x':.001-(e-.15)**2,'y':.001-(e-.15)**2}
            def gross_payoffs(self,s):return {'x':sp.Integer(-1),'y':sp.Integer(-1)}
        g=Invalid(b.lifecycle,b.share_rule,e,d,strategies=(st(b,'DL'),))
        r=verify.check(g,[verify.Interior('varsigma',strategy='DL')],over={},fixed=P)
        self.assertEqual(r.results[0].skipped,1)

    def test_interior_passes_resolved_valid_candidate(self):
        g=repaired();r=verify.check(g,[verify.Interior('delta')],over={},fixed=dict(P,kappa_d=.05))
        self.assertTrue(r.results[0].holds);self.assertTrue(r.complete)

if __name__=='__main__':unittest.main()
