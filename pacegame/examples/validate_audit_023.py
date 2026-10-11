"""Executable acceptance of the three fourth-audit findings (not old defect reproduction)."""
from __future__ import annotations
import json, platform, sys
from dataclasses import dataclass, field, replace
from pathlib import Path
import sympy as sp
import pacegame as pg
from pacegame.analyze import derivative, rank_strategies, sweep, verify
from pacegame.core.lifecycle import TwoPhase, Segment
from pacegame.examples.validate_audit_022 import POINT, FixedTenth, silence, strategy, pack_solution, pack_report

@dataclass
class KeyedTwoPhase(TwoPhase):
    weights: dict = field(default_factory=lambda: {1: sp.Integer(2)})
    lookup: object = 1
    @property
    def gain(self):
        return self.weights.get('phase', self.weights).get(self.lookup, sp.Integer(1))
    def segments(self, *args, **kw):
        return [Segment(s.lo, s.hi, self.gain*s.expr) for s in super().segments(*args, **kw)]
    def capacity(self):return self.gain*super().capacity()

class Once:
    def __init__(self,values):self.values=values;self.iterations=0
    def __iter__(self):
        self.iterations+=1
        if self.iterations!=1:raise AssertionError('iterable consumed twice')
        return iter(self.values)

def keyed(weights=None,lookup=1):
    b=pg.models.preannounce_entry();l=b.lifecycle
    life=KeyedTwoPhase(l.sigma,l.growth_end,l.horizon,l.keep_stock,
                      {1:sp.Integer(2)} if weights is None else weights,lookup)
    return replace(b,lifecycle=life)

def solve_df(g):return pg.solve(g,strategy(g,'DF'),g.numeric(POINT))

def brief(o):
    return {'point':o.point,'payoffs':o.payoffs,'best':o.best,'complete':o.complete}

def main(outdir='validation'):
    assert pg.__version__=='0.2.11'
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True)
    groups={};states=[]
    for label,initial,mutated,lookup in [
        ('integer/string',{1:sp.Integer(2)},{'1':sp.Integer(2)},1),
        ('symbol assumptions',{sp.Symbol('gain'):sp.Integer(2)},
             {sp.Symbol('gain',positive=True):sp.Integer(2)},sp.Symbol('gain')),
        ('nested dictionary',{'phase':{1:sp.Integer(2)}},{'phase':{'1':sp.Integer(2)}},1)]:
        g=keyed(initial,lookup);before=solve_df(g);fp=g._fingerprint()
        g.lifecycle.weights=mutated;changed=fp!=g._fingerprint();after=solve_df(g)
        fresh=solve_df(replace(g));g.invalidate();explicit=solve_df(g)
        assert changed and before.rankable and after.rankable
        assert after.payoffs==fresh.payoffs==explicit.payoffs
        assert abs(before.payoffs['x']-51/8000)<1e-15 and abs(after.payoffs['x']-51/16000)<1e-15
        states.append({'case':label,'fingerprint_changed':changed,'before':pack_solution(before),
                       'after':pack_solution(after),'fresh':pack_solution(fresh),'invalidated':pack_solution(explicit)})
    g=keyed({1:sp.Integer(2),'unused':sp.Integer(3)});fp=g._fingerprint();s=solve_df(g)
    g.lifecycle.weights={'unused':sp.Integer(3),1:sp.Integer(2)}
    assert fp==g._fingerprint() and solve_df(g).payoffs==s.payoffs
    groups['R4-01']={'states':states,'insertion_order_ignored':True,'accepted':True}

    g=silence(pg.models.preannounce_entry(keep_stock=True),FixedTenth);st=strategy(g,'DF');p=g.share_rule.phi
    sub={g.lifecycle.sigma:sp.Rational(1,10),p:sp.Rational(17,20),
         g.lifecycle.growth_end:sp.Rational(3,10),g.entry:sp.Rational(1,10)}
    exact={k:sp.simplify(sp.diff(v,p).subs(sub)) for k,v in g.payoffs(st).items()}
    assert exact=={'x':sp.Rational(160,16136289),'y':-sp.Rational(160,16136289)}
    reports={};slopes={}
    for target in ['pi_x','pi_y']:
        slopes[target]=derivative(g,'DF','phi',POINT,quantity=target).slope
        for relation in ['>','<']:
            rep=verify.check(g,[verify.Sign(f'd {target} / d phi',relation,strategy='DF')],
                over={'phi':[.85]},fixed={'sigma':.1,'hatvarsigma':.3})
            good=(target,relation) in [('pi_x','>'),('pi_y','<')]
            assert rep.complete and rep.results[0].passed==int(good) and rep.results[0].failed==int(not good)
            reports[target+relation]=pack_report(rep)
    rejected=[]
    for expr in ['d pi_UNKNOWN / d phi','d varsigma / d phi','d banana / d phi',
                 'd pi_x / d TYPO','d pi_x / d phi / d sigma','pi_x/phi','d pi_x/dphi']:
        try:verify.check(g,[verify.Sign(expr,'>',strategy='DF')],over={},fixed=POINT)
        except ValueError as e:rejected.append({'expr':expr,'type':type(e).__name__,'reason':str(e)})
    assert len(rejected)==7 and slopes['pi_x']>0 and slopes['pi_y']<0
    assert max(abs(slopes['pi_'+k]-float(x)) for k,x in exact.items())<1e-12
    custom=replace(g,focal='alpha',rival='beta')
    rep=verify.check(custom,[verify.Sign('d pi_beta / d phi','<',strategy='DF')],over={},fixed=POINT)
    assert rep.results[0].passed==1 and rep.complete
    groups['R4-02']={'exact_derivatives':{k:str(x) for k,x in exact.items()},'numerical_slopes':slopes,
        'reports':reports,'rejected':rejected,'custom_player_report':pack_report(rep),'accepted':True}

    pool=[strategy(g,'DF'),strategy(g,'DL')];fixed={'sigma':.1,'hatvarsigma':.3}
    factories=[('list',list),('tuple',tuple),('iterator',iter),('generator',lambda xs:(s for s in xs)),('once',Once)]
    results={}
    for label,factory in factories:
        selected=factory(pool)
        results[label]=[brief(o) for o in sweep(g,'phi',[.8,.85,.9],fixed,selected)]
        if isinstance(selected,Once):assert selected.iterations==1
    assert all(x==results['list'] for x in results.values())
    failures=[]
    for selected in [[],[pool[0],pool[0]],[pg.Strategy('UNKNOWN',False,True)]]:
        try:sweep(g,'phi',[],fixed,selected)
        except ValueError as e:failures.append(str(e))
    assert len(failures)==3 and sweep(g,'phi',[],fixed,pool)==[]
    one=rank_strategies(g,POINT,(s for s in pool));assert one.complete
    groups['R4-03']={'multi_point_results':results,'early_invalid_pools':failures,
                     'valid_empty_values':[],'single_point_generator':brief(one),'accepted':True}
    record={'environment':{'pacegame':pg.__version__,'import_path':pg.__file__,'python':sys.version,
              'sympy':sp.__version__,'platform':platform.platform()},'groups':groups,'all_accepted':True}
    path=out/'audit_023_acceptance.json';path.write_text(json.dumps(record,indent=2,ensure_ascii=False,allow_nan=False))
    print(path);return 0

if __name__=='__main__':raise SystemExit(main(sys.argv[1] if len(sys.argv)>1 else 'validation'))
