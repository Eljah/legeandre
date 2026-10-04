#!/usr/bin/env python3
"""Direct VTK rendering of actual R06 BREP tessellations. No image generation.
--viewer runs the real interactive application; --quick renders one preview.
"""
from pathlib import Path
import sys,json,math
import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk
ROOT=Path(__file__).resolve().parents[1]
ITEMS=json.loads((ROOT/'cad/model_R06.json').read_text())
PAL=json.loads((ROOT/'cad/palette.json').read_text())
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

# Procedural weave, applied to actual surfaces; does not replace CAD geometry.
def textile_texture():
 n=384;yy,xx=np.mgrid[:n,:n];rng=np.random.default_rng(605)
 weave=0.97+.010*np.sin(xx*2*np.pi/8)*np.sin(yy*2*np.pi/8)+.006*np.cos(xx*2*np.pi/4)+.004*np.cos(yy*2*np.pi/4)+rng.normal(0,.003,(n,n))
 rgb=np.repeat(np.clip(weave[...,None]*255,0,255).astype(np.uint8),3,axis=2)
 im=vtk.vtkImageData();im.SetDimensions(n,n,1);im.GetPointData().SetScalars(numpy_to_vtk(rgb.reshape(-1,3),deep=True,array_type=vtk.VTK_UNSIGNED_CHAR))
 t=vtk.vtkTexture();t.SetInputData(im);t.InterpolateOn();t.RepeatOn();return t
TEXTURE=textile_texture()

def poly(v,f):
 pts=vtk.vtkPoints();pts.SetData(numpy_to_vtk(np.asarray(v,np.float64),deep=True));cells=vtk.vtkCellArray()
 for row in f:
  cells.InsertNextCell(len(row))
  for i in row:cells.InsertCellPoint(int(i))
 p=vtk.vtkPolyData();p.SetPoints(pts);p.SetPolys(cells);return p

def line(renderer,points,color=(.23,.32,.34),radius=1.4):
 p=vtk.vtkPoints();ca=vtk.vtkCellArray();ca.InsertNextCell(len(points))
 for i,q in enumerate(points):p.InsertNextPoint(*q);ca.InsertCellPoint(i)
 d=vtk.vtkPolyData();d.SetPoints(p);d.SetLines(ca)
 tf=vtk.vtkTubeFilter();tf.SetInputData(d);tf.SetRadius(radius);tf.SetNumberOfSides(8)
 mp=vtk.vtkPolyDataMapper();mp.SetInputConnection(tf.GetOutputPort());a=vtk.vtkActor();a.SetMapper(mp);a.GetProperty().SetColor(*color);a.GetProperty().SetAmbient(.3);renderer.AddActor(a);return a

def label(renderer,text,x,y,size=19,color=(.12,.22,.25)):
 a=vtk.vtkTextActor();a.SetInput(text);pr=a.GetTextProperty();pr.SetFontFamily(vtk.VTK_FONT_FILE);pr.SetFontFile(FONT);pr.SetFontSize(size);pr.SetColor(*color);a.SetPosition(x,y);renderer.AddActor2D(a)
 return a

