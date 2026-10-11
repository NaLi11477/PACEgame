"""Independent public-API audit; exit 1 means confirmed defects, not probe failure."""
from pathlib import Path
from dataclasses import fields
import argparse, json, platform, sys
ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path);ap.add_argument('--out',type=Path,required=True)
a=ap.parse_args()
if a.source_root:sys.path.insert(0,str(a.source_root.resolve()))
import sympy as sp
import pacegame as pg
from pacegame.solve.feasible import check_point
from pacegame.analyze import rank_strategies, verify, threshold, statics
U=sp.Symbol('audit12_u',real=True);Z=sp.Symbol('audit12_unresolved',real=True)
TINY=sp.Rational(1,10**400);POINT={'sigma':.1,'phi':.85,'hatvarsigma':.3}
def report(r):return {'ok':r.ok,'complete':r.complete,'findings':[vars(f) for f in r.findings]}
def claims(r):return [{'claim':x.claim,'passed':x.passed,'failed':x.failed,'skipped':x.skipped,'errors':x.errors,'reasons':x.reasons,'counterexamples':x.counterexamples} for x in r.results]
owned=[]
for label,value,known in [('tiny_complex',1+sp.I*TINY,True),('complex',1+sp.I/10,True),('nan',sp.nan,True),('infinity',sp.oo,True),('unknown',Z,False)]:
    for kind in ('fixed','interior','lower','skipped'):
        if kind=='fixed':target=value;payoff=0;bounds=(0,0);point=0;extra={}
        elif kind=='interior':target=value-U**2;payoff=-U**2;bounds=(-1,1);point=0;extra={}
        elif kind=='lower':target=value-U;payoff=-U;bounds=(0,1);point=0;extra={}
        else:target=value;payoff=0;bounds=(0,1);point=0;extra={'skip_optimality':{U}}
        r=check_point(payoff,{U:point},{U:bounds},{},gross=1,upper_bound=2,payoff_for={U:target},**extra)
        owned.append({'label':label,'kind':kind,'target_at_point':str(target.subs(U,point)), 'known_invalid':known,'report':report(r),'false_complete_pass':r.ok and r.complete})
# Finite real own-player objectives can differ from the focal objective.
controls=[]
for val in (sp.Integer(-1),sp.Integer(2)):
    r=check_point(-U**2,{U:0},{U:(-1,1)},{},payoff_for={U:val-U**2},gross=1)
    assert r.ok and r.complete;controls.append(report(r))
bad_net=check_point(1+sp.I*TINY,{U:0},{U:(0,0)},{},gross=1)
assert not bad_net.ok
assert all(x['false_complete_pass'] for x in owned if x['label'] in ('tiny_complex','complex','unknown'))
assert any(x['false_complete_pass'] for x in owned if x['label']=='nan')
assert any(x['false_complete_pass'] for x in owned if x['label']=='infinity')

class OffsetGame(pg.Game):
    base=sp.Integer(0);gap=sp.Integer(1);better='RL'
    def payoffs(self,st):return {self.focal:self.base+(self.gap if st.name==self.better else 0),self.rival:sp.Integer(0)}
    def gross_payoffs(self,st):return {self.focal:self.base+sp.Integer(4),self.rival:sp.Integer(0)}
    def costs(self,st):return {self.focal:self.base+4-self.payoffs(st)[self.focal],self.rival:sp.Integer(0)}
    def decision_order(self,st):return [(self.focal,[self.signal])]
    def bounds(self,st):return {self.signal:(0,0)}
    def demand_ceiling(self,st,at=None):return self.base+4
    def ceiling_is_endogenous(self,st):return False
    def share_sensitivity(self,st,p):return sp.Integer(0)
def fixture(base):
    b=pg.models.preannounce_entry();data={f.name:getattr(b,f.name) for f in fields(pg.Game) if f.init}
    data.update(signal=U,strategies=tuple(b.strategies[:2]));g=OffsetGame(**data);g.base=sp.Integer(base);return g
