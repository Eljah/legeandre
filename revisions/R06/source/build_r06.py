#!/usr/bin/env python3
"""R06: edit R05 desk, replace body support and upholstery.
Millimetres, nominal geometries; NOT a granular/contact/cloth simulation.
Source history/R05/Lezhandr_R05_rolled.step is genuinely read and reused.
"""
from pathlib import Path
import cadquery as cq
import numpy as np
from scipy.interpolate import PchipInterpolator as Pchip
import json, math, hashlib, sys
ROOT=Path(__file__).resolve().parents[1]
for d in ['cad','calculations','tests','patterns']:(ROOT/d).mkdir(exist_ok=True)
ITEMS=[];SHAPES={};BEAMS=[];PROFILES={}
PAL={
 'cloth':(.42,.51,.53),'lining':(.56,.64,.64),'seam':(.24,.33,.35),
 'fill1':(.76,.66,.46),'fill2':(.62,.72,.66),'contact':(.63,.73,.74),
 'webbing':(.28,.32,.30),'hardware':(.25,.29,.29),'frame':(.81,.49,.22),
 'floor':(.27,.32,.33),'tray':(.58,.46,.33),'device':(.15,.18,.20),
 'screen':(.23,.41,.49),'human':(.75,.79,.78),'white':(.87,.89,.87)}

def dump(p,x):
 p.write_text(json.dumps(x,ensure_ascii=False,indent=2,default=lambda x:x.item() if isinstance(x,np.generic) else x.tolist()))

def add(id,shape,kind,group,states=('work','folded','empty','cutaway','relax','small','entry'),desc='',source=None):
 if not id.startswith('KEY_'): print('BUILD',id,flush=True)
 if id in SHAPES: raise ValueError('duplicate '+id)
 if not shape.isValid():raise RuntimeError('invalid shape '+id)
 v,f=shape.tessellate(1.8,.20)
 b=shape.BoundingBox()
 o={'id':id,'kind':kind,'group':group,'states':list(states),'description':desc,
 'vertices_mm':[p.toTuple() for p in v],'faces':f,
 'bounds_mm':[b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax],
 'tessellation_bounds_mm':([min(p.x for p in v),max(p.x for p in v),min(p.y for p in v),max(p.y for p in v),min(p.z for p in v),max(p.z for p in v)] if v else [b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax]),
 'solid_count':len(shape.Solids()),'volume_litre':shape.Volume()/1e6 if shape.Solids() else None}
 if source:o['source']=source
 ITEMS.append(o);SHAPES[id]=shape
 return o

def boxshape(c,dim,fillet=0,tilt=0):
 w=cq.Workplane('XY').box(*dim)
 if fillet:w=w.edges().fillet(fillet)
 return w.val().rotate((0,0,0),(0,1,0),-tilt).translate(c)

def ellipse_solid(c,r,direction=None):
 sh=cq.Solid.makeSphere(1,angleDegrees1=-90,angleDegrees2=90).transformGeometry(cq.Matrix([[r[0],0,0,0],[0,r[1],0,0],[0,0,r[2],0],[0,0,0,1]]))
 if direction is not None:
  d=np.array(direction)/np.linalg.norm(direction);axis=np.cross([0,0,1],d);angle=math.degrees(math.acos(np.clip(d[2],-1,1)))
  if np.linalg.norm(axis)>1e-8:sh=sh.rotate((0,0,0),tuple(axis),angle)
 return sh.translate(c)

def rounded_limb(a,b,r):
 a=np.array(a);b=np.array(b);v=b-a
 sh=cq.Solid.makeCylinder(r,float(np.linalg.norm(v)),cq.Vector(*a),cq.Vector(*v))
 for p in [a,b]:sh=sh.fuse(cq.Solid.makeSphere(r,cq.Vector(*p),angleDegrees1=-90,angleDegrees2=90))
 return sh

def wire(points):
 # Periodic interpolant, no duplicate end point.
 pts=np.array(points,float)
 if np.linalg.norm(pts[0]-pts[-1])<1e-6:pts=pts[:-1]
 return cq.Wire.assembleEdges([cq.Edge.makeSpline([cq.Vector(*p) for p in pts],periodic=True)])

def loft(rings):return cq.Solid.makeLoft([wire(p) for p in rings],False)

def seam(id,pts,states,group='seams',rad=1.5):
 # A genuine BREP edge accompanies the rendering spline; not a painted screenshot.
 e=cq.Edge.makeSpline([cq.Vector(*p) for p in pts])
 o=add(id,e,'seam',group,states);o['polyline_mm']=np.asarray(pts).tolist();o['radius_mm']=rad
 return o

