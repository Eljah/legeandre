from pathlib import Path
import json,csv
from collections import defaultdict
import numpy as np
import ezdxf
from shapely.geometry import Polygon
R=Path(__file__).resolve().parents[1]
pan=json.loads((R/'cad/sewing_surfaces.json').read_text());pat=json.loads((R/'textile/patterns_R02.json').read_text())
edges=defaultdict(list)
for id,d in pan.items():
 if not id.startswith('O'):continue
 vs=np.array(d['vertices_mm']);loop=d['boundary']
 for i,j in zip(loop,loop[1:]+loop[:1]):
  k=tuple(sorted((tuple(np.round(vs[i],5)),tuple(np.round(vs[j],5)))))
  edges[k].append((id,i,j))
rows=[]
for id in [f'O{j:02}A' for j in range(6,12)]:
 d=pan[id];v=np.array(d['vertices_mm']);uv=np.array(pat[id]['uv_vertices_mm']);loop=d['boundary'];doc=ezdxf.readfile(R/'textile/pieces'/f'{id}.dxf')
 for layer,col in [('ZIPPER',1),('BINDING',4)]:
  if layer not in doc.layers:doc.layers.new(layer,dxfattribs={'color':col})
 for a,b in zip(loop,loop[1:]+loop[:1]):
  k=tuple(sorted((tuple(np.round(v[a],5)),tuple(np.round(v[b],5)))));others=[q for q in edges[k] if q[0]!=id]
  if others and all(q[0].endswith('A') for q in others):continue
  typ='ZIPPER' if others else 'BINDING';neigh=','.join(q[0] for q in others) or 'HEAD_OPENING'
  doc.modelspace().add_lwpolyline([uv[a],uv[b]],dxfattribs={'layer':typ})
  rows.append([id,a,b,typ,neigh,round(float(np.linalg.norm(v[a]-v[b])),3)])
 doc.saveas(R/'textile/pieces'/f'{id}.dxf')
with (R/'textile/closure_plan.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['piece','vertex1','vertex2','edge_treatment','mate_or_opening','segment_length_mm']);w.writerows(rows)
# Mapping from the exact CAD OHEAD planar face to its own unfolded coordinates.
id='OHEAD';v=np.array(pan[id]['vertices_mm']);uv=np.array(pat[id]['uv_vertices_mm']);M=np.column_stack([v[:,1],v[:,2],np.ones(len(v))]);coef=np.linalg.lstsq(M,uv,rcond=None)[0]
frame_yz=np.array([[-85,25],[85,25],[85,200],[-85,200]])
frame=np.column_stack([frame_yz,np.ones(4)])@coef
poly=Polygon(pat[id]['sew']);inside=poly.covers(Polygon(frame))
assert inside,'Patch frame extends outside OHEAD sew line'
doc=ezdxf.readfile(R/'textile/pieces/OHEAD.dxf');ms=doc.modelspace()
if 'EMBROIDERY' not in doc.layers:doc.layers.new('EMBROIDERY',dxfattribs={'color':6})
ms.add_lwpolyline(frame,close=True,dxfattribs={'layer':'EMBROIDERY'})
c=frame.mean(0);ms.add_text('LOGO 160 mm / FIELD 170 x 175',dxfattribs={'height':6,'insert':tuple(c),'layer':'EMBROIDERY'})
doc.saveas(R/'textile/embroidery_placement_on_OHEAD.dxf')
(R/'tests/results/closure_patch_R02.json').write_text(json.dumps({'closure_segments':len(rows),'zipper_geometric_length_mm':round(sum(q[-1] for q in rows if q[3]=='ZIPPER'),2),'binding_head_opening_length_mm':round(sum(q[-1] for q in rows if q[3]=='BINDING'),2),'patch_frame_inside_OHEAD':inside,'patch_frame_mm':[170,175],'patch_CAD_plane':'X=0; Y=-85..85; Z=25..200','closure_hardware_selection':'pending mockup; values are seam lengths, not purchase lengths'},indent=2))
print('closure',len(rows),'patchinside',inside)
