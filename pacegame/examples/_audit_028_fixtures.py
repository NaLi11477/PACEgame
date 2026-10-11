"""Public joint-objective extension and exact ninth-audit ground truth."""
import sympy as sp
import pacegame as pg

POINT = {'sigma': .1, 'phi': .85, 'hatvarsigma': 1}
SCALES = (2**40, 2**53, 2**60, 10**20)
NAMES = ('audit_u', 'z_u')

class JointGame(pg.Game):
    objective = sp.Integer(0)
    def payoffs(self, st): return {self.focal:self.objective, self.rival:sp.Integer(0)}
    def gross_payoffs(self, st): return {self.focal:sp.Integer(3), self.rival:sp.Integer(0)}
    def costs(self, st): return {self.focal:3-self.objective, self.rival:sp.Integer(0)}
    def decision_order(self, st): return [(self.focal,[self.entry,self.signal])]
    def bounds(self, st): return {self.entry:(0,1),self.signal:(0,1)}
    def demand_ceiling(self, st, at=None): return sp.Integer(3)
    def ceiling_is_endogenous(self, st): return False
    def share_sensitivity(self, st, parameter): return sp.Integer(0)

def fixture(name='audit_u'):
    base=pg.models.preannounce_entry()
    data={key:value for key,value in vars(base).items() if not key.startswith('_')}
    u,v=sp.symbols(name+' audit_v',real=True)
    data.update(entry=u,signal=v,strategies=(base.strategies[1],))
    return JointGame(**data)

def expressions(game,A):
    u,v=game.entry,game.signal
    factored=-sp.Integer(A)*(u-v)**2+2*u*v
    return factored,sp.expand(factored)

def report(value):
    return {'ok':value.ok,'complete':value.complete,'findings':[vars(f) for f in value.findings]}

def packed(value):
    return {'point':{str(k):str(v) for k,v in value.point.items()},'payoffs':value.payoffs,
            'rankable':value.rankable,'report':report(value.feasibility)}
