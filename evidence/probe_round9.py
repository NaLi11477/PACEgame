"""Independent public-interface audit probes for the immutable 0.2.7 release.

Exit 1 means confirmed audit defects, not a broken probe. No production files
are edited. Analytic ground truth is exact and independent of internal helpers.
"""
from pathlib import Path
import argparse,json,platform,sys
parser=argparse.ArgumentParser()
parser.add_argument('--source-root',type=Path)
parser.add_argument('--out',type=Path,required=True)
args=parser.parse_args()
if args.source_root:sys.path.insert(0,str(args.source_root.resolve()))
import sympy as sp
import pacegame as pg
from pacegame.solve.feasible import check_point
from pacegame.analyze import rank_strategies,verify

POINT={'sigma':.1,'phi':.85,'hatvarsigma':1}
def report(r):return {'ok':r.ok,'complete':r.complete,'findings':[vars(x) for x in r.findings]}
def packed(s):
    return {'point':{str(k):str(v) for k,v in s.point.items()},
            'point_exact_rationals':{str(k):str(sp.Rational(v)) for k,v in s.point.items()},
            'kind':{str(k):v for k,v in s.kind.items()},'payoffs':s.payoffs,
            'rankable':s.rankable,'feasibility':report(s.feasibility)}

class JointGame(pg.Game):
    objective=sp.Integer(0)
    def payoffs(self,st):return {self.focal:self.objective,self.rival:sp.Integer(0)}
    def gross_payoffs(self,st):return {self.focal:sp.Integer(3),self.rival:sp.Integer(0)}
    def costs(self,st):return {self.focal:3-self.objective,self.rival:sp.Integer(0)}
    def decision_order(self,st):return [(self.focal,[self.entry,self.signal])]
    def bounds(self,st):return {self.entry:(0,1),self.signal:(0,1)}
    def demand_ceiling(self,st,at=None):return sp.Integer(3)
    def ceiling_is_endogenous(self,st):return False
    def share_sensitivity(self,st,parameter):return sp.Integer(0)

def fixture(name='audit_u'):
    u,v=sp.symbols(name+' audit_v',real=True)
    base=pg.models.preannounce_entry()
    data={k:x for k,x in vars(base).items() if not k.startswith('_')}
    data.update(entry=u,signal=v,strategies=(base.strategies[1],))
    return JointGame(**data)

variants=[]
for scale in [2**40,2**53,2**60,10**20]:
    A=sp.Integer(scale)
    for name in ['audit_u','z_u']:
        g=fixture(name);u,v=g.entry,g.signal;params=g.numeric(POINT)
        factored=-A*(u-v)**2+2*u*v
        expanded=sp.expand(factored)
        assert sp.expand(factored-expanded)==0
        H=sp.hessian(expanded,[u,v]);eigen=H.eigenvals()
        assert eigen=={sp.Integer(2):1,-4*A-2:1}
        direction=sp.Matrix([1,1]);quadratic=(direction.T*H*direction)[0]
        assert quadratic==4 and expanded.subs({u:0,v:0})==0
        assert expanded.subs({u:sp.Rational(1,10),v:sp.Rational(1,10)})==sp.Rational(1,50)
        assert expanded.subs({u:1,v:1})==2
        # f<=2 because -A(u-v)^2<=0 and 2uv<=2 on [0,1]^2.
        # Gross 3 and cost 3-f>=1; no negative-cost or unsafe-coordinate input.
        low=check_point(expanded,{u:0,v:0},{u:(0,1),v:(0,1)},params,gross=3,upper_bound=3)
        forms={}
        for label,expression in [('factored',factored),('expanded',expanded)]:
            g.objective=expression
            solution=pg.solve(g,g.strategies[0],params)
            forms[label]=packed(solution)
        if scale==2**40:
            assert not low.ok and low.complete
            assert all(s['rankable'] and s['payoffs']['x']==2 for s in forms.values())
        record={'A':str(A),'coordinate':name,'objective':str(expanded),
                'equivalent_factored_objective':str(factored),'exact_hessian':str(H),
                'exact_eigenvalues':{str(k):n for k,n in eigen.items()},
                'critical_direction':[1,1],'exact_directional_second_derivative':str(quadratic),
                'exact_improving_step_gain':'1/50','exact_maximum':'2','exact_maximizer':['1','1'],
                'low_level_at_wrong_lower_point':report(low),'solutions':forms,
                'wrong_lower_accepted':bool(low.ok and low.complete),
                'incorrect_solver_rankable':bool(forms['expanded']['rankable'] and forms['expanded']['payoffs']['x']!=2)}
        if scale==2**60:
            g.objective=expanded
            ranking=rank_strategies(g,POINT)
            claim=verify.check(g,[verify.Feasible()],over={},fixed=POINT)
            record['ranking']={'best':ranking.best,'payoffs':ranking.payoffs,'complete':ranking.complete,'rankable':ranking.rankable}
            record['Feasible']={'ok':claim.ok,'complete':claim.complete,
                'counts':{k:getattr(claim.results[0],k) for k in ['passed','failed','skipped','errors']}}
        variants.append(record)

