#!/usr/bin/env python3
"""Lezhandr R05. SI mechanics, millimetre CAD. Based on genuine R04 data.
Nominal upholstery + rigid-body kinematics; NOT a contact/physiology/cloth solver.
Run: python source/build_r05.py. Rebuilds geometry, patterns, numerical studies.
"""
from pathlib import Path
import math,json,csv,hashlib,sys
import numpy as np
import cadquery as cq
from scipy.interpolate import PchipInterpolator
ROOT=Path(__file__).resolve().parents[1]
for d in ['cad','calculations','patterns','tests']:(ROOT/d).mkdir(exist_ok=True)
ITEMS=[];SHAPES={};PATTERNS=[];BEAMS=[]
PAL={'outer':(.62,.58,.52),'lining':(.16,.31,.37),'cushion':(.30,.46,.50),'floor':(.18,.20,.21),'tray':(.61,.46,.30),'device':(.13,.15,.17),'screen':(.18,.36,.47),'frame':(.90,.47,.12),'padding':(.80,.72,.52),'human':(.68,.76,.78),'trim':(.10,.21,.26),'cape':(.30,.46,.50),'flap':(.52,.64,.66),'cavity':(.10,.61,.78)}
def dump(p,a):p.write_text(json.dumps(a,ensure_ascii=False,indent=2,default=lambda o:o.item() if isinstance(o,np.generic) else o.tolist()))
def add(id,shape,kind,modes=('closed','rolled','interior','exit','sleep'),group='',desc='',mass=None,uv=None):
    if not shape.isValid():raise RuntimeError('Invalid '+id)
    vv,ff=shape.tessellate(1.5,.12)
    o={'id':id,'kind':kind,'group':group or kind,'modes':list(modes),'description':desc,'vertices_mm':[q.toTuple() for q in vv],'faces':ff}
    if mass is not None:o['mass_kg']=mass
    if uv is not None:o['uv']=uv
    ITEMS.append(o);SHAPES[id]=shape;return o

def face(id,g,kind,modes=('closed','rolled','interior','exit','sleep'),group='',desc=''):
    a=np.array(g);sh=cq.Face.makeSplineApprox([[cq.Vector(*p) for p in row] for row in a],tol=.015,minDeg=1,maxDeg=3)
    o=add(id,sh,kind,modes,group,desc);o['grid_mm']=a.tolist();return o

def box(id,c,dim,kind,modes=('closed','rolled','interior','exit','sleep'),group='',fillet=0,rot=0,desc=''):
    w=cq.Workplane('XY').box(*dim)
    if fillet:w=w.edges().fillet(fillet)
    sh=w.val().rotate((0,0,0),(0,1,0),-rot).translate(c)
    return add(id,sh,kind,modes,group,desc)

def ellipsoid(id,c,r,kind='human',modes=('closed','rolled','interior'),direction=None):
    sh=cq.Solid.makeSphere(1,angleDegrees1=-90,angleDegrees2=90)
    mat=cq.Matrix([[r[0],0,0,0],[0,r[1],0,0],[0,0,r[2],0],[0,0,0,1]])
    sh=sh.transformGeometry(mat)
    if direction is not None:
        d=np.array(direction);d=d/np.linalg.norm(d);ax=np.cross([0,0,1],d);ang=math.degrees(math.acos(np.clip(d[2],-1,1)))
        if np.linalg.norm(ax)>1e-9:sh=sh.rotate((0,0,0),tuple(ax),ang)
    return add(id,sh.translate(c),kind,modes,'manikin' if kind=='human' else kind)

def cylinder(a,b,r):
    a=np.array(a);b=np.array(b);v=b-a;return cq.Solid.makeCylinder(r,float(np.linalg.norm(v)),cq.Vector(*a),cq.Vector(*v))

def limb(id,a,b,r,kind='human',modes=('closed','rolled','interior')):
    sh=cylinder(a,b,r)
    for p in [a,b]:sh=sh.fuse(cq.Solid.makeSphere(r,cq.Vector(*p),angleDegrees1=-90,angleDegrees2=90))
    return add(id,sh,kind,modes,'manikin')

# Actual R04 outer/inner sewing surfaces. Do not replace these with image geometry.
old=json.loads((ROOT/'history/R04/surfaces_R04.json').read_text())
for p in old:
    if p['id'][0] not in 'OL':continue
    g=np.array(p['grid_mm']);oo=face('R04_'+p['id'],g,'outer' if p['id'][0]=='O' else 'lining',group='outer_shell',desc='R04 surface retained. O03/O04/L03/L04 form removable right access panel. Outer flattening remains draft.')
    if p['id'] in ['O03','O04','L03','L04']:
        oo['modes'].remove('exit');oo['access_gate']=True
# Ground textile and compliant floor insulation retained in dimensions.
for id,h,z,kind in [('FLOOR_TEXTILE',1,0,'floor'),('FLEXIBLE_FLOOR_PAD',25,1,'padding')]:
    sh=cq.Workplane('XY').ellipse(1180,545).extrude(h).translate((1180,0,z)).val();add(id,sh,kind,group='floor_soft')

