"""Export version-bound numerical evidence and independent quadrature."""
from __future__ import annotations
import json
import math
import os
import platform
import sys
try:
 import pacegame as pg
except ImportError:
 sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
 import pacegame as pg
import sympy as sp
import mpmath as mp
from pacegame.analyze import rank_strategies,verify
from pacegame.models.preannounce_entry import BASELINE,REPAIRED
from pacegame.examples.audit_preannouncement import configurations,claims

def pack_sol(sol):
 return {'point':{str(k):float(v) for k,v in sol.point.items()},
         'kind':{str(k):v for k,v in sol.kind.items()},'payoffs':sol.payoffs,
         'rankable':sol.rankable,'unresolved':sol.unresolved,
         'feasibility_complete':sol.feasibility.complete,
         'findings':[{'check':f.check,'status':f.status,'detail':f.detail,
                      'required':f.required,'verdict':f.verdict}
                     for f in sol.feasibility.findings]}
def quadrature(g,s,params,sol):
 at=g.numeric(params);at.update(sol.point)
 roles=g.roles(s);stocks=g.stocks(s);shares=g.shares(s)
 mp.mp.dps=40
 result={}
 for player in (g.focal,g.rival):
  pioneer=player==roles.pioneer
  segs=g.lifecycle.segments(g.time,entry=sp.Integer(0) if pioneer else g.entry,
      rivals_entry=g.entry if pioneer else sp.Integer(0),share=shares[player],
      stock=stocks[player],is_pioneer=pioneer)
  val=mp.mpf('0')
  for seg in segs:
   lo,hi=float(seg.lo.subs(at)),float(seg.hi.subs(at))
   assert lo<=hi
   if hi>lo:
    fn=sp.lambdify(g.time,seg.expr.subs(at),'mpmath')
    val+=mp.quad(fn,[lo,hi])/4
  val-=mp.mpf(str(float(g.costs(s)[player].subs(at))))
  result[player]={'quadrature':float(val),'solver':sol.payoffs[player],
                  'absolute_error':abs(float(val)-sol.payoffs[player])}
 return result

def main(outdir='validation'):
 os.makedirs(outdir,exist_ok=True)
 rec={'software_version':pg.__version__,'python':sys.version,'platform':platform.platform(),
      'sympy':sp.__version__,'cases':[],'quadrature':[]}
 for label,g,point in configurations():
  out=rank_strategies(g,point)
  report=verify.check(g,claims(),over={'sigma':(.05,.4),'phi':(.3,.95)},n=3,
        fixed={k:v for k,v in point.items() if k not in ('sigma','phi')})
  rec['cases'].append({'label':label,'parameters':point,'best':out.best,
     'complete':out.complete,'excluded':out.excluded,
     'solutions':{n:pack_sol(s) for n,s in out.solutions.items()},
     'claims':[{'claim':r.claim,'passed':r.passed,'failed':r.failed,'skipped':r.skipped,
                'errors':r.errors,'counterexamples':r.counterexamples,'reasons':r.reasons}
               for r in report.results]})
 # Numerical quadrature integrates segment functions at fixed points directly.
 cases=configurations()[1:]+[('logistic',pg.models.logistic_entry(),pg.models.LOGISTIC_POINT),
               ('asymmetric',pg.models.asymmetric_quality(omega=2),pg.models.ASYMMETRIC_POINT)]
 for label,g,point in cases:
  for s in g.strategies:
   sol=pg.solve(g,s,g.numeric(point))
   q=quadrature(g,s,point,sol)
   if any(r['absolute_error']>1e-10 for r in q.values()): raise AssertionError(q)
   rec['quadrature'].append({'model':label,'strategy':s.name,'players':q})
 g=pg.models.preannounce_entry();s=next(s for s in g.strategies if s.name=='RL')
 expr=g.payoffs(s)['x'].subs(g.numeric({'sigma':.1,'phi':.85,'hatvarsigma':.3})).subs(g.entry,0)
 rec['finite_asymptote']={'slice':'baseline RL, entry=0, sigma=.1 phi=.85 growth=.3',
    'expression':str(expr),'limit':float(sp.limit(expr,g.signal,sp.oo)),
    'warning':'conditional slice; solver finite-cap status is unresolved'}
 # Analytic sequential toy with an independently derived follower response.
 base=pg.models.preannounce_entry();d,e=base.signal,base.entry
 class Toy(pg.Game):
  def payoffs(self,strategy): return {'x':d-e-d*d/2,'y':-(e-d/2)**2}
  def bounds(self,strategy): return {d:(0,2),e:(0,1)}
 toy=Toy(base.lifecycle,base.share_rule,e,d)
 sol=pg.solve(toy,next(s for s in toy.strategies if s.name=='RF'),toy.numeric({'sigma':10,'phi':.85,'hatvarsigma':1}))
 err=max(abs(float(sol.point[d])-.5),abs(float(sol.point[e])-.25))
 if err>1e-6 or abs(sol.payoffs['x']-.125)>1e-8: raise AssertionError(sol)
 rec['analytic_sequential_toy']={'reference':{'delta':.5,'varsigma':.25,'pi_x':.125},'computed':pack_sol(sol),'decision_max_error':err}
 target=os.path.join(outdir,'release_validation.json')
 with open(target,'w',encoding='utf-8') as f: json.dump(rec,f,indent=2,allow_nan=False)
 print(target)
 return 0
if __name__=='__main__': raise SystemExit(main(sys.argv[1] if len(sys.argv)>1 else 'validation'))
