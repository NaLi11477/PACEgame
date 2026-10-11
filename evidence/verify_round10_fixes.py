"""Independent public-interface acceptance of the tenth-audit revision.

Analytic oracles do not call PACEgame's retained-number helpers.
Run with --source-root PATH, or from an interpreter with the wheel installed.
"""
from pathlib import Path
import argparse, json, platform, sys
ap=argparse.ArgumentParser()
ap.add_argument('--source-root',type=Path)
ap.add_argument('--out',type=Path,required=True)
a=ap.parse_args()
if a.source_root:sys.path.insert(0,str(a.source_root.resolve()))
import sympy as sp
import pacegame as pg
from pacegame.solve.feasible import check_point
from pacegame.analyze import rank_strategies,verify
U,V=sp.symbols('r10_u r10_v',real=True)
POINT={'sigma':.1,'phi':.85,'hatvarsigma':.3}
def report(r):return {'ok':r.ok,'complete':r.complete,'findings':[vars(f) for f in r.findings]}
def counts(r):return [{'claim':x.claim,'passed':x.passed,'failed':x.failed,'skipped':x.skipped,'errors':x.errors} for x in r.results]
class CeilingInjection(pg.Game):
    amount=sp.Integer(0);limit=sp.Integer(0)
    def payoffs(self,st):return {self.focal:self.amount,self.rival:sp.Integer(0)}
    def gross_payoffs(self,st):return self.payoffs(st)
    def costs(self,st):return {self.focal:sp.Integer(0),self.rival:sp.Integer(0)}
    def decision_order(self,st):return [(self.focal,[self.entry,self.signal])]
    def bounds(self,st):return {self.entry:(0,0),self.signal:(0,0)}
    def demand_ceiling(self,st,at=None):return self.limit
    def ceiling_is_endogenous(self,st):return False
    def share_sensitivity(self,st,p):return sp.Integer(0)
def injection(amount,limit):
    b=pg.models.preannounce_entry()
    d={k:v for k,v in vars(b).items() if not k.startswith('_')}
    d.update(entry=U,signal=V,strategies=(b.strategies[1],))
    g=CeilingInjection(**d);g.amount=amount;g.limit=limit;return g
def magnitude(amount,limit):
    amount,limit=sp.sympify(amount),sp.sympify(limit)
    gap=amount-limit;tol=sp.Rational(1,10**9)
    expected=bool(gap>tol)
    low=check_point(amount,{U:0},{U:(0,0)},{},gross=amount,upper_bound=limit)
    g=injection(amount,limit);o=rank_strategies(g,POINT)
    r=verify.check(g,[verify.Feasible(),verify.Bounded('RL')],over={},n=1,fixed=POINT)
    c=counts(r)
    return {'amount':str(amount),'limit':str(limit),'exact_excess':str(gap),
      'must_violate_at_default_absolute_tol':expected,'low_level':report(low),
      'ranking':{'best':o.best,'complete':o.complete,'payoffs':o.payoffs},
      'claims':c,'confirmed_false_pass':expected and low.ok and low.complete and o.complete and all(x['passed']==1 for x in c)}
big_cases=[magnitude(sp.Integer(A)+delta,sp.Integer(A)) for A,delta in [(2**53,1),(2**60,128),(10**20,4096)]]
controls=[magnitude(2**40+1,2**40),magnitude(2**60+256,2**60),magnitude(2**60,2**60),magnitude(2**60-256,2**60)]
assert all(not x['confirmed_false_pass'] and not x['low_level']['ok'] and x['low_level']['complete'] and x['ranking']['best'] is None and not x['ranking']['complete'] and x['claims'][0]['failed']==1 and x['claims'][1]['skipped']==1 and all(c['passed']==0 and c['errors']==0 for c in x['claims']) for x in big_cases)
assert not controls[0]['low_level']['ok'] and not controls[1]['low_level']['ok']
assert controls[2]['low_level']['ok'] and controls[3]['low_level']['ok']
negative=-sp.Rational(1,10**400)
def negative_parameter(field,value):
    g=pg.models.preannounce_entry(**{field:True})
    p=dict(POINT,**{'kappa_d' if field=='signal_cost' else 'kappa_t':value})
    key='kappa_d' if field=='signal_cost' else 'kappa_t'
    try:
        subs=g.numeric(p)
        st=next(st for st in g.strategies if st.name=='DF')
        o=rank_strategies(g,p,[st])
        return {'field':field,'input':str(value),'exact_input_negative':bool(value<0),
          'stored_parameter':str(subs[g.parameters()[key]]),'stored_is_negative':subs[g.parameters()[key]].is_negative,
          'binary64_value':float(subs[g.parameters()[key]]),'rejected':False,
          'rank_best':o.best,'ranking_complete':o.complete,'payoffs':o.payoffs}
    except Exception as e:return {'field':field,'input':str(value),'rejected':True,'exception':type(e).__name__,'reason':str(e)}
bad_params=[negative_parameter(f,negative) for f in ('signal_cost','timing_cost')]
parameter_controls=[negative_parameter(f,v) for f in ('signal_cost','timing_cost') for v in (-sp.Rational(1,10**6),sp.Integer(0),sp.Rational(1,10**6))]
assert all(x['rejected'] and x['exception']=='ValueError' and 'nonnegative' in x['reason'] for x in bad_params)
assert all(x['rejected'] for x in parameter_controls if sp.sympify(x['input'])<0)
assert all(not x['rejected'] for x in parameter_controls if sp.sympify(x['input'])>=0)
mutations=[]
for field in ('signal_cost','timing_cost','phi_coefficient'):
    g=pg.models.preannounce_entry()
    if field=='phi_coefficient':g.share_rule.phi=negative
    else:setattr(g,field,negative)
    try:
        g.numeric(POINT);st=next(s for s in g.strategies if s.name=='DF')
        o=rank_strategies(g,POINT,[st]);mutations.append({'field':field,'rejected':False,'ranking_complete':o.complete})
    except Exception as e:mutations.append({'field':field,'rejected':True,'reason':str(e)})
assert all(x['rejected'] and 'nonnegative' in x['reason'] for x in mutations)
r={'version':pg.__version__,'environment':{'python':sys.version,'sympy':sp.__version__,'platform':platform.platform(),'import_path':pg.__file__},
 'production_files_modified':False,'findings':{'R10-01':{'priority':'P2','accepted':True,'scope':'deliberately injected over-ceiling output; diagnostic guard must reject','cases':big_cases,'controls':controls},
 'R10-02':{'priority':'P2','accepted':True,'scope':'strict nonnegative input contract; no sign tolerance declared','negative_parameters':bad_params,'normal_sign_controls':parameter_controls,'mutations':mutations}},
 'all_revision_criteria_passed':True,'independent_reaudit':'pending'}
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,ensure_ascii=False,indent=2,allow_nan=False))
print('PACEgame',pg.__version__,'R10-01 and R10-02 revision criteria passed',flush=True)
raise SystemExit(0)
