#!/usr/bin/env python3
"""Executed model viewer, NOT a screenshot imitation of commercial CAD.
Mouse controls are VTK trackball controls. 1=closed,2=open,3=sleep.
"""
import argparse
from render_model import scene
import vtk
p=argparse.ArgumentParser();p.add_argument('--state',choices=['closed','open','sleep'],default='closed');a=p.parse_args()
st,ang=('sleep',0) if a.state=='sleep' else ('work',105 if a.state=='open' else 0)
w,r=scene(st,ang,ui=True,w=1600,h=1040)
inter=vtk.vtkRenderWindowInteractor();inter.SetRenderWindow(w)
inter.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
def key(obj,event):
    global r
    k=obj.GetKeySym()
    if k not in ['1','2','3']:return
    state,an={'1':('work',0),'2':('work',105),'3':('sleep',0)}[k]
    new,rr=scene(state,an,ui=True,w=1600,h=1040);new.RemoveRenderer(rr)
    w.RemoveRenderer(r);w.AddRenderer(rr);r=rr;r.ResetCameraClippingRange();w.Render()
inter.AddObserver('KeyPressEvent',key)
inter.Initialize();w.Render();inter.Start()