# Anthropometric design scenarios: geometric dimensions, NOT population percentiles.
BACK=55.;THIGH=5.;ARM=-60.;FORE=16.;NECK=75.
def person(h=2000,side_shift=0,exit_pose=False):
    u=np.array([-math.cos(math.radians(BACK)),0,math.sin(math.radians(BACK))]);n=np.array([u[2],0,-u[0]])
    H=np.array([1050.,side_shift,205.]);S=H+(.30*h)*u
    E=S+np.array([.165*h*math.cos(math.radians(ARM)),0,.165*h*math.sin(math.radians(ARM))])
    dy=.045*h;fl=.1425*h;forward=math.sqrt(fl**2-dy**2)
    W=E+np.array([forward*math.cos(math.radians(FORE)),0,forward*math.sin(math.radians(FORE))])
    F=W+np.array([.045*h*math.cos(math.radians(FORE)),0,.045*h*math.sin(math.radians(FORE))])
    un=np.array([-math.cos(math.radians(NECK)),0,math.sin(math.radians(NECK))]);nn=np.array([un[2],0,-un[0]])
    head=S+.11*h*un+.023*h*nn;eye=S+.12*h*un+.071*h*nn
    K=H+np.array([.245*h*math.cos(math.radians(THIGH)),0,.245*h*math.sin(math.radians(THIGH))])
    A=K+np.array([.245*h*math.cos(math.radians(8)),0,-.245*h*math.sin(math.radians(8))])
    return {'hip':H,'shoulder_center':S,'elbow_center':E,'wrist_center':W,'fingers_center':F,'head':head,'eyes':eye,'knee_center':K,'ankle_center':A,'torso_axis':u,'anterior':n,'h':h}
EXIT_SLIDE=80.0
P=person();W=P['wrist_center'];KBC=np.array([W[0]+35,0,W[2]+35*math.tan(math.radians(FORE))])
TILT=FORE
# keyboard plane is aligned with forearms, 36 mm over tabletop (feet, base, keys).
def kz(x):return float(W[2]+(x-W[0])*math.tan(math.radians(TILT)))
def tz(x):return kz(x)-36.
T0=1030.;T1=1440.;TW=680.;TC=(T0+T1)/2
# Back, pelvis and leg-support surfaces are explicit; occupant void lies above them.
u=P['torso_axis'];n=P['anterior'];H=P['hip'];S=P['shoulder_center']
backtop=S-n*115;backbottom=H-n*115
# Remove the top 85 mm along axis to leave neck/head support fully soft.
bak_a=backtop-u*25;bak_b=backbottom+u*5
xx=np.linspace(0,1,35);yy=np.linspace(-300,300,19)
g=np.array([[bak_a*(1-t)+bak_b*t+np.array([0,y,0]) for y in yy] for t in xx])
face('B01_BACK_LINER',g,'cushion',group='support')
# Foam beneath spine, exact constant-thickness prism of this profile.
poly=[tuple(bak_a[[0,2]]),tuple(bak_b[[0,2]]),tuple((bak_b-n*65)[[0,2]]),tuple((bak_a-n*65)[[0,2]])]
sh=cq.Workplane('XZ').polyline(poly).close().extrude(300,both=True).val();add('BACK_FOAM_65',sh,'padding',group='support_foam')
box('PELVIS_PAD',(1100,0,83),(430,650,114),'cushion',group='support',fillet=35)
# knee and calf support keep a shallow knee bend, not suspended feet.
prof=np.array([[1315,133],[1510,157],[1675,150],[2090,63],[2240,60]],float)
xg=np.linspace(1315,2240,70);zg=PchipInterpolator(prof[:,0],prof[:,1])(xg)
face('B03_LEG_LINER',[[[x,y,z] for y in np.linspace(-300,300,19)] for x,z in zip(xg,zg)],'cushion',group='support')
leg_poly=prof.tolist()+[[2240,26],[1315,26]]
sh=cq.Workplane('XZ').polyline(leg_poly).close().extrude(300,both=True).val();add('LEG_FOAM_NOMINAL',sh,'padding',group='support_foam',desc='Nominal shaped filler volume, no compression constitutive law.')
# Pillow remains soft and deliberately independent of rigid back cradle.
ellipsoid('SOFT_HEAD_PILLOW',tuple(P['head']-P['anterior']*135),(155,250,75),'cushion',modes=('closed','rolled','interior','exit'),direction=u)
# Rounded removable arm cradles UNDER forearms. No encircling cuffs.
for sy in [-1,1]:
    a=P['elbow_center']+np.array([0,sy*245,-55]);b=P['wrist_center']+np.array([0,sy*155,-55]);mid=(a+b)/2
    ellipsoid('ARM_PAD_'+str(sy),tuple(mid),(52,70,np.linalg.norm(b-a)/2+65),'cushion',modes=('closed','rolled','interior'),direction=b-a)

