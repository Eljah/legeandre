#!/usr/bin/env python3
"""Render actual R08 BREP tessellation in VTK. No generative images or fake CAD UI."""
from pathlib import Path
import json,sys,math,os,time,subprocess
import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk
ROOT=Path(__file__).resolve().parents[1]
ROWS=json.loads((ROOT/'cad/model_R08.json').read_text());PAL=json.loads((ROOT/'cad/palette.json').read_text())
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
def text(r,s,x,y,size=20):
 a=vtk.vtkTextActor();a.SetInput(s);p=a.GetTextProperty();p.SetFontFamily(vtk.VTK_FONT_FILE);p.SetFontFile(FONT);p.SetFontSize(size);p.SetColor(.26,.20,.15);a.SetPosition(x,y);r.AddActor2D(a)
def texture():
 yy,xx=np.mgrid[:256,:256];rnd=np.random.default_rng(808);im=.985+.005*np.sin(xx*2*np.pi/5)+.005*np.cos(yy*2*np.pi/5)+rnd.normal(0,.002,xx.shape);rgb=np.repeat(np.clip(im[...,None]*255,0,255).astype('uint8'),3,2)
 d=vtk.vtkImageData();d.SetDimensions(256,256,1);d.GetPointData().SetScalars(numpy_to_vtk(rgb.reshape(-1,3),deep=True,array_type=vtk.VTK_UNSIGNED_CHAR));t=vtk.vtkTexture();t.SetInputData(d);t.InterpolateOn();t.RepeatOn();return t
TEX=texture()
def actor(r,o,clip=False,move=(0,0,0),colour=None,opacity=1):
 v=np.array(o['vertices_mm']).reshape((-1,3))+move;p=vtk.vtkPoints();p.SetData(numpy_to_vtk(v,deep=True));d=vtk.vtkPolyData();d.SetPoints(p)
 if not o['faces']:
  pp=o.get('polyline_mm')
  if not pp:return
  p=vtk.vtkPoints();ca=vtk.vtkCellArray();ca.InsertNextCell(len(pp))
  for i,q in enumerate(np.array(pp)+move):p.InsertNextPoint(*q);ca.InsertCellPoint(i)
  d.SetPoints(p);d.SetLines(ca);tube=vtk.vtkTubeFilter();tube.SetInputData(d);tube.SetRadius(o.get('radius_mm',2));tube.SetNumberOfSides(8);port=tube.GetOutputPort()
 else:
  ca=vtk.vtkCellArray()
  for row in o['faces']:
   ca.InsertNextCell(len(row))
   for i in row:ca.InsertCellPoint(int(i))
  d.SetPolys(ca);clean=vtk.vtkCleanPolyData();clean.SetInputData(d)
  normals=vtk.vtkPolyDataNormals();normals.SetInputConnection(clean.GetOutputPort());normals.ConsistencyOn();normals.AutoOrientNormalsOn();normals.SplittingOff();port=normals.GetOutputPort()
 if clip:
  plane=vtk.vtkPlane();plane.SetOrigin(0,0,0);plane.SetNormal(0,-1,0);pc=vtk.vtkPlaneCollection();pc.AddItem(plane);c=vtk.vtkClipClosedSurface();c.SetInputConnection(port);c.SetClippingPlanes(pc);c.SetTolerance(.01);c.GenerateFacesOn();port=c.GetOutputPort()
 m=vtk.vtkPolyDataMapper();m.SetInputConnection(port);m.ScalarVisibilityOff();a=vtk.vtkActor();a.SetMapper(m);pr=a.GetProperty();pr.SetColor(*(colour or PAL[o['kind']]));pr.SetAmbient(.3);pr.SetDiffuse(.7);pr.SetSpecular(0 if o['kind'] in ['cloth','lining','contact'] else .04);pr.SetOpacity(opacity)
 if o['kind'] in ['cloth','lining','contact'] and not clip and o['faces']:
  uv=vtk.vtkTextureMapToCylinder();uv.SetInputConnection(port);uv.PreventSeamOff();uv.AutomaticCylinderGenerationOn();tx=vtk.vtkTransformTextureCoords();tx.SetInputConnection(uv.GetOutputPort());tx.SetScale(8,10,1);m.SetInputConnection(tx.GetOutputPort());a.SetTexture(TEX)
 r.AddActor(a)
