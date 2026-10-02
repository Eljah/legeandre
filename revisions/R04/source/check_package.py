from pathlib import Path
import json,hashlib,platform,shutil,importlib.metadata as md
import numpy as np,ezdxf
R=Path(__file__).resolve().parents[1]
model=json.loads((R/'cad/model_R04.json').read_text());ps=json.loads((R/'patterns/patterns_R04.json').read_text())
checks=[]
def ck(name,result,detail):checks.append({'test':name,'pass':bool(result),'detail':detail})
ids=[o['id'] for o in model]
ck('Unique model IDs',len(ids)==len(set(ids)),len(ids))
ck('No hand-heater CAD part',not any(x=='EH3' or x=='HZ3' for x in ids),'Body EH0-EH2 are only location references.')
ck('Passive hood in project.json',json.loads((R/'project.json').read_text())['hand_heater']['power_W']==0,'No canopy heating/cabling modeled.')
for state in ['work_closed','work_open','sleep']:
    d=json.loads((R/'tests'/f'STEP_{state}.json').read_text());ck('STEP reimport '+state,d['reimported_valid'],{'solids':d['solid_count'],'parts':len(d['part_ids'])})
for n in ['hood','foot_quilt','sleep_quilt']:
    a=np.load(R/'simulation'/f'{n}_drape.npz');m=json.loads((R/'simulation'/f'{n}_metrics.json').read_text());ck('Finite vertices '+n,np.isfinite(a['final_m']).all(),m['vertices']);ck('Fixed pins '+n,m['max_pin_error_mm']<1e-8,m['max_pin_error_mm']);ck('Small last-step motion '+n,m['last_step_motion_mm']<.05,{'last_step_motion_mm':m['last_step_motion_mm'],'threshold_mm':.05,'not_physical_validation':True})
for p in sorted((R/'patterns/pieces').glob('*.dxf')):
    d=ezdxf.readfile(p);a=d.audit();ck('DXF '+p.name,not a.errors and not a.fixes and d.units==4,{'errors':len(a.errors),'fixes':len(a.fixes),'units':d.units})
cl=json.loads((R/'tests/hood_clearances.json').read_text());ck('Keyboard canopy-only sightlines',cl['canopy_occluded_samples_open']==0,cl)
body=np.concatenate([np.asarray(o['vertices_mm']) for o in model if o['id'].startswith(('O','L','FLOOR_','SOFT_')) and 'vertices_mm' in o])
bounds={'bbox_mm':[body.min(0).tolist(),body.max(0).tolist()],'extent_mm':(body.max(0)-body.min(0)).tolist(),'nominal_support_shape_not_loaded':True}
(R/'tests/body_bounds.json').write_text(json.dumps(bounds,indent=2))
ck('Body at floor',abs(body[:,2].min())<.1,bounds)
report={'checks':checks,'passed':sum(c['pass'] for c in checks),'total':len(checks),'release_status':'RESEARCH MODEL ONLY','known_rejections':['Shell flat patterns: up to 8.61% edge distortion; no production release.','Initial sleep drape trial was unstable; saved in simulation/rejected_trials.','No named commercial apparel solver was run.','No calibrated filler, human load, self-collision, heat or sewing validation.']}
(R/'tests/verification.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
versions={p:md.version(p) for p in ['cadquery','vtk','numpy','scipy','numba','ezdxf','reportlab','Pillow']}
(R/'tests/environment.json').write_text(json.dumps({'os':platform.platform(),'python':platform.python_version(),'packages':versions,'executables':{x:shutil.which(x) for x in ['CLO','Rhino','blender','inkscape','Xvfb']},'commercial_plugin_search_results':0,'blender_install':'attempted download/install; unavailable in runtime'},indent=2))
provenance=[]
for p in [Path('/mnt/data/Spim_s_haski_Lezhandr_R02.zip'),Path('/mnt/data/Spim_s_haski_R03_Embroidery.zip')]:
    if p.exists():provenance.append({'name':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(R/'history/provenance.json').write_text(json.dumps(provenance,indent=2))
print(report['passed'], '/', report['total'], 'automated checks; production release excluded')
