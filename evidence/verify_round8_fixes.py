"""Independent public-interface probes. Exit zero means covered revision criteria passed.

The delivered release is never edited. Analytic ground truth uses the actual
retained binary parameter value, not an intended decimal value.
"""
from pathlib import Path
import argparse,json,sys,platform
ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
if args.source_root:sys.path.insert(0,str(args.source_root.absolute()))
import sympy as sp
import pacegame as pg
from pacegame.solve.feasible import check_point
from pacegame.analyze import rank_strategies,verify
U,V=sp.symbols('audit_u audit_v',real=True)
POINT={'sigma':.1,'phi':.85,'hatvarsigma':.3}
def report(r):return {'ok':r.ok,'complete':r.complete,'findings':[vars(f) for f in r.findings]}
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
def fixture(objective=None):
    b=pg.models.preannounce_entry();data={k:v for k,v in vars(b).items() if not k.startswith('_')}
    data.update(entry=U,signal=V,strategies=(b.strategies[2],));g=AuditScalar(**data)
    if objective is not None:g.objective=objective
    return g
groups={};variants=[]
for A in [sp.Integer(10**20),sp.Integer(2**60)]:
    for power in [1,2]:
        g=fixture();c=g.parameters()['sigma'];g.objective=(c-A+1)*U**power
        params=g.numeric({**POINT,'sigma':float(A)})
        retained=sp.Rational(params[c]);assert retained==A
        truth=g.objective.subs({c:retained});assert truth==U**power
        sol=pg.solve(g,g.strategies[0],params)
        assert sp.Rational(sol.point[U])==1 and sol.payoffs['x']==1 and sol.rankable
        assert truth.subs(U,1)==1 and truth.subs(U,0)==0
        low=check_point(g.objective,{U:0},{U:(0,1)},params,gross=1,upper_bound=1)
        assert not low.ok and low.complete
        # A simplified but exactly equivalent objective with identical float
        # parameters must return the upper corner. No higher precision search.
        simple=fixture(U**power);simple_sol=pg.solve(simple,simple.strategies[0],params)
        assert sp.Rational(simple_sol.point[U])==1 and simple_sol.payoffs['x']==1 and simple_sol.rankable
        exact_params={**params,c:A};exact_sol=pg.solve(g,g.strategies[0],exact_params)
        assert sp.Rational(exact_sol.point[U])==1 and exact_sol.payoffs['x']==1
        if power==1:
            assert exact_sol.rankable
        else:
            # The true strict upper gradient is 2. No nonzero critical
            # direction remains; positive curvature must not reject it.
            assert exact_sol.rankable
            assert any(f.check=='joint curvature' and f.status=='ok' for f in exact_sol.feasibility.findings)
        exact_low=check_point(g.objective,{U:0},{U:(0,1)},exact_params,gross=1,upper_bound=1)
        assert not exact_low.ok
        named={**POINT,'sigma':float(A)};ranking=rank_strategies(g,named)
        assert ranking.best=='DF' and ranking.payoffs['DF']==1
        claim=verify.check(g,[verify.Feasible()],over={},fixed=named)
        counts={k:getattr(claim.results[0],k) for k in ['passed','failed','skipped','errors']}
        assert counts=={'passed':1,'failed':0,'skipped':0,'errors':0} and claim.ok and claim.complete
        variants.append({'A':str(A),'power':power,'parameter_binary_rational':str(retained),'objective':str(g.objective),'retained_true_objective':str(truth),'true_maximizer':'1','true_maximum':'1','legacy_parameter_substitution':str(g.objective.subs(params)),
                         'solver':packed(sol),'low_level':report(low),'ranking_best':ranking.best,'ranking_payoffs':ranking.payoffs,'Feasible_claim_counts':counts,'simplified_control':packed(simple_sol),'integer_parameter_control':packed(exact_sol),'integer_parameter_low_level':report(exact_low)})
groups['R8-01_parameter_objective']={'revision_accepted':True,'variants':variants,'cause_control':'legacy ordinary substitution remains recorded for comparison; revised solve retains the nonzero objective'}
A=sp.Integer(10**20);c=sp.Symbol('audit_offset',real=True);params={c:float(A)};candidate=c-A+1
expression=check_point(-U**2,{U:candidate},{U:(0,1)},params,gross=1,upper_bound=1)
plain=check_point(-U**2,{U:sp.Integer(1)},{U:(0,1)},params,gross=1,upper_bound=1)
assert candidate.subs(c,sp.Rational(params[c]))==1 and not expression.ok and expression.complete and not plain.ok
groups['R8-01_candidate_expression']={'revision_accepted':True,'original_candidate':str(candidate),'retained_true_candidate':'1','legacy_numeric_candidate':str(candidate.subs(params)),'objective':'-audit_u**2','true_derivative_at_upper':'-2','expression_report':report(expression),'literal_same_candidate_control':report(plain),'scope':'same retained-substitution defect; not counted as a second independent defect'}
# A large representable parameter is not itself illegal, and ordinary small
# coefficients and the round-seven scalar boundary closure remain covered.
for x in [sp.Integer(0),sp.Rational(1,2),sp.Integer(1)]:
    r=check_point(-(U-x)**2,{U:x},{U:(0,1)},{},gross=1,upper_bound=1)
    assert r.ok and r.complete
boundary=check_point(U**2-10**8*U**4-V**2,{U:0,V:0},{U:(0,1),V:(0,0)},{},gross=1)
assert not boundary.ok and any(f.check=='joint curvature' and f.status=='violation' for f in boundary.findings)
groups['ordinary_controls']={'three_concave_candidates_passed':True,'round7_fixed_neighbor_curvature_failed_as_expected':report(boundary)}
args.out.write_text(json.dumps({'version':pg.__version__,'environment':{'python':platform.python_version(),'import_path':pg.__file__,'sympy':sp.__version__},'groups':groups,'all_revision_criteria_passed':True,'exit_zero_meaning':'covered revision criteria passed; independent re-audit pending'},ensure_ascii=False,indent=2))
print('Independent revision criteria passed:',len(groups),'groups; import',pg.__file__)
