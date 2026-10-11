"""Fixed candidates make retained payoff comparisons independently checkable."""
from dataclasses import fields
import sympy as sp
from ..core.game import Game
from .. import models
POINT={'sigma':.1,'phi':.85,'hatvarsigma':.3}
U=sp.Symbol('audit12_u',real=True)
class OffsetGame(Game):
    base=sp.Integer(0)
    gap=sp.Integer(1)
    def payoffs(self,st):
        return {self.focal:self.base+(self.gap if st.name=='RL' else 0),self.rival:self.base+self.lifecycle.sigma}
    def gross_payoffs(self,st):return {self.focal:self.base+4,self.rival:self.base+4}
    def costs(self,st):return {p:self.gross_payoffs(st)[p]-v for p,v in self.payoffs(st).items()}
    def decision_order(self,st):return [(self.focal,[self.signal])]
    def bounds(self,st):return {self.signal:(0,0)}
    def demand_ceiling(self,st,at=None):return self.base+4
    def ceiling_is_endogenous(self,st):return False
    def share_sensitivity(self,st,p):return sp.Integer(0)
def fixture(base=0,gap=1):
    b=models.preannounce_entry();d={f.name:getattr(b,f.name) for f in fields(Game) if f.init}
    d.update(signal=U,strategies=tuple(b.strategies[:2]));g=OffsetGame(**d);g.base=sp.Integer(base);g.gap=sp.sympify(gap);return g
