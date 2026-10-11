"""Executable acceptance for all five findings from the v0.2.3 audit.

Optional arguments: output folder, actual metadata JSON, actual workflow YAML.
The packaged metadata snapshot and unified test entry are also available after
installation; full Word/TeX/template alignment is recorded by the release checks.
"""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
import json, platform, sys, importlib.util
import sympy as sp
import pacegame as pg
from pacegame.analyze import rank_strategies, derivative
from pacegame.core.share import Proportional
from pacegame.solve.feasible import check_point
from pacegame.tests import load_suite
from pacegame.examples.validate_audit_022 import FixedTenth, silence

POINT=dict(sigma=.1,phi=.85,hatvarsigma=.3,**{'lambda':.1})
EXPECTED_CODE=[('C1','Current code version'),('C2','Permanent link to code/repository used for this code version'),('C3','Permanent link to Reproducible Capsule'),('C4','Legal Code License'),('C5','Code versioning system used'),('C6','Software code languages, tools and services used'),('C7','Compilation requirements, operating environments and dependencies'),('C8','If available, link to developer documentation/manual'),('C9','Support email for questions')]
EXPECTED_SOFTWARE=[('S1','Current software version'),('S2','Permanent link to executables of this version'),('S3','Permanent link to Reproducible Capsule'),('S4','Legal Software License'),('S5','Computing platforms / Operating Systems'),('S6','Installation requirements and dependencies'),('S7','If available, link to user manual'),('S8','Support email for questions')]

def silent(quality=None,phi=None,**names):
    g=pg.models.preannounce_entry(keep_stock=True,entry_floor=True)
    return replace(g,share_rule=Proportional(g.share_rule.phi if phi is None else phi,quality),
                   strategies=tuple(s for s in g.strategies if not s.signals),**names)

def report(r):return {'ok':r.ok,'complete':r.complete,'findings':[vars(f) for f in r.findings]}
def outcome(o):
    return {'payoffs':o.payoffs,'rival_payoffs':o.rival_payoffs,'alike':o.alike,
            'best':o.best,'complete':o.complete,'role_conflict':o.role_conflict()}
def cases(suite):
    for test in suite:
        if hasattr(test,'_tests'):yield from cases(test)
        else:yield test.id()

