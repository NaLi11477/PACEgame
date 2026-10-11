"""Regression tests for Round12 owner admission and retained payoff differences."""
import unittest
from unittest.mock import patch
import sympy as sp
import pacegame as pg
from pacegame.examples._audit_0211_fixtures import fixture,POINT,U
from pacegame.solve.feasible import check_point
from pacegame.analyze import rank_strategies,verify,threshold,statics
from pacegame.core.numeric import retained_difference,binary64_real
class Round12(unittest.TestCase):pass
def add(name,fn):setattr(Round12,'test_'+name,fn)
def owner_case(value,path):
    bounds={'fixed':(0,0),'interior':(-1,1),'lower':(0,1),'skipped':(0,1)}[path]
    main=-U**2 if path=='interior' else -U if path=='lower' else 0
    target=value+main
    return check_point(main,{U:0},{U:bounds},{},gross=1,upper_bound=2,payoff_for={U:target},skip_optimality={U} if path=='skipped' else set())
for label,value in [('tiny_complex',1+sp.I/sp.Integer(10)**400),('complex',1+sp.I/10),('nan',sp.nan),('infinity',sp.oo),('unknown',sp.Symbol('z',real=True))]:
 for path in ('fixed','interior','lower','skipped'):
  def run(self,value=value,path=path,label=label):
   r=owner_case(value,path);self.assertFalse(r.ok and r.complete)
   if label=='unknown':self.assertFalse(r.complete)
   fs=[f for f in r.findings if f.check==f'owner payoff ({U})'];self.assertTrue(fs)
   self.assertTrue(all(f.required for f in fs));self.assertEqual(fs[0].status,'warning' if label=='unknown' else 'violation')
   if label!='unknown':self.assertFalse(r.ok)
  add('owner_'+label+'_'+path,run)
for path in ('fixed','interior','lower','skipped'):
 def run(self,path=path):
  for val in (-1,2):
   r=owner_case(val,path);self.assertTrue(r.ok);self.assertTrue(r.complete)
 add('legal_owner_'+path,run)
for base in (2**53,2**60,10**20):
 for reverse in (False,True):
  def run(self,base=base,reverse=reverse):
   g=fixture(base);g.strategies=tuple(reversed(g.strategies)) if reverse else g.strategies
   o=rank_strategies(g,POINT);self.assertEqual(o.best,'RL');self.assertEqual(o.ties(),['RL']);self.assertTrue(o.complete)
   self.assertEqual(o.payoff_value('RL')-o.payoff_value('RF'),1)
   r=verify.check(g,[verify.Dominates('RL','RF'),verify.Dominates('RF','RL',strict=False)],over={},fixed=POINT)
   self.assertEqual((r.results[0].passed,r.results[1].failed),(1,1));self.assertFalse(r.results[1].holds)
  add(f'offset_{base}_{reverse}',run)
for base,gap in ((0,1),(2**40,1),(2**53,2)):
 def run(self,base=base,gap=gap):
  o=rank_strategies(fixture(base,gap),POINT);self.assertEqual(o.best,'RL');self.assertEqual(o.ties(),['RL'])
 add(f'representable_{base}_{gap}',run)
def crossing(self):
 g=fixture(2**53);g.gap=g.share_rule.phi-sp.Rational(1,2)
 self.assertEqual(threshold(g,'phi',.25,.75,{'sigma':.1,'hatvarsigma':.3},'RL','RF',scan=4),.5)
add('retained_crossing',crossing)
for target in ('payoff','rival','gap'):
 def run(self,target=target):
  g=fixture(2**53);g.gap=g.lifecycle.sigma
  strategy=('RL','RF') if target=='gap' else 'RL';quantity=f'pi_{g.rival}' if target=='rival' else 'payoff'
  r=statics.derivative(g,strategy,'sigma',POINT,quantity=quantity);self.assertAlmostEqual(r.slope,1,places=9);self.assertEqual(r.sign,'+')
 add('retained_slope_'+target,run)
def bound_candidates(self):
 g=fixture(2**53);g.gap=g.signal;g.bounds=lambda st:{g.signal:(1,1) if st.name=='RL' else (0,0)}
 o=rank_strategies(g,POINT);self.assertEqual(o.best,'RL');self.assertEqual(o.payoff_value('RL')-o.payoff_value('RF'),1)
add('bind_each_candidate',bound_candidates)
def moving_candidate(self):
 g=fixture(2**53);g.gap=g.signal;g.bounds=lambda st:{g.signal:(g.lifecycle.sigma,g.lifecycle.sigma) if st.name=='RL' else (0,0)}
 r=statics.derivative(g,'RL','sigma',POINT);self.assertAlmostEqual(r.slope,1,places=9)
add('bind_each_perturbed_parameter',moving_candidate)
def tolerance(self):
 for gap,strict_pass in ((sp.Rational(1,10**13),False),(sp.Rational(1,10**11),True)):
  g=fixture(2**53,gap);r=verify.check(g,[verify.Dominates('RL','RF')],over={},fixed=POINT)
  self.assertEqual(r.results[0].holds,strict_pass);self.assertEqual(rank_strategies(g,POINT).ties(),['RF','RL'])
add('absolute_tolerances_preserved',tolerance)
def unknown(self):
 o=rank_strategies(fixture(2**53),POINT);o.retained_payoffs['RL']=sp.Symbol('unknown',real=True)
 self.assertFalse(o.complete)
 with self.assertRaises(ValueError):_=o.best
 with self.assertRaises(ValueError):o.ties()
add('unknown_comparison_incomplete',unknown)
def claim_unavailable(self):
 g=fixture(2**53)
 with patch('pacegame.solve.engine.Solution.payoff_value',side_effect=ValueError('unavailable retained payoff')):
  r=verify.check(g,[verify.Dominates('RL','RF',strict=False)],over={},fixed=POINT)
 self.assertEqual(r.results[0].passed,0);self.assertEqual(r.results[0].skipped,1);self.assertFalse(r.results[0].holds)
add('unknown_weak_never_passes',claim_unavailable)
def range_policy(self):
 self.assertEqual(retained_difference(sp.Integer(10)**400+1,sp.Integer(10)**400),1)
 for x in (sp.Integer(10)**400,sp.Rational(1,10**400)):
  with self.assertRaises(ValueError):binary64_real(x)
add('result_range_unavailable',range_policy)
if __name__=='__main__':unittest.main()