def scene(state='open',view='head',width=2200,height=1500,ui=False):
 r=vtk.vtkRenderer();r.SetBackground(.967,.955,.933)
 for o in ROWS:
  g=o['group'];move=np.array([0.,0,0]);clip=False;visible=state
  if state in ['cutaway','rear','wiring','thermal','entry']:visible='open'
  if visible not in o['states']:continue
  if state in ['open','closed','rear'] and g in ['heater','harness','zipper']:continue
  if state=='wiring' and g not in ['harness','service','zipper','desk','laptop','frame','heater','floor','human']:continue
  if state=='thermal' and g not in ['heater','human','contact_fill','pelvis','desk']:continue
  if state=='cutaway':
   if g in ['leg_quilt','shoulder','flap','zipper','frame_padding']:continue
   if g in ['lower_shell','rear_gusset','hood','floor','forming_fill','contact_fill','pelvis','leg_support','pillow']:clip=True
  if state=='entry':
   if g in ['shoulder','leg_quilt','flap','human']:continue
   if g in ['lower_shell','rear_gusset','hood','floor']:clip=True
   if g in ['desk','laptop']:move[0]=80
  if state=='thermal':actor(r,o,colour=(.75,.79,.77) if g=='human' else None,opacity=.28 if g in ['human','contact_fill','pelvis'] else 1);continue
  actor(r,o,clip,move)
 plane=vtk.vtkPlaneSource();plane.SetOrigin(-6000,-6000,-8);plane.SetPoint1(8000,-6000,-8);plane.SetPoint2(-6000,6000,-8);m=vtk.vtkPolyDataMapper();m.SetInputConnection(plane.GetOutputPort());a=vtk.vtkActor();a.SetMapper(m);a.GetProperty().SetColor(.954,.941,.919);r.AddActor(a)
 r.AutomaticLightCreationOff()
 for loc,intensity in [((-1200,2300,4000),.9),((2600,-2100,2600),.7),((3300,3300,2200),.4)]:
  l=vtk.vtkLight();l.SetPosition(*loc);l.SetFocalPoint(1200,0,400);l.SetIntensity(intensity);r.AddLight(l)
 steps=vtk.vtkRenderStepsPass();ao=vtk.vtkSSAOPass();ao.SetDelegatePass(steps);ao.SetRadius(35);ao.SetBias(2);ao.SetKernelSize(64);ao.BlurOn();r.SetPass(ao)
 c=r.GetActiveCamera();c.ParallelProjectionOn();c.SetViewUp(0,0,1);c.SetFocalPoint(1160,0,555);c.SetParallelScale(1050)
 if view=='head':c.SetPosition(-1500,2700,2050)
 if view=='foot':c.SetPosition(3450,2900,2200)
 if view=='rear':c.SetPosition(-2200,-2600,1250);c.SetFocalPoint(760,0,575);c.SetParallelScale(950)
 if view=='side':c.SetPosition(1170,5000,550);c.SetParallelScale(900)
 if view=='thermal':c.SetPosition(2600,2700,1550);c.SetFocalPoint(950,0,470);c.SetParallelScale(720)
 if view=='top':c.SetPosition(1150,0,6000);c.SetViewUp(-1,0,0);c.SetParallelScale(1380)
 if ui:
  text(r,'LEZHANDR R08 | Real OpenCASCADE geometry / VTK',22,height-40,23);text(r,'Matte sepia | no conductive path through occupant | mm',22,height-72,17);text(r,'Mouse: rotate / zoom | X: head-to-feet | Y+: right exit',22,20,17)
 r.ResetCameraClippingRange();w=vtk.vtkRenderWindow();w.SetWindowName('Lezhandr R08 - actual CAD viewer');w.SetSize(width,height);w.SetMultiSamples(0);w.AddRenderer(r);return w
if __name__=='__main__':
 if '--viewer' in sys.argv:
  w=scene(ui=True,width=1500,height=1000);it=vtk.vtkRenderWindowInteractor();it.SetRenderWindow(w);it.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera());w.Render();it.Initialize();it.Start()
 elif '--capture' in sys.argv:
  from PIL import ImageGrab
  xv=subprocess.Popen(['Xvfb',':93','-screen','0','1500x1000x24'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(1);env=os.environ.copy();env['DISPLAY']=':93';p=subprocess.Popen([sys.executable,__file__,'--viewer'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  try:
   time.sleep(12);ImageGrab.grab(xdisplay=':93').save(ROOT/'renders/VTK_R08_actual.png')
  finally:p.terminate();xv.terminate()
 else:
  for state,view,name in [('open','foot','work_open.png'),('closed','foot','work_closed.png'),('rear','rear','rear_closed.png'),('cutaway','side','occupied_cutaway.png'),('cutaway','head','interior.png'),('thermal','thermal','corrected_heaters.png'),('wiring','foot','harness_layout.png'),('entry','foot','right_entry.png'),('open','top','top.png')]:
   w=scene(state,view);w.SetOffScreenRendering(1);w.Render();f=vtk.vtkWindowToImageFilter();f.SetInput(w);f.Update();wr=vtk.vtkPNGWriter();wr.SetFileName(str(ROOT/'renders'/name));wr.SetInputConnection(f.GetOutputPort());wr.Write();w.Finalize();print('RENDER',name,flush=True)
