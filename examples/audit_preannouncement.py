"""Inspect the supplied stylized model, with all configurations disclosed."""
from __future__ import annotations
import json
import os
import sys
try:
    import pacegame as pg
except ImportError:
    sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import pacegame as pg
import sympy as sp
from pacegame.analyze import rank_strategies,verify
PT={'sigma':.1,'phi':.85,'hatvarsigma':.3}
REP=dict(PT,kappa_d=.05)
def claims():
    return [verify.Dominates('RL','RF'),verify.Dominates('DF','DL'),
            verify.Dominates('RL','DF'),verify.Interior('varsigma','RL'),
            verify.Interior('delta','RL'),verify.Feasible()]
def configurations():
    repair=dict(keep_stock=True,signal_accrues=True,signal_cost=True)
    return [('baseline',pg.models.preannounce_entry(),PT),
            ('stock-cost variant',pg.models.preannounce_entry(**repair),REP),
            ('bounded-signal variant',pg.models.preannounce_entry(**repair,signal_ceiling=True),REP),
            ('readiness-lag variant',pg.models.preannounce_entry(**repair,entry_floor=True),dict(REP,**{'lambda':.1}))]
def main():
    print(f'PACEgame {pg.__version__}: numerical candidates, not Nash certificates')
    base=pg.models.preannounce_entry()
    silent=next(s for s in base.strategies if s.name=='DL')
    roots=pg.solve_symbolic(base,silent)
    print('Unconstrained stationary roots:',roots)
    for tag,g,point in configurations():
        print('\n'+tag)
        out=rank_strategies(g,point)
        print(out)
        for n,s in out.solutions.items():
            print(n,{str(k):v for k,v in s.kind.items()})
        report=verify.check(g,claims(),over={'sigma':(.05,.4),'phi':(.3,.95)},
                            n=3,fixed={k:v for k,v in point.items() if k not in ('sigma','phi')})
        print(report)
        print(verify.check(g,[verify.Competitive(n) for n in ('RF','RL','DF','DL')],
                            over={},fixed=point))
    st=next(s for s in base.strategies if s.name=='RL')
    expr=base.payoffs(st)['x'].subs(base.numeric(PT)).subs(base.entry,0)
    print('\nBaseline fixed-entry signal limit:',sp.limit(expr,base.signal,sp.oo))
    print('This limit is finite. The finite-cap search does not prove divergence.')
    return 0
if __name__=='__main__':
    raise SystemExit(main())