# C support: two C ribs on user's LEFT (-Y), open on RIGHT (+Y).
# No full head-to-foot frame; all tubes confined to central trunk region.
def tube(id,a,b,depth=45,width=25,t=2.5,group='frame'):
    a=np.array(a,float);b=np.array(b,float);v=b-a;L=float(np.linalg.norm(v));d=v/L
    # Strong axis in vertical plane for horizontal rails.
    xd=np.array([1.,0,0]) if abs(d[1])>.8 or abs(d[2])>.95 else np.array([0.,1,0])
    xd=xd-d*np.dot(xd,d);xd/=np.linalg.norm(xd)
    pl=cq.Plane(origin=tuple(a),xDir=tuple(xd),normal=tuple(d))
    sh=cq.Workplane(pl).rect(width,depth).rect(width-2*t,depth-2*t).extrude(L).val()
    area=width*depth-(width-2*t)*(depth-2*t);mass=area*L*2.7e-6
    o=add(id,sh,'frame',group=group,mass=mass);o['axis_mm']=[a.tolist(),b.tolist()];o['section_mm']=[depth,width,t]
    BEAMS.append({'id':id,'a_mm':a.tolist(),'b_mm':b.tolist(),'length_mm':L,'depth_mm':depth,'width_mm':width,'wall_mm':t,'mass_kg':mass})
    return o
bx0=610.;bx1=1450.;by=445.;bz=40.
for sy in [-1,1]:tube('F_BASE_LONG_'+str(sy),(bx0,sy*by,bz),(bx1,sy*by,bz),35,20,2)
for x in [bx0,bx1,1110]:tube('F_BASE_CROSS_'+str(x),(x,-by,bz),(x,by,bz),35,20,2)
for i,x in enumerate([1110.,1380.]):
    top=tz(x)-12-22.5
    tube('C'+str(i+1)+'_UPRIGHT',(x,-by,bz),(x,-by,top))
    tube('C'+str(i+1)+'_UPPER',(x,-by,top),(x,330,top))
    # conceptual joint gussets shown; fasteners and holes require detailed design.
    box('JOINT_BLOCK_'+str(i),(x,-by,top-40),(60,60,90),'frame',group='joints')
# inclined back cradle attached to local base; padded sling bridges rails.
ra=(bak_a-n*75);rb=(bak_b-n*75)
# keep geometry to the central region; rounded padding covers both ends.
for sy in [-1,1]:
    a=ra+np.array([0,sy*315,0]);b=rb+np.array([0,sy*315,0])
    tube('F_BACK_RAIL_'+str(sy),a,b)
    tube('F_BACK_PROP_'+str(sy),(a[0],a[1],bz),a)
    tube('F_BACK_BASE_LINK_'+str(sy),(a[0],a[1],bz),(bx0,sy*by,bz),35,20,2)
    tube('F_BACK_LOWER_STUB_'+str(sy),b,(b[0],sy*315,bz),35,20,2)
    tube('F_BACK_LOWER_LINK_'+str(sy),(b[0],sy*315,bz),(1110,sy*315,bz),35,20,2)
tube('F_BACK_CROSS',ra+np.array([0,-315,0]),ra+np.array([0,315,0]))
# Flexible, tensioned sling: no transverse hard bar behind the spine.
face('BACK_SLING',g-n*72,'lining',group='sling')
# Local padded socket volumes show 30 mm radial / 65 mm back upholstery allowance.
for b in BEAMS:
    if 'BASE' in b['id']:continue
    a=np.array(b['a_mm']);bb=np.array(b['b_mm']);r=52 if b['depth_mm']<=35 else 56
    sh=cylinder(a,bb,r)
    if '_UPPER' in b['id']:
        lim=tz(a[0])-12
        sh=sh.intersect(cq.Workplane('XY').box(5000,5000,2000).translate((1000,0,lim-1000)).val())
    add('PAD_'+b['id'],sh,'padding',group='frame_padding',desc='Nominal 30 mm minimum corner padding (trimmed below tray contact); compression not solved.')
# Vented laptop shelf. R04 tray concept rebuilt at the kinematically computed inclination.
plate=cq.Workplane('XY').box(T1-T0,TW,12).edges('|Z').fillet(22)
# U-shaped abdomen clearance, not a full-depth solid desk edge.
plate=plate.cut(cq.Workplane('XY').center(1000-TC,0).ellipse(135,230).extrude(40,both=True))
for x in [-135,-45,45,135]:
    for y in [-190,-95,0,95,190]:
        cutter=cq.Workplane('XY').center(x,y).slot2D(65,18).extrude(30,both=True)
        plate=plate.cut(cutter)