# 1. Padded lower eggshell, a continuous finite-thickness BREP volume.
px=np.array([55,150,300,450,650,850,1050,1300,1600,1900,2140,2290,2345.])
pw=np.array([65,250,400,490,532,545,545,527,496,444,350,205,65.])
pr=np.array([150,410,775,835,780,630,500,409,360,353,346,295,165.])
pb=np.array([40,15,8,8,8,8,8,8,8,8,10,20,50.])
W=Pchip(px,pw);R=Pchip(px,pr);B=Pchip(px,pb)

def tub_ring(x):
 w=float(W(x));rim=float(R(x));base=float(B(x));t=min(72,w*.42,(rim-base)*.48)
 th=np.linspace(-np.pi/2,np.pi/2,25)
 outer=np.c_[np.full(len(th),x),w*np.sin(th),base+(rim-base)*(1-np.cos(th))**4]
 a=np.linspace(0,np.pi,10)[1:]
 capr=np.c_[np.full(len(a),x),w-t/2+t/2*np.cos(a),rim+t/2*np.sin(a)]
 thi=th[::-1][1:]
 inner=np.c_[np.full(len(thi),x),(w-t)*np.sin(thi),base+t+(rim-base-t)*(1-np.cos(thi))**4]
 capl=np.c_[np.full(len(a),x),-w+t/2+t/2*np.cos(a),rim+t/2*np.sin(a)]
 return np.vstack([outer,capr,inner,capl])
# Split at genuine transverse bag/chamber seams. Geometry is a padded shape, not a sheet.
segments=[55,260,530,810,1120,1460,1790,2100,2250]
for i,(a,b) in enumerate(zip(segments[:-1],segments[1:]),1):
 if b<=530:continue
 xs=np.linspace(a,b,6);sh=loft([tub_ring(x) for x in xs])
 add(f'O{i:02d}_PADDED_LOWER',sh,'cloth','lower_shell',desc='Outer lower padded cocoon chamber; cloth and filler represented by one nominal envelope.')
 if i<8:
  p=tub_ring(b);seam(f'SEAM_LOWER_{i}',p,('work','folded','empty','cutaway','relax','small','entry'))
# Soft ground contact, no furniture legs.
solex=np.linspace(70,2335,70)
solepoints=np.vstack([np.c_[solex,[W(x) for x in solex]],np.c_[solex[::-1],[-W(x) for x in solex[::-1]]]])
sole=cq.Workplane('XY').spline([tuple(p) for p in solepoints],periodic=True).close().extrude(62).val()
add('G01_FLEXIBLE_FLOOR',sole,'cloth','floor',desc='62 mm padded flexible floor enclosure; not a rigid plate. Conceals low table rails.')
# Removable head cushion sewn to the rear lining.
add('N01_HEAD_CUSHION',ellipse_solid((480,0,730),(110,275,155),(-.65,0,.76)),'lining','pillow',desc='Soft granular head-zone bolstering; not a rigid neck support.')

hood_outer=ellipse_solid((400,0,470),(340,560,470))
hood_inner=ellipse_solid((480,0,480),(290,467,380))
hood=hood_outer.cut(hood_inner).intersect(boxshape((-550,0,600),(2300,2500,2000)))
add('O00_PADDED_HOOD',hood,'cloth','lower_shell',desc='Closed rear padded shell. Front plane at X=600 joins lower cocoon, no back frame.')
toe=ellipse_solid((2220,0,210),(145,320,190)).cut(ellipse_solid((2165,0,210),(140,245,126)))
toe=toe.intersect(boxshape((2750,0,400),(1040,2200,1500)))
add('O09_PADDED_TOE_BOX',toe,'cloth','lower_shell',desc='Closed padded toe shell, no hard footboard.')

# 2. Original desk/laptop geometry is imported by component name.
base=cq.Assembly.load(str(ROOT/'history/R05/Lezhandr_R05_rolled.step'))
source_ids=[]
for id,o in base.objects.items():
 if o.obj is None:continue
 if id=='TRAY_VENTED' or id.startswith(('LAPTOP_','RUBBER_RISER_','KEY_')):
  kind='tray' if id=='TRAY_VENTED' else ('screen' if id=='LAPTOP_SCREEN' else 'device')
  sh=o.obj.located(o.loc).translate((0,0,25))
  g='desk' if id=='TRAY_VENTED' else 'laptop'
  add(id,sh,kind,g,source='R05 named STEP component; translated +25 mm Z; no new image geometry')
  source_ids.append(id)
# Independent C-desk module. No inclined rails / sling / props under the back.

