"""Small public Game extensions for eleventh-audit geometry controls."""
from dataclasses import fields
import sympy as sp
import pacegame as pg

POINT = {'sigma': .1, 'phi': .85, 'hatvarsigma': .3}
U = sp.Symbol('audit_r11_u', real=True)
EPS = sp.Rational(1, 10**20)
TINY = sp.Rational(1, 10**400)

class DomainGame(pg.Game):
    domain = (0, 1)
    def payoffs(self, strategy):
        return {self.focal: -self.signal, self.rival: sp.Integer(0)}
    def gross_payoffs(self, strategy):
        return {self.focal: sp.Integer(1), self.rival: sp.Integer(0)}
    def costs(self, strategy):
        return {self.focal: 1+self.signal, self.rival: sp.Integer(0)}
    def decision_order(self, strategy):
        return [(self.focal, [self.signal])]
    def bounds(self, strategy):
        return {self.signal: self.domain}
    def demand_ceiling(self, strategy, at=None):
        return sp.Integer(2)
    def ceiling_is_endogenous(self, strategy):
        return False
    def share_sensitivity(self, strategy, params):
        return sp.Integer(0)

class ComplexGame(DomainGame):
    def payoffs(self, strategy):
        return {self.focal: 1+sp.I*TINY, self.rival: sp.Integer(0)}

def fixture(domain, cls=DomainGame):
    base = pg.models.preannounce_entry()
    data = {f.name: getattr(base, f.name) for f in fields(pg.Game) if f.init}
    data.update(signal=U, strategies=(base.strategies[1],))
    game = cls(**data)
    game.domain = domain
    return game

def report(value):
    return {'ok': value.ok, 'complete': value.complete,
            'findings': [vars(f) for f in value.findings]}
