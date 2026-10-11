"""Public Game extension fixtures shared by sixth-audit controls and exporter."""
from dataclasses import replace
import sympy as sp
import pacegame as pg

POINT={'sigma':.1,'phi':.85,'hatvarsigma':.3,'lambda':.1}
A=sp.Integer(10**20)
U,V,W=sp.symbols('u v w', real=True)

class ScalarFixture(pg.Game):
    objective=sp.Integer(0)
    domain=(0,1)
    def payoffs(self,st):return {self.focal:self.objective,self.rival:sp.Integer(0)}
    def gross_payoffs(self,st):return self.payoffs(st)
    def decision_order(self,st):return [(self.focal,[self.entry])]
    def bounds(self,st):return {self.entry:self.domain}
    def demand_ceiling(self,st,at=None):return sp.Integer(1)
    def ceiling_is_endogenous(self,st):return False
    def share_sensitivity(self,st,parameter):return sp.Integer(0)

class JointFixture(ScalarFixture):
    def decision_order(self,st):return [(self.focal,[self.entry,self.signal])]
    def bounds(self,st):return {self.entry:(0,1),self.signal:(0,1)}

class FixedTenth(pg.Game):
    def bounds(self,st):
        b=super().bounds(st);b[self.entry]=(sp.Rational(1,10),)*2;return b

def fixture(cls=ScalarFixture):
    base=pg.models.preannounce_entry()
    data={k:v for k,v in base.__dict__.items() if not k.startswith('_')}
    data.update(entry=U,signal=V,strategies=(base.strategies[3],))
    return cls(**data)

def silent(base=None,cls=pg.Game):
    base=base or pg.models.preannounce_entry(keep_stock=True,entry_floor=True)
    data={k:v for k,v in base.__dict__.items() if not k.startswith('_')}
    data['strategies']=tuple(s for s in base.strategies if not s.signals)
    return cls(**data)

def solve_fixture(g):return pg.solve(g,g.strategies[0],g.numeric(POINT))
def packed(sol):
    return {'point':{str(k):str(v) for k,v in sol.point.items()},'kind':{str(k):v for k,v in sol.kind.items()},
            'payoffs':sol.payoffs,'rankable':sol.rankable,'feasibility_ok':sol.feasibility.ok,
            'feasibility_complete':sol.feasibility.complete,'findings':[vars(f) for f in sol.feasibility.findings]}
def report(rep):return {'ok':rep.ok,'complete':rep.complete,'findings':[vars(f) for f in rep.findings]}

def rejected(fn,exception=ValueError):
    try:fn()
    except exception as error:return {'type':type(error).__name__,'reason':str(error)}
    raise AssertionError('invalid request was accepted')