def tube(id,a,b,depth=45,width=25,t=2.5):
 a=np.array(a,float);b=np.array(b,float);v=b-a;L=float(np.linalg.norm(v));d=v/L
 xd=np.array([1.,0,0]) if abs(d[1])>.8 or abs(d[2])>.95 else np.array([0.,1,0])
 xd-=d*np.dot(xd,d);xd/=np.linalg.norm(xd)
 plane=cq.Plane(origin=tuple(a),xDir=tuple(xd),normal=tuple(d))
 sh=cq.Workplane(plane).rect(width,depth).rect(width-2*t,depth-2*t).extrude(L).val()
 mass=(width*depth-(width-2*t)*(depth-2*t))*L*2.7e-6
 o=add(id,sh,'frame','frame');o['axis_mm']=[a.tolist(),b.tolist()];o['mass_kg']=mass
 BEAMS.append({'id':id,'a':a.tolist(),'b':b.tolist(),'L_mm':L,'section_mm':[depth,width,t],'mass_kg':mass})
 return sh
bx0=955.;bx1=1565.;by=445.;bz=30.
for sy in [-1,1]:tube('D_BASE_LONG_'+str(sy),(bx0,sy*by,bz),(bx1,sy*by,bz),35,20,2)
for x in [bx0,bx1,1120]:tube('D_BASE_CROSS_'+str(x),(x,-by,bz),(x,by,bz),35,20,2)
wrist_z=510.2396898118931
kz=lambda x:wrist_z+(x-1130.7950132277535)*math.tan(math.radians(16))
tz=lambda x:kz(x)-36
for i,x in enumerate([1110,1380],1):
 top=tz(x)-12-22.5
 tube(f'D_C{i}_LEFT_COLUMN',(x,-by,bz),(x,-by,top))
 tube(f'D_C{i}_CANTILEVER',(x,-by,top),(x,330,top))
 add(f'D_JOINT_{i}',boxshape((x,-by,top-40),(60,60,90),3),'frame','frame')
 # Adjustable stub within sleeve, geometric only; not a production clamp.
 add(f'D_ADJUSTER_{i}',boxshape((x,-by,top-80),(70,70,38),5),'hardware','hardware',desc='Concept height collar. Lock, holes and hold-downs not detailed.')
for b in BEAMS:
 if 'BASE' in b['id']:continue
 a=np.array(b['a']);bb=np.array(b['b']);rad=51
 pad=rounded_limb(a,bb,rad).intersect(boxshape((1200,0,1010),(5000,5000,2000)))  # Z >= 10 mm; no padding below floor
 if 'CANTILEVER' in b['id']:
  pad=pad.intersect(cq.Workplane('XY').box(5000,5000,2000).translate((1200,0,tz(a[0])-14-1000)).val())
 add('PAD_'+b['id'],pad,'cloth','frame_padding')
# Sole load spreader pads under the local table, not under shoulders/head.
for x in [bx0,bx1]:
 for sy in [-1,1]:add(f'D_FLOOR_PAD_{int(x)}_{sy}',boxshape((x,sy*by,7),(135,125,14),5),'floor','table_feet',desc='Flush rubber/flexible pad inside sole, not external legs.')

# 3. Two prescribed postures, both WITHOUT spinal frame.
def person(h=2000,back=55):
 u=np.array([-math.cos(math.radians(back)),0,math.sin(math.radians(back))]);n=np.array([u[2],0,-u[0]])
 H=np.array([1050.,0,230. if back==55 else 197.]);S=H+.30*h*u
 E=S+np.array([.165*h*.5,0,-.165*h*math.sin(math.radians(60))])
 f=.1425*h;dy=.045*h;fw=math.sqrt(f*f-dy*dy)
 wr=E+np.array([fw*math.cos(math.radians(16)),0,fw*math.sin(math.radians(16))])
 fng=wr+np.array([.045*h*math.cos(math.radians(16)),0,.045*h*math.sin(math.radians(16))])
 un=np.array([-.259,0,.966]);nn=np.array([.966,0,.259])
 hd=S+.11*h*un+.023*h*nn
 knee=H+np.array([.245*h*math.cos(math.radians(5)),0,.245*h*math.sin(math.radians(5))])
 ankle=knee+np.array([.245*h*math.cos(math.radians(8)),0,-.245*h*math.sin(math.radians(8))])
 return {'hip':H,'shoulder':S,'elbow':E,'wrist':wr,'fingers':fng,'head':hd,'u':u,'n':n,'knee':knee,'ankle':ankle,'height_mm':h,'back_deg':back}

# Filler chambers have closed independent envelopes; no claim of a calibrated DEM.
back_profiles={
 'work':([365,440,555,685,820,980,1070],[115,425,615,610,420,180,135]),
 'relax':([270,365,490,660,835,1000,1100],[95,280,400,430,335,160,125])}