def main(outdir='validation',metadata_path=None,workflow_path=None):
    assert pg.__version__=='0.2.11'
    groups={};x,y=sp.symbols('x y');wrong={}
    for kind in ['upper','upper corner','fixed']:
        r=check_point(x,{x:sp.Rational(1,2)},{x:(0,1)},{},gross=x,kinds={x:kind})
        assert not r.ok;wrong[kind]=report(r)
    missing=check_point(0,{x:0},{x:(0,0),y:(2,1)},{},gross=0)
    assert not missing.ok and any(f.check=='bounds' and f.status=='violation' for f in missing.findings)
    upper=check_point(x,{x:1},{x:(0,1)},{},gross=x,kinds={x:'upper corner'})
    fixed=check_point(x,{x:sp.Rational(1,2)},{x:(sp.Rational(1,2),sp.Rational(1,2))},{},gross=x,kinds={x:'fixed'})
    interior=check_point(x,{x:sp.Rational(1,2)},{x:(0,1)},{},gross=x,kinds={x:'interior'})
    assert upper.ok and upper.complete and fixed.ok and fixed.complete and not interior.ok and interior.complete
    groups['R5-01']={'wrong_kinds':wrong,'missing_coordinate':report(missing),'true_upper':report(upper),
                     'true_fixed':report(fixed),'nonstationary_interior':report(interior),'accepted':True}
    try:silent({'x':2,'z':2})
    except ValueError as error:rejected={'type':type(error).__name__,'reason':str(error)}
    else:raise AssertionError('unrelated quality player accepted')
    partial=rank_strategies(silent({'x':2}),POINT);normalized=rank_strategies(silent({'x':2,'y':1}),POINT)
    equal=rank_strategies(silent({'x':2,'y':2}),POINT)
    custom=rank_strategies(silent({'alpha':2},focal='alpha',rival='beta'),POINT)
    assert partial.payoffs==normalized.payoffs and partial.rival_payoffs==normalized.rival_payoffs
    assert partial.role_conflict() is None and normalized.role_conflict() is None and custom.role_conflict() is None
    assert not any(partial.alike.values()) and all(equal.alike.values()) and equal.role_conflict() is not None
    groups['R5-02']={'unknown_key_rejected':rejected,'partial':outcome(partial),'normalized':outcome(normalized),
                     'equal':outcome(equal),'custom_names':outcome(custom),'accepted':True}
    inventory=sorted(cases(load_suite()));modules=sorted({t.rsplit('.',2)[0] for t in inventory})
    assert any('test_audit_023' in t for t in inventory) and any('test_audit_024' in t for t in inventory)
    exporters=['validate_release','validate_audit_021','validate_audit_022','validate_audit_023','validate_audit_024']
    assert all(importlib.util.find_spec('pacegame.examples.'+module) is not None for module in exporters)
    workflow_checked=False
    if workflow_path:
        text=Path(workflow_path).read_text()
        assert "'-m','pacegame.tests'" in text and 'cwd=tempfile.mkdtemp()' in text
        assert all(module in text for module in exporters) and 'cwd=folder' in text
        workflow_checked=True
    groups['R5-03']={'test_count_loaded':len(inventory),'test_modules':modules,'exporters':exporters,
                     'workflow_checked':workflow_checked,'hosted_matrix_executed':False,'accepted':True}
    alpha=sp.Symbol('alpha',positive=True);results={}
    for label,coefficient,p,reference_phi in [('constant',sp.Rational(17,20),{k:v for k,v in POINT.items() if k!='phi'},.85),
            ('compound',2*alpha,dict({k:v for k,v in POINT.items() if k!='phi'},alpha=.85),1.7)]:
        g=silent(phi=coefficient);o=rank_strategies(g,p);ref=rank_strategies(silent(),dict(POINT,phi=reference_phi))
        error=max(abs(a[name]-b[name]) for a,b in [(o.payoffs,ref.payoffs),(o.rival_payoffs,ref.rival_payoffs)] for name in a)
        assert error<1e-15 and o.complete and ref.complete
        assert str(coefficient) not in g.parameters()
        results[label]={'parameters':sorted(g.parameters()),'coefficient':str(coefficient),'outcome':outcome(o),
                        'reference_outcome':outcome(ref),'maximum_payoff_difference':error,'payoffs_agree_within_1e_minus15':True}
    g=silence(silent(phi=2*alpha),FixedTenth);ref=silence(silent(),FixedTenth);slopes={}
    for player in ['x','y']:
        actual=derivative(g,'DF','alpha',dict(POINT,alpha=.85),quantity='pi_'+player).slope
        expected=2*derivative(ref,'DF','phi',dict(POINT,phi=1.7),quantity='pi_'+player,step=2e-4).slope
        assert abs(actual-expected)<1e-11
        slopes[player]={'actual':actual,'chain_rule_reference':expected}
    errors=[]
    for p in [dict(POINT),dict(POINT,alpha=-1)]:
        try:silent(phi=2*alpha).numeric(p)
        except (KeyError,ValueError) as error:errors.append({'type':type(error).__name__,'reason':str(error)})
    assert len(errors)==2
    groups['R5-04']={'configurations':results,'explicit_player_statics':slopes,'invalid_inputs':errors,'accepted':True}
    metadata_path=Path(metadata_path) if metadata_path else Path(__file__).with_name('manuscript_metadata.json')
    meta=json.loads(metadata_path.read_text())
    assert [(x[0],x[1]) for x in meta['code']]==EXPECTED_CODE
    assert [(x[0],x[1]) for x in meta['software']]==EXPECTED_SOFTWARE
    assert meta['code'][0][2]==meta['software'][0][2]==pg.__version__
    groups['R5-05']={'expected_fields':17,'checked_fields':17,'matched_fields':17,
        'comparison_basis':'supplied depth report Appendix C; current official template certification pending',
        'support_field':meta['software'][-1][1],'contact_pending':True,'accepted':True}
    record={'environment':{'pacegame':pg.__version__,'import_path':pg.__file__,'python':sys.version,
                          'sympy':sp.__version__,'platform':platform.platform()},
            'groups':groups,'all_accepted':all(g['accepted'] for g in groups.values())}
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True);path=out/'audit_024_acceptance.json'
    path.write_text(json.dumps(record,indent=2,ensure_ascii=False,allow_nan=False));print(path);return 0

if __name__=='__main__':raise SystemExit(main(*sys.argv[1:]))
