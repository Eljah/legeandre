#!/usr/bin/env python3
"""Real VTK view of preserved CAD with explicit E01 motions, overlays and labels."""
from pathlib import Path
import sys,json,math
import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk
from exit_model import *
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BROWN=(.48,.34,.23);ARROW=(.74,.32,.12);GREEN=(.20,.38,.34);BLUE=(.24,.40,.48)

def line(r,pts,color=ARROW,radius=4):
 p=vtk.vtkPoints();ca=vtk.vtkCellArray();ca.InsertNextCell(len(pts))
 for i,q in enumerate(pts):p.InsertNextPoint(*q);ca.InsertCellPoint(i)
 d=vtk.vtkPolyData();d.SetPoints(p);d.SetLines(ca);tf=vtk.vtkTubeFilter();tf.SetInputData(d);tf.SetRadius(radius);tf.SetNumberOfSides(10);m=vtk.vtkPolyDataMapper();m.SetInputConnection(tf.GetOutputPort());a=vtk.vtkActor();a.SetMapper(m);a.GetProperty().SetColor(*color);a.GetProperty().SetAmbient(.65);r.AddActor(a);return a

def arrow(r,pts,color=ARROW,radius=6):
 line(r,pts,color,radius);end=np.array(pts[-1],float);dire=end-np.array(pts[-2]);dire/=np.linalg.norm(dire)
 c=vtk.vtkConeSource();c.SetDirection(*dire);c.SetCenter(*(end-dire*25));c.SetHeight(64);c.SetRadius(21);c.SetResolution(20);m=vtk.vtkPolyDataMapper();m.SetInputConnection(c.GetOutputPort());a=vtk.vtkActor();a.SetMapper(m);a.GetProperty().SetColor(*color);a.GetProperty().SetAmbient(.65);r.AddActor(a)

def label(r,text,point,color=ARROW,size=32):
 s=vtk.vtkBillboardTextActor3D();s.SetInput(text);s.SetPosition(*point);p=s.GetTextProperty();p.SetFontFamily(vtk.VTK_FONT_FILE);p.SetFontFile(FONT);p.SetFontSize(size);p.SetColor(*color);p.SetBold(True);p.SetBackgroundColor(.98,.967,.94);p.SetBackgroundOpacity(.9);p.SetFrame(0);r.AddActor(s)

def actor(r,row,color=None,alpha=1):
 if not row['faces']:return
 d=poly(row['vertices_mm'],row['faces']);cl=vtk.vtkCleanPolyData();cl.SetInputData(d);no=vtk.vtkPolyDataNormals();no.SetInputConnection(cl.GetOutputPort());no.ConsistencyOn();no.AutoOrientNormalsOn();no.SplittingOff()
 m=vtk.vtkPolyDataMapper();m.SetInputConnection(no.GetOutputPort());a=vtk.vtkActor();a.SetMapper(m);p=a.GetProperty();p.SetColor(*(color or PAL[row['kind']]));p.SetOpacity(alpha);p.SetAmbient(.30);p.SetDiffuse(.70);p.SetSpecular(.015 if row['kind'] in ['frame','tray','device'] else 0);r.AddActor(a)
 return a

def ellipsoid(r,center,radii,color,frame=None):
 s=vtk.vtkSphereSource();s.SetThetaResolution(32);s.SetPhiResolution(24);s.SetRadius(1)
 m=vtk.vtkPolyDataMapper();m.SetInputConnection(s.GetOutputPort());a=vtk.vtkActor();a.SetMapper(m);a.SetPosition(*center);a.SetScale(*radii)
 if frame is not None:a.RotateZ(frame)
 a.GetProperty().SetColor(*color);a.GetProperty().SetAmbient(.3);r.AddActor(a)

