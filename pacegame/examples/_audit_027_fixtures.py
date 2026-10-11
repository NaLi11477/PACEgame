"""Public extension models and analytic controls for eighth-audit precision."""
import sympy as sp
import pacegame as pg

POINT = {'sigma': .1, 'phi': .85, 'hatvarsigma': .3}
SCALES = (sp.Integer(10**20), sp.Integer(2**60))
NAMES = ('audit_u', 'z_u')


class RetainedScalar(pg.Game):
    objective = sp.Integer(0)
    domain = (0, 1)

    def payoffs(self, strategy):
        return {self.focal: self.objective, self.rival: sp.Integer(0)}

    def gross_payoffs(self, strategy):
        return {self.focal: sp.Integer(1), self.rival: sp.Integer(0)}

    def costs(self, strategy):
        return {self.focal: 1-self.objective, self.rival: sp.Integer(0)}

    def decision_order(self, strategy):
        return [(self.focal, [self.entry])]

    def bounds(self, strategy):
        return {self.entry: self.domain}

    def demand_ceiling(self, strategy, at=None):
        return sp.Integer(1)

    def ceiling_is_endogenous(self, strategy):
        return False

    def share_sensitivity(self, strategy, parameter):
        return sp.Integer(0)


def fixture(name='audit_u'):
    base = pg.models.preannounce_entry()
    data = {key: value for key, value in vars(base).items() if not key.startswith('_')}
    data.update(entry=sp.Symbol(name, real=True), signal=sp.Symbol('audit_v', real=True),
                strategies=(base.strategies[2],))
    return RetainedScalar(**data)


def parameter_case(A, power, name='audit_u', integer=False):
    game = fixture(name)
    coefficient = game.parameters()['sigma']
    game.objective = (coefficient-A+1)*game.entry**power
    params = game.numeric({**POINT, 'sigma': float(A)})
    if integer:
        params[coefficient] = A
    assert sp.Rational(params[coefficient]) == A
    return game, params


def report(value):
    return {'ok': value.ok, 'complete': value.complete,
            'findings': [vars(finding) for finding in value.findings]}


def packed(value):
    return {'point': {str(k): str(v) for k, v in value.point.items()},
            'point_exact_rationals': {str(k): str(sp.Rational(v)) for k, v in value.point.items()},
            'kind': {str(k): v for k, v in value.kind.items()}, 'payoffs': value.payoffs,
            'rankable': value.rankable, 'report': report(value.feasibility)}
