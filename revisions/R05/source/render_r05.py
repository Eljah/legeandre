#!/usr/bin/env python3
"""Real VTK renderer/viewer of R05 CAD tessellations. Keys 1..7 change actual layers."""
from pathlib import Path
import json,math,sys
import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk
ROOT=Path(__file__).resolve().parents[1]
PAL={'outer':(.62,.58,.52),'lining':(.16,.31,.37),'cushion':(.30,.46,.50),'floor':(.18,.20,.21),'tray':(.61,.46,.30),'device':(.13,.15,.17),'screen':(.18,.36,.47),'frame':(.90,.47,.12),'padding':(.80,.72,.52),'human':(.68,.76,.78),'trim':(.10,.21,.26),'cape':(.30,.46,.50),'flap':(.52,.64,.66),'cavity':(.10,.61,.78)}
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
ITEMS=json.loads((ROOT/'cad/model_R05.json').read_text())

def poly(v,f):
    p=vtk.vtkPoints();p.SetData(numpy_to_vtk(np.array(v,dtype=np.float64),deep=True));c=vtk.vtkCellArray()
    for face in f:
        c.InsertNextCell(len(face))
        for j in face:c.InsertCellPoint(int(j))
    d=vtk.vtkPolyData();d.SetPoints(p);d.SetPolys(c);return d

def line(r,p,color=(.12,.22,.27),rad=2):
    pt=vtk.vtkPoints();c=vtk.vtkCellArray();c.InsertNextCell(len(p))
    for i,x in enumerate(p):pt.InsertNextPoint(*x);c.InsertCellPoint(i)
    d=vtk.vtkPolyData();d.SetPoints(pt);d.SetLines(c);f=vtk.vtkTubeFilter();f.SetInputData(d);f.SetRadius(rad);f.SetNumberOfSides(10)
    m=vtk.vtkPolyDataMapper();m.SetInputConnection(f.GetOutputPort());a=vtk.vtkActor();a.SetMapper(m);a.GetProperty().SetColor(*color);r.AddActor(a);return a

def label(r,txt,x,y,size=20,color=(.12,.19,.23)):
    t=vtk.vtkTextActor();t.SetInput(txt);p=t.GetTextProperty();p.SetFontFamily(vtk.VTK_FONT_FILE);p.SetFontFile(FONT);p.SetFontSize(size);p.SetColor(*color);t.SetPosition(x,y);r.AddActor2D(t);return t

def add_actor(r,o,clip_right=False,opacity=1,translate=None):
    v=np.array(o['vertices_mm']);f=o['faces'];d=poly(v,f)
    if translate is not None:
        v+=np.array(translate);d=poly(v,f)
    clean=vtk.vtkCleanPolyData();clean.SetInputData(d);clean.Update();inp=clean.GetOutputPort()
    if clip_right:
        plane=vtk.vtkPlane();plane.SetOrigin(0,0,0);plane.SetNormal(0,1,0)
        if o['group'] in ['floor_soft','support_foam'] or o['id']=='PELVIS_PAD':
            # Actual VTK plane section: add section caps to closed solids only.
            plane.SetNormal(0,-1,0)
            planes=vtk.vtkPlaneCollection();planes.AddItem(plane)
            cl=vtk.vtkClipClosedSurface();cl.SetInputConnection(inp);cl.SetClippingPlanes(planes);cl.SetTolerance(.001);cl.Update();inp=cl.GetOutputPort()
        else:
            cl=vtk.vtkClipPolyData();cl.SetInputConnection(inp);cl.SetClipFunction(plane);cl.InsideOutOn();cl.Update();inp=cl.GetOutputPort()
    norm=vtk.vtkPolyDataNormals();norm.SetInputConnection(inp);norm.ConsistencyOn();norm.SplittingOff();norm.AutoOrientNormalsOn();norm.Update()
    m=vtk.vtkPolyDataMapper();m.SetInputConnection(norm.GetOutputPort());m.SetResolveCoincidentTopologyToPolygonOffset();m.SetRelativeCoincidentTopologyPolygonOffsetParameters(-2,-2) if o['id'] in ['B01_BACK_LINER','B03_LEG_LINER'] else None;a=vtk.vtkActor();a.SetMapper(m);p=a.GetProperty();p.SetColor(*PAL['lining'] if o['group']=='frame_padding' else PAL[o['kind']]);p.SetAmbient(.27);p.SetDiffuse(.73);p.SetSpecular(.10 if o['kind']=='frame' else .035);p.SetSpecularPower(20);p.SetOpacity(opacity);r.AddActor(a);return a