def actor(renderer,o,clip=None,move=(0,0,0),opacity=1,color=None,texture=True):
 if len(o['faces'])==0:
  if o.get('polyline_mm'):
   pp=np.array(o['polyline_mm'])+move
   if clip is not None:pp=pp[pp[:,1]<=clip]
   if len(pp)>1:return line(renderer,pp,tuple(PAL[o['kind']]),o.get('radius_mm',1.5))
  return
 v=np.array(o['vertices_mm'])+move
 d=poly(v,o['faces']);clean=vtk.vtkCleanPolyData();clean.SetInputData(d)
 norm=vtk.vtkPolyDataNormals();norm.SetInputConnection(clean.GetOutputPort());norm.ConsistencyOn();norm.AutoOrientNormalsOn();norm.SplittingOff();norm.Update();out=norm.GetOutputPort()
 if clip is not None:
  pl=vtk.vtkPlane();pl.SetOrigin(0,clip,0);pl.SetNormal(0,-1,0)
  if o.get('solid_count',0):
   pc=vtk.vtkPlaneCollection();pc.AddItem(pl);cl=vtk.vtkClipClosedSurface();cl.SetInputConnection(out);cl.SetClippingPlanes(pc);cl.SetTolerance(.01);cl.GenerateFacesOn();cl.Update();out=cl.GetOutputPort()
  else:
   cl=vtk.vtkClipPolyData();cl.SetInputConnection(out);cl.SetClipFunction(pl);cl.InsideOutOff();cl.Update();out=cl.GetOutputPort()
 if clip is not None:
  nn=vtk.vtkPolyDataNormals();nn.SetInputConnection(out);nn.ComputePointNormalsOn();nn.ComputeCellNormalsOn();nn.ConsistencyOn();nn.AutoOrientNormalsOn();nn.SplittingOn();nn.SetFeatureAngle(65);nn.Update();out=nn.GetOutputPort()
 mp=vtk.vtkPolyDataMapper();mp.SetInputConnection(out);mp.ScalarVisibilityOff()
 a=vtk.vtkActor();a.SetMapper(mp);pr=a.GetProperty();pr.SetColor(*(color or PAL[o['kind']]));pr.SetAmbient(.27 if clip is not None else .18);pr.SetDiffuse(.70 if clip is not None else .80);pr.SetSpecular(.10 if o['kind'] in ['hardware','frame','device'] else .04);pr.SetSpecularPower(20);pr.SetOpacity(opacity)
 if texture and o['kind'] in ['cloth','lining','contact'] and clip is None:
  coords=vtk.vtkTextureMapToCylinder();coords.SetInputConnection(out);coords.PreventSeamOff();coords.AutomaticCylinderGenerationOn();coords.Update()
  trans=vtk.vtkTransformTextureCoords();trans.SetInputConnection(coords.GetOutputPort());trans.SetScale(7,10,1);mp.SetInputConnection(trans.GetOutputPort());a.SetTexture(TEXTURE)
 renderer.AddActor(a);return a


