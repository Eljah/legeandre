from pathlib import Path
import json,sys,math
import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk
ROOT=Path(__file__).resolve().parents[1]
PAL={'outer':(.60,.56,.50),'lining':(.17,.30,.37),'cushion':(.28,.41,.46),'floor':(.23,.24,.24),'tray':(.65,.49,.31),'device':(.12,.14,.17),'screen':(.16,.36,.46),'trim':(.13,.23,.29),'heat':(.89,.37,.16),'foam':(.39,.37,.33),'reference':(.50,.61,.65)}
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

def poly(v,f):
    p=vtk.vtkPoints();p.SetData(numpy_to_vtk(np.asarray(v,dtype=np.float64),deep=True))
    c=vtk.vtkCellArray()
    for face in f:
        c.InsertNextCell(len(face))
        for i in face:c.InsertCellPoint(int(i))
    d=vtk.vtkPolyData();d.SetPoints(p);d.SetPolys(c);return d

def lineactor(points,col=(.12,.22,.28),rad=1.7):
    p=vtk.vtkPoints();l=vtk.vtkCellArray();l.InsertNextCell(len(points))
    for i,q in enumerate(points):p.InsertNextPoint(*q);l.InsertCellPoint(i)
    d=vtk.vtkPolyData();d.SetPoints(p);d.SetLines(l)
    t=vtk.vtkTubeFilter();t.SetInputData(d);t.SetRadius(rad);t.SetNumberOfSides(8);t.Update()
    m=vtk.vtkPolyDataMapper();m.SetInputConnection(t.GetOutputPort());a=vtk.vtkActor();a.SetMapper(m);a.GetProperty().SetColor(*col);return a

def fabric_texture():
    n=128;y,x=np.indices((n,n));rng=np.random.default_rng(42)
    weave=.83+.07*np.sin(x*np.pi/4)*np.cos(y*np.pi/4)+rng.normal(0,.021,(n,n))
    a=np.repeat((np.clip(weave,0,1)*255).astype(np.uint8)[:,:,None],3,axis=2)
    img=vtk.vtkImageData();img.SetDimensions(n,n,1);img.GetPointData().SetScalars(numpy_to_vtk(a.reshape(-1,3),deep=True,array_type=vtk.VTK_UNSIGNED_CHAR))
    t=vtk.vtkTexture();t.SetInputData(img);t.InterpolateOn();t.RepeatOn();return t

def getactor(o):
    if 'curve_mm' in o:return lineactor(o['curve_mm'],rad=2.2)
    v=np.array(o['vertices_mm']);d=poly(v,o['faces'])
    clean=vtk.vtkCleanPolyData();clean.SetInputData(d);clean.Update()
    n=vtk.vtkPolyDataNormals();n.SetInputConnection(clean.GetOutputPort());n.ConsistencyOn();n.AutoOrientNormalsOn();n.SplittingOff();n.ComputePointNormalsOn();n.Update()
    data=n.GetOutput()
    if o['kind'] in ['outer','lining','cushion']:
        vv=np.array([data.GetPoint(i) for i in range(data.GetNumberOfPoints())]);uv=np.column_stack(((vv[:,0]+.2*vv[:,1])/90,(vv[:,2]+.45*vv[:,1])/90)).astype(np.float32)
        arr=numpy_to_vtk(uv,deep=True);arr.SetName('UV');data.GetPointData().SetTCoords(arr)
    m=vtk.vtkPolyDataMapper();m.SetInputData(data);a=vtk.vtkActor();a.SetMapper(m);p=a.GetProperty();p.SetColor(*PAL['floor'] if o['id']=='SOFT_UNDERLAY' else PAL[o['kind']]);p.SetInterpolationToPhong();p.SetAmbient(.28);p.SetDiffuse(.72);p.SetSpecular(.055);p.SetSpecularPower(18)
    if o['kind'] in ['outer','lining','cushion']:a.SetTexture(fabric_texture())
    return a

def text(ren,txt,x,y,size=20,col=(.09,.13,.17)):
    t=vtk.vtkTextActor();t.SetInput(txt);tp=t.GetTextProperty();tp.SetFontFamily(vtk.VTK_FONT_FILE);tp.SetFontFile(FONT);tp.SetFontSize(size);tp.SetColor(*col);t.SetPosition(x,y);ren.AddActor2D(t);return t