for posture in ['work','relax']:
 xpoints,ztop=back_profiles[posture];zfun=Pchip(xpoints,ztop)
 bounds=[xpoints[0],660 if posture=='work' else 630,865,1070 if posture=='work' else 1100]
 states=('work','folded','empty','cutaway','small','entry') if posture=='work' else ('relax',)
 for i,(a,b) in enumerate(zip(bounds[:-1],bounds[1:]),1):
  rings=[]
  for x in np.linspace(a,b,9):
   top=float(zfun(x));bottom=55;z=(top+bottom)/2;r=(top-bottom)/2
   w=305 if i==1 else 322
   th=np.linspace(0,2*np.pi,40,endpoint=False)
   # rounded ellipsoidal cross-section, chambers touch at partition planes.
   rings.append(np.c_[np.full(len(th),x),w*np.sin(th),z+r*np.cos(th)])
  sh=cq.Solid.makeLoft([wire(rr) for rr in rings],True)
  add(f'B{i:02d}_{posture.upper()}_GRANULAR',sh,'fill1' if i%2 else 'fill2','forming_fill',states,desc='Separate granular forming chamber; nominal envelope, uncalibrated response.')
  if i<3:
   top=float(zfun(b));rad=(top-55)/2;z=(top+55)/2
   add(f'BAFFLE_{posture}_{i}',cq.Face.makeFromWires(wire([[b,322*math.sin(t),z+rad*math.cos(t)] for t in np.linspace(0,2*np.pi,40,endpoint=False)])),'webbing','baffle',states)
 # continuous compliant contact bag along spine, not a rigid backboard.
 p=person(back=55 if posture=='work' else 35);u=p['u'];n=p['n'];H=p['hip'];S=p['shoulder']
 pts=[];rings=[]
 for t in np.linspace(-.04,1.05,14):
  tt=np.clip((t+.04)/1.09,0,1);point=H+t*(S-H)-n*(112+42)+n*10*math.sin(np.pi*tt)
  width=282*(.56+.44*math.sin(np.pi*tt)**.25)
  thick=38*(.30+.70*math.sin(np.pi*tt)**.35)
  th=np.linspace(0,2*np.pi,40,endpoint=False)
  rings.append(np.array([point+[0,width*math.sin(v),0]+n*thick*math.cos(v) for v in th]))
 add('B04_CONTACT_'+posture.upper(),loft(rings),'contact','contact_fill',states,desc='Free granular contact pillow above forming chambers; no anatomical certification.')
 # Broad internal webbing on both sides of body; never wraps the user.
 for sy in [-1,1]:
  A=S-p['n']*160+np.array([0,sy*329,-85]);C=np.array([1110,sy*347,80]);M=(A+C)/2+np.array([-65,0,-20 if posture=='work' else -70])
  pp=np.array([A,M,C]);shift=np.array([0,sy*22,0])
  g=np.stack([pp-shift,pp+shift],axis=1)
  sf=cq.Face.makeSplineApprox([[cq.Vector(*q) for q in row] for row in g],tol=.01,minDeg=1,maxDeg=2)
  o=add(f'B_TIE_{sy}_{posture}',sf,'webbing','straps',states,desc='40 mm internal shape-control strap. Not a body restraint. Geometry only.');o['polyline_mm']=pp.tolist();o['width_mm']=44
  add(f'B_ADJUSTER_{sy}_{posture}',boxshape(tuple(C+[0,0,35]),(65,60,22),5),'hardware','straps',states)
# Dedicated pelvis chamber and shallow anti-slide ramp, both soft.
add('P01_PELVIS_CHAMBER',boxshape((1110,0,110),(460,625,157),56),'contact','pelvis',desc='Separated pelvis filling cannot migrate freely into foot end.')
add('P02_THIGH_TRANSITION',ellipse_solid((1390,0,148),(215,295,62)),'contact','pelvis',desc='Soft shallow transition under thighs; no hard crossbar at knee.')
# Lower legs fully soft, shallow envelope.
add('L01_CALF_CONTACT',ellipse_solid((1795,0,94),(440,295,55)),'lining','leg_support')

# 4. Height adjustment references. Discrete stations are a model parameter, not a proven anthropometric range.
foot_settings=[]
for h,st in [(1600,1980),(1800,2090),(2000,2200)]:
 p=person(h);toe=p['ankle'][0]+.025*h+.0575*h
 foot_settings.append({'scenario_height_mm':h,'heel_point_mm':p['ankle'].tolist(),'toe_reference_x_mm':float(toe),'stop_front_x_mm':st,'table_delta_z_mm':float(p['wrist'][2]-person()['wrist'][2]),'table_delta_x_mm':float(p['wrist'][0]-person()['wrist'][0]),'population_fit':'Not verified; nominal proportional manikins only'})
