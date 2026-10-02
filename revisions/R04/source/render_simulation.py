"""Plots the computed cloth arrays, in VTK. Colors mean displacement, not stress."""
from pathlib import Path
import numpy as np,vtk
from vtk.util.numpy_support import numpy_to_vtk
from render_model import poly,text
R=Path(__file__).resolve().parents[1]
for name in ['hood','foot_quilt','sleep_quilt']:
    z=np.load(R/'simulation'/f'{name}_drape.npz');p=z['initial_m']*1000;q=z['final_m']*1000;f=z['triangles'];pins=z['pins']
    r=vtk.vtkRenderer();r.SetBackground(.965,.96,.947)
    d=poly(q,f);values=np.linalg.norm(q-p,axis=1);a=numpy_to_vtk(values,deep=True);a.SetName('Displacement / mm');d.GetPointData().SetScalars(a)
    m=vtk.vtkPolyDataMapper();m.SetInputData(d);m.SetScalarRange(0,float(values.max()));act=vtk.vtkActor();act.SetMapper(m);act.GetProperty().EdgeVisibilityOn();act.GetProperty().SetEdgeColor(.25,.25,.25);r.AddActor(act)
    mi=vtk.vtkPolyDataMapper();mi.SetInputData(poly(p,f));ai=vtk.vtkActor();ai.SetMapper(mi);ai.GetProperty().SetRepresentationToWireframe();ai.GetProperty().SetColor(.50,.50,.50);ai.GetProperty().SetOpacity(.24);r.AddActor(ai)
    points=vtk.vtkPoints();points.SetData(numpy_to_vtk(p[pins],deep=True));po=vtk.vtkPolyData();po.SetPoints(points);so=vtk.vtkSphereSource();so.SetRadius(3.5 if name=='hood' else 5)
    g=vtk.vtkGlyph3D();g.SetSourceConnection(so.GetOutputPort());g.SetInputData(po);g.ScalingOff();gm=vtk.vtkPolyDataMapper();gm.SetInputConnection(g.GetOutputPort());ga=vtk.vtkActor();ga.SetMapper(gm);ga.GetProperty().SetColor(.12,.12,.12);r.AddActor(ga)
    bar=vtk.vtkScalarBarActor();bar.SetLookupTable(m.GetLookupTable());bar.SetTitle('Displacement / mm');bar.SetNumberOfLabels(5);bar.SetPosition(.87,.23);bar.SetWidth(.10);bar.SetHeight(.52);bar.GetTitleTextProperty().SetColor(.1,.1,.1);bar.GetLabelTextProperty().SetColor(.1,.1,.1);r.AddActor2D(bar)
    c=r.GetActiveCamera();center=q.mean(0);c.SetFocalPoint(*center);c.SetPosition(*(center+np.array([-800,-1400,1100])));c.SetViewUp(0,0,1);c.ParallelProjectionOn();c.SetParallelScale(410 if name=='hood' else (700 if name=='foot_quilt' else 1040));r.ResetCameraClippingRange()
    text(r,name+' / computed cloth mesh',24,835,24);text(r,'Gray: initial mesh   |   Black nodes: fixed   |   Color: displacement',24,800,18);text(r,'Uncalibrated fabric; fixed support; no self-collision or foam mechanics',24,22,17)
    w=vtk.vtkRenderWindow();w.SetOffScreenRendering(1);w.SetSize(1400,880);w.AddRenderer(r);w.Render();fil=vtk.vtkWindowToImageFilter();fil.SetInput(w);fil.Update();wr=vtk.vtkPNGWriter();wr.SetInputConnection(fil.GetOutputPort());wr.SetFileName(str(R/'renders'/f'{name}_simulation.png'));wr.Write();w.Finalize()