def scene(state='work',angle=0,view='iso',technical=False,ui=False,show_external=False,w=1800,h=1180):
    items=json.loads((ROOT/'cad/model_R04.json').read_text());r=vtk.vtkRenderer();r.SetBackground(.965,.96,.947)
    visible=[]
    for o in items:
        mode=o['modes']
        if o.get('external') and not show_external:continue
        if o.get('technical') and not technical:continue
        if mode=='work' and state=='sleep':continue
        if mode=='sleep' and state!='sleep':continue
        if mode.startswith('hood') and (state=='sleep' or mode!='hood'+str(angle)):continue
        a=getactor(o)
        if technical and o['kind'] in ['outer','lining','cushion']:a.GetProperty().SetOpacity(.20)
        r.AddActor(a);visible.append(o['id'])
    # CAD seam curves are displayed from the actual common surface boundaries.
    patterns=json.loads((ROOT/'patterns/surfaces_R04.json').read_text())
    for d in patterns:
        if d['id'].startswith('L'):continue
        grid=np.asarray(d['grid_mm']);r.AddActor(lineactor(grid[0],rad=1.5));r.AddActor(lineactor(grid[:,-1],rad=2))
    # Hand-canopy binding shown from the actual simulated grid, with no fake embroidery.
    name='PASSIVE_HOOD_'+str(angle)
    if state!='sleep':
        p=np.array(next(o['vertices_mm'] for o in items if o['id']==name)).reshape(25,49,3)
        for q in [p[0],p[-1],p[:,0],p[:,-1]]:r.AddActor(lineactor(q,rad=2.8))
        # Fabric hinge itself; opposite edge uses manual quick-release tabs.
        if angle==0:
            for x in [995,1295]:r.AddActor(lineactor([[x,-335,545],[x,-356,513]],rad=7))
    # Ground plane is scene-only, never STEP furniture.
    plane=vtk.vtkPlaneSource();plane.SetOrigin(-8000,-8000,-1.2);plane.SetPoint1(9000,-8000,-1.2);plane.SetPoint2(-8000,8000,-1.2)
    mp=vtk.vtkPolyDataMapper();mp.SetInputConnection(plane.GetOutputPort());pa=vtk.vtkActor();pa.SetMapper(mp);pa.GetProperty().SetColor(.95,.943,.927);r.AddActor(pa)
    # Floor is a scene-only reference; no separate shadow/contact solve.
    r.TwoSidedLightingOn()
    r.AutomaticLightCreationOff()
    for pos,intensity in [((-1000,-2500,4500),.75),((2000,1500,3000),.42),((3000,-1000,1500),.18)]:
        l=vtk.vtkLight();l.SetLightTypeToSceneLight();l.SetPosition(*pos);l.SetFocalPoint(1100,0,350);l.SetIntensity(intensity);r.AddLight(l)
    cam=r.GetActiveCamera();cam.SetViewUp(0,0,1);cam.SetFocalPoint(1190,0,420);cam.ParallelProjectionOn()
    if view=='iso':cam.SetPosition(-1500,-3000,2450);cam.SetParallelScale(1170)
    elif view=='foot':cam.SetPosition(3850,-3400,2300);cam.SetParallelScale(1110)
    elif view=='side':cam.SetPosition(1180,-5000,500);cam.SetParallelScale(840)
    elif view=='top':cam.SetPosition(1180,0,5000);cam.SetViewUp(1,0,0);cam.SetParallelScale(1360)
    elif view=='hands':cam.SetFocalPoint(1165,0,660);cam.SetPosition(330,-1250,1800);cam.SetParallelScale(680)
    r.ResetCameraClippingRange()
    if ui:
        text(r,'LEZHANDR LAB / R04   |   OpenCASCADE + VTK',28,h-48,25)
        text(r,f'State: {state}  |  canopy: {angle} deg  |  mm',28,h-84,18)
        text(r,'Own model viewer - not CLO / Rhino / Blender',28,26,17)
        text(r,'Mouse: orbit / pan / zoom  |  keys 1/2/3: closed / open / sleep',28,54,15)
        text(r,'NO HAND HEATER\nPASSIVE HINGED CANOPY\n\n'+str(len(visible))+' displayed parts\n\nModel source:\ncad/model_R04.json\n\nCloth engine:\nXPBD distance network\nUncalibrated materials',w-355,h-345,18)
    win=vtk.vtkRenderWindow();win.SetWindowName('Lezhandr Lab R04 | OpenCASCADE + VTK (not CLO)');win.SetSize(w,h);win.SetMultiSamples(8);win.AddRenderer(r)
    return win,r

def save(win,name):
    win.SetOffScreenRendering(1);win.Render();f=vtk.vtkWindowToImageFilter();f.SetInput(win);f.Update();wr=vtk.vtkPNGWriter();wr.SetInputConnection(f.GetOutputPort());wr.SetFileName(str(ROOT/'renders'/name));wr.Write();win.Finalize()

if __name__=='__main__':
    for state,a,view,name in [('work',0,'iso','work_closed.png'),('work',105,'iso','work_open.png'),('work',0,'foot','work_foot.png'),('work',105,'hands','keyboard_open.png'),('work',0,'hands','keyboard_closed.png'),('work',0,'side','work_side.png'),('sleep',0,'iso','sleep.png'),('work',0,'top','work_top.png')]:
        wi,re=scene(state,a,view);save(wi,name)
    wi,re=scene('work',105,'iso',technical=True,show_external=True);save(wi,'technical.png')