for h,front in [(1600,1980),(1800,2090),(2000,2200)]:
 st=('small',) if h==1600 else (('adjust',) if h==1800 else ('work','folded','empty','cutaway','entry'))
 # Sloping front face in a soft, rounded bolster.
 rings=[]
 for x in np.linspace(front,front+100,8):
  a=(x-front)/100;w=min(213,float(W(x))-75);zz=182;rz=100*(1-.22*a);th=np.linspace(0,2*np.pi,40,endpoint=False)
  rings.append(np.c_[np.full(len(th),x),w*np.sin(th),zz+rz*np.cos(th)])
 sh=loft(rings)
 add(f'F01_FOOTSTOP_{h}',sh,'lining','footstop',st,desc=f'Movable soft stop; reference height {h} mm is illustrative, not certified fit.')
 for sy in [-1,1]:
  a=np.array([1420.,sy*235,64.]);b=np.array([front+60,sy*200,74.]);w=np.array([0,20,0])
  face=cq.Face.makeFromWires(cq.Wire.makePolygon([cq.Vector(*(a-w)),cq.Vector(*(b-w)),cq.Vector(*(b+w)),cq.Vector(*(a+w))],close=True))
  add(f'F_TIE_{h}_{sy}',face,'webbing','foot_straps',st,desc='Tension load transferred to reinforced internal floor, not to exterior cosmetic fabric.')
for i,x in enumerate([1980,2035,2090,2145,2200]):
 for sy in [-1,1]:add(f'F_ANCHOR_{i}_{sy}',boxshape((x,sy*252,63),(32,48,8),3),'webbing','foot_anchors')

# 5. Puffy integrated sleeping-bag covers, not planes. Actual upper and lower surfaces.
# Upper cross-section and exact inward normal on ellipse; differential layer lengths recorded.
qxs=np.array([620,700,810,950,1080,1315.]);qcent=np.array([904,897,810,712,622,658.]);qwid=np.array([475,505,522,527,535,512.]);qedge=np.array([817,742,644,548,490,413.])
QH=Pchip(qxs,qcent);QW=Pchip(qxs,qwid);QE=Pchip(qxs,qedge)

def cover_ring(x,width,edge,crown,thick):
 th=np.linspace(-np.pi/2,np.pi/2,35)
 h=crown-edge
 y=width*np.sin(th);z=edge+h*np.cos(th)
 normal=np.c_[h*np.sin(th),width*np.cos(th)];normal/=np.linalg.norm(normal,axis=1)[:,None]
 off=thick*(.04+.96*np.cos(th))
 outer=np.c_[np.full(len(th),x),y,z]
 inner=np.c_[np.full(len(th),x),y-off*normal[:,0],z-off*normal[:,1]]
 # 0.5 mm end offsets removed by short interpolated edge caps.
 ring=np.vstack([outer,inner[::-1]])
 return ring,outer,inner

neck_cut=cq.Workplane('XY').center(625,0).ellipse(195,178).extrude(1400).val()
cover_sections=[]

def quilt_piece(id,xa,xb,func,states,group='upper',notch=False):
 rings=[];go=[];gi=[]
 for j,x in enumerate(np.linspace(xa,xb,11)):
  u=(x-xa)/(xb-xa);w,e,h=func(x);puff=12*math.sin(np.pi*u)**.7
  thick=18+30*math.sin(np.pi*u)**.7
  rr,ou,inn=cover_ring(x,w,e,h+puff,thick);rings.append(rr);go.append(ou);gi.append(inn)
 wires=[]
 for ou,inn in zip(go,gi):
  e1=cq.Edge.makeSpline([cq.Vector(*p) for p in ou])
  e2=cq.Edge.makeLine(cq.Vector(*ou[-1]),cq.Vector(*inn[-1]))
  e3=cq.Edge.makeSpline([cq.Vector(*p) for p in inn[::-1]])
  e4=cq.Edge.makeLine(cq.Vector(*inn[0]),cq.Vector(*ou[0]))
  wires.append(cq.Wire.assembleEdges([e1,e2,e3,e4]))
 shape=cq.Solid.makeLoft(wires,False)
 if notch:shape=shape.cut(neck_cut)
 o=add(id,shape,'cloth',group,states,desc='Padded sewn volume with distinct outer and inner skins, nominal 18–48 mm. Same exterior material as lower cocoon.')
 o['outer_grid_mm']=np.array(go).tolist();o['inner_grid_mm']=np.array(gi).tolist()
 PROFILES[id]={'outer_grid_mm':o['outer_grid_mm'],'inner_grid_mm':o['inner_grid_mm'],'sewing_status':'nominal geometry, not flattening/drape validation'}
 # True sewing line at each transverse baffle, excluding head opening points.
 line=go[-1]
 if notch:line=[p for p in line if ((p[0]-625)/195)**2+(p[1]/178)**2>=1]
 if len(line)>2:seam('STITCH_'+id,np.array(line),states,rad=1.35)
 # Finite thickness at sample 50% longitudinal section.
 mid=len(go)//2;outer=np.array(go[mid]);inner=np.array(gi[mid]);Lout=float(np.linalg.norm(np.diff(outer,axis=0),axis=1).sum());Lin=float(np.linalg.norm(np.diff(inner,axis=0),axis=1).sum())
 cover_sections.append({'id':id,'x_mm':float(outer[0,0]),'outer_section_arc_mm':Lout,'inner_section_arc_mm':Lin,'difference_mm':Lout-Lin,'max_geometric_thickness_mm':float(np.linalg.norm(outer-inner,axis=1).max()),'note':'3D sectional arc lengths, not finished 2D pattern lengths'})
 return shape

