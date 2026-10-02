from pathlib import Path
import cadquery as cq, numpy as np,json,math
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
R=Path(__file__).resolve().parents[1];p=json.load(open(R/'calculations/pose_reference.json'))
u=np.array(p['torso_axis']);hip=np.array(p['hip']);s=np.array(p['shoulder_center']);w=p['wrist_center'];TC=1235;T0=1030;T1=1440
sh=cq.Solid.makeSphere(1,angleDegrees1=-90,angleDegrees2=90).transformGeometry(cq.Matrix([[112,0,0,0],[0,205,0,0],[0,0,350,0],[0,0,0,1]]))
ax=np.cross([0,0,1],u);angle=math.degrees(math.acos(u[2]));body=sh.rotate((0,0,0),tuple(ax),angle).translate(tuple((hip+s)/2))
kz=lambda x:w[2]+(x-w[0])*math.tan(math.radians(16));tz=lambda x:kz(x)-36
for rx,ry in [(0,0),(135,230),(175,260),(180,300)]:
 plate=cq.Workplane('XY').box(T1-T0,680,12).edges('|Z').fillet(22)
 if rx:plate=plate.cut(cq.Workplane('XY').center(1000-TC,0).ellipse(rx,ry).extrude(40,both=True))
 tray=plate.val().rotate((0,0,0),(0,1,0),-16).translate((TC,0,tz(TC)-6))
 d=BRepExtrema_DistShapeShape(body.wrapped,tray.wrapped);d.Perform();a=d.PointOnShape1(1);b=d.PointOnShape2(1)
 print(rx,ry,d.Value(),(a.X(),a.Y(),a.Z()),(b.X(),b.Y(),b.Z()),flush=True)
