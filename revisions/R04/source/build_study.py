#!/usr/bin/env python3
"""R04: a real OpenCASCADE model and a reproducible numerical cloth study.
The inherited source/parameters are stored in history. No image-generation.
Geometry in millimetres; cloth experiment in SI. See docs/LIMITATIONS_RU.md.
"""
from pathlib import Path
import math,json,csv,hashlib,importlib.util,sys,os
import numpy as np
import cadquery as cq
from scipy.optimize import brentq
from cloth_solver import solve,grid_faces
ROOT=Path(__file__).resolve().parents[1]
for d in ['cad','simulation','renders','tests','patterns','exchange']:(ROOT/d).mkdir(exist_ok=True)
def cachedsolve(name,p,nu,nv,pins,area,**kw):
    npz=ROOT/'simulation'/f'{name}_drape.npz'; js=ROOT/'simulation'/f'{name}_metrics.json'
    if npz.exists() and js.exists():
        d=np.load(npz);m=json.loads(js.read_text())
        if d['initial_m'].shape==p.shape and np.allclose(d['initial_m'],p,atol=1e-12) and m['steps']==kw.get('steps',240) and abs(m['area_m2']-area)<1e-10:
            print('Reusing computed, matching simulation:',name,flush=True)
            return d['final_m'],d['triangles'],m,d['track'],d['snapshots']
    print('Computing simulation:',name,flush=True)
    return solve(p,nu,nv,pins,area,**kw)

P=json.loads((ROOT/'history/project_R02.json').read_text())
P['revision']='R04 cloth/hinged-cover study';P['hand_heater']={'installed':False,'power_W':0,'wiring':False}
P['zones']=[z for z in P['zones'] if z['id']!=3]
P['hood']={'type':'passive fabric flip-up canopy','x_limits_mm':[965,1325],'half_width_mm':335,'rise_mm':165,'hinge_z_mm':545,'open_angle_deg':105,'hinge_side':'+Y','electrical_parts':0,'unheated':True}
P['model_status']='Nominal surface model + uncalibrated cloth drape experiment. No CLO/Rhino/Blender run.'
(ROOT/'project.json').write_text(json.dumps(P,indent=2,ensure_ascii=False))
PAL={'outer':(.56,.52,.46),'lining':(.17,.30,.37),'cushion':(.25,.39,.45),'floor':(.23,.24,.24),'tray':(.65,.49,.31),'device':(.12,.14,.17),'screen':(.16,.36,.46),'trim':(.13,.23,.29),'heat':(.89,.37,.16),'foam':(.82,.78,.66),'reference':(.55,.63,.66)}
ITEMS=[];PATCHES=[]

def save_json(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2))
def addmesh(id,v,f,kind,mode='both',desc='',uv=None,technical=False):
    item={'id':id,'vertices_mm':np.asarray(v).round(5).tolist(),'faces':np.asarray(f).tolist(),'kind':kind,'modes':mode,'description':desc,'technical':technical}
    if uv is not None:item['uv']=np.asarray(uv).tolist()
    ITEMS.append(item);return item

def cqmesh(id,shape,kind,mode='both',desc=''):
    vv,ff=shape.tessellate(1.5,.08)
    item=addmesh(id,[p.toTuple() for p in vv],ff,kind,mode,desc);item['brep']=shape
    return item

def surface(id,pts,kind,mode='both',pattern=False,desc=''):
    a=np.asarray(pts);nu,nv,_=a.shape
    sh=cq.Face.makeSplineApprox([[cq.Vector(*p) for p in row] for row in a],tol=.05,minDeg=1,maxDeg=3)
    if not sh.isValid():raise ValueError(id)
    vv,ff=sh.tessellate(1.5,.08)
    item=addmesh(id,[p.toTuple() for p in vv],ff,kind,mode,desc);item['brep']=sh
    if pattern:PATCHES.append({'id':id,'grid_mm':a.tolist(),'material':kind,'seam_allowance_mm':12,'method':'approximate flattening; distortion reported separately'})
    return item

