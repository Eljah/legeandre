#!/usr/bin/env python3
"""Reproducible CadQuery/OpenCASCADE solid assembly. Units mm; not a cloth FEM.
No native SolidWorks feature tree. STEP carries uniquely named colored parts.
"""
import cadquery as cq, math, json, csv
from pathlib import Path
import vtk
ROOT=Path(__file__).resolve().parents[2]
P=json.loads((ROOT/'project.json').read_text())
OUT=ROOT/'cad'; PARTS=[]
PAL={'metal':(0.46,0.51,0.56),'hinge':(0.85,0.49,0.18),'wood':(0.70,0.51,0.31),'foam':(0.75,0.81,0.84),'cover':(0.16,0.31,0.42),'heat':(0.89,0.39,0.18),'device':(0.13,0.16,0.20),'screen':(0.22,0.55,0.68),'base':(0.22,0.25,0.29)}

def box(l,w,h,pos):return cq.Workplane('XY').box(l,w,h).translate(pos).val()
def beam(a,b,side=35,wall=2):
 a=cq.Vector(*a);b=cq.Vector(*b);d=b-a
 wp=cq.Workplane(cq.Plane(origin=a,normal=d))
 return wp.rect(side,side).rect(side-2*wall,side-2*wall).extrude(d.Length).val()
def rot(s,angle,origin=(0,0,420)):
 return s.rotate(origin,(origin[0],origin[1]+1,origin[2]),angle)
def add(parts,id,name,s,kind='metal',length=None,material=None):
 assert s.isValid(),id
 parts.append({'id':id,'name':name,'shape':s,'kind':kind,'length_mm':length,'material':material or kind})

def arch(length,width,height,t,x0,z0):
 # Developable prismatic half-ellipse, faceted into 24 panels. Textile envelope, not cloth FEM.
 outer=[(-width/2,0)]+[(width/2*math.cos(math.pi-i*math.pi/24),height*math.sin(math.pi-i*math.pi/24)) for i in range(25)]
 inner=[((width/2-t)*math.cos(i*math.pi/24),max(0,(height-t)*math.sin(i*math.pi/24))) for i in range(25)]
 points=outer+inner
 # avoid duplicate initial point
 points=points[1:]
 return cq.Workplane('YZ',origin=(x0,0,z0)).polyline(points).close().extrude(length).val()

