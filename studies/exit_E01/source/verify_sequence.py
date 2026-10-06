#!/usr/bin/env python3
"""Verify discrete mesh poses. NOT an anatomical, strength or continuous-path test."""
from exit_model import *
from vtk.util.numpy_support import vtk_to_numpy
from collections import Counter

def cleaned(r):
 d=poly(r['vertices_mm'],r['faces']);c=vtk.vtkCleanPolyData();c.SetInputData(d);c.Update();n=vtk.vtkPolyDataNormals();n.SetInputConnection(c.GetOutputPort());n.ConsistencyOn();n.AutoOrientNormalsOn();n.SplittingOff();n.Update();o=vtk.vtkPolyData();o.DeepCopy(n.GetOutput());return o

def gap(a,b):
 a=np.array(a['vertices_mm']);b=np.array(b['vertices_mm']);return float(np.linalg.norm(np.maximum(0,np.maximum(a.min(0)-b.max(0),b.min(0)-a.max(0)))))

def main():
 out=[];pair_results=[];floor=[]
 for s in SEQUENCES:
  rows,q=frame_rows(s);hard=[r for r in rows if r['group'] in ['desk','frame','hardware','service','laptop'] and not r['id'].startswith('KEY_')];human=[r for r in rows if r['group']=='human'];minimum=999999;points_inside=0;pairs=0
  for b in human:
   if s['pose']=='rest' and b['id'].startswith('M_HAND'):continue # intended keyboard contact
   for h in hard:
    bbox=gap(b,h)
    if bbox>30:continue
    hd=cleaned(h);bd=cleaned(b)
    f=vtk.vtkImplicitPolyDataDistance();f.SetInput(hd)
    pts=np.array(b['vertices_mm']);ds=np.array([f.EvaluateFunction(v) for v in pts]);dist=float(np.abs(ds).min());minimum=min(minimum,dist)
    inside=vtk.vtkSelectEnclosedPoints();inside.SetInputData(bd);inside.SetSurfaceData(hd);inside.SetTolerance(.000001);inside.CheckSurfaceOff();inside.Update();a=inside.GetOutput().GetPointData().GetArray('SelectedPoints');count=int(vtk_to_numpy(a).sum())
    pairs+=1;points_inside+=count
    pair_results.append({'state':s['id'],'body':b['id'],'equipment':h['id'],'sampled_vertex_min_distance_mm':dist,'vertices_inside':count})
  if minimum==999999:
   minimum=min(gap(b,h) for b in human for h in hard)
   typ='AABB_lower_bound'
  else:typ='sampled_mesh_vertex_distance'
  maxbone=0
  for sy in [-1,1]:
   for a,b,L in [(q[f'hip{sy}'],q[f'knee{sy}'],490),(q[f'knee{sy}'],q[f'ankle{sy}'],490)]:maxbone=max(maxbone,abs(np.linalg.norm(a-b)-L))
  vv=np.concatenate([np.array(r['vertices_mm']) for r in human]);zmin=float(vv[:,2].min())
  out.append({'state':s['id'],'pose':s['pose'],'screened_pairs':pairs,'body_vertices_inside_hard_parts':points_inside,'distance_mm':minimum,'distance_kind':typ,'max_leg_length_error_mm':float(maxbone),'minimum_human_mesh_z_mm':zmin})
  print(out[-1],flush=True)
 doc={'source_hash':hashlib.sha256((BASE/'cad/model_R08.json').read_bytes()).hexdigest(),'states':out,'pair_checks':pair_results,'scope':'Discrete CAD-derived mesh vertices vs closed hard surfaces with AABB prefilter. Does not certify all triangle intersections or swept paths. Intentional hand-keyboard contacts excluded in seated pose. No cloth, granular or force simulation.','new_design_requirements':['E01 right side panel end-release seams Z05a/Z05b and closed filler liners','Left stowage ties for shoulder wrap','Z06 releasable left leg-cover edge; toe anchorage retained; guide for folds','Table slide lock and controlled cable service loop'],'cloth_isometry_validated':False,'continuous_collision_validation':False,'physical_exit_tested':False}
 (HERE/'checks/exit_pose_checks.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
