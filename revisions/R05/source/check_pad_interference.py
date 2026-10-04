"""Triangle-surface intersection screen of nominal pads, not pressure/contact mechanics."""
import sys,json
from pathlib import Path
import numpy as np
import vtk
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'source'))
from render_r05 import poly
items=json.loads((ROOT/'cad/model_R05.json').read_text())
pads=[o for o in items if o['group']=='frame_padding'];body=[o for o in items if o['id'].startswith('EXIT_')]
def bb(v):return np.min(v,0),np.max(v,0)
def cross(a,b):return bool(np.all(a[0]<=b[1]) and np.all(b[0]<=a[1]))
pd=[poly(o['vertices_mm'],o['faces']) for o in pads];bd=[poly(o['vertices_mm'],o['faces']) for o in body]
pb=[bb(np.array(o['vertices_mm'])) for o in pads];bbod=[bb(np.array(o['vertices_mm'])) for o in body]
res=[]
for shift in range(0,801,100):
 hits=[];tr=vtk.vtkTransform();tr.Translate(0,shift-800,0);identity=vtk.vtkTransform()
 for i,p in enumerate(pads):
  for j,b in enumerate(body):
   delta=np.array([0,shift-800,0]);bq=(bbod[j][0]+delta,bbod[j][1]+delta)
   if not cross(pb[i],bq):continue
   f=vtk.vtkCollisionDetectionFilter();f.SetInputData(0,pd[i]);f.SetInputData(1,bd[j]);f.SetTransform(0,identity);f.SetTransform(1,tr);f.SetCollisionModeToFirstContact();f.SetBoxTolerance(.01);f.SetCellTolerance(.0001);f.Update()
   if f.GetNumberOfContacts()>0:hits.append([p['id'],b['id']])
 res.append({'lateral_shift_mm':shift,'intersecting_surface_pairs':hits})
 print(shift,hits,flush=True)
(ROOT/'calculations/pad_interference.json').write_text(json.dumps({'method':'VTK triangle intersection of nominal uncompressed sleeve surfaces and tucked-arm mannequin','poses':res,'status':'Only positive intersection findings are established. Absence of contacts is not a continuous swept-volume or a physiological validation.','requires':'Real padding compression / folding / clearance fit check'},indent=2))