sh=plate.val().rotate((0,0,0),(0,1,0),-TILT).translate((TC,0,tz(TC)-6))
add('TRAY_VENTED',sh,'tray',modes=('closed','rolled','interior','exit'),group='desk',mass=1.55)
# Laptop reference: fixed input geometry. Hinge 20 degrees behind vertical.
LF=1050.;LR=1340.;LH=270.;HA=20.
box('LAPTOP_BASE',((LF+LR)/2,0,kz((LF+LR)/2)-10),(290,390,18),'device',modes=('closed','rolled','interior','exit'),group='laptop',rot=TILT)
for x in [1130,1310]:
    for y in [-177,177]:box(f'RUBBER_RISER_{x}_{y}',(x,y,tz(x)+8),(24,18,16),'device',modes=('closed','rolled','interior','exit'),group='laptop',rot=TILT)
hinge=np.array([LR,0,kz(LR)-5]);dirscr=np.array([math.sin(math.radians(HA)),0,math.cos(math.radians(HA))])
sc=hinge+LH/2*dirscr
box('LAPTOP_SCREEN',tuple(sc),(8,390,LH),'screen',modes=('closed','rolled','interior','exit'),group='laptop',rot=-HA)
for row in range(5):
    for col in range(14):
        x=1150+row*21;y=-171+col*26.2
        box(f'KEY_{row}_{col}',(x,y,kz(x)+.8),(17,23,1.6),'device',modes=('closed','rolled','interior','exit'),group='key')
# Body model with separate limbs, no opaque shell posing as an inner space.
def manikin(prefix='',shift=0,exit_pose=False,modes=('closed','rolled','interior')):
    p=person(side_shift=shift);h=p['h'];hip=p['hip'];s=p['shoulder_center'];u=p['torso_axis']
    ellipsoid(prefix+'TORSO',tuple((hip+s)/2),(112,205,np.linalg.norm(s-hip)/2+50),modes=modes,direction=u)
    ellipsoid(prefix+'PELVIS',tuple(hip),(125,210,110),modes=modes)
    ellipsoid(prefix+'HEAD',tuple(p['head']),(92,90,125),modes=modes,direction=np.array([-.259,0,.966]))
    for sy in [-1,1]:
        shoulder=s+np.array([0,sy*225,0]);elbow=p['elbow_center']+np.array([0,sy*245,0]);wrist=p['wrist_center']+np.array([0,sy*155,0]);finger=p['fingers_center']+np.array([0,sy*155,0])
        if exit_pose:
            wrist=np.array([955.,shift+sy*145,405.]);finger=wrist+np.array([55,0,-12])
        limb(prefix+'UPPER_ARM_'+str(sy),shoulder,elbow,44,modes=modes)
        limb(prefix+'FOREARM_'+str(sy),elbow,wrist,36,modes=modes)
        ellipsoid(prefix+'HAND_'+str(sy),tuple((wrist+finger)/2),(22,44,np.linalg.norm(finger-wrist)/2+18),modes=modes,direction=finger-wrist)
        hipleg=hip+np.array([0,sy*120,0]);kn=p['knee_center']+np.array([0,sy*120,0]);ank=p['ankle_center']+np.array([0,sy*120,0])
        limb(prefix+'THIGH_'+str(sy),hipleg,kn,90,modes=modes)
        limb(prefix+'SHIN_'+str(sy),kn,ank,64,modes=modes)
        ellipsoid(prefix+'FOOT_'+str(sy),tuple(ank+[70,0,0]),(135,56,46),modes=modes)
    return p
manikin()
manikin('EXIT_',shift=800,exit_pose=True,modes=('exit',))

# Exact developable sewing mid-surfaces: generalized cylinders.
# Each panel is derived from 3D curve c(s) extruded along fixed direction d.
# 2D coordinates = accumulated perpendicular chord length, projection along d.
def develop_panel(id,c,d,vmin,vmax,kind,modes,desc='',layer='outer',allow=12):
    c=np.array(c,float);d=np.array(d,float);d/=np.linalg.norm(d)
    eta=(c-c[0])@d;dc=np.diff(c,axis=0);de=np.diff(eta);du=np.sqrt(np.maximum(0,np.sum(dc*dc,axis=1)-de*de));uu=np.r_[0,np.cumsum(du)]
    v0=np.broadcast_to(np.asarray(vmin,float),(len(c),));v1=np.broadcast_to(np.asarray(vmax,float),(len(c),));vv=v0[:,None]+np.linspace(0,1,11)[None,:]*(v1-v0)[:,None];g=c[:,None,:]+vv[:,:,None]*d
    face(id,g,kind,modes,group='quilt' if id.startswith('Q') else 'pattern_geometry',desc=desc)
    # sewing boundary: start vmin -> end vmin -> end vmax -> start vmax
    poly=np.concatenate([np.c_[uu,eta+v0],np.c_[uu[::-1],(eta+v1)[::-1]]])
    uv=np.stack([np.broadcast_to(uu[:,None],vv.shape),eta[:,None]+vv],axis=-1)
    edge_err=[]
    for di,dj in [(1,0),(0,1),(1,1)]:
        a=g[:len(c)-di,:vv.shape[1]-dj];b=g[di:,dj:];aa=uv[:len(c)-di,:vv.shape[1]-dj];bb=uv[di:,dj:]
        l3=np.linalg.norm(b-a,axis=-1);l2=np.linalg.norm(bb-aa,axis=-1);edge_err.extend((abs(l3-l2)/np.maximum(l3,1e-8)).ravel())
    PATTERNS.append({'id':id,'seam_polygon_mm':poly.tolist(),'grid_3d_mm':g.tolist(),'grid_2d_mm':uv.tolist(),'allowance_mm':allow,'layer':layer,'quantity':1,'max_relative_edge_error':float(max(edge_err)),'note':desc,'type':'developable extrusion of the sampled 3D centreline','centerline_length_mm':float(np.linalg.norm(dc,axis=1).sum()),'extrusion_width_mm':float(max(v1-v0))})
    return g
