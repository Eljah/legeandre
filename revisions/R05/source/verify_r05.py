#!/usr/bin/env python3
"""Independent output consistency checks; not certification or a physical test."""
from pathlib import Path
import json,hashlib,math,importlib.metadata
import numpy as np
import ezdxf
from lxml import etree
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads((ROOT/p).read_text())
checks=[]
def check(name,ok,detail=''):
 checks.append({'check':name,'pass':bool(ok),'detail':detail})
model=read('cad/model_R05.json');project=read('project.json')
check('Unique CAD item identifiers',len({q['id'] for q in model})==len(model))
check('Hand heater absent by project requirement',project['hand_heater'] is False)
check('Fabric flap has no rigid arch',read('calculations/visibility.json')['no_hard_flap_arch'])
old=read('history/R04/surfaces_R04.json');old={p['id']:p for p in old if p['id'].startswith(('O','L'))}
ret=[q for q in model if q['id'].startswith('R04_')]
check('All 24 R04 exterior/lining source grids retained',len(ret)==24 and all(np.array_equal(q['grid_mm'],old[q['id'][4:]]['grid_mm']) for q in ret))
for p in sorted((ROOT/'tests').glob('STEP_*.json')):
 a=json.loads(p.read_text());check('STEP round-trip: '+p.stem,a['valid_after_reimport'] and a['faces']>0,f"{a['solids']} solids, {a['faces']} faces; surfaces are also present")
for p in sorted((ROOT/'patterns').rglob('*.dxf')):
 d=ezdxf.readfile(p);a=d.audit();check('DXF '+p.name,not a.errors and not a.fixes and d.units==4,'units mm; no audit errors or automatic fixes')
for p in sorted((ROOT/'patterns').rglob('*.svg')):
 r=etree.parse(str(p));check('SVG parse '+p.name,r.getroot().tag.endswith('svg'))
v=read('calculations/visibility.json');check('Reference gaze: flap rolled',v['rolled_blocked']==0 and v['tested_keys']==140)
check('Reference gaze: flap closed',v['closed_blocked']==140)
a=read('calculations/exit_clearance.json');check('Nine static bare-body/rigid clearance samples positive',len(a['poses'])==9 and a['minimum_distance_mm']>0,'Not swept continuous motion, padding clearance, or an ability-to-stand proof')
b=read('cad/beams_R05.json');check('C top connections originate on occupant left',all(t['a_mm'][1]<0 and t['b_mm'][1]>0 for t in b if t['id'] in ['C1_UPPER','C2_UPPER']))
check('No C upright on occupant right',all(t['a_mm'][1]<0 for t in b if t['id'].startswith('C') and 'UPRIGHT' in t['id']))
check('Rigid axes confined to central x region',all(min(t['a_mm'][0],t['b_mm'][0])>=550 and max(t['a_mm'][0],t['b_mm'][0])<=1500 for t in b),'Bounds concern member axes, not the full padded or fabric envelope')
for q in read('patterns/seam_pairs.json'):check('Seam '+q['seam_id'],abs(q['length_a_mm']-q['length_b_mm'])<1e-6 and q['maximum_vertex_mismatch_mm']<1e-6)
p=read('patterns/summary.json');check('Discrete developable edge metric',p['new_developable_edge_max_relative_error']<1e-9,'Discrete numerical metric only, not an actual fabric or sewing tolerance')
check('Old outer shell patterns NOT released',p['old_shell_patterns_released'] is False)
for a in read('calculations/empty_stability_parked.json'):check(f"Gravity projection, parked, laptop {a['laptop_mass_kg']} kg",a['minimum_gravity_margin_mm']>0,'On rigid flat support polygon, not on deforming cushion')
check('Rear/keyboard flap no electrical parts',not any('HEAT' in q['id'] or 'WIRE' in q['id'] for q in model if q['group']=='quilt'))
result={'passed':sum(x['pass'] for x in checks),'total':len(checks),'checks':checks,'scope':'Digital output consistency only; no load, thermal, clinical, filler, or sewing trial.'}
(ROOT/'tests/verification.json').write_text(json.dumps(result,indent=2,ensure_ascii=False))
versions={p:importlib.metadata.version(p) for p in ['cadquery','vtk','numpy','scipy','shapely','ezdxf','reportlab','Pillow','PyMuPDF','lxml']}
(ROOT/'tests/software_versions.json').write_text(json.dumps(versions,indent=2))
(ROOT/'requirements.txt').write_text('\n'.join(f'{k}=={v}' for k,v in versions.items())+'\n')
archive=ROOT/'history/Spim_s_haski_Lezhandr_R04_original.zip'
(ROOT/'history/R04_SHA256.txt').write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name+'\n')
print(json.dumps({'passed':result['passed'],'total':result['total'],'failed':[q for q in checks if not q['pass']]},ensure_ascii=False,indent=2))
if result['passed']!=result['total']:raise SystemExit(1)
