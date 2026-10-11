"""Independent public-interface acceptance for the eleventh-audit revision of PACEgame.

No production file is changed; rational arithmetic supplies the analytic oracles.
"""
from pathlib import Path
from dataclasses import fields
import argparse,json,sys,platform
ap=argparse.ArgumentParser();ap.add_argument('outdir',nargs='?',default='validation');a=ap.parse_args();a.source_root=None;a.expect_parent_defects=False;a.out=Path(a.outdir)/'audit_0210_acceptance.json'
if a.source_root:sys.path.insert(0,str(a.source_root.resolve()))
import sympy as sp
import pacegame as pg
from pacegame.solve.feasible import check_point
from pacegame.analyze import rank_strategies,verify
POINT={'sigma':.1,'phi':.85,'hatvarsigma':.3}
U=sp.Symbol('audit11_u',real=True); EPS=sp.Rational(1,10**20);TINY=sp.Rational(1,10**400)
def retained(x):
    x=sp.sympify(x)
    return x.xreplace({f:sp.Rational(f) for f in x.atoms(sp.Float)})
def low_report(r):return {'ok':r.ok,'complete':r.complete,'findings':[vars(f) for f in r.findings]}
def claims(r):return [{'claim':x.claim,'passed':x.passed,'failed':x.failed,'skipped':x.skipped,'errors':x.errors} for x in r.results]
class DomainGame(pg.Game):
    domain=(0,1)
    def payoffs(self,st):return {self.focal:-self.signal,self.rival:sp.Integer(0)}
    def gross_payoffs(self,st):return {self.focal:sp.Integer(1),self.rival:sp.Integer(0)}
    def costs(self,st):return {self.focal:1+self.signal,self.rival:sp.Integer(0)}
    def decision_order(self,st):return [(self.focal,[self.signal])]
    def bounds(self,st):return {self.signal:self.domain}
    def demand_ceiling(self,st,at=None):return sp.Integer(2)
    def ceiling_is_endogenous(self,st):return False
    def share_sensitivity(self,st,p):return sp.Integer(0)
def fixture(domain):
    base=pg.models.preannounce_entry()
    data={f.name:getattr(base,f.name) for f in fields(pg.Game) if f.init}
    data.update(signal=U,strategies=(base.strategies[1],))
    g=DomainGame(**data);g.domain=domain;return g
def domain_case(lo,hi):
    lo,hi=sp.sympify(lo),sp.sympify(hi);gap=retained(hi)-retained(lo)
    row={'lo':str(lo),'hi':str(hi),'exact_width':str(gap),'exact_relation':'reversed' if gap<0 else ('fixed' if gap==0 else 'nonzero'),
         'binary64_endpoints_equal':float(lo)==float(hi),'pre_retention_subtraction':str(hi-lo)}
    row['low']=low_report(check_point(-U,{U:lo},{U:(lo,hi)},{},gross=1,upper_bound=2))
    g=fixture((lo,hi))
    try:
        s=pg.solve(g,g.strategies[0],g.numeric(POINT))
        row['solve']={'rejected':False,'rankable':s.rankable,'point':{str(k):str(v) for k,v in s.point.items()},'kind':{str(k):v for k,v in s.kind.items()},'payoffs':s.payoffs,'feasibility':low_report(s.feasibility)}
    except Exception as e:row['solve']={'rejected':True,'exception':type(e).__name__,'reason':str(e)}
    try:
        o=rank_strategies(g,POINT);row['ranking']={'rejected':False,'best':o.best,'complete':o.complete,'excluded':o.excluded}
    except Exception as e:row['ranking']={'rejected':True,'exception':type(e).__name__,'reason':str(e)}
    row['claims']=claims(verify.check(g,[verify.Feasible(),verify.Bounded('RL')],over={},fixed=POINT))
    row['confirmed_false_fixed_pass']=gap!=0 and row['low']['ok'] and row['low']['complete'] and row['solve'].get('rankable') is True and row['ranking'].get('complete') is True and all(x['passed']==1 for x in row['claims'])
    return row
cases=[domain_case(sp.Float(1.),1+EPS),domain_case(sp.Float(1.),1-EPS),domain_case(sp.Float(.1),sp.Rational(1,10)+EPS)]
controls=[domain_case(1,1+EPS),domain_case(1,1-EPS),domain_case(sp.Float(1.),1),domain_case(sp.Float(1.),sp.Rational(11,10))]
if a.expect_parent_defects:
    assert all(x['confirmed_false_fixed_pass'] for x in cases)
else:
    assert not any(x['confirmed_false_fixed_pass'] for x in cases)
    assert not cases[0]['low']['complete'] and cases[0]['solve']['exception']=='BoundsPrecisionError'
    assert all(not x['low']['ok'] and x['solve']['exception']=='ValueError' for x in cases[1:])
    assert all(x['ranking']['rejected'] and all(c['passed']==0 and c['errors']==1 for c in x['claims']) for x in cases)
assert controls[0]['solve']['exception']=='BoundsPrecisionError' and not controls[0]['low']['complete']
assert controls[1]['solve']['rejected'] and not controls[1]['low']['ok']
assert all(x['solve']['rankable'] and x['ranking']['complete'] for x in controls[2:])
def tolerance_case(tol,payoff=0,ceiling=0):
    row={'tol':str(tol),'exact_tol_negative':bool(tol<0),'payoff':str(payoff),'ceiling':str(ceiling)}
    try:
        r=check_point(payoff,{U:0},{U:(0,0)},{},gross=sp.Abs(payoff),upper_bound=ceiling,tol=tol)
        row.update(rejected=False,report=low_report(r))
    except Exception as e:row.update(rejected=True,exception=type(e).__name__,reason=str(e))
    return row