for i,(a,b) in enumerate([(620,820),(820,952),(952,1080)],1):
 quilt_piece(f'Q0{i}_SHOULDER_BODY',a,b,lambda x:(float(QW(x)),float(QE(x)),float(QH(x))),('work','folded','small'),notch=i==1)
quilt_piece('Q04_KEYBOARD_CLOSED',1080,1315,lambda x:(float(QW(x)),float(QE(x)),float(QH(x))),('work','small'),'keyboard')
# Passive padded flap folded back once towards sitter. Prescribed pose, not fabric dynamics.
quilt_piece('Q04_KEYBOARD_FOLDED',887,1084,lambda x:(588., float(QH(x))+19, float(QH(x))+64),('folded',),'keyboard')
# Lower continuation from around notebook opening to closed foot box.
lx=np.array([1380,1620,1860,2110,2290.]);lh=np.array([461,444,418,405,343.]);le=np.array([376,351,345,335,291.]);lw=np.array([513,480,445,358,200.]);LH=Pchip(lx,lh);LE=Pchip(lx,le);LW=Pchip(lx,lw)
for i,(a,b) in enumerate([(1380,1640),(1640,1870),(1870,2110),(2110,2290)],5):
 quilt_piece(f'Q{i:02d}_LEG_CONTINUATION',a,b,lambda x:(float(LW(x)),float(LE(x)),float(LH(x))),('work','folded','small'),'lower_quilt')
# Soft neck edge piping remains open, never a drawstring around a neck.
a=np.linspace(-np.pi/2,np.pi/2,60)
npnt=[]
for tt in a:
 x=625+195*math.cos(tt);y=178*math.sin(tt);xx=np.clip(x,620,1080)
 h=float(QH(xx));e=float(QE(xx));w=float(QW(xx));u=(xx-620)/200
 z=e+(h-e)*math.sqrt(max(0,1-(y/w)**2))+12*max(0,math.sin(np.pi*np.clip(u,0,1)))**.7
 npnt.append([x,y,z+1.5])
npnt=np.array(npnt)
seam('OPEN_NECK_EDGE',npnt,('work','folded','small'),rad=4)
# Right release seam runs along body perimeter; one-piece look in closed state.
for sy in [-1,1]:
 xs=np.linspace(490,2290,110);points=np.array([[x,sy*(float(W(x))-10),float(R(x))+25] for x in xs])
 seam('SIDE_ZIP_RIGHT' if sy==1 else 'LEFT_PERMANENT_JOIN',points,('work','folded','empty','cutaway','small','entry','relax'),rad=3)
# Tiny soft tabs show release route without a closed loop around the body.
for x in [900,1270,1740]:
 add('ZIP_PULL_'+str(x),boxshape((x,float(W(x))-8,float(R(x))+26),(22,12,7),2),'webbing','release_tabs')

