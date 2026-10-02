#!/usr/bin/env python3
"""R02 edit of the uploaded R01 CadQuery project. Millimetres.
No legs, frame or sprung slats. The textile sewing surface is a BREP shell
of triangulated gores. Each gore has only boundary vertices and is unfolded
isometrically by textile/build_patterns.py. This is not a cloth/load FEM.
R01 tray, laptop and electronics are rebuilt from the preserved R01 source.
"""
from pathlib import Path
import json,math,csv,importlib.util
import numpy as np
import cadquery as cq
import vtk
ROOT=Path(__file__).resolve().parents[2]
P=json.loads((ROOT/'project.json').read_text()); C=P['soft_cocoon']
OUT=ROOT/'cad'; PANELS={}
COL={'outer':(.63,.67,.68),'lining':(.22,.34,.40),'floor':(.32,.38,.40),'foam':(.80,.80,.70),'tray':(.56,.46,.33),'device':(.18,.22,.25),'screen':(.29,.53,.63),'heat':(.93,.48,.23),'harness':(.7,.27,.14),'seam':(.14,.24,.30)}

def vec(p):return cq.Vector(*map(float,p))
def box(l,w,h,pos):return cq.Workplane('XY').box(l,w,h).translate(pos).val()
def poly_face(points):return cq.Face.makeFromWires(cq.Wire.makePolygon([vec(p) for p in points],close=True))
def mesh_shape(v,f):
 faces=[poly_face([v[i] for i in t]) for t in f]
 shell=cq.Shell.makeShell(faces)
 if not shell.isValid(): raise ValueError('Invalid sewing surface')
 return shell

def profile(x,lining=False):
 a=np.array(C['profile_controls'],float)
 w=np.interp(x,a[:,0],a[:,1]);h=np.interp(x,a[:,0],a[:,2])
 if lining: w-=2*C['lining_inset_mm']; h-=2*C['lining_inset_mm']
 return w,h

def point(x,j,lining=False):
 w,h=profile(x,lining); th=math.radians(220-260*j/16)
 z=h*(math.sin(th)+math.sin(math.radians(40)))/(1+math.sin(math.radians(40)))
 if lining:z+=C['lining_inset_mm']
 return [float(x),float(.5*w*math.cos(th)),float(z if abs(z)>1e-9 else 0)]

def strip_panel(id,A,B,material,description,**kwargs):
 A=np.array(A,float);B=np.array(B,float);v=np.stack([A,B],axis=1).reshape(-1,3)
 faces=[]
 for i in range(len(A)-1):faces += [[2*i,2*i+1,2*i+2],[2*i+1,2*i+3,2*i+2]]
 d={'id':id,'description':description,'material':material,'vertices_mm':v.tolist(),'triangles':faces,
    'boundary':list(range(0,len(v),2))+list(range(len(v)-1,0,-2)), 'strip':True,'quantity':1,**kwargs}
 PANELS[id]=d
 return d

def planar_panel(id,points,material,description,**kwargs):
 v=np.array(points,float)
 faces=[[0,i,i+1] for i in range(1,len(v)-1)]
 d={'id':id,'description':description,'material':material,'vertices_mm':v.tolist(),'triangles':faces,
    'boundary':list(range(len(v))),'strip':False,'quantity':1,**kwargs}
 PANELS[id]=d;return d