def ring(s,q):
    # A soft annular bolster rising at the head. Plan ellipse, variable cross-section.
    a=1080.; b=435.;c=1180.; head=(1-math.cos(s))/2
    h=155+285*head**4
    r=100+22*math.sin(s)**2
    n=np.array([math.cos(s)/a,math.sin(s)/b]);n/=np.linalg.norm(n)
    center=np.array([c+a*math.cos(s),b*math.sin(s),h])
    p=center+np.array([n[0]*r*math.cos(q),n[1]*r*math.cos(q),h*math.sin(q)])
    return p

for k in range(12):
    for typ,q0,q1,kind in [('O',-math.pi/2,math.pi/2,'outer'),('L',math.pi/2,3*math.pi/2,'lining')]:
        ss=np.linspace(2*math.pi*k/12,2*math.pi*(k+1)/12,11);qq=np.linspace(q0,q1,17)
        pts=[[ring(s,q) for q in qq] for s in ss]
        surface(f'{typ}{k+1:02}',pts,kind,pattern=True,desc='Smooth textile sewing surface over nominal filler, not a rigid frame')
# Floor textile + compliant foam underlay; neither is plywood.
base=cq.Workplane('XY').ellipse(1175,540).extrude(26).translate((1180,0,0)).val()
cqmesh('SOFT_UNDERLAY',base,'foam','both','Flexible 26 mm floor insulation')
floor=cq.Workplane('XY').ellipse(1180,545).extrude(1).translate((1180,0,0)).val()
cqmesh('FLOOR_TEXTILE',floor,'floor')

def mattress(x,y,mode):
    nx=(x-1180)/1100
    side=max(0,1-(y/355)**2)
    crown=22*max(0,1-nx*nx)*side
    if mode=='sleep':rise=0
    else:
        t=np.clip((x-300)/820,0,1);rise=515*(1-t)**2*(1+2*t)
    return [x,y,112+crown+rise]

for mode in ['work','sleep']:
    xx=np.linspace(160,2210,45); vv=np.linspace(-1,1,25)
    pts=[]
    for x in xx:
        width=310*np.sqrt(max(.08,1-((x-1180)/1120)**4))
        pts.append([mattress(x,v*width,mode) for v in vv])
    surface('MATTRESS_'+mode,pts,'cushion',mode,desc='Smoothed support shape; foam deformation not solved')
    # Cervical pillow is an explicit soft envelope, not a load-rated insert.
    sh=cq.Workplane('XY').box(220,390,105).edges().fillet(45).val()
    if mode=='work':sh=sh.rotate((0,0,0),(0,1,0),34).translate((405,0,634))
    else:sh=sh.translate((340,0,177))
    cqmesh('PILLOW_'+mode,sh,'lining',mode)