def build(mode):
 parts=[]; ba=P[mode+'_angles_deg']['back']; la=P[mode+'_angles_deg']['leg']
 # Base with wide anti-tip feet: no reliance on a bean-bag for load-bearing.
 for i,y in enumerate([-380,380]):add(parts,f'B0{i+1}','Base longitudinal rail',beam((-780,y,160),(1280,y,160)),length=2060)
 for i,x in enumerate([-700,200,1180]):
  add(parts,f'B1{i}','Base cross rail',beam((x,-362.5,160),(x,362.5,160)),length=725)
  for j,y in enumerate([-380,380]):
   add(parts,f'B2{i}{j}','Leg',beam((x,y,30),(x,y,160)),length=130)
   add(parts,f'B3{i}{j}','Foot pad',box(90,90,24,(x,y,18)),'base')
 # Anchor crossmembers ensure no stay or stanchion hangs in space.
 for i,x in enumerate([-520,20,530,800,1130]):
  add(parts,f'B6{i}','Anchor base crossmember',beam((x,-362.5,160),(x,362.5,160)),length=725)
 # Fixed seat support legs and crossmembers.
 for i,x in enumerate([20,530]):
  for j,y in enumerate([-340,340]):add(parts,f'B4{i}{j}','Seat stanchion',beam((x,y,175),(x,y,405)),length=230)
  add(parts,f'B5{i}','Seat support',beam((x,-350,405),(x,350,405)),length=700)
 # 3 independent anatomical frames. Keep 15 mm end gaps at pivots for rotation.
 specs=[('R',-850,0,ba,(0,0,420)),('S',0,550,0,(0,0,420)),('L',550,1350,-la,(550,0,420))]
 # Back extends in negative X and rotates +Y to lift; leg uses +Y for downward feet.
 for prefix,start,end,angle,origin in specs:
  L=end-start
  for j,y in enumerate([-340,340]):
   add(parts,f'{prefix}01{j}','Segment side rail',rot(beam((start+15,y,420),(end-15,y,420)),angle,origin),length=L-30)
  for j,x in enumerate([start+30,end-30]):
   add(parts,f'{prefix}02{j}','Segment crossrail',rot(beam((x,-322.5,420),(x,322.5,420)),angle,origin),length=645)
  # Curved support from slat heights + contoured cushion. Individual lamellas.
  n=int(L/100)
  for j in range(n):
   x=start+60+j*(L-120)/max(1,n-1)
   # Each curved lamella touches the side rails at its ends.
   crown=12 if prefix=='R' else 6
   ys=[-357.5+k*715/20 for k in range(21)]
   lower=[(y,437.5+crown*(1-(y/357.5)**2)) for y in ys]
   upper=[(y,z+9) for y,z in reversed(lower)]
   slat=cq.Workplane('YZ',origin=(x-27.5,0,0)).polyline(lower+upper).close().extrude(55).val()
   add(parts,f'{prefix}10{j:02}','Curved spring slat (plywood)',rot(slat,angle,origin),'wood')
  cushion=box(L-20,650,70,((start+end)/2,0,485))
  try:cushion=cq.Workplane(obj=cushion).edges('|Z').fillet(25).val()
  except Exception:pass
  add(parts,prefix+'200','Segment removable cushion',rot(cushion,angle,origin),'foam')
 # hinge discs + protected pivot pin; locking stay carries moment rather than friction disc.
 for i,x in enumerate([0,550]):
  for j,y in enumerate([-340,340]):
   disc=cq.Workplane('XZ',origin=(x,y,420)).circle(43).circle(6.2).extrude(6).val()
   add(parts,f'H0{i}{j}','Hinge cheek / drilled pivot',disc,'hinge')
   pin=cq.Workplane('XZ',origin=(x,y+8,420)).circle(6).extrude(22).val()
   add(parts,f'H1{i}{j}','M12 pivot',pin,'metal')
 # Telescopic stays are functional envelopes; production pin-hole/clevis details NOT released.
 anchors=[((-520,0,175),(-550*math.cos(math.radians(ba)),0,420+550*math.sin(math.radians(ba)))),
          ((1130,0,175),(550+600*math.cos(math.radians(la)),0,420+600*math.sin(math.radians(la))))]
 for i,(a,b) in enumerate(anchors):
  for j,y in enumerate([-340,340]):
   aa=(a[0],y,a[2]);bb=(b[0],y,b[2]);length=math.dist(aa,bb)
   add(parts,f'T{i}{j}','Pinned telescopic support envelope',beam(aa,bb,25,2),'hinge',None)
 # Textile cover split at mechanical folds; harness never crosses a hinge without service loop.
 cover_specs=[('C1',-750,670,230,ba,(0,0,420),520),('C2',0,530,240,0,(0,0,420),520),('C3',565,740,190,-la,(550,0,420),520)]
 for id,x,L,H,angle,origin,z in cover_specs:
  s=arch(L,790,H,16,x,z)
  add(parts,id,'Removable insulated textile envelope',rot(s,angle,origin),'cover')
 cappts=[(-395,0)]+[(395*math.cos(math.pi-i*math.pi/24),190*math.sin(math.pi-i*math.pi/24)) for i in range(25)]
 cap=cq.Workplane('YZ',origin=(1305,0,520)).polyline(cappts[1:]).close().extrude(16).val()
 add(parts,'C31','Textile foot-end cap',rot(cap,-la,(550,0,420)),'cover')
 # Side bag bolsters visually explain bean-bag feel; removable microfibre fill, not primary structure.
 for i,y in enumerate([-370,370]):
  s=box(470,100,170,(280,y,530))
  try:s=cq.Workplane(obj=s).edges('|Z').fillet(40).val()
  except Exception:pass
  add(parts,f'C4{i}','Soft side bolster',s,'cover')
 # Heater surfaces follow the inner quilt, with explicit area matching project.json.
 def pad(id,area,width,height,x0,z0,angle,origin):
  pts=[(width/2*math.cos(k*math.pi/24),height*math.sin(k*math.pi/24)) for k in range(25)]
  arc=sum(math.dist(pts[i],pts[i+1]) for i in range(24))
  length=area*1e6/arc
  add(parts,id,'Curved removable heater; area '+str(area)+' m2',rot(arch(length,width,height,4,x0,z0),angle,origin),'heat')
  parts[-1]['heater_area_m2']=area
  parts[-1]['heater_cut_length_mm']=length
  return length
 pad('EH0',P['zones'][0]['area_m2'],758,214,-650,520,ba,(0,0,420))
 leglen=pad('EH1',P['zones'][1]['area_m2'],758,174,580,520,-la,(550,0,420))
 pad('EH2',P['zones'][2]['area_m2'],758,174,580+leglen+12,520,-la,(550,0,420))
 # laptop bridge removable as a unit before flattening. Hand hood opens around rear screen edge.
 if mode=='work':
  for i,y in enumerate([-370,370]):
   add(parts,f'D0{i}','Tray upright',beam((250,y,420),(250,y,710),25,2),length=290)
   add(parts,f'D1{i}','Tray support arm',beam((250,y,705),(250,y*0.73,705),20,2),length=abs(y-y*.73))
  tray=box(460,600,12,(215,0,715))
  # Vent slots go through tray; 50 mm clear channels on laptop sides.
  for y in [-220,-170,170,220]:tray=tray.cut(box(320,28,18,(235,y,715)))
  add(parts,'D20','Removable ventilated tray',tray,'wood')
  add(parts,'D21','Laptop keyboard reference envelope',box(290,390,18,(235,0,746)),'device')
  screen=box(12,390,240,(390,0,875)).rotate((390,0,755),(390,1,755),-12)
  add(parts,'D22','Laptop open display reference',screen,'screen')
  add(parts,'D23','Hand hood, open at screen seam',arch(380,690,150,12,-20,740),'cover')
  pad('EH3',P['zones'][3]['area_m2'],666,138,0,740,0,(0,0,420))
 else:
  # folded-down/open hood removed from sleeping face, tray parked outboard on side clip.
  add(parts,'D20','Tray parked for sleep',box(460,12,600,(220,450,370)),'wood')
 # External battery enclosure OUTSIDE thermal cocoon; set on frame side/below deck.
 add(parts,'E09','Power module cradle, straps required',box(350,210,10,(650,-270,180)),'wood')
 add(parts,'E10','External power module ENVELOPE - vendor TBD',box(300,180,180,(650,-275,275)),'device')
 add(parts,'E12','Main electronics enclosure ENVELOPE',box(230,190,90,(250,0,300)),'device')
 add(parts,'E13','A2 PCB envelope',box(200,160,1.6,(250,0,320)),'base')
 add(parts,'E14','A1 PCB envelope',box(145,122,1.6,(250,0,280)),'base')
 add(parts,'E11','Controller housing',box(170,60,110,(100,-405,515)),'device')
 return parts