def scene(s,view='standard',width=2100,height=1480,annotate=True):
 r=vtk.vtkRenderer();r.SetBackground(.981,.973,.956);rows,q=frame_rows(s)
 for row in rows:
  if row['group'] in ['heater','harness','zipper']:continue
  if view=='wiring' and row['group'] not in ['desk','laptop','frame','service','hardware','table_feet']:continue
  if view=='cutaway' and row['group'] in ['hood','rear_gusset','lower_shell','floor','forming_fill','contact_fill','pelvis','pillow','leg_support']:
   d=poly(row['vertices_mm'],row['faces']);d,_=clip_part(d,[0,0,0],[0,-1,0]);v,f=poly_arrays(d);row={**row,'vertices_mm':v.tolist(),'faces':f.tolist()}
  if view=='cutaway' and row['group'] in ['shoulder','leg_quilt','flap']:continue
  actor(r,row)
 # Thin soles attach to the original foot shapes; ground contact is visible.
 for sy in ([] if view=='wiring' else [-1,1]):
  F=q['F'] if not(s['pose']=='kneel' and sy==-1) else -q['F'];center=q[f'ankle{sy}']+F*50-np.array([0,0,51])
  ellipsoid(r,center,[116,49,9],(.36,.36,.32),q['yaw']+(180 if s['pose']=='kneel' and sy==-1 else 0))
 # Zipper rail and two end releases. Split teeth represented as two offset lines.
 if annotate and s['id'] in ['03','04','05','06']:
  pts=np.array(json.loads((BASE/'harness/zippers.json').read_text())[0]['points_mm']);pts[:,1]+=12
  line(r,pts,ARROW,4)
  if s['zip']:
   line(r,pts+[0,16,10],(.60,.51,.42),2)
   arrow(r,pts[1:10],ARROW,5)
  label(r,'Z01',pts[9]+[0,25,80],size=27)
 if annotate and s['id'] in ['03','06']:
  for x,z in [(845,795),(2140,365)]:
   y=float(W(x))+10
   p=np.array([[x,y,z],[x,y,160]])
   line(r,p,BLUE,5);arrow(r,p,BLUE,4);label(r,'Z05a' if x==845 else 'Z05b',[x,y+30,(z+160)/2],BLUE,24)
 if annotate:
  if s['id']=='01':arrow(r,[[1180,210,705],[1180,-100,725],[1180,-340,700]]);label(r,'K',[1300,-320,735])
  if s['id']=='02':
   arrow(r,[[1190,400,575],[1370,400,620]]);label(r,'+80 мм',[1310,410,660],size=30)
  if s['id']=='04':
   arrow(r,[[850,180,930],[850,-180,1070],[850,-700,1030]]);label(r,'S',[900,-740,1110])
  if s['id']=='05':
   line(r,[[965,-522,580],[1290,-522,430],[1650,-482,380],[2110,-359,360],[2320,-145,290]],BLUE,4);label(r,'Z06',[1650,-510,560],BLUE,27)
   arrow(r,[[1350,180,600],[1570,180,640],[1870,180,740]]);label(r,'L',[1900,200,795])
  if s['id']=='06':
   arrow(r,[[1210,555,470],[1210,790,360],[1210,910,160]]);label(r,'B',[1380,915,190])
  if s['id']=='07':
   arrow(r,[[1530,220,480],[1630,460,500],[1550,700,460]]);label(r,'1',[1710,940,140],GREEN)
  if s['id']=='08':
   arrow(r,[[1160,500,460],[1130,730,410],[1140,1050,350]]);label(r,'2',[1160,1410,130],GREEN)
  if s['id']=='09':
   label(r,'КОЛЕНО',q['knee-1']+[65,0,115],GREEN,26);label(r,'СТОПА',q['ankle1']+[-70,80,100],GREEN,26)
  if s['id']=='10':
   arrow(r,[[600,1500,650],[600,1500,1200],[600,1500,1600]],GREEN,5)
 if view=='wiring':
  for z in json.loads((BASE/'harness/routes.json').read_text()):
   pp=np.array(z['points_mm']);
   if z['id'].startswith(('W01','W02')):pp[:,0]+=80*np.linspace(0,1,len(pp))
   line(r,pp,ARROW if z['id'].startswith(('W01','W03','W04')) else GREEN,4)
  label(r,'ВВОД СЛЕВА',[780,-660,260],BLUE,28)
  label(r,'ЗАПАС КАБЕЛЯ',[1190,-530,610],BLUE,28)
 # Fine line of floor / route to the user's right.
 plane=vtk.vtkPlaneSource();plane.SetOrigin(-8000,-8000,-6);plane.SetPoint1(8000,-8000,-6);plane.SetPoint2(-8000,8000,-6)
 m=vtk.vtkPolyDataMapper();m.SetInputConnection(plane.GetOutputPort());a=vtk.vtkActor();a.SetMapper(m);a.GetProperty().SetColor(.971,.961,.942);a.GetProperty().SetAmbient(.6);r.AddActor(a)
 r.AutomaticLightCreationOff()
 for p,level in [((-1000,2800,4800),.8),((2400,-2500,3200),.7),((3800,3600,2200),.3)]:
  l=vtk.vtkLight();l.SetPosition(*p);l.SetFocalPoint(1100,300,600);l.SetIntensity(level);r.AddLight(l)
 steps=vtk.vtkRenderStepsPass();ao=vtk.vtkSSAOPass();ao.SetDelegatePass(steps);ao.SetRadius(35);ao.SetBias(2);ao.SetKernelSize(32);ao.BlurOn();r.SetPass(ao)
 c=r.GetActiveCamera();c.ParallelProjectionOn();c.SetViewUp(0,0,1)
 # Same camera and scale for the staged large views: no deceptive scaling.
 c.SetFocalPoint(1220,240,600);c.SetPosition(3600,3700,2600);c.SetParallelScale(1620)
 if view=='close':c.SetFocalPoint(1100,0,650);c.SetPosition(2500,3200,2300);c.SetParallelScale(840)
 if view=='wiring':c.SetFocalPoint(1130,-140,330);c.SetPosition(2700,-3500,2100);c.SetParallelScale(970)
 if view=='cutaway':c.SetFocalPoint(1170,0,580);c.SetPosition(2600,3700,1850);c.SetParallelScale(1190)
 if view=='side':c.SetFocalPoint(1150,700,850);c.SetPosition(1180,6000,950);c.SetParallelScale(1250)
 if view=='top':c.SetFocalPoint(1200,400,0);c.SetPosition(1200,400,6500);c.SetViewUp(-1,0,0);c.SetParallelScale(1850)
 if view=='zipper':c.SetFocalPoint(1080,520,500);c.SetPosition(2000,3000,1650);c.SetParallelScale(590)
 if view=='left':c.SetFocalPoint(1100,-400,500);c.SetPosition(3200,-3900,2100);c.SetParallelScale(1450)
 r.ResetCameraClippingRange();w=vtk.vtkRenderWindow();w.SetSize(width,height);w.SetMultiSamples(0);w.SetWindowName('Lezhandr E01 | exit kinematics | source CAD R08/R09');w.AddRenderer(r)
 return w,r,rows,q