g=fixture();u,v=g.entry,g.signal
a,b=u-sp.Rational(1,2),v-sp.Rational(1,2)
saddle=-a*a-b*b+3*a*b
H=sp.hessian(saddle,[u,v]);assert H.eigenvals()=={sp.Integer(1):1,sp.Integer(-5):1}
gain=sp.simplify(saddle.subs({u:sp.Rational(3,5),v:sp.Rational(3,5)})-saddle.subs({u:sp.Rational(1,2),v:sp.Rational(1,2)}))
assert gain==sp.Rational(1,100)
kwargs={'point':{u:sp.Rational(1,2),v:sp.Rational(1,2)},'bounds':{u:(0,1),v:(0,1)},'params':{},'gross':3,'upper_bound':3}
interior=check_point(saddle,**kwargs)
explicit=check_point(saddle,**kwargs,kinds={u:'interior',v:'interior'},payoff_for={u:saddle,v:saddle})
concave=check_point(-a*a-b*b,**kwargs)
assert concave.ok and concave.complete
boundary=check_point(-u*u-v*v+3*u*v,{u:0,v:0},{u:(0,1),v:(0,1)},{},gross=3,upper_bound=3)
assert not boundary.ok
g.objective=saddle;guarded_solver=pg.solve(g,g.strategies[0],g.numeric(POINT))
assert guarded_solver.rankable and guarded_solver.payoffs['x']>0
interior_record={'objective':str(saddle),'point':['1/2','1/2'],'exact_hessian':str(H),
                'exact_eigenvalues':{'1':1,'-5':1},'exact_improving_step_gain':str(gain),
                'report':report(interior),'explicit_metadata_report':report(explicit),
                'concave_control':report(concave),'same_hessian_boundary_control':report(boundary),
                'main_solver_control':packed(guarded_solver),
                'incorrect_low_level_complete':bool(interior.ok and interior.complete and explicit.ok and explicit.complete)}
finding1=any(x['incorrect_solver_rankable'] for x in variants)
finding2=interior_record['incorrect_low_level_complete']
result={'version':pg.__version__,'environment':{'import_path':pg.__file__,'python':platform.python_version(),'sympy':sp.__version__,'platform':platform.platform()},
        'R9-01':{'confirmed':finding1,'variants':variants,'scope':'One boundary Hessian precision defect; binary64 search cancellation is a trigger, not a second finding. Final-point payoff agreement can hold at a non-maximizing point.'},
        'R9-02':{'confirmed':finding2,**interior_record},
        'audit_approval':not(finding1 or finding2),'confirmed_counterexamples':bool(finding1 or finding2),
        'exit_one_meaning':'audit findings confirmed; analytic controls and probe execution successful'}
args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
print('R9-01',finding1,'R9-02',finding2,'import',pg.__file__)
raise SystemExit(1 if finding1 or finding2 else 0)
