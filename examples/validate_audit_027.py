"""Export eighth-audit closure and scoped analytic control evidence."""
from pathlib import Path
import json, platform, sys
import sympy as sp
import pacegame as pg
from pacegame.analyze import rank_strategies, verify
from pacegame.solve.feasible import check_point
from pacegame.examples._audit_027_fixtures import (
    SCALES, NAMES, POINT, fixture, parameter_case, report, packed)


def main(outdir='validation'):
    assert pg.__version__ == '0.2.11'
    variants=[]
    for A in SCALES:
        for name in NAMES:
            for power in (1,2):
                game,params=parameter_case(A,power,name)
                u=game.entry
                solution=pg.solve(game,game.strategies[0],params)
                assert sp.Rational(solution.point[u])==1 and solution.payoffs[game.focal]==1 and solution.rankable
                low=check_point(game.objective,{u:0},{u:(0,1)},params,gross=1)
                assert not low.ok and low.complete
                integer_game,integer_params=parameter_case(A,power,name,True)
                integer_solution=pg.solve(integer_game,integer_game.strategies[0],integer_params)
                assert integer_solution.rankable and sp.Rational(integer_solution.point[u])==1
                assert integer_solution.payoffs[game.focal]==1
                simple=fixture(name);simple.objective=u**power
                simplified=pg.solve(simple,simple.strategies[0],params)
                assert simplified.rankable and simplified.payoffs[game.focal]==1
                ranking=rank_strategies(game,{**POINT,'sigma':float(A)})
                claim=verify.check(game,[verify.Feasible()],over={},fixed={**POINT,'sigma':float(A)})
                counts={key:getattr(claim.results[0],key) for key in ('passed','failed','skipped','errors')}
                assert ranking.payoffs['DF']==1 and counts=={'passed':1,'failed':0,'skipped':0,'errors':0}
                assert claim.ok and claim.complete
                variants.append({'A':str(A),'coordinate':name,'power':power,
                                 'actual_parameter':str(sp.Rational(params[game.parameters()['sigma']])),
                                 'analytic_maximizer':'1','analytic_maximum':'1',
                                 'solver':packed(solution),'wrong_lower_report':report(low),
                                 'integer_parameter_control':packed(integer_solution),
                                 'simplified_control':packed(simplified),'ranking_payoff':ranking.payoffs['DF'],
                                 'Feasible_counts':counts})
    candidates=[]
    for A in SCALES:
        for name in NAMES:
            u=sp.Symbol(name,real=True);offset=sp.Symbol('audit_offset',real=True)
            params={offset:float(A)}
            expression=check_point(-u**2,{u:offset-A+1},{u:(0,1)},params,gross=1)
            literal=check_point(-u**2,{u:1},{u:(0,1)},params,gross=1)
            assert not expression.ok and not literal.ok and expression.complete and literal.complete
            assert report(expression)==report(literal)
            candidates.append({'A':str(A),'coordinate':name,'actual_candidate':'1',
                               'expression':str(offset-A+1),'expected_upper_derivative':'-2',
                               'expression_report':report(expression),'literal_report':report(literal)})
    controls=[]
    for A in SCALES:
        u,v,sigma=sp.symbols('audit_u audit_v sigma',real=True)
        for mixed in (False,True):
            result=check_point((sigma-A+1)*(u**2-v**2),{u:0,v:0},
                               {u:(0,1),v:(-1,1) if mixed else (0,1)},
                               {sigma:float(A)},gross=1)
            assert not result.ok and any(f.check=='joint curvature' and f.status=='violation' for f in result.findings)
            controls.append({'A':str(A),'mixed_boundary_interior':mixed,'report':report(result)})
    u,v,b=sp.symbols('audit_u audit_v missing',real=True)
    unknown=check_point(b*u,{u:0},{u:(0,1)},{},gross=1)
    old=check_point(u**2-10**8*u**4-v**2,{u:0,v:0},{u:(0,1),v:(0,0)},{},gross=1)
    assert not unknown.complete and not old.ok
    groups={
        'R8-01_parameters':{'accepted':True,'variants':variants},
        'R8-01_candidates':{'accepted':True,'variants':candidates},
        'R8-01_derivative_controls':{'accepted':True,'critical_hessian_variants':controls,
                                     'unavailable_required_condition':report(unknown),
                                     'round7_fixed_neighbor_control':report(old),
                                     'scope':'Three acceptance groups for one R8-01 finding. Actual supplied Float values are retained; binary64 compiled evaluation, finite search and local necessary diagnostics remain bounded in scope.'}}
    record={'environment':{'pacegame':pg.__version__,'import_path':pg.__file__,
                           'python':sys.version,'sympy':sp.__version__,'platform':platform.platform()},
            'groups':groups,'all_accepted':True}
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True)
    path=out/'audit_027_acceptance.json';path.write_text(json.dumps(record,ensure_ascii=False,indent=2,allow_nan=False))
    print(path);return 0


if __name__=='__main__': raise SystemExit(main(*sys.argv[1:]))