def save(s,view='standard',suffix=''):
 w,r,rows,q=scene(s,view);w.SetOffScreenRendering(1);w.Render();f=vtk.vtkWindowToImageFilter();f.SetInput(w);f.Update();o=HERE/'renders'/('stage_'+s['id']+suffix+'.png');wr=vtk.vtkPNGWriter();wr.SetFileName(str(o));wr.SetInputConnection(f.GetOutputPort());wr.Write();w.Finalize();print(o.name,flush=True)
 # Skeleton and reversible settings, not bulky mesh duplicates in report package.
 (HERE/'checks'/('pose_'+s['id']+suffix+'.json')).write_text(json.dumps({'settings':s,'joints_mm':q},indent=2,default=lambda o:o.tolist() if isinstance(o,np.ndarray) else o))
 return o
if __name__=='__main__':
 if '--quick' in sys.argv:
  for i in [0,4,6,7,8,9,10]:save(SEQUENCES[i])
 elif '--viewer' in sys.argv:
  w,r,_,_=scene(SEQUENCES[8],width=1500,height=1000);it=vtk.vtkRenderWindowInteractor();it.SetRenderWindow(w);it.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera());w.Render();it.Initialize();it.Start()
 else:
  for s in SEQUENCES:save(s)
  for i,view in [(1,'close'),(2,'close'),(3,'zipper'),(4,'left'),(6,'top'),(8,'side'),(10,'top'),(9,'top'),(0,'cutaway'),(2,'wiring')]:save(SEQUENCES[i],view,'_'+view)
  s=dict(SEQUENCES[4]);s['shoulder']=.5;save(s,'standard','_middle')
  s=dict(SEQUENCES[6]);s['side']=.5;save(s,'standard','_middle')