# Three-part shoulder roof with a real U-shaped neck opening, 310 x 145 mm.
# No material covers the face/throat. Wings start behind the shoulder joint.
c0=np.array([[650,0,855],[720,0,850],[795,0,785],[870,0,710],[955,0,626],[1035,0,577],[1100,0,545]],float)
cx=np.r_[np.linspace(650,795,30,endpoint=False),np.linspace(795,1100,61)];cz=PchipInterpolator(c0[:,0],c0[:,2])(cx);c=np.c_[cx,np.zeros(len(cx)),cz]
qc=[]
qc.append(develop_panel('Q01_CENTRE',c[cx>=795],[0,1,0],-155,155,'cape',('closed','rolled'),'Central chest cover. Front edge of open neck cutout, no neck seal.'))
for sy in [-1,1]:
    lo,hi=(-310,-155) if sy<0 else (155,310)
    qc.append(develop_panel('Q01_WING_'+('L' if sy<0 else 'R'),c,[0,1,0],lo,hi,'cape',('closed','rolled'),'Shoulder wing continuing from behind shoulder to wrist.'))
    cside=c+np.array([0,sy*310,0]);develop_panel('Q02_SIDE_'+('L' if sy<0 else 'R'),cside,[0,sy*110,-280],0,math.hypot(110,280),'cape',('closed','rolled'),'Arm-side wrap, right edge detachable from inside.')
qtop=qc[0]
# Forward flap continues over wrists and keyboard. No arch, hinge hardware or heater.
c2c=np.array([[1100,0,545],[1160,0,568],[1260,0,589],[1310,0,590]],float)
x2=np.linspace(1100,1310,55);z2=PchipInterpolator(c2c[:,0],c2c[:,2])(x2);c2=np.c_[x2,np.zeros(len(x2)),z2]
qflap=develop_panel('Q03_KEYBOARD_FLAP',c2,[0,1,0],-310,310,'flap',('closed',),'Soft detachable-edge keyboard flap; rolls towards sitter, no electrical components.')
flapL=float(np.linalg.norm(np.diff(c2,axis=0),axis=1).sum())
# Isometric rolled arrangement of the same flap length: short return then constant radius roll.
# A kinematic fabric state; NOT a bending/contact simulation.
ss=np.r_[0,np.cumsum(np.linalg.norm(np.diff(c2,axis=0),axis=1))];roll=[]
lead=60.;r=22.;center=np.array([1040.,0,545.+r])
for s in ss:
    if s<=lead:roll.append([1100-s,0,545.])
    else:
        a=-math.pi/2-(s-lead)/r
        roll.append([center[0]+r*math.cos(a),0,center[2]+r*math.sin(a)])
rg=np.array(roll)[:,None,:]+np.linspace(-310,310,11)[None,:,None]*np.array([0,1,0])
face('Q03_FLAP_ROLLED',rg,'flap',('rolled',),group='quilt',desc='Same material length, prescribed roll towards sitter. No dynamics.')
# Closed lower quilt from laptop toward toes, unheated reference drape.
cc=np.array([[1450,0,380],[1580,0,380],[1900,0,290],[2240,0,270]],float)
xf=np.linspace(1450,2240,65);zf=PchipInterpolator(cc[:,0],cc[:,2])(xf)
develop_panel('Q04_LOWER_QUILT',np.c_[xf,np.zeros(len(xf)),zf],[0,1,0],-np.linspace(320,150,len(xf)),np.linspace(320,150,len(xf)),'cape',('closed','rolled'),'Nominal leg blanket; does not contain rigid rails.')
# Inner lining patterns matching the visible support surfaces, not the old outer gores.
develop_panel('P01_BACK_TOP',np.array([bak_a*(1-t)+bak_b*t for t in xx]),[0,1,0],-300,300,'cushion',(),desc='Top of 65 mm back-foam cassette',layer='lining')
develop_panel('P02_PELVIS_TOP',np.array([[x,0,140.] for x in np.linspace(885,1315,20)]),[0,1,0],-325,325,'cushion',(),desc='Nominal pelvis-pad top prior to corner tailoring',layer='lining')
develop_panel('P03_LEG_TOP',np.c_[xg,np.zeros(len(xg)),zg],[0,1,0],-300,300,'cushion',(),desc='Leg-support top in work pose',layer='lining')
# Sleep: no head-to-foot rigid conversion claimed. Local module withdrawn without cloth heating.
box('SLEEP_SOFT_MAT',(1180,0,100),(2150,630,145),'cushion',modes=('sleep',),group='support',fillet=55)
# Surface-only inner free-space reference: explicitly a space envelope, not foam.
xc=np.linspace(420,2200,70)
zc=np.interp(xc,[420,730,1050,1550,2200],[890,850,600,440,260])
face('SPACE_CROWN_REFERENCE',[[[x,y,z] for y in [-290,0,290]] for x,z in zip(xc,zc)],'cavity',(),group='space_reference',desc='Reference upper interior boundary, not a physical part.')
# Export ordinary model, frame and interior separately. Sleep has removable C module omitted.
def included(o,mode):
    if mode=='frame':return o['group'] in ['frame','joints','desk']
    if mode=='cavity':return o['group'] in ['outer_shell','support','floor_soft','sling','frame','desk'] and 'sleep' not in o['id'].lower()
    if mode=='interior':return mode in o['modes'] and o['group'] not in ['outer_shell','frame_padding']
    if mode=='sleep':return mode in o['modes'] and o['group'] not in ['frame','joints','frame_padding','sling','manikin'] and not o['id'].startswith(('B01','BACK_','PELVIS','B03','LEG_FOAM'))
    return mode in o['modes']
