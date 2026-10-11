"""Seventh-audit public extensions with lawful negative net payoffs."""
import sympy as sp
from pacegame.examples._audit_025_fixtures import (
    A,U,V,W,POINT,ScalarFixture,fixture,solve_fixture,report,packed,rejected)

class NetFixture(ScalarFixture):
    def gross_payoffs(self,st):return {self.focal:sp.Integer(1),self.rival:sp.Integer(0)}
    def costs(self,st):return {self.focal:1-self.objective,self.rival:sp.Integer(0)}

class FixedNeighbor(NetFixture):
    domains={U:(0,1),V:(0,0)}
    def decision_order(self,st):return [(self.focal,[self.entry,self.signal])]
    def bounds(self,st):return self.domains

def offset_model(domain=None):
    g=fixture(NetFixture);g.objective=A-U;g.domain=domain or (A+1,A+32769)
    return g
