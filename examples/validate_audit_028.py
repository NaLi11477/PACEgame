"""Three acceptance groups closing the two ninth-audit findings."""
from pathlib import Path
import json,platform,sys
import sympy as sp
import pacegame as pg
from pacegame.solve.feasible import check_point
from pacegame.analyze import rank_strategies,verify
from pacegame.examples._audit_028_fixtures import POINT,SCALES,NAMES,fixture,expressions,report,packed

def main(outdir='validation'):
    assert pg.__version__=='0.2.11'
    variants=[]
    for A in SCALES:
        for name in NAMES:
            g=fixture(name);u,v=g.entry,g.signal;factored,expanded=expressions(g,A)
            H=sp.hessian(expanded,[u,v]);assert H.eigenvals()=={sp.Integer(2):1,-4*sp.Integer(A)-2:1}
            r=check_point(expanded,{u:0,v:0},{u:(0,1),v:(0,1)},{},gross=3)
            assert not r.ok and r.complete
            forms={}
            for label,f in [('factored',factored),('expanded',expanded)]:
                g.objective=f;s=pg.solve(g,g.strategies[0],g.numeric(POINT))
                assert not s.rankable or (s.payoffs[g.focal]==2 and all(sp.Rational(s.point[x])==1 for x in (u,v)))
                if label=='factored':assert s.rankable and s.payoffs[g.focal]==2
                forms[label]=packed(s)
            g.objective=expanded;ranking=rank_strategies(g,POINT);claim=verify.check(g,[verify.Feasible()],over={},fixed=POINT)
            counts={key:getattr(claim.results[0],key) for key in ['passed','failed','skipped','errors']}
            assert not ranking.complete or ranking.payoffs['RL']==2
            if forms['expanded']['rankable']:assert counts['passed']==1
            else:assert counts['passed']==0 and not claim.ok
            variants.append({'A':str(A),'coordinate':name,'analytic_maximum':'2','analytic_maximizer':['1','1'],
                'exact_hessian':str(H),'exact_eigenvalues':{str(k):n for k,n in H.eigenvals().items()},
                'wrong_lower_report':report(r),'solutions':forms,'ranking_complete':ranking.complete,
                'ranking_payoffs':ranking.payoffs,'Feasible_counts':counts})
    u,v,w=sp.symbols('audit_u audit_v audit_w',real=True);a,b=u-sp.Rational(1,2),v-sp.Rational(1,2);f=-a*a-b*b+3*a*b
    kw={'point':{u:sp.Rational(1,2),v:sp.Rational(1,2)},'bounds':{u:(0,1),v:(0,1)},'params':{},'gross':3}
    auto=check_point(f,**kw);explicit=check_point(f,**kw,kinds={u:'interior',v:'interior'},payoff_for={u:f,v:f})
    concave=check_point(-a*a-b*b,**kw);assert not auto.ok and not explicit.ok and auto.complete and explicit.complete
    assert concave.ok and concave.complete
    g=fixture();g.objective=f;s=pg.solve(g,g.strategies[0],g.numeric(POINT));assert s.rankable and s.payoffs[g.focal]==.25
    controls={}
    def control(label,target,bounds,**extra):
        rr=check_point(target,{u:0,v:0},bounds,{},gross=3,**extra);controls[label]=report(rr);return rr
    assert control('negative_cross_outside_cone',-u*u-v*v-3*u*v,{u:(0,1),v:(0,1)}).ok
    assert control('distinct_objectives',-u*u-v*v+3*u*v,{u:(-1,1),v:(-1,1)},payoff_for={u:-u*u+3*u*v,v:-v*v}).ok
    assert control('earlier_stage_skipped',-u*u-v*v+3*u*v,{u:(-1,1),v:(-1,1)},skip_optimality={u}).ok
    assert control('fixed_coordinate',-u*u-v*v+3*u*v,{u:(0,0),v:(-1,1)}).ok
    huge=control('beyond_80_digits',sp.expand(-10**120*(u-v)**2+2*u*v),{u:(0,1),v:(0,1)});assert not huge.ok and huge.complete
    unknown=control('unavailable_required',sp.Symbol('missing',real=True)*u*v-u*u-v*v,{u:(-1,1),v:(-1,1)})
    assert not unknown.complete
    groups={
       'R9-01_retained_boundary':{'accepted':True,'variants':variants},
       'R9-02_joint_interior':{'accepted':True,'exact_eigenvalues':['1','-5'],'improving_step_gain':'1/100',
            'automatic_report':report(auto),'explicit_report':report(explicit),'concave_control':report(concave),'main_solver_control':packed(s)},
       'R9_scope_controls':{'accepted':True,'controls':controls,'scope':'Three groups for two findings. Retained-value necessary curvature checks may exclude unstable binary64 search candidates; no global maximum or continuous-domain certificate.'}}
    record={'environment':{'pacegame':pg.__version__,'import_path':pg.__file__,'python':sys.version,'sympy':sp.__version__,'platform':platform.platform()},'groups':groups,'all_accepted':True}
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True);path=out/'audit_028_acceptance.json'
    path.write_text(json.dumps(record,ensure_ascii=False,indent=2,allow_nan=False));print(path);return 0
if __name__=='__main__':raise SystemExit(main(*sys.argv[1:]))
