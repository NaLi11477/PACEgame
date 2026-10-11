"""Independent revised counterexample controls; no maximum certificate."""
from pathlib import Path
import argparse,json,sys,platform
ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
if a.source_root:sys.path.insert(0,str(a.source_root.resolve()))
import sympy as sp
import pacegame as pg
from pacegame.solve.feasible import check_point
from pacegame.analyze import rank_strategies
U,V,W=sp.symbols('audit_u audit_v audit_w',real=True)
POINT={'sigma':.1,'phi':.85,'hatvarsigma':.3,'lambda':.1}
def report(r):return {'ok':r.ok,'complete':r.complete,'findings':[vars(x) for x in r.findings]}
def packed(s):return {'point':{str(k):str(v) for k,v in s.point.items()},'point_exact_rationals':{str(k):str(sp.Rational(v)) for k,v in s.point.items()},'kind':{str(k):v for k,v in s.kind.items()},'payoffs':s.payoffs,'rankable':s.rankable,'report':report(s.feasibility)}
class AuditScalar(pg.Game):
 objective=sp.Integer(0);domain=(0,1)
 def payoffs(self,st):return {self.focal:self.objective,self.rival:sp.Integer(0)}
 def gross_payoffs(self,st):return {self.focal:sp.Integer(1),self.rival:sp.Integer(0)}
 def costs(self,st):return {self.focal:1-self.objective,self.rival:sp.Integer(0)}
 def decision_order(self,st):return [(self.focal,[self.entry])]
 def bounds(self,st):return {self.entry:self.domain}
 def demand_ceiling(self,st,at=None):return sp.Integer(1)
 def ceiling_is_endogenous(self,st):return False
 def share_sensitivity(self,st,parameter):return sp.Integer(0)
class AuditJoint(AuditScalar):
 domains={U:(0,1),V:(0,1)}
 def decision_order(self,st):return [(self.focal,[self.entry,self.signal])]
 def bounds(self,st):return self.domains
def fixture(cls=AuditScalar):
 b=pg.models.preannounce_entry();data={k:v for k,v in vars(b).items() if not k.startswith('_')};data.update(entry=U,signal=V,strategies=(b.strategies[2],));return cls(**data)
def solve(g):return pg.solve(g,g.strategies[0],g.numeric(POINT))
def rejected(fn):
 try:fn()
 except Exception as e:return {'type':type(e).__name__,'reason':str(e)}
 raise AssertionError('expected rejection')
groups={}
A=sp.Integer(10**20);lo=A+1;hi=A+32769;f=A-U
g=fixture();g.objective=f;g.domain=(lo,hi)
low=check_point(f,{U:A},{U:(lo,hi)},{},gross=1)
upper=check_point(0,{U:A+32770},{U:(lo,hi)},{},gross=1)
assert not low.ok and not upper.ok and not low.complete and not upper.complete
assert float(lo)!=float(hi)
solver=rejected(lambda:solve(g));ranking=rejected(lambda:rank_strategies(g,POINT))
assert solver["type"]==ranking["type"]=="BoundsPrecisionError"
single=fixture();single.objective=f;single.domain=(lo,lo)
se=rejected(lambda:solve(single));assert se["type"]=="BoundsPrecisionError"
shift=fixture();shift.objective=-U;shift.domain=(1,32769);ss=solve(shift)
assert ss.rankable and sp.Rational(ss.point[U])==1 and ss.payoffs["x"]==-1
cancel=fixture();cancel.objective=A+1-U;cancel.domain=(A,A+32768);cs=solve(cancel)
assert not cs.rankable and any(x.check=="evaluation" and x.status=="violation" for x in cs.feasibility.findings)
groups["R7-01"]={"lower":report(low),"upper":report(upper),"solver":solver,"ranking":ranking,"singleton":se,"shifted":packed(ss),"cancellation":packed(cs),"accepted":True}
f=U**2-10**8*U**4-V**2
corner=fixture(AuditJoint);corner.objective=f;corner.domains={U:(0,1),V:(0,0)}
cl=check_point(f,{U:0,V:0},corner.domains,{},gross=1);cs=solve(corner)
assert not cl.ok and cs.rankable and abs(cs.payoffs["x"]-2.5e-9)<1e-15
assert f.subs({U:sp.Rational(1,100000),V:0})==sp.Rational(99,10**12)
groups["R7-02"]={"low":report(cl),"solver_correct_interior":packed(cs),"accepted":True}
a.out.write_text(json.dumps({"version":pg.__version__,"import_path":pg.__file__,"groups":groups,"all_accepted":True},indent=2))
print("Independent controls passed",pg.__file__)
