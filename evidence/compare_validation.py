"""Compare fresh environments and separately list changes from frozen v0.2.10."""
from pathlib import Path
import json,math
A=Path(__file__).resolve().parent.parent;B=A/'evidence'
load=lambda p:json.loads(p.read_text())
result={'environments':['source','wheel','core'],'acceptance_groups':[],'excluded_group_fields':{'R6-05':['installed_versions','installed_matches_snapshot']}}
names=[f'audit_{n:03}_acceptance.json' for n in range(21,30)]+['audit_0210_acceptance.json','audit_0211_acceptance.json'];total=0
for name in names:
 docs=[load(B/f'validation_{e}'/name) for e in result['environments']];gs=[d['groups'] for d in docs]
 for g in gs:
  for k in result['excluded_group_fields']['R6-05']:
   if 'R6-05' in g:g['R6-05'].pop(k,None)
 row={'exporter':name,'count':len(gs[0]),'all_accepted':all(d['all_accepted'] for d in docs),'source_wheel_equal':gs[0]==gs[1],'source_core_equal':gs[0]==gs[2]}
 assert all(row[k] for k in ('all_accepted','source_wheel_equal','source_core_equal'));total+=row['count'];result['acceptance_groups'].append(row)
assert total==41;result['groups_per_environment']=total
new=[load(B/f'validation_{e}/release_validation.json') for e in result['environments']];old=load(A.parent/'audit_v0210/work/PACEgame_v0_2_10/evidence/validation_source/release_validation.json')
def differences(a,b,path=''):
 if type(a)!=type(b):return [{'path':path,'parent':a,'revision':b}]
 if isinstance(a,dict):
  out=[]
  for k in sorted(set(a)|set(b)):
   if k not in a or k not in b:out.append({'path':path+'/'+k,'parent':a.get(k),'revision':b.get(k)})
   else:out+=differences(a[k],b[k],path+'/'+k)
  return out
 if isinstance(a,list):
  if len(a)!=len(b):return [{'path':path,'parent':a,'revision':b}]
  return [x for i,(aa,bb) in enumerate(zip(a,b)) for x in differences(aa,bb,path+'/'+str(i))]
 return [] if a==b else [{'path':path,'parent':a,'revision':b}]
result['baseline']={}
for k in ('cases','quadrature','finite_asymptote','analytic_sequential_toy'):
 assert new[0][k]==new[1][k]==new[2][k]
 dif=differences(old[k],new[0][k]);result['baseline'][k]={'source_wheel_core_equal':True,'frozen_release_exact_equal':not dif,'parent_differences':dif}
 # Only independently reviewable small changes in finite-difference response values
 # may differ from the frozen baseline; decisions, payoffs, verdicts stay exact.
 for d in dif:
  assert isinstance(d['parent'],(int,float)) and isinstance(d['revision'],(int,float)),d
  assert '/slope' in d['path'] or '/response' in d['path'],d
  assert math.isclose(d['parent'],d['revision'],rel_tol=1e-9,abs_tol=1e-10),d
result['all_comparisons_passed']=True;(B/'validation_comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