def scene(view='iso',state='rolled',ui=False,shift=None,transparent=False,w=1900,h=1250):
    r=vtk.vtkRenderer();r.SetBackground(.966,.960,.948);visible=[]
    for o in ITEMS:
        g=o['group'];oid=o['id'];modes=o['modes'];mode=state
        if state in ['closed','rolled','hands'] and g in ['frame','joints']:continue
        if state in ['cutaway','section','hands']:mode='rolled'
        if state=='empty':mode='interior'
        if state=='frame':
            if g not in ['frame','joints','desk','laptop','key']:continue
        elif state=='egress':
            if g in ['quilt','frame_padding','space_reference','pattern_geometry']:continue
            if o.get('access_gate'):continue
            if g=='manikin':
                if not oid.startswith('EXIT_'):continue
            elif 'interior' not in modes:continue
        else:
            if mode not in modes:continue
            if state=='empty' and g=='manikin':continue
            if state=='sleep' and (g in ['frame','joints','frame_padding','sling','support_foam'] or oid.startswith(('B01','BACK_','PELVIS','B03'))):continue
        if oid.startswith('EXIT_') and state not in ['exit','egress']:continue
        clip=state in ['cutaway','section','empty'] and g in ['outer_shell','floor_soft','support','support_foam','sling','quilt','frame_padding']
        if state in ['cutaway','section','empty','frame','egress'] and g=='frame_padding':continue
        if state=='section' and g=='quilt':continue
        if state=='hands' and g in ['frame','joints','frame_padding','floor_soft']:continue
        if state=='egress' and g=='outer_shell':clip=True
        trans=None
        if state=='egress' and g=='manikin':trans=(0,(shift or 0)-800,0)
        if state=='egress' and g in ['desk','laptop','key']:trans=(80,0,0)
        opacity=.22 if transparent and g in ['outer_shell','quilt'] else 1
        if state=='cutaway' and g=='quilt':opacity=.30
        add_actor(r,o,clip,opacity,trans);visible.append(oid)
        # Embroidery is not invented; actual new seam lines on developable cloth.
        if 'grid_mm' in o and g=='quilt' and not transparent and state not in ['section','empty','egress']:
            grid=np.array(o['grid_mm'])
            for edge in [grid[0],grid[-1],grid[:,0],grid[:,-1]]:
                if clip:edge=edge[edge[:,1]<=0]
                if len(edge)>1:line(r,edge,rad=1.5)
    # Scene-only floor.
    ground=vtk.vtkPlaneSource();ground.SetOrigin(-3000,-3000,-2);ground.SetPoint1(5000,-3000,-2);ground.SetPoint2(-3000,4000,-2)
    mp=vtk.vtkPolyDataMapper();mp.SetInputConnection(ground.GetOutputPort());a=vtk.vtkActor();a.SetMapper(mp);a.GetProperty().SetColor(.942,.938,.925);r.AddActor(a)
    r.AutomaticLightCreationOff()
    for p,intens in [((-1000,2500,4500),.85),((2100,-2500,3600),.50),((3200,1200,2300),.2)]:
        l=vtk.vtkLight();l.SetLightTypeToSceneLight();l.SetPosition(*p);l.SetFocalPoint(1200,0,400);l.SetIntensity(intens);r.AddLight(l)
    cam=r.GetActiveCamera();cam.ParallelProjectionOn();cam.SetViewUp(0,0,1);cam.SetFocalPoint(1210,0,445)
    if view=='iso':cam.SetPosition(3650,3200,2450);cam.SetParallelScale(1000)
    elif view=='foot':cam.SetPosition(3700,3400,2450);cam.SetParallelScale(1110)
    elif view=='side':cam.SetPosition(1150,5000,465);cam.SetParallelScale(870)
    elif view=='front':cam.SetPosition(4200,0,380);cam.SetParallelScale(780)
    elif view=='top':cam.SetPosition(1180,0,5000);cam.SetViewUp(-1,0,0);cam.SetParallelScale(1320)
    elif view=='hands':cam.SetFocalPoint(1020,0,650);cam.SetPosition(300,1700,2050);cam.SetParallelScale(650)
    elif view=='frame':cam.SetFocalPoint(1050,0,290);cam.SetPosition(2600,2700,2200);cam.SetParallelScale(860)
    elif view=='egress':cam.SetFocalPoint(1220,430,370);cam.SetPosition(3500,3200,2700);cam.SetParallelScale(1430)
    r.ResetCameraClippingRange()
    if ui:
        label(r,'LEZHANDR LAB  |  R05  |  OpenCASCADE / VTK',25,h-45,26)
        label(r,'Actual model viewer. Not CLO / Rhino / SolidWorks.',25,h-78,17)
        label(r,'1 closed   2 rolled flap   3 cutaway   4 empty   5 C-frame   6 exit\nMouse: rotate / pan / zoom. All dimensions in millimetres.',25,25,17)
        label(r,f'STATE: {state}\n\n{len(visible)} displayed items\nY+ = occupant RIGHT\n\nShoulder / arm wrap\nSoft roll-back flap\nLocal left C-support\nNo hand heater\n\nNominal upholstery\nAnalytical screening\nNot a human test',w-340,h-415,19)
    win=vtk.vtkRenderWindow();win.SetWindowName('Lezhandr R05 | Real OpenCASCADE/VTK viewer');win.SetSize(w,h);win.SetMultiSamples(8);win.AddRenderer(r)
    return win,r