for mode in ['closed','rolled','interior','frame','cavity','exit','sleep']:
    a=cq.Assembly(name='Lezhandr_R05_'+mode);ids=[]
    for o in ITEMS:
        if included(o,mode):
            sh=SHAPES[o['id']]
            if mode=='exit' and o['group'] in ['desk','laptop','key']:sh=sh.translate((EXIT_SLIDE,0,0))
            a.add(sh,name=o['id'],color=cq.Color(*PAL[o['kind']]));ids.append(o['id'])
    print('Export',mode,len(ids),flush=True)
    a.save(str(ROOT/'cad'/f'Lezhandr_R05_{mode}.step'))
    sh=cq.importers.importStep(str(ROOT/'cad'/f'Lezhandr_R05_{mode}.step')).val()
    dump(ROOT/'tests'/f'STEP_{mode}.json',{'part_ids':ids,'valid_after_reimport':sh.isValid(),'solids':len(sh.Solids()),'faces':len(sh.Faces())})
# User can inspect independent, correctly named solids/surfaces in STEP and viewer.
dump(ROOT/'cad/model_R05.json',ITEMS);dump(ROOT/'patterns/panels_R05.json',PATTERNS);dump(ROOT/'cad/beams_R05.json',BEAMS)
dump(ROOT/'project.json',{'revision':'R05','base':'R04 supplied archive','date':'2026-10-01','units':'mm','reference_height_mm':2000,'design_mass_case_kg':120,'axes':{'X':'head to feet','Y':'positive = occupant RIGHT; negative = occupant LEFT','Z':'up from floor'},'working_back_deg_from_floor':BACK,'thigh_deg_from_floor':THIGH,'hand_heater':False,'keyboard_flap':'rolls towards sitter; main shoulder and forearm wrap remains','model_status':'Nominal CAD + analytical/kinematic screening, not physiological or fabric/filler contact proof','materials':{'tube':'6082-T6 candidate, bolted/gusset joints concept; no assumed welded strength','E_MPa_assumed':69000,'rho_kg_m3_assumed':2700,'screening_allowable_MPa_assumed':80},'frame_floor_support_polygon_mm':[[bx0,-by],[bx1,-by],[bx1,by],[bx0,by]],'neck_open':True,'exit_table_slide_mm':EXIT_SLIDE,'slide_mechanism_status':'80 mm kinematic rail travel; joint lock/hold-down hardware not detailed','existing_outer_patterns':'R04 DRAFT, NOT production','pattern_basis':'New developable mid-surface panels. No final shrinkage/drape correction.'})
# Anthropometric numerical outputs shared with CAD dimensions.
ergo=[]
for h in [1600,1800,2000]:
    p=person(h);hsc=h/2000;sc2=sc.copy();sc2[2]+=p['wrist_center'][2]-W[2];sc2[0]+=p['wrist_center'][0]-W[0]
    a=p['shoulder_center']-p['elbow_center'];b=p['wrist_center']-p['elbow_center']+np.array([0,-.045*h,0])
    elbow=math.degrees(math.acos(np.dot(a,b)/np.linalg.norm(a)/np.linalg.norm(b)))
    ray=sc2-p['eyes'];distance=float(np.linalg.norm(ray));worldang=math.degrees(math.atan2(-ray[2],np.linalg.norm(ray[:2])));neutral_gaze_up=90-NECK
    ergo.append({'height_mm':h,'population_percentile':'not asserted','hip_angle_deg':180-BACK-THIGH,'elbow_angle_deg':elbow,'forearm_up_deg':FORE,'keyboard_wrist_plane_z_mm':float(p['wrist_center'][2]),'tabletop_at_wrist_z_mm':float(p['wrist_center'][2]-36),'eye_to_screen_center_mm':distance,'screen_down_from_horizontal_deg':worldang,'screen_down_from_neutral_head_deg':worldang+neutral_gaze_up,'head_forward_rotation_relative_torso_deg':NECK-BACK,'eyes_mm':p['eyes'].tolist(),'wrist_mm':p['wrist_center'].tolist()})
