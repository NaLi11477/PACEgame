"""Export executable acceptance evidence for the seven second-audit groups."""
from __future__ import annotations
import contextlib
import io
import json
import os
import platform
import sys
import sympy as sp
import pacegame as pg
from pacegame.analyze import threshold,critical_value,verify
from pacegame.cli import main as cli_main
from pacegame.solve.feasible import check_point
from pacegame.examples.validate_release import pack_sol,quadrature

P={'sigma':.1,'phi':.85,'hatvarsigma':.3}
def st(g,n):return next(s for s in g.strategies if s.name==n)
def pack_report(r):
    return {'ok':r.ok,'complete':r.complete,
            'claims':[{'claim':x.claim,'passed':x.passed,'failed':x.failed,
                       'skipped':x.skipped,'errors':x.errors,'holds':x.holds,
                       'reasons':x.reasons} for x in r.results]}
def command(args):
    out=io.StringIO()
    with contextlib.redirect_stdout(out),contextlib.redirect_stderr(out):
        code=cli_main(args)
    return {'exit':code,'stdout':out.getvalue()}

def main(outdir='validation'):
    os.makedirs(outdir,exist_ok=True)
    rec={'software_version':pg.__version__,'python':sys.version,
         'platform':platform.platform(),'sympy':sp.__version__,
         'package_path':pg.__file__,'groups':{}}
    cmds=[command(['sweep','preannounce_entry','--wrt','sigma','--from','.1','--to','.2','--steps','1']),
          command(['sweep','preannounce_entry','--repair','--wrt','sigma','--from','.1','--to','.2','--steps','1']),
          command(['sweep','preannounce_entry','--wrt','TYPO','--from','.1','--to','.2'])]
    rec['groups']['R2-01']={'commands':cmds,'accepted':[c['exit'] for c in cmds]==[1,0,2]}

    b=pg.models.preannounce_entry();e,d=b.entry,b.signal
    phi,sigma=b.share_rule.phi,b.lifecycle.sigma
    silent=tuple(s for s in b.strategies if not s.signals)
    class Gap(pg.Game):
        def payoffs(self,s):
            v=sp.Rational(1,1000)*(phi if s.name=='DF' else 1)
            return {'x':v,'y':v}
    class Slope(pg.Game):
        def payoffs(self,s):
            v=sp.Rational(1,1000)*(1+sigma*(phi-1))
            return {'x':v,'y':v}
    g=Gap(b.lifecycle,b.share_rule,e,d,strategies=silent)
    h=Slope(b.lifecycle,b.share_rule,e,d,strategies=silent)
    roots=[{'scan':n,'payoff_threshold':threshold(g,'phi',.5,1.5,P,'DF','DL',scan=n),
            'derivative_threshold':critical_value(h,'DL','sigma','phi',.5,1.5,P,scan=n)} for n in [2,3,12]]
    rec['groups']['R2-02']={'reference':1,'roots':roots,
        'accepted':all(abs(q['payoff_threshold']-1)<1e-8 and abs(q['derivative_threshold']-1)<1e-8 for q in roots)}

    g=pg.models.preannounce_entry(keep_stock=True,signal_accrues=True,signal_cost=True,entry_floor=True)
    p=dict(P,kappa_d=.05,**{'lambda':.3})
    sol=pg.solve(g,st(g,'RL'),g.numeric(p))
    rec['groups']['R2-03']={'parameters':p,'solution':pack_sol(sol),
        'reference':{'delta':1.05,'varsigma':.3,'pi_x':.0275625},
        'accepted':sol.rankable and sol.kind[g.entry]=='fixed' and abs(sol.payoffs['x']-.0275625)<1e-12}

    g=pg.models.preannounce_entry();g.share_rule.quality={'x':sp.Integer(1),'y':1+sp.floor(g.share_rule.phi)}
    sol=pg.solve(g,st(g,'DL'),g.numeric(P))
    rep=verify.check(g,[verify.Competitive('DL')],over={'phi':(.5,.85)},n=3,fixed=P)
    rec['groups']['R2-04']={'quality':'x:1, y:1+floor(phi)','solution':pack_sol(sol),
        'report':pack_report(rep),'accepted':rep.results[0].skipped==3 and rep.results[0].passed==0 and not rep.complete}

    short=pg.models.logistic_entry();short.lifecycle.horizon=sp.Rational(1,2)
    ss=pg.solve(short,st(short,'DL'),short.numeric(pg.models.LOGISTIC_POINT))
    four=pg.models.preannounce_entry(entry_floor=True);four.lifecycle.horizon=sp.Integer(4)
    fp=dict(P,hatvarsigma=3,**{'lambda':3})
    fs=pg.solve(four,st(four,'DF'),four.numeric(fp));at=four.numeric(fp);at.update(fs.point)
    ceiling=float(four.demand_ceiling(st(four,'DF'),at).subs(at))
    q=[{'case':'logistic T=.5, DL','players':quadrature(short,st(short,'DL'),pg.models.LOGISTIC_POINT,ss)},
       {'case':'TwoPhase T=4, DF','players':quadrature(four,st(four,'DF'),fp,fs)}]
    rec['groups']['R2-05']={'short_logistic':pack_sol(ss),'long_two_phase':pack_sol(fs),
        'long_ceiling':ceiling,'long_analytic_gross':.1875,'quadrature':q,
        'accepted':ss.rankable and float(ss.point[short.entry])<=.5 and fs.rankable
                   and abs(fs.payoffs['x']-.1875)<1e-12 and ceiling+1e-12>=.1875
                   and all(p['absolute_error']<1e-10 for row in q for p in row['players'].values())}

    x,bb,u=sp.symbols('x b u')
    unknown=check_point(1-x*x,{x:0},{x:(bb,bb+1)},{},upper_bound=u,gross=1-x*x)
    negative=check_point(-1-x*x,{x:0},{x:(-1,1)},{})
    rec['groups']['R2-06']={'unknown_required_checks':{'ok':unknown.ok,'complete':unknown.complete,'findings':[vars(f) for f in unknown.findings]},
        'negative_net_omitted_gross':{'ok':negative.ok,'complete':negative.complete,'findings':[vars(f) for f in negative.findings]},
        'accepted':not unknown.complete and negative.ok and negative.complete
                   and not any(f.check=='bounds' and f.status=='ok' for f in unknown.findings)}

    class Open(pg.Game):
        def payoffs(self,s):return {'x':sp.log(1+d)/1000,'y':-(e-sp.Rational(3,20))**2}
    g=Open(b.lifecycle,b.share_rule,e,d,strategies=(st(b,'RF'),))
    rep=verify.check(g,[verify.Interior('varsigma',strategy='RF')],over={},fixed=P)
    rec['groups']['R2-07']={'scope':'whole valid candidate','report':pack_report(rep),
        'accepted':rep.results[0].skipped==1 and not rep.complete}
    rec['all_accepted']=all(v['accepted'] for v in rec['groups'].values())
    target=os.path.join(outdir,'audit_021_acceptance.json')
    with open(target,'w',encoding='utf-8') as f:json.dump(rec,f,ensure_ascii=False,indent=2,allow_nan=False)
    if not rec['all_accepted']:raise AssertionError('at least one acceptance group failed; inspect '+target)
    print(target)
    return 0
if __name__=='__main__':raise SystemExit(main(sys.argv[1] if len(sys.argv)>1 else 'validation'))