def save(view,state,name,**kw):
    win,r=scene(view,state,**kw);win.SetOffScreenRendering(1);win.Render();cap=vtk.vtkWindowToImageFilter();cap.SetInput(win);cap.Update();wr=vtk.vtkPNGWriter();wr.SetInputConnection(cap.GetOutputPort());wr.SetFileName(str(ROOT/'renders'/name));wr.Write();win.Finalize()

if __name__=='__main__':
    if '--viewer' in sys.argv:
        state=sys.argv[-1] if sys.argv[-1] in ['closed','rolled','cutaway','empty','frame','egress'] else 'cutaway'
        win,r=scene('iso' if state!='frame' else 'frame',state,ui=True,w=1600,h=1000)
        inter=vtk.vtkRenderWindowInteractor();inter.SetRenderWindow(win);inter.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
        def key(obj,event):
            states={'1':'closed','2':'rolled','3':'cutaway','4':'empty','5':'frame','6':'egress'}
            k=obj.GetKeySym()
            if k in states:
                ww,rr=scene('frame' if k=='5' else 'iso',states[k],ui=True,w=1600,h=1000);win.RemoveRenderer(win.GetRenderers().GetFirstRenderer());ww.RemoveRenderer(rr);win.AddRenderer(rr);win.Render()
        inter.AddObserver('KeyPressEvent',key);win.Render();inter.Initialize();inter.Start()
    else:
        for view,state,name in [('iso','closed','work_closed.png'),('iso','rolled','work_rolled.png'),('iso','empty','empty_cutaway.png'),('iso','cutaway','occupied_cutaway.png'),('side','section','side_section.png'),('front','cutaway','C_front.png'),('hands','closed','hands_closed.png'),('hands','rolled','hands_rolled.png'),('frame','frame','frame_iso.png'),('iso','sleep','sleep_module_removed.png')]:
            print(name,flush=True);save(view,state,name)
        for i,shift in enumerate([0,260,520,800]):save('egress','egress',f'exit_{i}.png',shift=shift)
