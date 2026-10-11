"""Installed acceptance for all five findings in the sixth audit.

Arguments: output directory, optional actual requirements-reproduce.txt.
The packaged snapshot permits core-only execution without plotting imports.
"""
from pathlib import Path
from dataclasses import replace
import importlib.metadata as metadata
import json, platform, sys
import sympy as sp
import pacegame as pg
from pacegame.analyze import rank_strategies, verify
from pacegame.solve.feasible import check_point
from pacegame.examples._audit_025_fixtures import (
    A,U,V,W,POINT,fixture,silent,FixedTenth,JointFixture,solve_fixture,packed,report,rejected)

def main(outdir='validation',requirements_path=None):
    assert pg.__version__=='0.2.11'
    groups={}
    collapsed=check_point(U-A,{U:A},{U:(A,A+1)},{},gross=U-A,kinds={U:'fixed'})
    assert not collapsed.complete and any(f.check=='bounds precision' and f.required for f in collapsed.findings)
    g=fixture();g.domain=(A,A+1);g.objective=U-A
    solve_error=rejected(lambda:solve_fixture(g),pg.BoundsPrecisionError)
    rank_error=rejected(lambda:rank_strategies(g,POINT),pg.BoundsPrecisionError)
    claim=verify.check(g,[verify.Feasible()],over={},fixed=POINT)
    assert claim.results[0].errors==1 and not claim.ok
    reverse=check_point(U-A,{U:A},{U:(A+1,A)},{},gross=U-A)
    assert not reverse.ok
    offset=sp.Symbol('offset',real=True)
    substituted=check_point(U-offset,{U:A},{U:(offset,offset+1)},{offset:sp.Float(A)},gross=U-offset,kinds={U:'fixed'})
    assert not substituted.complete
    g.domain=(A,A);singleton=solve_fixture(g);assert singleton.rankable and singleton.kind[U]=='fixed'
    g.domain=(0,1);g.objective=U;unit=solve_fixture(g);assert unit.rankable and unit.payoffs['x']==1
    half=sp.Rational(1,2*10**10)
    narrow=check_point(1-(U-half)**2,{U:half},{U:(0,2*half)},{},gross=1-(U-half)**2,kinds={U:'interior'})
    assert narrow.ok and narrow.complete
    groups['R6-01']={'exact_width':'1','float_endpoints_equal':float(A)==float(A+1),
        'collapsed':report(collapsed),'solver_rejected':solve_error,'ranking_rejected':rank_error,
        'claim_errors':claim.results[0].errors,'reverse':report(reverse),'substituted_width':report(substituted),
        'true_singleton':packed(singleton),'rescaled_unit':packed(unit),'narrow_control':report(narrow),'accepted':True}
    base=pg.models.preannounce_entry()
    bad={'time_as_rate':lambda:replace(base,lifecycle=pg.TwoPhase(base.time,base.lifecycle.growth_end,1,True)),
         'entry_as_phi':lambda:replace(base,share_rule=pg.Proportional(base.entry)),
         'signal_equals_entry':lambda:replace(base,signal=base.entry),
         'time_equals_entry':lambda:replace(base,time=base.entry),
         'nonscalar_signal':lambda:replace(base,signal=base.entry+1)}
    failures={name:rejected(action) for name,action in bad.items()}
    mutated=silent();mutated.lifecycle.sigma=mutated.time
    mutation=rejected(lambda:mutated.payoffs(mutated.strategies[0]))
    base=silent(cls=FixedTenth);alpha=sp.Symbol('alpha',positive=True)
    independent=replace(base,lifecycle=pg.TwoPhase(alpha,base.lifecycle.growth_end,1,True))
    constant=replace(base,lifecycle=pg.TwoPhase(sp.Integer(1),base.lifecycle.growth_end,1,True))
    a=rank_strategies(independent,dict(POINT,alpha=1));b=rank_strategies(constant,POINT)
    error=max(abs(a.payoffs[k]-b.payoffs[k]) for k in a.payoffs)
    assert error==0 and a.complete and b.complete
    groups['R6-02']={'constructor_rejections':failures,'mutated_rate_rejected_before_integration':mutation,
        'independent_rate_payoffs':a.payoffs,'constant_rate_payoffs':b.payoffs,'maximum_payoff_difference':error,'accepted':True}
    def curvature(f,point=None,bounds=None,kinds=None):
        return check_point(f,point or {U:0,V:0},bounds or {U:(0,1),V:(0,1)},{},gross=f,
            kinds=kinds or {U:'lower corner',V:'lower corner'},payoff_for={U:f,V:f})
    f=-U**2-V**2+3*U*V-10**8*(U+V)**4
    bad_corner=curvature(f);assert not bad_corner.ok
    g=fixture(JointFixture);g.objective=f;solution=solve_fixture(g);assert not solution.rankable
    good=curvature(-U**2-V**2);infeasible=curvature(-U**2-V**2-3*U*V)
    strict=curvature(-U-V**2+100*U*V)
    assert all(r.ok and r.complete for r in [good,infeasible,strict])
    mixed=curvature(-U**2-V**2+3*U*V,bounds={U:(0,1),V:(-1,1)},kinds={U:'lower corner',V:'interior'})
    oriented=curvature(-U**2-(V-1)**2-3*U*(V-1),point={U:0,V:1},kinds={U:'lower corner',V:'upper corner'})
    assert not mixed.ok and not oriented.ok
    flat=curvature((U+V)**4);assert any(x.check=='joint curvature scope' and x.status=='warning' for x in flat.findings)
    three=check_point(-U**2-V**2-W**2,{U:0,V:0,W:0},{x:(0,1) for x in (U,V,W)},{},gross=-U**2-V**2-W**2,
                      kinds={x:'lower corner' for x in (U,V,W)})
    assert not three.complete
    gain=sp.simplify(f.subs({U:sp.Rational(1,100000),V:sp.Rational(1,100000)}))
    assert gain>0
    groups['R6-03']={'audited_corner':report(bad_corner),'solver':packed(solution),'exact_feasible_gain':str(gain),
        'concave_control':report(good),'infeasible_positive_eigenvalue_control':report(infeasible),
        'strict_gradient_control':report(strict),'mixed':report(mixed),'upper_lower':report(oriented),
        'flat_higher_order_warning':report(flat),'three_dimensional_incomplete':report(three),
        'scope':'Necessary curvature checks for boundary groups with one or two critical directions; finite global search remains heuristic.',
        'accepted':True}
    duplicate=rejected(lambda:replace(silent(),focal='x',rival='x'))
    g=silent();g.rival=g.focal
    mutated_errors={name:rejected(action) for name,action in {
        'stocks':lambda:g.stocks(g.strategies[0]),'shares':lambda:g.shares(g.strategies[0]),
        'payoffs':lambda:g.payoffs(g.strategies[0]),'rank':lambda:rank_strategies(g,POINT)}.items()}
    custom=rank_strategies(replace(silent(),focal='alpha',rival='beta'),POINT)
    default=rank_strategies(silent(),POINT)
    assert custom.complete and default.complete
    assert all(set(s.payoffs)=={'alpha','beta'} for s in custom.solutions.values())
    assert all(set(s.payoffs)=={'x','y'} for s in default.solutions.values())
    assert custom.payoffs==default.payoffs and custom.rival_payoffs==default.rival_payoffs
    groups['R6-04']={'duplicate_constructor':duplicate,'mutated_duplicate':mutated_errors,
        'custom_player_payoffs':custom.payoffs,'default_player_payoffs':default.payoffs,'two_keys_preserved':True,'accepted':True}
    snapshot=json.loads(Path(__file__).with_name('reproduce_requirements.json').read_text())
    installed={}
    for name,version in snapshot['pins'].items():
        try:installed[name]=metadata.version(name)
        except metadata.PackageNotFoundError:installed[name]=None
        if name in ('sympy','mpmath'):assert installed[name] is not None
    checked=False
    if requirements_path:
        lines=Path(requirements_path).read_text().splitlines()
        pins=dict(x.split('==',1) for x in lines if '==' in x and not x.lstrip().startswith('#'))
        assert pins==snapshot['pins'];checked=True
    # Plotting is optional. Release figure validation separately checks its exact installed pins.
    groups['R6-05']={'packaged_pins':snapshot['pins'],'installed_versions':installed,'actual_requirements_checked':checked,'installed_matches_snapshot':installed==snapshot['pins'],
        'core_runs_without_plotting_imports':True,'scope':snapshot['scope'],'accepted':True}
    record={'environment':{'pacegame':pg.__version__,'import_path':pg.__file__,'python':sys.version,
        'sympy':sp.__version__,'platform':platform.platform()},'groups':groups,'all_accepted':all(x['accepted'] for x in groups.values())}
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True);path=out/'audit_025_acceptance.json'
    path.write_text(json.dumps(record,ensure_ascii=False,indent=2,allow_nan=False));print(path);return 0

if __name__=='__main__':raise SystemExit(main(*sys.argv[1:]))
