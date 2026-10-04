#!/usr/bin/env python3
"""Validate exported bytes, numeric checks, all pattern DXFs and PDF. No certification."""
from pathlib import Path
import json,hashlib,datetime,os
import fitz,ezdxf,numpy as np
ROOT=Path(__file__).resolve().parents[1]
read=lambda p:json.loads((ROOT/p).read_text())
checks=[]
def ok(name,value,detail=None):checks.append({'name':name,'passed':bool(value),'detail':detail})
cad=read('tests/CAD_checks.json');pat=read('tests/pattern_checks.json');th=read('thermal/verification.json')
ok('CAD declared checks',cad['all_passed'],len(cad['checks']))
ok('No thermal cassette intersections',all(r['intersection_cm3']<.001 for r in read('tests/interference_pairs.json')))
ok('Four STEP exports',len(list((ROOT/'cad').glob('*.step')))==4)
ok('Metric pattern criterion <=2 percent',pat['max_metric_distortion_percent']<=2,pat['max_metric_distortion_percent'])
ok('Matched source segment difference <=1 mm',pat['max_seam_mismatch_mm']<=1,pat['max_seam_mismatch_mm'])
registry=read('patterns/patterns_registry.json');ok('Unique pattern IDs',len({r['id'] for r in registry})==len(registry))
for r in registry:
 d=ezdxf.readfile(ROOT/'patterns'/(r['id']+'.dxf'));a=d.audit();ok('DXF '+r['id'],not a.errors and not a.fixes and d.units==4)
nest=read('patterns/nesting.json');bad=[]
for i,a in enumerate(nest):
 for b in nest[i+1:]:
  if a['material']!=b['material']:continue
  if min(a['x_mm']+a['width_mm'],b['x_mm']+b['width_mm'])>max(a['x_mm'],b['x_mm']) and min(a['y_mm']+a['height_mm'],b['y_mm']+b['height_mm'])>max(a['y_mm'],b['y_mm']):bad.append([a['id'],b['id']])
ok('Pattern nesting bounding boxes do not overlap',not bad,bad)
for r in read('harness/routes.json'):
 ok('Harness left-only '+r['id'],not r['right_exit_crossed'])
 ok('Harness cut reserve '+r['id'],r['cut_length_mm']>=r['centerline_length_mm']+r['service_allowance_mm']+80)
ok('Receiver balances close',th['all_energy_balances_pass'],th['max_abs_residual_W'])
with fitz.open(ROOT/'docs/Lezhandr_R08_CAD_Cutting_Assembly.pdf') as d:
 ok('Report is 16 pages',len(d)==16)
 for i,p in enumerate(d):
  bounds=[]
  for b in p.get_text('blocks'):
   if len(b)>6 and b[6]==0 and not (0<=b[0]<b[2]<=p.rect.width+1 and 0<=b[1]<b[3]<=p.rect.height+1):bounds.append(b[:4])
  ok(f'PDF text bounds page {i+1}',not bounds,bounds)
  if i in [0,2,3,14]:p.get_pixmap(matrix=fitz.Matrix(.8,.8)).save(ROOT/'tests'/f'report_review_{i+1:02}.png')
with fitz.open(ROOT/'patterns/R08_patterns_P0_1to1.pdf') as d:ok('1:1 PDF matches registry',len(d)==len(registry),len(d))
result={'revision':'R08','checks':checks,'passed':sum(c['passed'] for c in checks),'total':len(checks),'all_passed':all(c['passed'] for c in checks),'workflow_run_id':os.getenv('GITHUB_RUN_ID'),'verified_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'manufacturing_approved':False,'human_tested':False,'electrical_hardware_updated':False}
(ROOT/'tests/verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
files=[]
for p in sorted(ROOT.rglob('*')):
 if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ['.pyc','.zip'] and p.name!='MANIFEST_SHA256.json' and 'pdf_qc' not in p.parts:
  if p.suffix.lower() in ['.ttf','.otf','.woff','.woff2']:raise RuntimeError('Font binary must not be published')
  files.append({'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(ROOT/'MANIFEST_SHA256.json').write_text(json.dumps({'files':files,'count':len(files)},ensure_ascii=False,indent=2)+'\n')
print('VALIDATION',result['passed'],result['total'],'FILES',len(files),flush=True)
if not result['all_passed']:raise SystemExit(1)
