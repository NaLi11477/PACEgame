"""Adversarial regressions for previously passing but incorrect outcomes."""
import importlib
import importlib.util
import math
import os
import subprocess
import sys
import unittest
from dataclasses import replace
import sympy as sp
import pacegame as pg
from pacegame.analyze import rank_strategies,sweep,threshold,derivative,verify
from pacegame.solve.feasible import check_point

P={'sigma':.1,'phi':.85,'hatvarsigma':.3}
def st(g,name): return next(s for s in g.strategies if s.name==name)
class Tests(unittest.TestCase):
 def test_finite_asymptote_is_not_infinite_payoff(self):
  g=pg.models.preannounce_entry();s=pg.solve(g,st(g,'RL'),g.numeric(P))
  self.assertFalse(s.unbounded);self.assertTrue(s.unresolved)
  e=g.payoffs(st(g,'RL'))['x'].subs(g.numeric(P)).subs(g.entry,0)
  self.assertAlmostEqual(float(sp.limit(e,g.signal,sp.oo)),.006375,places=12)
 def test_unresolved_candidates_are_excluded(self):
  g=pg.models.preannounce_entry();o=rank_strategies(g,P)
  self.assertEqual(o.excluded,['RF','RL']);self.assertFalse(o.complete)
  self.assertEqual(o.ties(),['DF','DL'])
 def test_all_unresolved_has_no_best(self):
  g=pg.models.preannounce_entry();g.strategies=tuple(s for s in g.strategies if s.signals)
  self.assertIsNone(rank_strategies(g,P).best)
 def test_broken_feasibility_cannot_pass(self):
  g=pg.models.preannounce_entry()
  class Broken(pg.Game):
   def payoffs(self,strategy): raise RuntimeError('intentional failure')
  b=Broken(g.lifecycle,g.share_rule,g.entry,g.signal)
  r=verify.check(b,[verify.Feasible()],over={},fixed=P)
  self.assertFalse(r.ok);self.assertEqual(r.results[0].errors,1)
  self.assertIn('intentional failure',str(r))
 def test_unknown_strategy_is_an_error(self):
  g=pg.models.preannounce_entry()
  r=verify.check(g,[verify.Feasible(('TYPO',))],over={},fixed=P)
  self.assertFalse(r.ok);self.assertEqual(r.results[0].errors,1)
 def test_nonfinite_parameters_rejected(self):
  g=pg.models.preannounce_entry()
  for v in [float('nan'),float('inf'),-float('inf')]:
   with self.subTest(v=v),self.assertRaises(ValueError): g.numeric(dict(P,sigma=v))
 def test_negative_parameters_rejected(self):
  g=pg.models.preannounce_entry(signal_cost=True)
  with self.assertRaises(ValueError): g.numeric(dict(P,kappa_d=-.1))
 def test_invalid_lifecycle_rejected(self):
  g=pg.models.preannounce_entry()
  with self.assertRaises(ValueError): g.numeric(dict(P,hatvarsigma=1.2))
 def test_invalid_entry_floor_rejected(self):
  g=pg.models.preannounce_entry(entry_floor=True)
  with self.assertRaises(ValueError): g.numeric(dict(P,**{'lambda':.4}))
 def test_unadmitted_strategy_rejected(self):
  g=pg.models.logistic_entry()
  with self.assertRaises(ValueError): pg.solve(g,pg.STANDARD_STRATEGIES[0],g.numeric(pg.models.LOGISTIC_POINT))
 def test_invalid_method_and_cap_rejected(self):
  g=pg.models.preannounce_entry()
  for kwargs in ({'method':'typo'},{'signal_cap':float('nan')},{'signal_cap':0}):
   with self.subTest(kwargs=kwargs),self.assertRaises(ValueError): pg.solve(g,st(g,'DL'),g.numeric(P),**kwargs)
 def test_unknown_sweep_is_refused(self):
  with self.assertRaises(ValueError): sweep(pg.models.preannounce_entry(),'TYPO',[.1,.2],P)
 def test_grid_must_have_coverage(self):
  for n in (0,-1,1.5):
   with self.assertRaises(ValueError): verify.grid({'x':(0,1)},n)
  with self.assertRaises(ValueError): verify.grid({'x':[]})
 def test_unknown_grid_parameter_is_refused(self):
  with self.assertRaises(ValueError): verify.check(pg.models.preannounce_entry(),[verify.Feasible()],over={'TYPO':(0,1)},fixed=P)
 def test_empty_claim_list_refused(self):
  with self.assertRaises(ValueError): verify.check(pg.models.preannounce_entry(),[],over={},fixed=P)
 def test_nan_bound_is_refused(self):
  g=pg.models.preannounce_entry();g.entry_floor=sp.nan
  with self.assertRaises(ValueError): g.numeric(P)
 def test_first_order_condition_is_checked_inside(self):
  x=sp.Symbol('x');r=check_point(-x*x,{x:.5},{x:(-1,1)},{},kinds={x:'interior'})
  self.assertTrue(any(f.check=='stationarity' and f.status=='violation' for f in r.findings))
 def test_joint_saddle_is_detected(self):
  from unittest.mock import patch
  eng=importlib.import_module('pacegame.solve.engine')
  g=pg.models.preannounce_entry();d,e=g.signal,g.entry
  class Saddle(pg.Game):
   def payoffs(self,strategy): return {'x':-d*d-e*e+3*d*e,'y':sp.Integer(0)}
   def bounds(self,strategy): return {d:(-1,1),e:(-1,1)}
  g=Saddle(g.lifecycle,g.share_rule,e,d)
  # Force the erroneous stationary candidate through the public solver and
  # require the combined Hessian diagnostic, not only its diagonal entries.
  with patch.object(eng,'_max_nd',return_value=({d:0,e:0},0)):
   sol=pg.solve(g,st(g,'RL'),g.numeric(P))
  self.assertTrue(any(f.check=='joint curvature' and f.status=='violation'
                      for f in sol.feasibility.findings))
 def test_time_symbol_invalidates_cached_payoffs(self):
  g=pg.models.preannounce_entry();a=g._fingerprint();g.time=sp.Symbol('other_t')
  self.assertNotEqual(a,g._fingerprint())
 def test_one_quality_is_not_symmetric(self):
  self.assertFalse(pg.Proportional(sp.Symbol('phi'),quality={'x':2}).is_symmetric())
 def test_matching_signal_is_not_symmetric_decision_rights(self):
  g=pg.models.preannounce_entry(rival_signals=True,signal_cost=True)
  self.assertFalse(g.players_alike(st(g,'RL')))
 def test_sign_zero_parameter_uses_feasible_stencil(self):
  g=pg.models.preannounce_entry(timing_cost=True)
  r=derivative(g,'DL','kappa_t',dict(P,kappa_t=0))
  self.assertEqual(r.stencil,'forward');self.assertTrue(math.isfinite(r.slope))
 def test_flat_optimal_signal_does_not_become_a_noise_slope(self):
  g=pg.models.preannounce_entry(keep_stock=True,signal_accrues=True,signal_cost=True,entry_floor=True)
  p=dict(P,kappa_d=.05,**{'lambda':.1})
  r=derivative(g,'RL','sigma',p,quantity='delta')
  self.assertEqual(r.sign,'0')
  self.assertLess(abs(r.slope),1e-10)
 def test_sign_relation_typo_is_refused(self):
  with self.assertRaises(ValueError): verify.Sign('d pi_x / d sigma','TYPO')
 def test_skips_do_not_establish_a_whole_grid_claim(self):
  r=verify.Result('partial',passed=1,skipped=1)
  self.assertFalse(r.holds);self.assertFalse(verify.Report([r],2).complete)
 def test_benchmark_failure_cannot_be_a_timing_result(self):
  spec=importlib.util.spec_from_file_location('bench',os.path.join(os.path.dirname(pg.__file__),'examples','benchmark.py'))
  bench=importlib.util.module_from_spec(spec);spec.loader.exec_module(bench)
  with self.assertRaises(RuntimeError): bench.measure([sys.executable,'-c','raise SystemExit(7)'],1,1)
 def test_cli_unknown_set_is_refused(self):
  from pacegame.cli import main
  self.assertEqual(main(['solve','preannounce_entry','--set','typo=1']),2)
 def test_cli_zero_points_is_refused(self):
  from pacegame.cli import main
  self.assertEqual(main(['verify','preannounce_entry','--points','0']),2)
 def test_open_threshold_cannot_use_cap_payoffs(self):
  g=pg.models.preannounce_entry()
  with self.assertRaises(ValueError): threshold(g,'sigma',.05,.2,P,'RL','RF',scan=2)
 def test_evaluator_retries_exact_after_local_failure(self):
  eng=importlib.import_module('pacegame.solve.engine');x=sp.Symbol('x')
  ev=eng._Evaluator(1/x,[x]);self.assertIsNone(ev(0));self.assertAlmostEqual(ev(1),1)
if __name__=='__main__': unittest.main()