dump(ROOT/'calculations/ergonomics.json',ergo)
dump(ROOT/'calculations/pose_reference.json',{k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in P.items()})
# Finite ray intersections from the actual eye point to actual key surface; flap + wrap.
def ray_hits(origin,targets,gs):
    verts=[];faces=[];n=0
    for g in gs:
        g=np.array(g);nr,nc,_=g.shape;v=g.reshape(-1,3);f=[]
        for i in range(nr-1):
            for j in range(nc-1):
                a=i*nc+j;f.extend([[a,a+nc,a+1],[a+1,a+nc,a+nc+1]])
        verts.extend(v);faces.extend(np.array(f)+n);n+=len(v)
    verts=np.array(verts);faces=np.array(faces);aa=verts[faces[:,0]];e1=verts[faces[:,1]]-aa;e2=verts[faces[:,2]]-aa
    hits=[]
    for t in targets:
        d=t-origin;hh=np.cross(d,e2);det=(e1*hh).sum(1);ok=abs(det)>1e-10;iv=np.zeros_like(det);iv[ok]=1/det[ok];s=origin-aa;u=(s*hh).sum(1)*iv;q=np.cross(s,e1);v=(q*d).sum(1)*iv;tt=(q*e2).sum(1)*iv
        hits.append(bool(np.any(ok&(u>=0)&(v>=0)&(u+v<=1)&(tt>0)&(tt<1))))
    return hits
keys=np.array([[x,y,kz(x)+1.6] for x in np.linspace(1148,1237,10) for y in np.linspace(-175,175,14)])
sidegs=[o['grid_mm'] for o in ITEMS if o['id'] in ['Q02_SIDE_L','Q02_SIDE_R']]
visibility={'tested_keys':len(keys),'reference_height_mm':2000,'closed_blocked':sum(ray_hits(P['eyes'],keys,qc+[qflap]+sidegs)),'rolled_blocked':sum(ray_hits(P['eyes'],keys,qc+[rg]+sidegs)),'scope':'Wrap + flap only; reference eyes, not dynamic gaze or all users','flap_flat_length_mm':flapL,'no_hard_flap_arch':True}
dump(ROOT/'calculations/visibility.json',visibility)
# Static load estimate: torso at 60% body weight, supported on inclined back + pelvis.
loads=[]
for mass in [60,90,120]:
    wt=mass*.60*9.81;nb=wt*math.cos(math.radians(BACK));tb=wt*math.sin(math.radians(BACK));vp=mass*9.81-nb*math.cos(math.radians(BACK));horizontal=nb*math.sin(math.radians(BACK))
    loads.append({'mass_kg':mass,'assumed_torso_fraction':.6,'back_normal_N':nb,'pelvis_and_lower_support_vertical_N':vp,'pelvic_horizontal_resistance_N':horizontal,'back_tangential_transfer_N':tb,'back_mean_pressure_kPa':nb/(.55*.42)/1000,'pelvis_mean_pressure_kPa':vp/(.42*.38)/1000,'scope':'Simplified static partition, no measured pressure map. Some leg load is conservatively assigned to pelvis.'})
dump(ROOT/'calculations/support_loads.json',loads)
# Member screening (not joint certification or whole-frame FEA).
E=69000.;D=45.;B=25.;t=2.5;I=(B*D**3-(B-2*t)*(D-2*t)**3)/12;Z=I/(D/2);L=775.
checks=[]
for total,label in [(75,'centred laptop + accessories, 75 N total'),(150,'centred screening 150 N total'),(300,'equivalent 150 N on ONE upper beam')]:
    p=total/2;moment=p*L;sigma=moment/Z;delta=p*L**3/(3*E*I)
    checks.append({'case':label,'total_N':total,'per_upper_beam_N':p,'section_mm':[D,B,t],'I_mm4':I,'sigma_MPa':sigma,'tip_deflection_mm':delta,'assumed_allowable_MPa':80,'local_member_screen_pass':sigma<80,'not_included':'upright flex, joint rotation, torsion, local buckling, fatigue'})