# Rebuild the inherited actual R01 tray/laptop solid geometry in a valid path layout.
import tempfile,shutil
hist=ROOT/'history/rebuild_R01';(hist/'cad/source').mkdir(parents=True,exist_ok=True)
shutil.copyfile(ROOT/'history/build_cad_R01.py',hist/'cad/source/build_cad.py');shutil.copyfile(ROOT/'history/project_R01.json',hist/'project.json')
spec=importlib.util.spec_from_file_location('r01',hist/'cad/source/build_cad.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
baseparts={p['id']:p for p in old.build('work')}
tray=baseparts['D20']['shape']
for sy in [-330,330]:tray=tray.fuse(old.box(460,60,12,(215,sy,715)))
tray=tray.translate((950,0,-215))
cqmesh('D20_R02_TRAY',tray,'tray','work','Retained ventilated tray from R02, moved as a rigid part')
cqmesh('D21_LAPTOP',baseparts['D21']['shape'].translate((975,0,-215)),'device','work','R01 laptop reference 290 x 390 x 18 mm')
screen=baseparts['D22']['shape'].rotate((390,0,755),(390,1,755),24).translate((975,0,-215))
cqmesh('D22_SCREEN',screen,'screen','work','Screen tilt corrected to lean away from user')
# Keyboard keys and touchpad added as view references, not a different laptop envelope.
for row in range(5):
    for col in range(14):
        key=old.box(16,22,1.6,(1115+row*21,-171+col*26.2,540.6))
        cqmesh(f'KEY_{row:02}_{col:02}',key,'reference','work')
cqmesh('TOUCHPAD',old.box(62,120,1.0,(1065,0,540.2)),'reference','work')
for x in [1070,1345]:
    for y in [-177,177]:cqmesh('FOOT_'+str(x)+'_'+str(y),old.box(24,18,16,(x,y,514)),'device','work','Removable riser; does not block laptop air intakes')
for sy in [-365,365]:
    arm=cq.Workplane('XY').box(450,145,175).edges().fillet(60).translate((1165,sy,406)).val()
    cqmesh('ARM_BAG_'+str(sy),arm,'lining','work','Soft load spreader; shelf stability not tested')
# Electronics remains outside the insulated body; no cable enters the hand canopy.
for id,target in {'E10':(1650,-865,105),'E12':(1300,-855,60),'E11':(1000,-605,245)}.items():
    sh=baseparts[id]['shape'];bb=sh.BoundingBox();c=np.array([(bb.xmin+bb.xmax)/2,(bb.ymin+bb.ymax)/2,(bb.zmin+bb.zmax)/2]);sh=sh.translate(tuple(np.asarray(target)-c))
    item=cqmesh(id+'_EXTERNAL',sh,'device');item['external']=True
# Body heater references: previous three zones, no HZ3 / hand heat. NOT new certified car-seat mats.
for z,x in [(0,635),(1,1590),(2,2030)]:
    pts=[[np.array(mattress(xx,yy,'work'))+np.array([0,0,4]) for yy in np.linspace(-145,145,5)] for xx in np.linspace(x-150,x+150,5)]
    it=surface('EH'+str(z),pts,'heat','work',desc='R02 body heater location only; heater specification not revalidated');it['technical']=True
# Main unheated canopy: 360 mm long half-ellipse, two end ribs and one textile hinge.
nu,nv=25,49
us=np.linspace(965,1325,nu);ts=np.linspace(0,math.pi,nv)
hood=np.array([[x,335*math.cos(t),545+165*math.sin(t)] for x in us for t in ts])/1000
pins=np.asarray([i*nv+j for i in range(nu) for j in range(nv) if i in [0,nu-1] or j in [0,nv-1]],np.int32)
arc=np.sum(np.linalg.norm(np.diff(hood[:nv],axis=0),axis=1));area=.36*arc
out,faces,hm,track,saved=cachedsolve('hood',hood,nu,nv,pins,area,steps=240,iterations=32,slack=1.002,floor=.535)
np.savez_compressed(ROOT/'simulation/hood_drape.npz',initial_m=hood,final_m=out,triangles=faces,pins=pins,track=track,snapshots=saved)
save_json(ROOT/'simulation/hood_metrics.json',hm)
with (ROOT/'simulation/hood_history.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['time_s','max_displacement_m','max_step_motion_m','max_speed_m_s']);w.writerows(track)
# A kinematic opening after the closed drape has settled. Not a cloth opening simulation.
def hood_rotate(a):
    p=out*1000;ang=math.radians(-a);p=p.copy();cy=335;cz=545
    yy=p[:,1]-cy;zz=p[:,2]-cz
    p[:,1]=cy+math.cos(ang)*yy-math.sin(ang)*zz;p[:,2]=cz+math.sin(ang)*yy+math.cos(ang)*zz
    return p
for a in [0,55,105]:
    addmesh('PASSIVE_HOOD_'+str(a),hood_rotate(a),faces,'outer','hood'+str(a),desc='Draped mesh rotated about +Y textile hinge; no heat, no wiring')
# Two rib envelopes are explicitly identified; they shape canopy only, not the body support.
for end,x in enumerate([965,1325]):
    for a in [0,55,105]:
        pv=hood_rotate(a)[end*(nu-1)*nv:(end*(nu-1)+1)*nv]
        # Curves rendered as piping; CAD uses a polygonal open wire.
        w=cq.Wire.makePolygon([cq.Vector(*v) for v in pv],close=False)
        it={'id':f'FLEXIBLE_RIB_{end}_{a}','curve_mm':pv.tolist(),'kind':'trim','modes':'hood'+str(a),'technical':False,'description':'Removable flexible rib envelope, not stiffness calculation','brep':w}
        ITEMS.append(it)
# Two adjustable textile limit tethers hold the 105-degree parked position.
for end,x in enumerate([965,1325]):
    pt=hood_rotate(105)[end*(nu-1)*nv+nv-1]
    route=[[x,280,506],pt.tolist()]
    wire=cq.Wire.makePolygon([cq.Vector(*p) for p in route],close=False)
    ITEMS.append({'id':'LIMIT_TETHER_'+str(end),'curve_mm':route,'kind':'trim','modes':'hood105','technical':False,'brep':wire,
                  'description':'Adjustable textile opening stop; stow loose when closed; strength unverified'})
# Foot quilt drape with an explicit knee/shin collision envelope.
nuq,nvq=43,29
xx=np.linspace(1390,2205,nuq);vv=np.linspace(-1,1,nvq)
qv=[]
for x in xx:
    s_rim=brentq(lambda s:ring(s,2.05)[0]-x,0,math.pi)
    edge=ring(s_rim,2.05);w=edge[1]
    for v in vv:qv.append([x,v*w,edge[2]+110*(1-v*v)*min(1,(2205-x)/260)])
qv=np.asarray(qv)/1000
qpin=np.array([i*nvq+j for i in range(nuq) for j in range(nvq) if j in [0,nvq-1] or i==nuq-1],np.int32)
qa=grid_faces(nuq,nvq);qarea=float(np.sum(np.linalg.norm(np.cross(qv[qa[:,1]]-qv[qa[:,0]],qv[qa[:,2]]-qv[qa[:,0]]),axis=1))*.5)
qo,qf,qm,qt,qs=cachedsolve('foot_quilt',qv,nuq,nvq,qpin,qarea,rho=.5,steps=300,iterations=32,slack=1.01,floor=.135,ell=[1.78,0,.22,.48,.21,.16])
addmesh('FOOT_QUILT_DRAPED',qo*1000,qf,'outer','work',desc='Uncalibrated drape calculation over fixed lower-leg proxy')
np.savez_compressed(ROOT/'simulation/foot_quilt_drape.npz',initial_m=qv,final_m=qo,triangles=qf,pins=qpin,track=qt,snapshots=qs)
save_json(ROOT/'simulation/foot_quilt_metrics.json',qm)
# Sleep quilt: independently settled over a static torso/leg clearance proxy.
nsu,nsv=57,29
sv=[]
for x in np.linspace(650,2205,nsu):
    sr=brentq(lambda s:ring(s,2.05)[0]-x,0,math.pi)
    ed=ring(sr,2.05)
    for v in np.linspace(-1,1,nsv):sv.append([x,v*ed[1],ed[2]+80*(1-v*v)*min(1,(2205-x)/260)])
sv=np.asarray(sv)/1000
sp=np.array([i*nsv+j for i in range(nsu) for j in range(nsv) if j in [0,nsv-1] or i in [0,nsu-1]],np.int32)
sf=grid_faces(nsu,nsv);sa=float(np.sum(np.linalg.norm(np.cross(sv[sf[:,1]]-sv[sf[:,0]],sv[sf[:,2]]-sv[sf[:,0]]),axis=1))*.5)
so,sf,sm,st,ss=cachedsolve('sleep_quilt',sv,nsu,nsv,sp,sa,rho=.5,steps=600,iterations=40,dt=1/240,damping=.70,slack=1.008,floor=.135,ell=[1.39,0,.18,.83,.235,.12])
addmesh('SLEEP_QUILT_DRAPED',so*1000,sf,'outer','sleep',desc='Sleep textile quilt; open head aperture; no simulated heat')
np.savez_compressed(ROOT/'simulation/sleep_quilt_drape.npz',initial_m=sv,final_m=so,triangles=sf,pins=sp,track=st,snapshots=ss)
save_json(ROOT/'simulation/sleep_quilt_metrics.json',sm)

# Very explicitly a sensitivity illustration: assumed nonlinear compressive laws, NOT material data.
fills=[]
for E in [10000,20000,40000]:
    strain=brentq(lambda e:E*(e+4*e**3)/(1-e)**2-400/.12,0,.85)
    fills.append({'assumed_modulus_Pa':E,'hypothetical_force_N':400,'assumed_contact_area_m2':.12,'unloaded_thickness_mm':100,'computed_compression_mm':100*strain,'not_measured_material':True})
save_json(ROOT/'simulation/filler_sensitivity.json',fills)
# Save model database separate from optional BREP objects.
serial=[{k:v for k,v in o.items() if k!='brep'} for o in ITEMS]
save_json(ROOT/'cad/model_R04.json',serial)
save_json(ROOT/'patterns/surfaces_R04.json',PATCHES)
# Native OCC STEP: smooth NURBS envelope + inherited solid hardware + draped cloth surfaces.
# Cloth triangulation is exported at reduced grid density to keep file inspectable.
def shell_from_grid(vertices,faces):
    fc=[]
    for tr in faces:
        w=cq.Wire.makePolygon([cq.Vector(*vertices[i]) for i in tr],close=True)
        fc.append(cq.Face.makeFromWires(w))
    return cq.Shell.makeShell(fc)
for state,angle in [('work_closed',0),('work_open',105),('sleep',None)]:
    ass=cq.Assembly(name='Lezhandr_R04_'+state);partids=[]
    for o in ITEMS:
        mode=o['modes']
        if o.get('external') or o['id'].startswith('KEY_') or o.get('technical'):continue
        if mode=='work' and state=='sleep':continue
        if mode=='sleep' and state!='sleep':continue
        if mode.startswith('hood'):
            if angle is None or mode!='hood'+str(angle):continue
        sh=o.get('brep')
        if sh is None and o['id'].startswith('PASSIVE_HOOD'):
            pp=np.asarray(o['vertices_mm']).reshape(25,49,3)[::2,::2,:]
            sh=cq.Face.makeSplineApprox([[cq.Vector(*p) for p in row] for row in pp],tol=.1,minDeg=1,maxDeg=3)
        elif sh is None and o['id']=='FOOT_QUILT_DRAPED':
            pp=np.asarray(o['vertices_mm']).reshape(43,29,3)[::2,::2,:]
            sh=cq.Face.makeSplineApprox([[cq.Vector(*p) for p in row] for row in pp],tol=.1,minDeg=1,maxDeg=3)
        elif sh is None and o['id']=='SLEEP_QUILT_DRAPED':
            pp=np.asarray(o['vertices_mm']).reshape(57,29,3)[::2,::2,:]
            sh=cq.Face.makeSplineApprox([[cq.Vector(*p) for p in row] for row in pp],tol=.1,minDeg=1,maxDeg=3)
        if sh is None:continue
        if not sh.isValid():raise ValueError(o['id'])
        ass.add(sh,name=o['id'],color=cq.Color(*PAL[o['kind']]));partids.append(o['id'])
    name=ROOT/'cad'/f'Lezhandr_R04_{state}.step';ass.save(str(name))
    test=cq.importers.importStep(str(name));valid=all(v.isValid() for v in test.vals())
    save_json(ROOT/'tests'/f'STEP_{state}.json',{'state':state,'part_ids':partids,'reimported_valid':valid,'solid_count':len(test.solids().vals()),'surface_and_solid_model':True,'no_hand_heater':not any('EH3' in x for x in partids)})
# OBJ conversion preserves actual mm coordinates for CAD / CLO static imports.
for state,angle in [('work_closed',0),('work_open',105),('sleep',None)]:
    path=ROOT/'exchange'/f'Lezhandr_R04_{state}_mm.obj';i0=1
    with path.open('w') as f:
        f.write('# Units millimetres. Static mesh import, not a CLO project.\n')
        for o in serial:
            mode=o['modes']
            if o.get('external') or o.get('technical') or 'vertices_mm' not in o:continue
            if mode=='work' and state=='sleep':continue
            if mode=='sleep' and state!='sleep':continue
            if mode.startswith('hood') and (angle is None or mode!='hood'+str(angle)):continue
            f.write('o '+o['id']+'\n')
            for p in o['vertices_mm']:f.write('v %.5f %.5f %.5f\n'%tuple(p))
            for t in o['faces']:f.write('f '+' '.join(str(int(j)+i0) for j in t)+'\n')
            i0+=len(o['vertices_mm'])
# Geometric clearance data: reference surfaces, not ventilation / thermal validation.
closed=hood_rotate(0);opened=hood_rotate(105)
kb=np.array([[x,y,542] for x in np.linspace(1085,1305,12) for y in np.linspace(-185,185,10)])
# Rays from one nominal eye point; finite triangles of the canopy only.
def segment_hits(origin,targets,v,faces):
    a=v[faces[:,0]];e1=v[faces[:,1]]-a;e2=v[faces[:,2]]-a;res=[]
    for target in targets:
        d=target-origin;h=np.cross(np.broadcast_to(d,e2.shape),e2);det=np.einsum('ij,ij->i',e1,h);ok=np.abs(det)>1e-9
        inv=np.zeros(len(det));inv[ok]=1/det[ok];s=origin-a;u=inv*np.einsum('ij,ij->i',s,h);q=np.cross(s,e1);vv=inv*np.einsum('ij,j->i',q,d);t=inv*np.einsum('ij,ij->i',e2,q)
        res.append(bool(np.any(ok&(u>=0)&(vv>=0)&(u+vv<=1)&(t>0)&(t<1))))
    return int(sum(res))
ey=np.array([460,0,1000.])
angles=np.linspace(0,105,43);sweep=np.concatenate([hood_rotate(a) for a in angles])
clear={'hood_electrical_power_W':0,'hood_heater_count':0,'hood_cable_count':0,'hinge_axis_mm':[[965,335,545],[1325,335,545]],'open_angle_deg':105,
'closed_bbox_mm':[closed.min(0).tolist(),closed.max(0).tolist()], 'open_bbox_mm':[opened.min(0).tolist(),opened.max(0).tolist()], 'sampled_sweep_bbox_mm':[sweep.min(0).tolist(),sweep.max(0).tolist()],
'eye_point_mm':ey.tolist(),'keyboard_samples':len(kb),'canopy_occluded_samples_closed':segment_hits(ey,kb,closed,faces),'canopy_occluded_samples_open':segment_hits(ey,kb,opened,faces),
'hood_screen_x_gap_mm':float(screen.BoundingBox().xmin-closed[:,0].max()),'laptop_bottom_to_tray_top_mm':16.0,
'caveat':'Single reference eye point and canopy only; no anthropometric certification, airflow, CFD or measured laptop heat.'}
save_json(ROOT/'tests/hood_clearances.json',clear)
print(json.dumps({'hood':hm,'quilt':qm,'clearance':clear},indent=2))