tolerances=[tolerance_case(-TINY),tolerance_case(TINY,TINY/2),tolerance_case(-sp.Rational(1,10**12)),tolerance_case(0),tolerance_case(sp.Rational(1,10**9),sp.Rational(1,2*10**9)),tolerance_case(sp.Rational(1,10**9),sp.Rational(2,10**9))]
if a.expect_parent_defects:
    assert not tolerances[0]['rejected'] and tolerances[0]['report']['ok'] and tolerances[0]['report']['complete']
    assert not tolerances[1]['rejected'] and not tolerances[1]['report']['ok'] and tolerances[1]['report']['complete']
else:
    assert tolerances[0]['rejected'] and 'nonnegative' in tolerances[0]['reason']
    assert tolerances[1]['rejected'] and 'binary64 range' in tolerances[1]['reason']
assert tolerances[2]['rejected'] and tolerances[2]['exception']=='ValueError'
assert tolerances[3]['report']['ok'] and tolerances[4]['report']['ok'] and not tolerances[5]['report']['ok']
def complex_case(imag):
    payoff=1+sp.I*imag
    r=check_point(payoff,{U:0},{U:(0,0)},{},gross=payoff)
    r_ceiling=check_point(payoff,{U:0},{U:(0,0)},{},gross=payoff,upper_bound=2)
    return {'imaginary_part':str(imag),'exact_payoff_is_real':payoff.is_real,'no_ceiling':low_report(r),'with_finite_ceiling':low_report(r_ceiling)}
complex_cases=[complex_case(TINY),complex_case(sp.Rational(1,10**10)),complex_case(sp.Rational(1,10**6)),complex_case(0)]
if a.expect_parent_defects:
    assert all(x['exact_payoff_is_real'] is False and x['no_ceiling']['ok'] and x['no_ceiling']['complete'] and not x['with_finite_ceiling']['complete'] for x in complex_cases[:2])
else:
    assert all(x['exact_payoff_is_real'] is False and not x['no_ceiling']['ok'] and not x['with_finite_ceiling']['ok'] for x in complex_cases[:3])
assert not complex_cases[2]['no_ceiling']['ok'] and complex_cases[3]['no_ceiling']['ok']
# The main solver has an additional symbolic-evaluation guard: do not overstate scope.
class ComplexGame(DomainGame):
    def payoffs(self,st):return {self.focal:1+sp.I*TINY,self.rival:sp.Integer(0)}
g=fixture((0,0));g.__class__=ComplexGame
s=pg.solve(g,g.strategies[0],g.numeric(POINT))
assert not s.rankable
complex_solver={'rankable':s.rankable,'feasibility':low_report(s.feasibility)}

# Additional independent guards and lawful controls.
gross_only=[]
for imag in (TINY,sp.Rational(1,10**10)):
    for ceiling in (None,2):
        r=check_point(1,{U:0},{U:(0,0)},{},gross=1+sp.I*imag,upper_bound=ceiling)
        gross_only.append({'imaginary_part':str(imag),'ceiling':ceiling,'report':low_report(r)})
        if not a.expect_parent_defects:assert not r.ok
unknown=[]
for target,extra in [(sp.Symbol('unresolved_net',real=True),{'gross':1}),
                     (1,{'gross':sp.Symbol('unresolved_gross',real=True)})]:
    r=check_point(target,{U:0},{U:(0,0)},{},**extra)
    if not a.expect_parent_defects:assert not r.complete
    unknown.append(low_report(r))
negative_net=[]
for gross in (None,1):
    r=check_point(-1,{U:0},{U:(0,0)},{},gross=gross)
    assert r.ok and r.complete
    negative_net.append(low_report(r))
representable=domain_case(sp.Float(1.),1+sp.Rational(1,2**40))
assert representable['solve']['rankable'] and representable['ranking']['complete']
rounding_controls=[tolerance_case(sp.Rational(1,10),sp.Rational(1,10)),
                   tolerance_case(sp.Rational(1,10),sp.Rational(1,10)+EPS)]
if not a.expect_parent_defects:
    assert rounding_controls[0]['report']['ok'] and not rounding_controls[1]['report']['ok']
accepted=not a.expect_parent_defects
findings={'R11-01':{'priority':'P2','accepted':accepted,'cases':cases,'controls':controls,
                    'representable_narrow_control':representable,
                    'policy':'Retain both endpoints before subtraction; reject reversed and unavailable domains before ranking; verification records computation errors, never passes.'},
          'R11-02':{'priority':'P2','accepted':accepted,'cases':tolerances,'original_rational_tolerance_controls':rounding_controls,
                    'policy':'Retained finite-real/sign admission before conversion; explicit nonzero binary64 underflow/overflow rejection; retain admitted absolute thresholds.'},
          'R11-03':{'priority':'P2','accepted':accepted,'cases':complex_cases,'gross_only':gross_only,
                    'unknown_admission_controls':unknown,'legal_negative_net_controls':negative_net,
                    'main_solver_control':complex_solver,
                    'policy':'Strict retained finite-real admission for net, supplied gross and realised payoffs; unknown is required unavailable; optional absent gross and negative net remain lawful.'}}
record={'version':pg.__version__,'audit_round':11,'environment':{'python':sys.version,'sympy':sp.__version__,'platform':platform.platform(),'package_path':pg.__file__},
        'production_files_modified':False,'expected_parent_defects':a.expect_parent_defects,
        'groups':findings,'all_accepted':accepted,'all_revision_criteria_passed':accepted,
        'parent_defects_observed':a.expect_parent_defects,'independent_reaudit':'pending'}
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'version':pg.__version__,'all_revision_criteria_passed':accepted,'parent_defects_observed':a.expect_parent_defects},indent=2))