# 6. Occupant models; only dimensional proxies, no pressure/comfort inference.
def manikin(prefix,h=2000,back=55,states=('cutaway',)):
 p=person(h,back);H=p['hip'];S=p['shoulder'];u=p['u'];f=h/2000
 add(prefix+'TORSO',ellipse_solid(tuple((H+S)/2),(112*f,205*f,np.linalg.norm(S-H)/2+45*f),u),'human','human',states)
 add(prefix+'PELVIS',ellipse_solid(tuple(H),(122*f,195*f,105*f)),'human','human',states)
 add(prefix+'NECK',rounded_limb(S+u*30,p['head']-np.array([0,0,100*f]),45*f),'human','human',states)
 add(prefix+'HEAD',ellipse_solid(tuple(p['head']),(90*f,86*f,116*f),(-.259,0,.966)),'human','human',states)
 for sy in [-1,1]:
  sho=S+[0,sy*225*f,0];elb=p['elbow']+[0,sy*245*f,0];wr=p['wrist']+[0,sy*155*f,0];fin=p['fingers']+[0,sy*155*f,0]
  if back!=55:
   elb=H+np.array([-120,sy*245,140]);wr=H+np.array([125,sy*180,135]);fin=wr+[90,0,0]
  for name,A,BB,r in [('ARM',sho,elb,43*f),('FOREARM',elb,wr,34*f)]:add(prefix+name+str(sy),rounded_limb(A,BB,r),'human','human',states)
  add(prefix+'HAND'+str(sy),ellipse_solid(tuple((wr+fin)/2),(20*f,40*f,np.linalg.norm(fin-wr)/2+13),fin-wr),'human','human',states)
  knee=p['knee']+[0,sy*115*f,0];ank=p['ankle']+[0,sy*115*f,0];hip=H+[0,sy*115*f,0]
  add(prefix+'THIGH'+str(sy),rounded_limb(hip,knee,83*f),'human','human',states)
  add(prefix+'SHIN'+str(sy),rounded_limb(knee,ank,59*f),'human','human',states)
  add(prefix+'FOOT'+str(sy),ellipse_solid(tuple(ank+[.025*h,0,0]),(.0575*h,51*f,43*f)),'human','human',states)
 return p
P=manikin('M_',2000,55,('work','folded','cutaway','entry'))
PR=manikin('MR_',2000,35,('relax',))
PS=manikin('MS_',1600,55,('small',))
# Nominal soft elbow pads, detachable, no rigid armrests.
for sy in [-1,1]:
 a=P['elbow']+[0,sy*245,-62];b=P['wrist']+[0,sy*155,-62]
 add('A_SOFT_'+str(sy),ellipse_solid(tuple((a+b)/2),(51,68,np.linalg.norm(b-a)/2+44),b-a),'contact','arm_support',('work','folded','cutaway','empty','entry'))

# Export states as genuine STEP assembly and sampled dataset.
def select(o,state):
 if state=='table':return o['group'] in ['frame','hardware','desk','laptop','table_feet']
 if state=='layers':return o['group'] in ['upper','keyboard','lower_quilt'] and 'work' in o['states']
 if state=='interior':return ('empty' in o['states'] or 'cutaway' in o['states']) and o['group'] not in ['lower_shell','upper','keyboard','lower_quilt','seams','frame_padding','human','pillow']
 if state=='small' and o['group'] in ['upper','keyboard','lower_quilt','seams']:return False
 if state=='empty':return 'empty' in o['states'] and o['group']!='human'
 return state in o['states']

for state in ['work','folded','empty','interior','relax','small','table','layers']:
 ass=cq.Assembly(name='Lezhandr_R06_'+state);ids=[]
 for o in ITEMS:
  if not select(o,state):continue
  sh=SHAPES[o['id']]
  if state in ['work','folded','small'] and o['group']=='human':continue # user shells exported without display mannequin
  if state=='relax' and o['group'] in ['desk','laptop']:sh=sh.translate((80,0,0))
  if state=='small':
   dz=foot_settings[0]['table_delta_z_mm'];dx=foot_settings[0]['table_delta_x_mm']
   if o['group'] in ['desk','laptop']:sh=sh.translate((dx,0,dz))
   elif 'LEFT_COLUMN' in o['id']:
    bid=o['id'].removeprefix('PAD_');bm=next(b for b in BEAMS if b['id']==bid);top=bm['b'][2];scale=(top-bz+dz)/(top-bz)
    sh=sh.transformGeometry(cq.Matrix([[1,0,0,0],[0,1,0,0],[0,0,scale,bz*(1-scale)],[0,0,0,1]]))
   elif 'CANTILEVER' in o['id'] or o['id'].startswith(('D_JOINT','D_ADJUSTER')):sh=sh.translate((0,0,dz))
  ass.add(sh,name=o['id'],color=cq.Color(*PAL[o['kind']]));ids.append(o['id'])
 out=ROOT/'cad'/f'Lezhandr_R06_{state}.step'
 print('EXPORT',state,len(ids),flush=True);ass.save(str(out))
 re=cq.importers.importStep(str(out)).val();dump(ROOT/'tests'/f'STEP_{state}.json',{'part_ids':ids,'valid_after_import':re.isValid(),'solids':len(re.Solids()),'faces':len(re.Faces()),'file_bytes':out.stat().st_size})
