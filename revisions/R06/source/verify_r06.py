#!/usr/bin/env python3
"""Independent readback and limited geometry checks. No mechanical certification."""
from pathlib import Path
import json,sys,hashlib,platform,importlib.metadata as im
import cadquery as cq
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
items=json.loads((ROOT/'cad/model_R06.json').read_text());proj=json.loads((ROOT/'project.json').read_text());checks=[]
def check(name,ok,detail=None):checks.append({'check':name,'passed':bool(ok),'detail':detail})
# Reopen output files; never substitute successful creation for readback.
for p in sorted((ROOT/'cad').glob('*.step')):
 sh=cq.importers.importStep(str(p)).val();check('STEP '+p.name,sh.isValid(),{'solids':len(sh.Solids()),'faces':len(sh.Faces())})
check('Unique component IDs',len({o['id'] for o in items})==len(items),len(items))
check('No inclined spinal frame',not any(o['id'].startswith('F_BACK') or o['id']=='BACK_SLING' for o in items))
beams=json.loads((ROOT/'cad/table_members.json').read_text());xa=min(min(b['a'][0],b['b'][0]) for b in beams);xb=max(max(b['a'][0],b['b'][0]) for b in beams)
check('Local desk frame only',xa>=950 and xb<=1570,[xa,xb])
check('No heater in keyboard flap',proj['changes']['hand_heater'] is False)
for o in items:
 if o['group'] in ['upper','keyboard','lower_quilt']:
  check('Padded closed volume '+o['id'],o['solid_count']>0 and o['volume_litre']>0,o['volume_litre'])
check('Same outer cloth color',all(o['kind']=='cloth' for o in items if o['group'] in ['upper','keyboard','lower_quilt','lower_shell']))
fs=json.loads((ROOT/'calculations/foot_settings.json').read_text());check('Ordered height stations',[r['stop_front_x_mm'] for r in fs]==sorted(r['stop_front_x_mm'] for r in fs));check('Foot range 220 mm',fs[-1]['stop_front_x_mm']-fs[0]['stop_front_x_mm']==220)
ss=json.loads((ROOT/'calculations/table_stability.json').read_text())
check('Four nominal self-weight cases',len(ss)==4 and all(s['minimum_margin_mm']>0 for s in ss),[s['minimum_margin_mm'] for s in ss])
if (ROOT/'tests/DXF_draft_audit.json').exists():
 for a in json.loads((ROOT/'tests/DXF_draft_audit.json').read_text()):check('Draft DXF '+a['file'],a['errors']==0 and a['fixes']==0 and a['units']==4,a)
# Bounds of the physical work assembly (not mannequin or rejected states).
physical=[o for o in items if 'work' in o['states'] and o['group'] not in ['human']]
bb=np.array([o['tessellation_bounds_mm'] for o in physical]);lo=bb[:,[0,2,4]].min(0);hi=bb[:,[1,3,5]].max(0)
check('No table padding below floor',all(o['tessellation_bounds_mm'][4]>=-0.1 for o in items if o['group']=='frame_padding'))
# Exact hard-part clearance under the unchanged R05 reference body.
a=cq.Assembly.load(str(ROOT/'cad/Lezhandr_R06_occupied_interior.step'))
bodyids=[n for n in a.objects if n.startswith(('M_TORSO','M_PELVIS','M_HEAD','M_THIGH','M_SHIN'))]
hardids=[n for n in a.objects if n.startswith('D_BASE') or n.startswith('D_C') or n=='TRAY_VENTED']
bodies=cq.Compound.makeCompound([a.objects[n].obj.located(a.objects[n].loc) for n in bodyids])
hard=cq.Compound.makeCompound([a.objects[n].obj.located(a.objects[n].loc) for n in hardids])
clear=bodies.distance(hard)
clearreport={'minimum_body_to_frame_or_tray_mm':clear,'body_parts':bodyids,'hard_parts':hardids,'scope':'Single nominal posture only; excludes hands on keyboard, deformed filler, joints under load and exit motion.'}
(ROOT/'calculations/nominal_hard_clearance.json').write_text(json.dumps(clearreport,indent=2))
check('No nominal torso/leg intersection with bare desk frame',clear>0,clearreport)
# No claim that different CAD filler envelopes preserve a granular charge.
fill=[]
for name in ['WORK','RELAX']:
 fill.append({'state':name,'forming_envelope_litre':sum(o['volume_litre'] for o in items if o['group']=='forming_fill' and name in o['id']),'contact_envelope_litre':sum(o['volume_litre'] for o in items if o['group']=='contact_fill' and name in o['id']),'fill_fraction':'not assigned','same_charge_kinematics':'not validated'})
(ROOT/'calculations/filler_envelopes.json').write_text(json.dumps(fill,indent=2))
# Cross-section outlines from the same CAD grid to millimetre DXF, not a pattern.
import ezdxf
cover=json.loads((ROOT/'cad/cover_grids.json').read_text());g=cover['Q04_KEYBOARD_CLOSED'];outer=np.array(g['outer_grid_mm'])[5];inner=np.array(g['inner_grid_mm'])[5]
d=ezdxf.new('R2010');d.units=4;ms=d.modelspace();ms.add_lwpolyline(outer[:,1:3],dxfattribs={'color':5});ms.add_lwpolyline(inner[:,1:3],dxfattribs={'color':3});ms.add_line(outer[17,1:3],inner[17,1:3],dxfattribs={'color':1});d.saveas(ROOT/'cad/section_Q04_outer_inner_mm.dxf')
versions={'python':sys.version,'platform':platform.platform(),'cadquery':cq.__version__}
for n in ['vtk','numpy','scipy','ezdxf','reportlab']:
 try:versions[n]=im.version(n)
 except Exception:pass
(ROOT/'tests/software_versions.json').write_text(json.dumps(versions,indent=2))
summary={'checks':checks,'passed':sum(c['passed'] for c in checks),'total':len(checks),'physical_tessellated_bounds_mm_approx':[lo.tolist(),hi.tolist()],'physical_tessellated_dimensions_mm_approx':(hi-lo).tolist(),'table_tube_mass_kg':sum(b['mass_kg'] for b in beams),'all_checks_passed':all(c['passed'] for c in checks)}
(ROOT/'tests/verification.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in summary.items() if k!='checks'},ensure_ascii=False,indent=2),flush=True)
