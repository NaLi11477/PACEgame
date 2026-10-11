"""Three acceptance groups for the two tenth-audit numerical findings."""
from pathlib import Path
import json,platform,sys
import sympy as sp
import pacegame as pg
from pacegame.solve.feasible import check_point
from pacegame.analyze import rank_strategies,verify
from pacegame.examples._audit_029_fixtures import POINT,NEGATIVE,injection,counts,report

def main(outdir='validation'):
    assert pg.__version__=='0.2.11'
    u=sp.Symbol('audit29_u',real=True)
    def magnitude(A,delta):
        A=sp.Integer(A);target=A+delta
        expected=bool(sp.sympify(delta)>sp.Rational(1e-9))
        low=check_point(target,{u:0},{u:(0,0)},{},gross=target,upper_bound=A)
        g=injection(target,A);ranking=rank_strategies(g,POINT)
        r=verify.check(g,[verify.Feasible(),verify.Bounded('RL')],over={},n=1,fixed=POINT)
        if expected:
            assert not low.ok and low.complete and ranking.best is None and not ranking.complete
            assert r.results[0].failed==1 and r.results[1].skipped==1
            assert all(x.passed==0 and x.errors==0 for x in r.results)
        else:
            assert low.ok and low.complete and ranking.best=='RL' and ranking.complete
            assert all(x.passed==1 and x.errors==0 for x in r.results)
        return {'ceiling':str(A),'target':str(target),'exact_excess':str(delta),'must_violate':expected,
                'low':report(low),'ranking_complete':ranking.complete,'best':ranking.best,
                'excluded':ranking.excluded,'claims':counts(r)}
    original=[magnitude(A,d) for A,d in ((2**53,1),(2**60,128),(10**20,4096))]
    controls=[magnitude(A,d) for A,d in ((2**40,1),(2**60,256),(2**60,0),(2**60,-256))]
    strict=injection(sp.Integer(10**6)+sp.Rational(1,10**11),sp.Integer(10**6))
    claim=verify.check(strict,[verify.Feasible(),verify.Bounded('RL')],over={},fixed=POINT)
    assert claim.results[0].passed==1 and claim.results[1].failed==1 and claim.results[1].errors==0
    unavailable=check_point(1,{u:0},{u:(0,0)},{},gross=1,upper_bound=sp.Symbol('missing',real=True))
    assert not unavailable.complete
    def reject(call,fragment):
        try:call()
        except ValueError as e:
            assert fragment in str(e),str(e)
            return {'rejected':True,'exception':'ValueError','reason':str(e)}
        raise AssertionError('invalid input accepted')
    parameters=[];legal=[];direct=[];mutations=[]
    for field,name in (('signal_cost','kappa_d'),('timing_cost','kappa_t')):
        g=pg.models.preannounce_entry(**{field:True});st=next(s for s in g.strategies if s.name=='DF')
        p=dict(POINT,**{name:NEGATIVE})
        parameters.append({'field':field,**reject(lambda:g.numeric(p),'nonnegative')})
        raw={sym:(NEGATIVE if n==name else sp.Float(POINT[n])) for n,sym in g.parameters().items()}
        direct.append({'field':field,**reject(lambda:pg.solve(g,st,raw),'nonnegative')})
        for v in (-sp.Rational(1,10**6),sp.Integer(0),sp.Rational(1,10**6)):
            pt=dict(POINT,**{name:v})
            if v<0:result=reject(lambda:g.numeric(pt),'nonnegative')
            else:
                o=rank_strategies(g,pt,[st]);assert o.complete
                result={'rejected':False,'complete':o.complete,'payoffs':o.payoffs}
            legal.append({'field':field,'value':str(v),**result})
    for field in ('signal_cost','timing_cost','phi_coefficient'):
        g=pg.models.preannounce_entry();raw=g.numeric(POINT);st=next(s for s in g.strategies if s.name=='DF')
        if field=='phi_coefficient':g.share_rule.phi=NEGATIVE
        else:setattr(g,field,NEGATIVE)
        mutations.append({'field':field,'numeric':reject(lambda:g.numeric(POINT),'nonnegative'),
                          'direct_solve':reject(lambda:pg.solve(g,st,raw),'nonnegative')})
    g=pg.models.preannounce_entry(signal_cost=True)
    ranges=[]
    for value,message in ((-NEGATIVE,'binary64 range'),(sp.Integer(10)**400,'binary64 range'),
                           (sp.nan,'finite real'),(sp.oo,'finite real'),(sp.I*(-NEGATIVE),'finite real')):
        ranges.append({'value':str(value),**reject(lambda:g.numeric(dict(POINT,kappa_d=value)),message)})
    q=sp.Symbol('audit_cost_factor',real=True);g=pg.models.preannounce_entry();g.signal_cost=q-1
    expression=reject(lambda:g.numeric(dict(POINT,audit_cost_factor=1+NEGATIVE)),'nonnegative')
    groups={'R10-01_ceiling':{'accepted':True,'original_counterexamples':original,'controls':controls,
              'stricter_Bounded_control':counts(claim),'unavailable':report(unavailable),
              'scope':'Deliberately injected over-ceiling output; fixed domains isolate the diagnostic guard. Necessary checks do not certify global optimality.'},
            'R10-02_signs':{'accepted':True,'parameters':parameters,'direct_solve':direct,'normal_sign_controls':legal,'public_mutations':mutations,'negative_expression':expression},
            'R10_numeric_range':{'accepted':True,'cases':ranges,'policy':'Retained finite-real and domain signs before binary64 checks; reject nonzero-to-zero underflow and nonfinite conversion; preserve supplied numeric values.'}}
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True);path=out/'audit_029_acceptance.json'
    record={'environment':{'pacegame':pg.__version__,'import_path':pg.__file__,'python':sys.version,'sympy':sp.__version__,'platform':platform.platform()},'groups':groups,'all_accepted':True}
    path.write_text(json.dumps(record,ensure_ascii=False,indent=2,allow_nan=False));print(path);return 0

if __name__=='__main__':raise SystemExit(main(*sys.argv[1:]))
