"""Executable acceptance for both seventh-audit findings and controls."""
from pathlib import Path
import json,sys,platform
import sympy as sp
import pacegame as pg
from pacegame.analyze import rank_strategies,verify
from pacegame.solve.feasible import check_point
from pacegame.examples._audit_026_fixtures import (
    A,U,V,POINT,NetFixture,FixedNeighbor,fixture,solve_fixture,offset_model,report,packed,rejected)

def main(outdir='validation'):
    assert pg.__version__=='0.2.11'
    g=offset_model();bounds={U:g.domain}
    lower=check_point(g.objective,{U:A},bounds,{},gross=1)
    upper=check_point(0,{U:A+32770},bounds,{},gross=1)
    exact_legal=check_point(g.objective,{U:A+1},bounds,{},gross=1)
    assert float(A+1)!=float(A+32769) and not lower.ok and not upper.ok
    assert not lower.complete and not upper.complete and not exact_legal.complete
    solver=rejected(lambda:solve_fixture(g),pg.BoundsPrecisionError)
    ranking=rejected(lambda:rank_strategies(g,POINT),pg.BoundsPrecisionError)
    single=rejected(lambda:solve_fixture(offset_model((A+1,A+1))),pg.BoundsPrecisionError)
    claim=verify.check(g,[verify.Feasible()],over={},fixed=POINT)
    assert claim.results[0].errors==1 and not claim.ok
    shifted=fixture(NetFixture);shifted.objective=-U;shifted.domain=(1,32769)
    shifted_solution=solve_fixture(shifted)
    assert shifted_solution.rankable and sp.Rational(shifted_solution.point[U])==1
    assert shifted_solution.payoffs['x']==-1
    represented=solve_fixture(offset_model((A,A+32768)))
    fixed=solve_fixture(offset_model((A,A)))
    assert represented.rankable and fixed.rankable and fixed.kind[U]=='fixed'
    assert represented.payoffs['x']==fixed.payoffs['x']==0
    cancellation_model=offset_model((A,A+32768));cancellation_model.objective=A+1-U
    cancellation=solve_fixture(cancellation_model)
    assert not cancellation.rankable and any(f.check=='evaluation' and f.status=='violation' for f in cancellation.feasibility.findings)
    parameter=sp.Symbol('offset',real=True)
    substituted=check_point(0,{U:A},{U:(parameter+1,parameter+32769)},{parameter:sp.Float(A)},gross=1)
    assert not substituted.ok and not substituted.complete
    precision={'noncollapsed_exact_interval':[str(A+1),str(A+32769)],'exact_expected_payoff':'-1',
        'lower_outside':report(lower),'upper_outside':report(upper),'exact_legal_but_coordinates_unavailable':report(exact_legal),
        'solver_rejected':solver,'ranking_rejected':ranking,'unrepresentable_singleton_rejected':single,
        'claim_errors':claim.results[0].errors,'shifted_equivalent':packed(shifted_solution),
        'representable_large_control':packed(represented),'representable_singleton':packed(fixed),
        'payoff_cancellation_not_silently_accepted':packed(cancellation),
        'parameter_offset_retained':report(substituted),'accepted':True}
    f=U**2-10**8*U**4-V**2
    domains={U:(0,1),V:(0,0)}
    def low(expr,point=None,bounds=None):
        return check_point(expr,point or {U:0,V:0},bounds or domains,{},gross=1)
    convex=low(f);scalar=low(U**2,{U:0},{U:(0,1)})
    assert not convex.ok and not scalar.ok
    concave=low(-U**2-V**2);upper_concave=low(-(U-1)**2-V**2,{U:1,V:0})
    strict=low(-U+100*U**2-V**2);fixed_only=low(U**2-V**2,bounds={U:(0,0),V:(0,0)})
    assert all(r.ok and r.complete for r in [concave,upper_concave,strict,fixed_only])
    flat=low(U**4-V**2)
    assert any(x.check=='joint curvature scope' and x.status=='warning' for x in flat.findings)
    toy=fixture(FixedNeighbor);toy.objective=f;positive=solve_fixture(toy)
    assert positive.rankable and abs(float(positive.point[U])-float(1/sp.sqrt(2*10**8)))<1e-10
    assert abs(positive.payoffs['x']-2.5e-9)<1e-15
    gain=f.subs({U:sp.Rational(1,100000),V:0});assert gain==sp.Rational(99,10**12)
    curvature={'fixed_neighbor_convex':report(convex),'scalar_convex':report(scalar),
        'concave_lower':report(concave),'concave_upper':report(upper_concave),
        'strict_gradient':report(strict),'fixed_only':report(fixed_only),'flat_higher_order_warning':report(flat),
        'exact_improving_step_gain':str(gain),'solver_positive_interior_control':packed(positive),
        'scope':'Necessary one/two-dimensional boundary critical curvature, including one remaining free coordinate after fixed coordinates are excluded; no local/global certificate.',
        'accepted':True}
    groups={'R7-01':precision,'R7-02':curvature}
    record={'environment':{'pacegame':pg.__version__,'import_path':pg.__file__,'python':sys.version,'sympy':sp.__version__,'platform':platform.platform()},'groups':groups,'all_accepted':True}
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True);path=out/'audit_026_acceptance.json'
    path.write_text(json.dumps(record,ensure_ascii=False,indent=2,allow_nan=False));print(path);return 0

if __name__=='__main__':raise SystemExit(main(*sys.argv[1:]))