def scene(state='folded',view='iso',width=2300,height=1450,ui=False):
 ren=vtk.vtkRenderer();ren.SetBackground(.966,.961,.948)
 vis=[]
 for o in ITEMS:
  id=o['id'];g=o['group'];mode=state;move=np.array([0.,0,0]);clip=None;opacity=1;color=None
  if state in ['cutaway','side_work','back','foot','dimensions']:mode='work'
  if state in ['empty_cut','table','layers','entry']:mode='empty' if state!='layers' else 'work'
  if state=='side_relax':mode='relax'
  if state in ['hands_closed']:mode='work'
  if state in ['hands_folded']:mode='folded'
  if state=='table':
   if g not in ['frame','hardware','desk','laptop','table_feet']:continue
  elif state=='back':
   if g not in ['forming_fill','contact_fill','straps','baffle','pelvis']:continue
   if 'work' not in o['states']:continue
   if g=='contact_fill':move+=np.array([100,0,140])
   if g=='forming_fill':
    if id.startswith('B01'):move+=np.array([-50,0,0])
    if id.startswith('B03'):move+=np.array([55,0,0])
  elif state=='layers':
   if g not in ['upper','keyboard','lower_quilt']:continue
   if 'work' not in o['states']:continue
   if g=='keyboard':move+=np.array([50,0,100])
   if g=='upper':move+=np.array([-50,0,100])
  elif state=='foot':
   if g in ['footstop','foot_straps']:
    if '1800' in id:opacity=.35;color=(.67,.46,.24)
    elif '1600' in id:opacity=.25;color=(.52,.58,.77)
   elif g not in ['foot_anchors','leg_support','pelvis','floor','lower_shell']:continue
  elif mode not in o['states']:continue
  if state in ['work','folded','dimensions'] and g=='human':continue
  if state=='small' and g in ['upper','keyboard','lower_quilt','seams']:continue
  if state in ['work','folded','hands_closed','hands_folded','small','dimensions'] and g in ['forming_fill','baffle','straps']:
   # Correctly buried inside opaque shell; leave all except internal schematic baffles.
   if g=='baffle':continue
  if state in ['hands_closed','hands_folded'] and g in ['floor','table_feet','footstop','foot_anchors','foot_straps']:continue
  if state in ['cutaway','side_work','side_relax','empty_cut','entry']:
   if g in ['upper','keyboard','lower_quilt','seams','release_tabs']:continue
   if g=='frame_padding':continue
   if g=='lower_shell':clip=0
   if g in ['forming_fill','contact_fill','pelvis','leg_support','pillow']:clip=0
   if g=='floor':clip=0
   if state in ['empty_cut','entry'] and g=='human':continue
  if state=='side_relax' and g in ['desk','laptop']:move+=np.array([80,0,0])
  if state=='entry':
   if g in ['desk','laptop']:move+=np.array([80,0,0])
  if state=='small' and g in ['desk','laptop']:
   ss=json.loads((ROOT/'calculations/foot_settings.json').read_text())[0];move+=np.array([ss['table_delta_x_mm'],0,ss['table_delta_z_mm']])
  if state=='small' and ('CANTILEVER' in id or id.startswith(('D_JOINT','D_ADJUSTER'))):
   ss=json.loads((ROOT/'calculations/foot_settings.json').read_text())[0];move[2]+=ss['table_delta_z_mm']
  if state=='small' and 'LEFT_COLUMN' in id:
   ss=json.loads((ROOT/'calculations/foot_settings.json').read_text())[0];bb=json.loads((ROOT/'cad/table_members.json').read_text());bm=next(b for b in bb if b['id']==id.removeprefix('PAD_'));top=bm['b'][2];sc=(top-30+ss['table_delta_z_mm'])/(top-30);o=dict(o);vv=np.array(o['vertices_mm']);vv[:,2]=30+(vv[:,2]-30)*sc;o['vertices_mm']=vv.tolist()
  if state=='foot' and g=='lower_shell':clip=0
  if state=='foot' and g in ['pelvis','floor']:opacity=.7
  if state in ['empty','empty_cut','foot','back','table','layers','entry'] and g=='human':continue
  if state in ['work','folded','hands_closed','hands_folded','small'] and g in ['forming_fill','baffle','straps']:color=tuple(PAL['contact'])
  actor(ren,o,clip,move,opacity,color,texture=state not in ['table','back']);vis.append(id)
 # Floor only scenery; no logo or fake software UI on render.
 if state not in ['layers','back']:
  ps=vtk.vtkPlaneSource();ps.SetOrigin(-10000,-10000,-8);ps.SetPoint1(12000,-10000,-8);ps.SetPoint2(-10000,10000,-8)
  mp=vtk.vtkPolyDataMapper();mp.SetInputConnection(ps.GetOutputPort());ac=vtk.vtkActor();ac.SetMapper(mp);ac.GetProperty().SetColor(.94,.936,.922);ren.AddActor(ac)
 ren.AutomaticLightCreationOff()
 for xyz,intensity in [((-500,1900,4500),.95),((2400,-2300,2800),.60),((3600,2400,2200),.35)]:
  light=vtk.vtkLight();light.SetLightTypeToSceneLight();light.SetPosition(*xyz);light.SetFocalPoint(1200,0,380);light.SetIntensity(intensity);ren.AddLight(light)
 # Screen-space occlusion makes soft intersections legible; does not simulate pressure.
 basic=vtk.vtkRenderStepsPass();ssao=vtk.vtkSSAOPass();ssao.SetDelegatePass(basic);ssao.SetRadius(45);ssao.SetBias(2.5);ssao.SetKernelSize(64);ssao.BlurOn();ren.SetPass(ssao)
 cam=ren.GetActiveCamera();cam.ParallelProjectionOn();cam.SetViewUp(0,0,1)
 cam.SetFocalPoint(1200,0,440)
 if view=='iso':cam.SetPosition(3520,3170,2200);cam.SetParallelScale(935)
 elif view=='head':cam.SetPosition(-1280,2770,2150);cam.SetParallelScale(920)
 elif view=='side':cam.SetPosition(1180,5000,390);cam.SetFocalPoint(1180,0,400);cam.SetParallelScale(775)
 elif view=='top':cam.SetPosition(1200,0,5000);cam.SetViewUp(-1,0,0);cam.SetParallelScale(1330)
 elif view=='foot':cam.SetFocalPoint(1900,0,185);cam.SetPosition(2830,1880,1970);cam.SetParallelScale(735)
 elif view=='back':cam.SetFocalPoint(740,0,350);cam.SetPosition(2200,2050,1470);cam.SetParallelScale(740)
 elif view=='hands':cam.SetFocalPoint(1000,0,700);cam.SetPosition(180,2250,2400);cam.SetParallelScale(710)
 elif view=='table':cam.SetFocalPoint(1260,0,340);cam.SetPosition(2300,2500,1770);cam.SetParallelScale(720)
 elif view=='layers':cam.SetFocalPoint(1440,0,630);cam.SetPosition(3000,2820,2000);cam.SetParallelScale(900)
 ren.ResetCameraClippingRange()
 if ui:
  label(ren,'LEZHANDR / R06  —  CAD VIEWER',25,height-42,25)
  label(ren,'Actual OpenCASCADE geometry • VTK rendering • units: mm',25,height-76,17)
  label(ren,'1 closed  2 folded  3 cutaway  4 chamber assembly  5 table  6 foot settings',25,25,16)
  label(ren,'STATE: '+state+'\n\n'+str(len(vis))+' visible parts\n\nNominal shape only\nNo filler simulation',width-260,height-235,18)
 win=vtk.vtkRenderWindow();win.SetWindowName('Lezhandr R06 | OpenCASCADE geometry / VTK');win.SetSize(width,height);win.SetMultiSamples(0);win.AddRenderer(ren)
 return win,ren,vis