def export_render(parts,name,view='iso',show_cover=True):
 ren=vtk.vtkRenderer();ren.SetBackground(0.96,0.97,0.98)
 for p in parts:
  if not show_cover and p['kind'] in ['cover','foam']:continue
  verts,faces=p['shape'].tessellate(2.0)
  pts=vtk.vtkPoints()
  for v in verts:pts.InsertNextPoint(v.x,v.y,v.z)
  cells=vtk.vtkCellArray()
  for f in faces:
   t=vtk.vtkTriangle()
   for j in range(3):t.GetPointIds().SetId(j,int(f[j]))
   cells.InsertNextCell(t)
  poly=vtk.vtkPolyData();poly.SetPoints(pts);poly.SetPolys(cells)
  mapper=vtk.vtkPolyDataMapper();mapper.SetInputData(poly)
  a=vtk.vtkActor();a.SetMapper(mapper);a.GetProperty().SetColor(*PAL[p['kind']]);a.GetProperty().SetSpecular(.18);a.GetProperty().SetSpecularPower(20)
  # Textile can be translucent to expose heat zoning; exported STEP stays solid.
  if p['kind']=='cover':a.GetProperty().SetOpacity(.40 if view=='iso' else .24)
  ren.AddActor(a)
 camera=ren.GetActiveCamera();camera.SetFocalPoint(220,0,480)
 if view=='iso':camera.SetPosition(-1950,-3000,2150);camera.SetViewUp(0,0,1)
 if view=='side':camera.SetPosition(220,-4000,480);camera.SetViewUp(0,0,1)
 if view=='top':camera.SetPosition(220,0,5000);camera.SetViewUp(1,0,0)
 if view=='front':camera.SetPosition(4000,0,480);camera.SetViewUp(0,0,1)
 camera.ParallelProjectionOn();ren.ResetCamera();camera.Zoom(1.13)
 win=vtk.vtkRenderWindow();win.SetOffScreenRendering(1);win.SetSize(1800,1100);win.AddRenderer(ren);win.SetMultiSamples(4);win.Render()
 filt=vtk.vtkWindowToImageFilter();filt.SetInput(win);filt.Update()
 w=vtk.vtkPNGWriter();w.SetFileName(str(OUT/'renders'/f'{name}.png'));w.SetInputConnection(filt.GetOutputPort());w.Write();win.Finalize()