def make_panels():
 PANELS.clear();xs=C['stations_mm']
 for lining in [False,True]:
  prefix='L' if lining else 'O';mat='lining' if lining else 'outer'
  for j in range(16):
   ranges=[('A',650,1550),('B',1550,2360)] if 5<=j<=10 else [('',0,2360)]
   for suffix,x0,x1 in ranges:
    xx=sorted(set([x0,x1]+[x for x in xs if x0<x<x1]))
    strip_panel(f'{prefix}{j+1:02}{suffix}',[point(x,j,lining) for x in xx],[point(x,j+1,lining) for x in xx],mat,
                'Detachable crown quilt' if suffix else 'Longitudinal cocoon gore',sector=j,stations_mm=xx,
                opening_piece=bool(suffix=='A'), seam_allowance_mm=12)
  strip_panel(prefix+'F',[point(x,0,lining) for x in xs],[point(x,16,lining) for x in xs],
              'floor' if not lining else 'lining','Flat floor-facing textile bottom',stations_mm=xs,seam_allowance_mm=12)
  # Planar end walls. Head opening is open above the two side rim points.
  for k,x in [('HEAD',0),('FOOT',2360)]:
   v=[point(x,j,lining) for j in range(17)]
   planar_panel(prefix+k,v,mat,'End wall '+k,seam_allowance_mm=12)
 # Full-width base mattress, independent soft load-bearing layer (no board).
 mx=[80,150,250,350,500,650,800,950,1100,1250,1400,1550,1725,1900,2050,2200,2280]
 b=[]
 for x in mx:b.append([x,-min(350,profile(x)[0]*.34),120])
 for x in reversed(mx):b.append([x,min(350,profile(x)[0]*.34),120])
 planar_panel('MT',b,'cushion','Mattress top',seam_allowance_mm=12)
 planar_panel('MB',[[x,y,24] for x,y,z in b],'cushion','Mattress bottom',seam_allowance_mm=12)
 # Two continuous mattress gussets, split at two opposite sewing corners.
 for name,path in [('MG_LEFT',b[:len(b)//2+1]),('MG_RIGHT',b[len(b)//2:]+[b[0]])]:
  strip_panel(name,[[x,y,24] for x,y,z in path],path,'cushion','Continuous mattress gusset',seam_allowance_mm=12)
 # Removable soft triangular back wedge: all five cut faces derived from the CAD solid.
 x=260;end=1110;z=120;rise=600;y=280
 for s in [-1,1]:planar_panel('WLEFT' if s<0 else 'WRIGHT',[[x,s*y,z],[end,s*y,z],[x,s*y,z+rise]],'cushion','Soft wedge triangular side',seam_allowance_mm=12)
 for id,vs in [('WBASE',[[x,-y,z],[end,-y,z],[end,y,z],[x,y,z]]),('WBACK',[[x,-y,z],[x,y,z],[x,y,z+rise],[x,-y,z+rise]]),('WSLOPE',[[x,-y,z+rise],[x,y,z+rise],[end,y,z],[end,-y,z]])]:
  planar_panel(id,vs,'cushion','Soft wedge '+id,seam_allowance_mm=12)
 # Arm bolster bags: closed rectangular bags contain only foam, not stanchions.
 for side,cy in [('LEFT',-355),('RIGHT',355)]:
  x0,x1=1050,1450;y0,y1=cy-55,cy+55;z0,z1=120,410
  faces={'TOP':[[x0,y0,z1],[x1,y0,z1],[x1,y1,z1],[x0,y1,z1]],'BOTTOM':[[x0,y0,z0],[x1,y0,z0],[x1,y1,z0],[x0,y1,z0]],
   'IN':[[x0,y0,z0],[x1,y0,z0],[x1,y0,z1],[x0,y0,z1]],'OUT':[[x0,y1,z0],[x1,y1,z0],[x1,y1,z1],[x0,y1,z1]],
   'HEAD':[[x0,y0,z0],[x0,y1,z0],[x0,y1,z1],[x0,y0,z1]],'FOOT':[[x1,y0,z0],[x1,y1,z0],[x1,y1,z1],[x1,y0,z1]]}
  for label,vs in faces.items():planar_panel('ARM_'+side+'_'+label,vs,'cushion','Foam arm bag '+side,seam_allowance_mm=12)
 # Hand tunnel: exact prismatic arch, not a drawing of a pattern.
 aa=[];bb=[]
 for t in np.linspace(math.pi,0,25):
  yz=[345*math.cos(t),441+150*math.sin(t)]
  aa.append([1045,*yz]);bb.append([1425,*yz])
 strip_panel('H01',aa,bb,'outer','Hand tunnel / screen seam open',seam_allowance_mm=12)
 strip_panel('H02',[[x,y*.975,z-8] for x,y,z in aa],[[x,y*.975,z-8] for x,y,z in bb],'lining','Hand tunnel inner liner',seam_allowance_mm=12)
 # Soft tray sleeve (ventilation insert separately); not a sealed hot laptop pouch.
 planar_panel('TRAY_TOP',[[1050,-360,423],[1510,-360,423],[1510,360,423],[1050,360,423]],'mesh','Tray sleeve top mesh',seam_allowance_mm=12)
 planar_panel('TRAY_BOTTOM',[[1050,-360,409],[1510,-360,409],[1510,360,409],[1050,360,409]],'mesh','Tray sleeve bottom mesh',seam_allowance_mm=12)
 # Flexible heater carrier mid-surfaces. Arc length fixes each original R01 area.
 # Resistive conductor layout is NOT sewn by an embroidery machine.
 for i,x0,z0,width,height in [(0,260,220,700,170),(1,1280,180,758,174),(2,1820,130,320,140),(3,1065,441,666,138)]:
  yz=[[width/2*math.cos(t),z0+height*math.sin(t)] for t in np.linspace(math.pi,0,25)]
  arc=sum(math.dist(a,b) for a,b in zip(yz,yz[1:]));length=P['zones'][i]['area_m2']*1e6/arc
  aa=[[x0,y,z] for y,z in yz];bb=[[x0+length,y,z] for y,z in yz]
  strip_panel('HZ'+str(i),aa,bb,'heater_carrier','Removable heater carrier, Z'+str(i),seam_allowance_mm=12,zone=i,nominal_watts=P['zones'][i]['watts'],nominal_area_m2=P['zones'][i]['area_m2'])
 return PANELS

def load_r01():
 path=ROOT/'history/R01/cad/source/build_cad.py'
 spec=importlib.util.spec_from_file_location('r01_preserved',path);r01=importlib.util.module_from_spec(spec);spec.loader.exec_module(r01)
 return {p['id']:p for p in r01.build('work')}

def add(parts,id,shape,kind,desc,**kw):
 if not shape.isValid(): raise ValueError('Invalid part '+id)
 parts.append({'id':id,'shape':shape,'kind':kind,'description':desc,**kw})

def build(mode,base):
 parts=[]
 for id,d in PANELS.items():
  # Seam surfaces and infill are separate; expose lining only in technical views.
  if id[0] in 'OL' and (id.startswith('O') or id.startswith('L')):
   if mode=='work' and d.get('opening_piece'):continue
   add(parts,id,mesh_shape(d['vertices_mm'],d['triangles']),d['material'],d['description'],panel_id=id)
 # Mattress solid from the very same CAD top boundary.
 d=PANELS['MT'];boundary=d['vertices_mm']
 sh=cq.Workplane('XY').polyline([(x,y) for x,y,z in boundary]).close().extrude(96).translate((0,0,24)).val()
 add(parts,'FOAM_MATTRESS',sh,'foam','Soft mattress core 96 mm; floor underlay below')
 # Closed-cell flexible thermal underlay, no rigid base plate.
 d=PANELS['OF'];idx=d['boundary'];poly=[d['vertices_mm'][i] for i in idx]
 sh=cq.Workplane('XY').polyline([(x,y) for x,y,z in poly]).close().extrude(24).val()
 add(parts,'FOAM_UNDERLAY',sh,'foam','Flexible floor insulation, not plywood')
 if mode=='work':
  # extruding XZ goes along -Y
  wedge=cq.Workplane('XZ',origin=(0,280,0)).polyline([(260,120),(1110,120),(260,720)]).close().extrude(560).val()
  add(parts,'FOAM_BACK_WEDGE',wedge,'foam','Removable soft back support: 35.2 degrees unloaded')
  for sign in [-1,1]:add(parts,'FOAM_ARM_'+('L' if sign<0 else 'R'),box(400,110,290,(1250,sign*355,265)),'lining','Foam arm bag; textile connection to bottom')
  # Actual R01 ventilated tray and laptop reference solids, rigidly relocated.
  for id in ['D20','D21','D22']:
   old=base[id]
   add(parts,id,(old['shape'].fuse(box(460,60,12,(215,-330,715))).fuse(box(460,60,12,(215,330,715))) if id=='D20' else old['shape']).translate((1065,0,-299)), 'tray' if id=='D20' else ('screen' if id=='D22' else 'device'),old['name']+' [R01 retained]',inherited_from_R01=id)
  for id in ['H01','H02']:
   d=PANELS[id];add(parts,id,mesh_shape(d['vertices_mm'],d['triangles']),d['material'],d['description'],panel_id=id)
 # Four original electrical zones are preserved; only their soft carriers move.
 for i in range(4):
  if mode=='sleep' and i==3:continue
  d=PANELS['HZ'+str(i)];sh=mesh_shape(d['vertices_mm'],d['triangles'])
  if i==0 and mode=='work':sh=sh.rotate((1110,0,120),(1110,1,120),35.2)
  add(parts,'EH'+str(i),sh,'heat','R01 electrical zone '+str(i)+' / revised flexible carrier',panel_id='HZ'+str(i))
 # Separate uninsulated service module on the floor outside cocoon: battery never under body.
 placements={'E10':(1250,-850,90),'E12':(1600,-820,45),'E13':(1600,-820,65),'E14':(1600,-820,25),'E11':(1130,-510,355)}
 for id,target in placements.items():
  old=base[id];bb=old['shape'].BoundingBox();cen=((bb.xmin+bb.xmax)/2,(bb.ymin+bb.ymax)/2,(bb.zmin+bb.zmax)/2)
  sh=old['shape'].translate(tuple(t-c for t,c in zip(target,cen)))
  add(parts,id,sh,'device',old['name']+' [R01 retained; moved outside thermal envelope]',external=id!='E11',inherited_from_R01=id)
 routefile=ROOT/'harness/routes_R02.json'
 if routefile.exists():
  for route in json.loads(routefile.read_text()):
   if mode=='sleep' and route['id'] in ['HP3','NTC30','NTC31','TH3','USB_DATA','USB_PD']:continue
   route_pts=route.get('points_sleep_mm',route['points_mm']) if mode=='sleep' else route['points_mm']
   pts=[route_pts[0]]
   for q in route_pts[1:]:
    if math.dist(q,pts[-1])>1e-6:pts.append(q)
   wire=cq.Wire.makePolygon([vec(q) for q in pts],close=False)
   add(parts,'WIRE_'+route['id'],wire,'harness','Harness centerline '+route['id'],external=True,curve_points=pts)
 return parts

def render(parts,name,view='iso',technical=False,external=False):
 ren=vtk.vtkRenderer();ren.SetBackground(.975,.978,.98)
 for d in parts:
  if d.get('external') and not external:continue
  if d['id'].startswith('L') and not technical: continue
  if d['kind']=='heat' and not technical:continue
  if d.get('curve_points'):
   pp=vtk.vtkPoints();ll=vtk.vtkCellArray();line=vtk.vtkPolyLine();line.GetPointIds().SetNumberOfIds(len(d['curve_points']))
   for i,q in enumerate(d['curve_points']):pp.InsertNextPoint(*q);line.GetPointIds().SetId(i,i)
   ll.InsertNextCell(line);pd=vtk.vtkPolyData();pd.SetPoints(pp);pd.SetLines(ll);mp=vtk.vtkPolyDataMapper();mp.SetInputData(pd)
   actor=vtk.vtkActor();actor.SetMapper(mp);actor.GetProperty().SetColor(.83,.31,.16);actor.GetProperty().SetLineWidth(2.5);ren.AddActor(actor)
   continue
  verts,faces=d['shape'].tessellate(2)
  pts=vtk.vtkPoints();cells=vtk.vtkCellArray()
  for v in verts:pts.InsertNextPoint(v.x,v.y,v.z)
  for f in faces:
   t=vtk.vtkTriangle()
   for j in range(3):t.GetPointIds().SetId(j,int(f[j]))
   cells.InsertNextCell(t)
  pd=vtk.vtkPolyData();pd.SetPoints(pts);pd.SetPolys(cells)
  clean=vtk.vtkCleanPolyData();clean.SetInputData(pd);clean.Update()
  normals=vtk.vtkPolyDataNormals();normals.SetInputConnection(clean.GetOutputPort());normals.SplittingOff();normals.ConsistencyOn();normals.Update()
  mapper=vtk.vtkPolyDataMapper();mapper.SetInputConnection(normals.GetOutputPort())
  actor=vtk.vtkActor();actor.SetMapper(mapper);pr=actor.GetProperty();pr.SetColor(*COL.get(d['kind'],COL['device']))
  pr.SetInterpolationToPhong();pr.SetSpecular(.08);pr.SetAmbient(.40);pr.SetDiffuse(.65)
  if technical and d['kind'] in ['outer','lining','floor']:pr.SetOpacity(.11)
  if technical and d['kind']=='foam':pr.SetOpacity(.23)
  ren.AddActor(actor)
 # Show actual panel perimeter edges, not artificial texture or fake UI.
 for id,d in PANELS.items():
  if not id.startswith('O') or ('work' in name and d.get('opening_piece')):continue
  arr=np.array(d['vertices_mm']);loop=arr[d['boundary']+[d['boundary'][0]]]
  pp=vtk.vtkPoints();ll=vtk.vtkCellArray();line=vtk.vtkPolyLine();line.GetPointIds().SetNumberOfIds(len(loop))
  for i,p in enumerate(loop):pp.InsertNextPoint(*p);line.GetPointIds().SetId(i,i)
  ll.InsertNextCell(line);pd=vtk.vtkPolyData();pd.SetPoints(pp);pd.SetLines(ll)
  mp=vtk.vtkPolyDataMapper();mp.SetInputData(pd);a=vtk.vtkActor();a.SetMapper(mp);a.GetProperty().SetColor(*COL['seam']);a.GetProperty().SetLineWidth(1.4)
  ren.AddActor(a)
 # Floor is a visual reference only, not a part of the product STEP.
 ps=vtk.vtkPlaneSource();ps.SetOrigin(-10000,-10000,-2);ps.SetPoint1(10000,-10000,-2);ps.SetPoint2(-10000,10000,-2)
 mp=vtk.vtkPolyDataMapper();mp.SetInputConnection(ps.GetOutputPort());a=vtk.vtkActor();a.SetMapper(mp);a.GetProperty().SetColor(.975,.978,.98);a.GetProperty().SetAmbient(1);a.GetProperty().SetDiffuse(0);ren.AddActor(a)
 cam=ren.GetActiveCamera();cam.SetFocalPoint(1160,0,380);cam.SetViewUp(0,0,1);cam.ParallelProjectionOn()
 if view=='iso':cam.SetPosition(3600,-3500,2700)
 elif view=='head':cam.SetPosition(-1500,-2500,2100)
 elif view=='side':cam.SetPosition(1160,-5000,430)
 elif view=='top':cam.SetPosition(1160,0,5500);cam.SetViewUp(1,0,0)
 elif view=='front':cam.SetPosition(5000,0,430)
 ren.ResetCamera(0,2360,-560 if not external else -1000,530,0,940);cam.Zoom(1.07)
 win=vtk.vtkRenderWindow();win.SetOffScreenRendering(1);win.SetSize(1800,1100);win.AddRenderer(ren);win.SetMultiSamples(4);win.Render()
 fl=vtk.vtkWindowToImageFilter();fl.SetInput(win);fl.Update();wr=vtk.vtkPNGWriter();wr.SetFileName(str(OUT/'renders'/f'{name}.png'));wr.SetInputConnection(fl.GetOutputPort());wr.Write();win.Finalize()

def save_dxf(parts,mode):
 import ezdxf
 for view,ax in [('top',(0,1)),('side',(0,2)),('front',(1,2))]:
  doc=ezdxf.new('R2010');doc.units=4;ms=doc.modelspace()
  for d in parts:
   if d['id'].startswith('L') or d.get('external'):continue
   doc.layers.new(d['id'])
   if d.get('panel_id') and not d['id'].startswith('EH'):
    pp=PANELS[d['panel_id']];v=np.array(pp['vertices_mm'])[pp['boundary']]
    ms.add_lwpolyline([(p[ax[0]],p[ax[1]]) for p in v],close=True,dxfattribs={'layer':d['id']})
   else:
    for e in d['shape'].Edges():
     vs=e.sample(12)[0] if e.geomType()!='LINE' else [e.startPoint(),e.endPoint()]
     ms.add_lwpolyline([(v.toTuple()[ax[0]],v.toTuple()[ax[1]]) for v in vs],dxfattribs={'layer':d['id']})
  doc.saveas(OUT/'dxf'/f'{mode}_{view}.dxf')

def export_all():
 make_panels();base=load_r01()
 (OUT/'sewing_surfaces.json').write_text(json.dumps(PANELS,ensure_ascii=False,indent=2))
 report={}
 for mode in ['work','sleep']:
  print('Building',mode,flush=True);parts=build(mode,base)
  ass=cq.Assembly(name='Lezhandr_R02_'+mode)
  for d in parts:ass.add(d['shape'],name=d['id'],color=cq.Color(*COL.get(d['kind'],COL['device'])))
  ass.save(str(OUT/'step'/f'lezhandr_{mode}.step'))
  body=[d['shape'] for d in parts if not d.get('external')]
  cq.exporters.export(cq.Compound.makeCompound(body),str(OUT/'stl'/f'lezhandr_{mode}.stl'),tolerance=2)
  bb=cq.Compound.makeCompound(body).BoundingBox()
  report[mode]={'parts':len(parts),'valid':all(d['shape'].isValid() for d in parts),'body_bbox_mm':[bb.xlen,bb.ylen,bb.zlen],'minimum_z_mm':bb.zmin,
                'rigid_frame_parts':0,'floor_surface_z_mm':0,'inherited_parts':[d['id'] for d in parts if d.get('inherited_from_R01')],
                'open_quilt_parts_not_mounted':[id for id,d in PANELS.items() if d.get('opening_piece') and id.startswith('O')] if mode=='work' else []}
  with (OUT/f'parts_{mode}.csv').open('w',encoding='utf-8-sig',newline='') as f:
   w=csv.writer(f);w.writerow(['id','description','kind','brep_valid','solid_count','surface_area_mm2','inherited_from_R01'])
   for d in parts:w.writerow([d['id'],d['description'],d['kind'],d['shape'].isValid(),len(d['shape'].Solids()),round(d['shape'].Area(),2),d.get('inherited_from_R01','')])
  for view in ['iso','head','side','top']:render(parts,mode+'_'+view,view)
  render(parts,mode+'_section','head',True,True)
  save_dxf(parts,mode)
  # Actual STEP roundtrip, not simply checking source objects.
  rt=cq.importers.importStep(str(OUT/'step'/f'lezhandr_{mode}.step')).val()
  report[mode]['step_roundtrip_valid']=rt.isValid();report[mode]['step_roundtrip_faces']=len(rt.Faces())
  print(mode,report[mode],flush=True)
 (ROOT/'tests/results/cad_R02.json').write_text(json.dumps(report,indent=2))
 return report
if __name__=='__main__':export_all()