def save(state,view,name,width=2300,height=1450):
 win,ren,vis=scene(state,view,width,height);win.SetOffScreenRendering(1);win.Render()
 ff=vtk.vtkWindowToImageFilter();ff.SetInput(win);ff.SetScale(1);ff.Update();wr=vtk.vtkPNGWriter();wr.SetFileName(str(ROOT/'renders'/name));wr.SetInputConnection(ff.GetOutputPort());wr.Write();win.Finalize()
 print(name,len(vis),flush=True)

if __name__=='__main__':
 if '--viewer' in sys.argv:
  win,ren,vis=scene('folded','iso',1550,1000,True);inter=vtk.vtkRenderWindowInteractor();inter.SetRenderWindow(win);inter.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
  def key(obj,event):
   d={'1':('work','head'),'2':('folded','head'),'3':('cutaway','iso'),'4':('back','back'),'5':('table','table'),'6':('foot','foot')}
   if obj.GetKeySym() in d:
    s,v=d[obj.GetKeySym()];ww,rr,_=scene(s,v,1550,1000,True);win.RemoveRenderer(win.GetRenderers().GetFirstRenderer());ww.RemoveRenderer(rr);win.AddRenderer(rr);win.Render()
  inter.AddObserver('KeyPressEvent',key);win.Render();inter.Initialize();inter.Start()
 elif '--quick' in sys.argv:
  save('work','head','quick.png',1500,1000)
 else:
  jobs=[('work','iso','work_closed.png'),('folded','iso','work_folded.png'),('work','iso','work_front.png'),('empty','head','empty.png'),('empty_cut','iso','empty_cutaway.png'),('cutaway','iso','occupied_cutaway.png'),('side_work','side','work_side.png'),('side_relax','side','relax_side.png'),('relax','head','relax.png'),('back','back','back_chambers.png'),('foot','foot','foot_adjustment.png'),('table','table','table_module.png'),('layers','layers','padded_layers.png'),('hands_closed','hands','hands_closed.png'),('hands_folded','hands','hands_folded.png'),('entry','iso','right_access_cutaway.png'),('work','top','top.png'),('small','head','short_person.png')]
  for s,v,n in jobs:save(s,v,n)