dump(ROOT/'calculations/beam_screening.json',checks)
# Empty C module stability using own weights only; filler/body/battery NOT ballast.
weights=[(b['mass_kg'],(np.array(b['a_mm'])+b['b_mm'])/2,b['id']) for b in BEAMS]
weights.extend([(.70,np.array([1180,-410,280]),'joint allowance'),(1.55,np.array([TC,0,tz(TC)]),'tray'),(.45,np.array([900,0,330]),'sling and pads allowance')])
stability=[]
for pc in [0,2.5]:
    pts=weights+([(pc,np.array([1220,0,570]),'laptop')] if pc else [])
    m=sum(w for w,p,l in pts);cm=sum(w*p for w,p,l in pts)/m;bounds=[cm[0]-bx0,bx1-cm[0],cm[1]+by,by-cm[1]];hm=600.
    crit=m*9.81*min(bounds)/hm
    stability.append({'laptop_mass_kg':pc,'module_mass_kg':m,'cg_mm':cm.tolist(),'minimum_gravity_margin_mm':min(bounds),'side_margins_mm':bounds,'horizontal_tip_force_N_at_600mm':crit,'sliding_force_N_mu_0_2':m*9.81*.2,'sliding_force_N_mu_0_4':m*9.81*.4,'vertical_gravity_stable_on_rigid_level_floor':min(bounds)>0,'caveat':'Floor-pad contact must be measured; this polygon is nominal, not valid on a soft mattress. Not a handrail.'})
park=[]
for row in stability:
    r=dict(row);r['table_slide_mm']=EXIT_SLIDE
    x=np.array(r['cg_mm']);x[0]+=EXIT_SLIDE*(1.55+r['laptop_mass_kg'])/r['module_mass_kg'];r['cg_mm']=x.tolist()
    bounds=[x[0]-bx0,bx1-x[0],x[1]+by,by-x[1]];r['minimum_gravity_margin_mm']=min(bounds);r['side_margins_mm']=bounds;r['horizontal_tip_force_N_at_600mm']=r['module_mass_kg']*9.81*min(bounds)/600;park.append(r)
dump(ROOT/'calculations/empty_stability_parked.json',park)
dump(ROOT/'calculations/empty_stability.json',stability)
# Lower rigidity bounds and critical assumptions explicit.
dump(ROOT/'calculations/frame_mass.json',{'tube_mass_kg':sum(b['mass_kg'] for b in BEAMS),'joint_allowance_kg':.7,'tube_count':len(BEAMS),'rigid_tube_x_bounds_mm':[min(min(b['a_mm'][0],b['b_mm'][0]) for b in BEAMS),max(max(b['a_mm'][0],b['b_mm'][0]) for b in BEAMS)],'soft_head_region_x_less_mm':550,'soft_foot_region_x_greater_mm':1500,'not_all_furniture_mass':True})

# Clearance screen using actual OpenCASCADE solid distance at discrete lateral poses.
# Tucked arms are used; blanket and right bolster must be opened separately.
rigid_ids=[o['id'] for o in ITEMS if o['group'] in ['frame','joints','desk','laptop'] and not o['id'].startswith('RUBBER')]
groups={o['id']:o['group'] for o in ITEMS}
rigid_shapes=[SHAPES[i].translate((EXIT_SLIDE,0,0)) if groups[i] in ['desk','laptop'] else SHAPES[i] for i in rigid_ids]
body_ids=[o['id'] for o in ITEMS if o['id'].startswith('EXIT_')]
body_shapes=[SHAPES[i] for i in body_ids]
def bounds(sh):
    q=sh.BoundingBox();return np.array([q.xmin,q.ymin,q.zmin]),np.array([q.xmax,q.ymax,q.zmax])
def bb_dist(bb1,bb2):
    return float(np.linalg.norm(np.maximum(0,np.maximum(bb1[0]-bb2[1],bb2[0]-bb1[1]))))
rbb=[bounds(q) for q in rigid_shapes];clear=[]
for shift in np.linspace(0,800,9):
    moved=[q.translate((0,float(shift)-800,0)) for q in body_shapes]
    mbb=[bounds(q) for q in moved]
    pairs=sorted((bb_dist(mbb[i],rbb[j]),i,j) for i in range(len(moved)) for j in range(len(rigid_shapes)))
    best=1e9;pair=None;tested=0
    for bound,i,j in pairs:
        if bound>best+1e-6:break
        dist=moved[i].distance(rigid_shapes[j]);tested+=1
        if dist<best:best=dist;pair=[body_ids[i],rigid_ids[j]]
        if best<1e-7:break
    clear.append({'lateral_shift_mm':float(shift),'surface_distance_mm':float(best),'closest_pair':pair,'exact_pair_evaluations':tested})
    print('Egress clearance',shift,best,pair,flush=True)
dump(ROOT/'calculations/exit_clearance.json',{'table_exit_slide_mm':EXIT_SLIDE,'poses':clear,'minimum_distance_mm':min(x['surface_distance_mm'] for x in clear),'method':'BRepExtrema between true mannequin solids and true rigid solids; 9 static poses','limitations':'Straight lateral swept-clearance screen, NOT a biomechanically solved getting-up trajectory; zero distance can mean touch or overlap. Does not validate unsupported body, folded bolster, or every possible movement. Padding clearances are separate.'})

print('ERGO',ergo,flush=True);print('VIS',visibility,flush=True);print('STABILITY',stability,flush=True)
