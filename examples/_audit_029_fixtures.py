"""Deliberately injected ceilings isolate numeric diagnostics from search."""
import sympy as sp
import pacegame as pg

POINT = {'sigma': .1, 'phi': .85, 'hatvarsigma': .3}
NEGATIVE = -sp.Rational(1, 10**400)

class CeilingInjection(pg.Game):
    def payoffs(self, st):
        return {self.focal: self.amount, self.rival: sp.Integer(0)}
    def gross_payoffs(self, st):
        return self.payoffs(st)
    def costs(self, st):
        return {self.focal: sp.Integer(0), self.rival: sp.Integer(0)}
    def decision_order(self, st):
        return [(self.focal, [self.entry, self.signal])]
    def bounds(self, st):
        return {self.entry: (0, 0), self.signal: (0, 0)}
    def demand_ceiling(self, st, at=None):
        return self.limit
    def ceiling_is_endogenous(self, st):
        return False
    def share_sensitivity(self, st, player):
        return sp.Integer(0)

def injection(amount, limit):
    b = pg.models.preannounce_entry()
    state = {k: v for k, v in vars(b).items() if not k.startswith('_')}
    u, v = sp.symbols('audit_r10_u audit_r10_v', real=True)
    state.update(entry=u, signal=v, strategies=(b.strategies[1],))
    g = CeilingInjection(**state)
    g.amount, g.limit = sp.sympify(amount), sp.sympify(limit)
    return g

def counts(result):
    return [{k: getattr(r, k) for k in ('claim','passed','failed','skipped','errors')}
            for r in result.results]

def report(r):
    return {'ok': r.ok, 'complete': r.complete,
            'findings': [vars(f) for f in r.findings]}