def save_dxf(parts,mode):
 import ezdxf
 # Projections from tessellated same solids. Silhouette + visible and hidden edges not classified.
 for view,axes in [('side',(0,2)),('top',(0,1)),('front',(1,2))]:
  doc=ezdxf.new('R2010');doc.units=4; m=doc.modelspace()
  for p in parts:
   doc.layers.new(p['id'],dxfattribs={'color':7})
   # Boundary edges of BREP, sampled curves; not an independently redrawn illustration.
   for e in p['shape'].Edges():
    try:
     ps=e.sample(16)[0] if e.geomType()!='LINE' else [e.startPoint(),e.endPoint()]
     xy=[(tuple(v.toTuple())[axes[0]],tuple(v.toTuple())[axes[1]]) for v in ps]
     m.add_lwpolyline(xy,dxfattribs={'layer':p['id']})
    except Exception:pass
  doc.saveas(OUT/'dxf'/f'{mode}_{view}.dxf')

if __name__=='__main__':
 for mode in ['work','sleep']:
  parts=build(mode);ass=cq.Assembly(name='Lezhandr_'+mode+'_R01')
  for p in parts:ass.add(p['shape'],name=p['id']+'_'+p['name'].split(' ')[0],color=cq.Color(*PAL[p['kind']]))
  ass.save(str(OUT/'step'/f'lezhandr_{mode}.step'))
  cq.exporters.export(cq.Compound.makeCompound([p['shape'] for p in parts]),str(OUT/'stl'/f'lezhandr_{mode}.stl'),tolerance=2,angularTolerance=.15)
  for v in ['iso','side','top','front']:export_render(parts,f'{mode}_{v}',v)
  if mode=='work':export_render(parts,'work_frame','iso',False)
  save_dxf(parts,mode)
  with (OUT/f'parts_{mode}.csv').open('w',newline='',encoding='utf-8-sig') as f:
   w=csv.writer(f);w.writerow(['ID','description','material','length_mm','solid_volume_mm3','valid'])
   for p in parts:w.writerow([p['id'],p['name'],p['material'],round(p['length_mm'],2) if p['length_mm'] else '',round(p['shape'].Volume(),2),p['shape'].isValid()])
  bb=cq.Compound.makeCompound([p['shape'] for p in parts]).BoundingBox()
  (ROOT/'tests/results'/f'cad_{mode}.json').write_text(json.dumps({'mode':mode,'parts':len(parts),'all_valid':all(p['shape'].isValid() for p in parts),'overall_bounding_mm':{'length':round(bb.xlen,1),'width':round(bb.ylen,1),'height':round(bb.zlen,1)},'heater_areas_m2':{p['id']:p['heater_area_m2'] for p in parts if 'heater_area_m2' in p},'heater_developed_lengths_mm':{p['id']:round(p['heater_cut_length_mm'],2) for p in parts if 'heater_cut_length_mm' in p},'method':'OpenCASCADE BREP validity, no interference/FEM proof'},indent=2))

 print('CAD export complete')