def gap_case(base,gap=1,reverse=False):
    g=fixture(base);g.gap=sp.Integer(gap)
    if reverse:g.strategies=tuple(reversed(g.strategies))
    o=rank_strategies(g,POINT);low='RF';high='RL'
    by_name={s.name:s for s in g.strategies}
    exact_gap=sp.simplify(g.payoffs(by_name[high])[g.focal]-g.payoffs(by_name[low])[g.focal])
    assert exact_gap==gap and exact_gap>sp.Rational(1,10**12)
    r=verify.check(g,[verify.Dominates(high,low),verify.Dominates(low,high,strict=False)],over={},fixed=POINT)
    return {'base':str(base),'exact_gap':str(exact_gap),'order':[s.name for s in g.strategies],
      'exact_payoffs':{s.name:str(g.payoffs(s)[g.focal]) for s in g.strategies},
      'binary64_payoffs':o.payoffs,'best':o.best,'ties':o.ties(),'complete':o.complete,'rankable':o.rankable,
      'claims':claims(r),'incorrect_weak_dominance_pass':r.results[1].passed==1,
      'missed_true_strict_dominance':r.results[0].failed==1,'incorrect_best':o.best!=high}
gaps=[gap_case(base,reverse=reverse) for base in (2**53,2**60,10**20) for reverse in (False,True)]
normal=[gap_case(base) for base in (0,2**40)]+[gap_case(2**53,2)]
assert all(x['incorrect_weak_dominance_pass'] and x['missed_true_strict_dominance'] and x['complete'] for x in gaps)
assert all(not x['incorrect_weak_dominance_pass'] and not x['missed_true_strict_dominance'] and not x['incorrect_best'] for x in normal)
assert any(x['incorrect_best'] for x in gaps)
g=fixture(2**53);g.gap=g.share_rule.phi-sp.Rational(1,2)
root=threshold(g,'phi',.25,.75,{'sigma':.1,'hatvarsigma':.3},winner='RL',loser='RF',scan=4,iters=30)
assert root is None
cross={'exact_gap':'phi - 1/2','exact_crossing':'1/2','sampled_exact_signs':[-1,-1,0,1,1],'reported_threshold':root,'all_five_binary64_gaps_zero':True}
sample=[]
for phi in (.25,.375,.5,.625,.75):
    o=rank_strategies(g,dict(POINT,phi=phi));sample.append({'phi':phi,'reported_gap':o.payoffs['RL']-o.payoffs['RF'],'complete':o.complete})
assert all(x['reported_gap']==0 and x['complete'] for x in sample);cross['samples']=sample
g=fixture(2**53);g.gap=g.lifecycle.sigma
response=statics.derivative(g,'RL','sigma',POINT)
assert response.slope==0 and response.sign=='0'
slope={'exact_payoff':'2^53 + sigma','analytic_derivative':'1','reported_slope':response.slope,'reported_sign':response.sign,'stencil':response.stencil}
# Same algebra at a representable scale verifies the public routines work.
g=fixture(0);g.gap=g.share_rule.phi-sp.Rational(1,2)
control_root=threshold(g,'phi',.25,.75,{'sigma':.1,'hatvarsigma':.3},winner='RL',loser='RF',scan=4,iters=30)
assert control_root==.5
g.gap=g.lifecycle.sigma;control_response=statics.derivative(g,'RL','sigma',POINT)
assert abs(control_response.slope-1)<1e-9
result={'version':pg.__version__,'audit_round':12,'environment':{'package_path':pg.__file__,'python':platform.python_version(),'sympy':sp.__version__,'platform':platform.platform()},
 'production_files_modified':False,'all_observations_asserted':True,'technical_approval':False,
 'findings':{'R12-01':{'priority':'P2','confirmed':True,'cases':owned,'legal_controls':controls,'net_admission_control':report(bad_net),
 'scope':'Public check_point payoff_for objectives lack retained finite-real admission; main solver complex guards are not claimed broken.'},
 'R12-02':{'priority':'P2','confirmed':True,'cases':gaps,'legal_controls':normal,'crossing':cross,'sensitivity':slope,
 'crossing_control':control_root,'sensitivity_control':control_response.slope,
 'scope':'Finite binary64 payoff operands erase an exact inter-strategy or inter-point difference before comparison. Dominates gives a false weak pass; rank/threshold/statics share the loss path. Fixed candidates remove search uncertainty.'}},
 'exit_one_meaning':'Confirmed audit defects, with successful probes and independent analytic controls.'}
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
print(json.dumps({'version':pg.__version__,'confirmed_findings':['R12-01','R12-02'],'technical_approval':False}));raise SystemExit(1)