# Assembly with occupant and hidden outer for easy inspection.
ass=cq.Assembly(name='Lezhandr_R06_occupied_interior');ids=[]
for o in ITEMS:
 if 'cutaway' not in o['states'] or o['group'] in ['lower_shell','upper','keyboard','lower_quilt','seams','frame_padding','pillow']:continue
 ass.add(SHAPES[o['id']],name=o['id'],color=cq.Color(*PAL[o['kind']]));ids.append(o['id'])
out=ROOT/'cad/Lezhandr_R06_occupied_interior.step';ass.save(str(out));re=cq.importers.importStep(str(out)).val();dump(ROOT/'tests/STEP_occupied_interior.json',{'part_ids':ids,'valid_after_import':re.isValid(),'solids':len(re.Solids()),'faces':len(re.Faces())})

# All dimensional outputs derive from CAD parameters, not guessed captions.
dump(ROOT/'cad/model_R06.json',ITEMS);dump(ROOT/'cad/palette.json',PAL);dump(ROOT/'cad/cover_grids.json',PROFILES)
dump(ROOT/'calculations/cover_sections.json',cover_sections);dump(ROOT/'calculations/foot_settings.json',foot_settings);dump(ROOT/'cad/table_members.json',BEAMS)
dump(ROOT/'calculations/poses.json',{'work':P,'relax':PR,'small':PS})
# Structural screening assumes metal parameters inherited from R05, no certification.
weights=[(b['mass_kg'],(np.array(b['a'])+b['b'])/2) for b in BEAMS]
weights += [(.55,np.array([1245,-420,380])),(1.55,np.array([1235,0,tz(1235)])),(.65,np.array([1200,-350,260]))]
stab=[]
for slide in [0,80]:
 for laptop_mass in [0,2.5]:
  ww=weights+[(laptop_mass,np.array([1220+slide,0,550]))]
  m=sum(k for k,p in ww);cg=sum(k*p for k,p in ww)/m;cg[0]+=1.55*slide/m
  margins=[cg[0]-bx0,bx1-cg[0],cg[1]+by,by-cg[1]]
  stab.append({'laptop_mass_kg':laptop_mass,'table_slide_mm':slide,'mass_kg':m,'cg_mm':cg.tolist(),'nominal_gravity_margins_mm':margins,'minimum_margin_mm':min(margins),'rigid_level_floor_only':True,'handrail':False,'no_filler_or_person_ballast':True})
dump(ROOT/'calculations/table_stability.json',stab)
D=45;BB=25;t=2.5;I=(BB*D**3-(BB-2*t)*(D-2*t)**3)/12;Z=I/(D/2);L=775;E=69000
beam=[{'load_per_cantilever_N':p,'stress_MPa':p*L/Z,'tip_mm':p*L**3/(3*E*I),'scope':'one ideal cantilever, no joint stiffness/torsion/whole-frame check'} for p in [37.5,75]]
dump(ROOT/'calculations/table_beam_screen.json',{'E_MPa_assumption':E,'I_mm4':I,'checks':beam})
changes={'base_revision':'R05','reused_named_STEP_components':source_ids,'removed_R05_groups':['inclined F_BACK_* rails and props','BACK_SLING','65 mm rigid-profile back cassette','single-sheet Q01...Q04 upholstery'],'new':['three granular forming chambers','separate compliant contact bag','two internal adjustable textile ties','separate pelvis chamber','movable soft foot block and floor anchors','finite-thickness sleeping-bag upper and lower skins','local desk-only C frame'],'hand_heater':False,'electronics_and_firmware_modified':False,'granular_simulation_performed':False,'fabric_simulation_performed':False,'postures':'prescribed 55 and 35 degrees; not calibrated/fixed angle','outer_shell_DXF_production_release':False}
dump(ROOT/'project.json',{'revision':'R06','units':'mm','axes':{'X':'head to feet','Y+':'occupant right','Z':'up'},'tube_x_span_mm':[bx0,bx1],'stop_adjust_range_mm':[1980,2200],'quilt_thickness_mm':[18,48],'design_status':'Nominal soft-goods CAD; no validation by manufacture','changes':changes})
dump(ROOT/'tests/build_summary.json',{'items':len(ITEMS),'all_created_valid':all(s.isValid() for s in SHAPES.values()),'reused_count':len(source_ids),'R05_input_sha256':hashlib.sha256((ROOT/'history/R05/Lezhandr_R05_rolled.step').read_bytes()).hexdigest()})
print('DONE',len(ITEMS),flush=True)
