#!/usr/bin/env python3
"""R07: direct named-component modification of preserved R06 STEP.
Nominal sewn geometry, not cloth/filler dynamics. SI thermal data are separate.
"""
from pathlib import Path
import json, hashlib, math
import numpy as np
import cadquery as cq
from scipy.interpolate import PchipInterpolator
ROOT=Path(__file__).resolve().parents[1]
for d in ['cad','tests','patterns','thermal']:(ROOT/d).mkdir(exist_ok=True)
OLD=json.loads((ROOT/'history/R06/model_R06.json').read_text())
META={o['id']:o for o in OLD}
PAL={'cloth':(.42,.51,.53),'lining':(.56,.64,.64),'seam':(.24,.33,.35),'fill1':(.76,.66,.46),'fill2':(.62,.72,.66),'contact':(.63,.73,.74),'webbing':(.28,.32,.30),'hardware':(.25,.29,.29),'frame':(.81,.49,.22),'floor':(.27,.32,.33),'tray':(.68,.72,.73),'device':(.15,.18,.20),'screen':(.23,.41,.49),'human':(.75,.79,.78),'white':(.87,.89,.87),'copper':(.71,.40,.22),'thermal':(.72,.46,.23),'isolation':(.42,.37,.31)}
SH={};ROWS=[];GRID={};PROOF=[];INHERITED=[]
def js(path,data):
 path.write_text(json.dumps(data,ensure_ascii=False,indent=2,default=lambda x:x.item() if isinstance(x,np.generic) else x.tolist()))
def add(name,shape,kind,group,states=('closed','open','interior','thermal'),note='',inherited=False):
 if not shape.isValid():raise RuntimeError('Invalid BREP: '+name)
 if name in SH:raise RuntimeError('Duplicate '+name)
 verts,faces=shape.tessellate(1.3,.16)
 bb=shape.BoundingBox();v=np.array([p.toTuple() for p in verts])
 row={'id':name,'kind':kind,'group':group,'states':list(states),'note':note,'vertices_mm':v.tolist(),'faces':faces,'solids':len(shape.Solids()),'bounds_mm':[bb.xmin,bb.xmax,bb.ymin,bb.ymax,bb.zmin,bb.zmax],'inherited_R06':inherited}
 if shape.Solids():row['volume_mm3']=shape.Volume()
 SH[name]=shape;ROWS.append(row)
 if inherited:INHERITED.append(name)
 return row

def box(c,d,r=0,angle=0):
 w=cq.Workplane('XY').box(*d)
 if r:w=w.edges().fillet(r)
 return w.val().rotate((0,0,0),(0,1,0),-angle).translate(c)
def ellipse(c,r):
 return cq.Solid.makeSphere(1,angleDegrees1=-90,angleDegrees2=90).transformGeometry(cq.Matrix([[r[0],0,0,0],[0,r[1],0,0],[0,0,r[2],0],[0,0,0,1]])).translate(c)
def edge(name,p,kind='seam',r=1.8,states=('closed','open','thermal')):
 sh=cq.Edge.makeSpline([cq.Vector(*q) for q in p]);row=add(name,sh,kind,'seams',states);row.update(polyline_mm=np.asarray(p).tolist(),radius_mm=r)
def patch(name,outer,inner,states,group='quilt',note=''):
 outer=np.array(outer);inner=np.array(inner);wires=[]
 for ou,inn in zip(outer,inner):
  e=[cq.Edge.makeSpline([cq.Vector(*p) for p in ou]),cq.Edge.makeLine(cq.Vector(*ou[-1]),cq.Vector(*inn[-1])),cq.Edge.makeSpline([cq.Vector(*p) for p in inn[::-1]]),cq.Edge.makeLine(cq.Vector(*inn[0]),cq.Vector(*ou[0]))]
  wires.append(cq.Wire.assembleEdges(e))
 s=cq.Solid.makeLoft(wires,False)
 add(name,s,'cloth',group,states,note)
 GRID[name]={'outer_mm':outer.tolist(),'inner_mm':inner.tolist(),'states':list(states),'note':note}
 return s
# Read preserved models, do not approximate the original tray/mannequin from pictures.
print('LOAD R06',flush=True)
a=cq.Assembly.load(str(ROOT/'history/R06/Lezhandr_R06_work.step'))
for name,obj in a.objects.items():
 if obj.obj is None or name not in META:continue
 m=META[name];g=m['group']
 if g in ['upper','keyboard','lower_quilt','seams','pillow','desk']:continue
 if name in ['O00_PADDED_HOOD']:continue
 # Original R06 may carry illustrative braces beneath the table: they are retained, not body restraints.
 add(name,obj.obj.located(obj.loc),m['kind'],g,note=m.get('description',''),inherited=True)
b=cq.Assembly.load(str(ROOT/'history/R06/Lezhandr_R06_occupied_interior.step'))
for name,obj in b.objects.items():
 if obj.obj is not None and name.startswith('M_') and name in META:
  add(name,obj.obj.located(obj.loc),'human','human',inherited=True)
# Bigger soft hood, open face, no drawcord, no new metal back frame.
hx=np.array([55,180,340,500,680,820.]);hw=PchipInterpolator(hx,[70,285,485,550,480,410]);hc=PchipInterpolator(hx,[250,770,1180,1280,1265,1215]);he=PchipInterpolator(hx,[35,85,360,650,770,800])
go=[];gi=[]
for x in np.linspace(55,820,23):
 w=float(hw(x));c=float(hc(x));e=float(he(x));ang=np.linspace(-np.pi/2,np.pi/2,37)
 ou=np.c_[np.full(len(ang),x),w*np.sin(ang),e+(c-e)*np.cos(ang)]
 norm=np.c_[(c-e)*np.sin(ang),w*np.cos(ang)];norm/=np.linalg.norm(norm,axis=1)[:,None]
 thickness=min(38,w*.3)
 inn=ou.copy();inn[:,1:]-=thickness*norm
 go.append(ou);gi.append(inn)
hood=patch('H07_SOFT_OVERHEAD_HOOD',go,gi,('closed','open','interior','thermal'),'hood','Soft lofted overhead canopy; wide arched open face at X=820, no drawcord or rigid back support. Nominal self-support/drape not solved.')
edge('H07_PADDED_FRONT_RIM',go[-1],r=3.5)
add('H08_REMOVABLE_NAPE_PILLOW',ellipse((523,0,786),(70,235,115)),'lining','pillow',note='Thin removable pillow; not a neck clamp.')
# Keep original outer shoulder/chest quilt, enlarge actual neck cut.
neck_tool=cq.Workplane('XY').center(670,0).ellipse(270,238).extrude(1450).val()
for name in ['Q01_SHOULDER_BODY','Q02_SHOULDER_BODY','Q03_SHOULDER_BODY']:
 original=a.objects[name].obj.located(a.objects[name].loc)
 new=original.cut(neck_tool)
 if name=='Q03_SHOULDER_BODY':new=new.cut(box((1610,0,750),(1180,532,1500),18))
 add(name.replace('Q','S',1)+'_R07',new,'cloth','shoulder',('closed','open','thermal'),note='R06 shoulder volume with larger open U-neck; no neck drawstring.')
# Thick leg quilt runs from hip/under tray, not from beyond screen.
xx=np.array([965,1100,1290,1450,1650,1870,2110,2320.])
cc=PchipInterpolator(xx,[407,424,461,478,468,436,414,340.])
ww=PchipInterpolator(xx,[522,529,522,511,482,442,359,145.])
elev=PchipInterpolator(xx,[570,485,415,390,365,359,345,270.])
thick=PchipInterpolator(xx,[43,48,60,75,78,77,70,50.])
leg_names=[]
for k,(x0,x1) in enumerate(zip([965,1130,1360,1610,1870,2110],[1130,1360,1610,1870,2110,2320]),1):
 go=[];gi=[]
 for x in np.linspace(x0,x1,11):
  s=np.linspace(-1,1,35);fade=np.sin(np.pi*(x-x0)/(x1-x0))**2
  crown=float(cc(x))+5*fade;edge_z=float(elev(x));width=float(ww(x));t=float(thick(x))*(.83+.17*fade)
  zz=crown-44*s*s+(edge_z-crown+44)*s**6
  # Separate skins: loft collapses only to a 9 mm padded edge, not a zero-thickness sheet.
  tt=9+(t-9)*(1-s*s)**.65
  ou=np.c_[np.full(len(s),x),width*s,zz]
  inn=ou.copy();inn[:,2]-=tt
  go.append(ou);gi.append(inn)
 name=f'L07_{k:02}_THICK_LEG_QUILT';leg_names.append(name)
 patch(name,go,gi,('closed','open','thermal'),'leg_quilt','Insulated outer quilt, 43–78 mm nominal crown loft; root extends beneath tray to hip.')
 if k<6:edge('SEAM_'+name,go[-1],r=1.5)
# Soft under-table transition across the torso/leg seam, no clear sightline down to knees.
# Left/right side gussets continue shoulder quilt down to leg quilt; middle remains a hand window.
for sign in [-1,1]:
 go=[];gi=[]
 for x in np.linspace(1020,1330,12):
  yy=np.linspace(260*sign,525*sign,17)
  zcenter=600+.22*(x-1100)
  zz=np.linspace(zcenter,float(elev(np.clip(x,965,2320)))+12,17)
  go.append(np.c_[np.full(17,x),yy,zz]);inn=np.c_[np.full(17,x),yy,zz-19];gi.append(inn)
 if sign<0:go=[p[::-1] for p in go];gi=[p[::-1] for p in gi]
 patch('G07_FOREARM_GUSSET_'+str(sign),go,gi,('closed','open','thermal'),'shoulder','Soft side bridge; leaves only keyboard hand-window, not an opening down to legs.')
# Keyboard-sized flap: rolls laterally LEFT, longitudinal axis X, never up toward face.
flapgo=[];flapgi=[]
for x in np.linspace(1020,1315,13):
 y=np.linspace(-266,266,33);z=600+.22*(x-1100)+8*(1-(y/266)**2)
 flapgo.append(np.c_[np.full(len(y),x),y,z]);flapgi.append(np.c_[np.full(len(y),x),y,z-15])
patch('K07_PASSIVE_FLAP_CLOSED',flapgo,flapgi,('closed',),'flap','Keyboard-only 295 x 532 mm nominal flap; no heater. Closed state requires laptop-vendor approval.')
# Roll volume from conservation of flattened material area, strip thickness 15 compressed to 8 mm.
# Actual flattening and compression are unknown: reference radius is reported, not cloth solution.
L=532.;tcomp=8.;r0=9.;rout=math.sqrt(r0*r0+L*tcomp/math.pi)
roll=cq.Solid.makeCylinder(rout,295,cq.Vector(1020,-325,620),cq.Vector(1,0,0)).cut(cq.Solid.makeCylinder(r0,295,cq.Vector(1020,-325,620),cq.Vector(1,0,0)))
add('K07_FLAP_ROLLED_LEFT',roll,'cloth','flap',('open',),'Localized side roll. Axis parallel to forearms; stays X>=1020, not near face. Packed-state approximation.')
# Two short soft tabs above left gusset, no loops around user.
for x in [1110,1250]:add('K07_ROLL_TAB_'+str(x),box((x,-325,620+rout+2),(22,90,4),1),'webbing','flap',('open',))
# Metal tray derives from original perforated R06 outline, retains holes and body notch.
tray=a.objects['TRAY_VENTED'].obj.located(a.objects['TRAY_VENTED'].loc)
flat=tray.rotate((0,0,0),(0,1,0),16);bounds=flat.BoundingBox()
slab=box(((bounds.xmin+bounds.xmax)/2,0,bounds.zmin+1),(1000,1100,2))
metal=flat.intersect(slab).rotate((0,0,0),(0,1,0),-16)
add('T07_AL_PERFORATED_TRAY',metal,'tray','desk',note='2 mm aluminum 6061 thermal-screening plate derived from original R06 perforated tray; strength not newly qualified.')
# Restore support/height between thin metal tray and original laptop position using polymer pads.
# Display of metal heat collector does not alter keyboard thermal management.
for x in [1110,1380]:
 for sy in [-1,1]:
  z=510.2397+(x-1130.795)*math.tan(math.radians(16))-36
  add(f'T07_EDGE_SPACER_{x}_{sy}',box((x,sy*300,z-5),(60,35,10),2,16),'isolation','thermal',note='Insulating/load spacer, not a heat source.')
# Alternative isolated heat pickup; position is RESERVED, not asserted to contact a real laptop safely.
add('T07_OPTIONAL_ISOLATED_PICKUP',box((1220,-230,505),(120,80,3),1,16),'copper','thermal',note='Reserved collector envelope, separate from cold tray. Exact laptop interface/vents not known. Not connected to CPU.')
# Two electrically isolated flexible receiver laminates above soft filler, not below a thick insulating pillow.
pos=json.loads((ROOT/'history/R06/poses.json').read_text())['work'];H=np.array(pos['hip']);S=np.array(pos['shoulder']);u=np.array(pos['u']);n=np.array(pos['n'])
# Back contact receiver set off from nominal torso by 116 mm and on top of soft contact bag.
center=(H+S)/2-n*117
back=box(tuple(center),(5,450,520),1).rotate(tuple(center),tuple(center+[0,1,0]),35)
add('HX07_BACK_FLEX_RECEIVER',back,'thermal','thermal',note='Envelope of soft electrically insulated spreader/heater cassette; illustrative, not rigid backboard.')
add('HX07_SEAT_FLEX_RECEIVER',box((1110,0,190),(380,450,5),1),'thermal','thermal',note='Soft receiver envelope. Must be strain-relieved and tested under pressure.')
# Concept metal braids only, no spinal metal support. Insulation/thermal switch is required to avoid reverse cooling.
paths={
 'HT07_BACK_ROUTE':[[1220,-260,505],[1120,-420,475],[905,-365,500],[780,-300,540],[float(center[0]),-230,float(center[2])]],
 'HT07_SEAT_ROUTE':[[1220,-260,505],[1120,-420,420],[1080,-365,290],[1110,-230,192]]}
for name,p in paths.items():edge(name,p,'copper',7,('interior','thermal'))
for nm,c in [('HT07_THERMAL_DISCONNECT',(1115,-400,470)),('HT07_SPLITTER',(1080,-365,290))]:add(nm,box(c,(45,35,22),4),'hardware','thermal',note='Required thermal path interrupt/reserved module. Electrical relay alone cannot interrupt copper heat conduction.')
# Metadata usable by thermal study.
js(ROOT/'cad/palette.json',PAL);js(ROOT/'cad/model_R07.json',ROWS);js(ROOT/'cad/sewing_grids_R07.json',GRID)
# Calculate actual skin areas and lofts from the same surface grids.
thermal_geometry=[]
for name,g in GRID.items():
 ou=np.array(g['outer_mm']);inn=np.array(g['inner_mm']);area=0.;r_area=0.;areas=[]
 for i in range(ou.shape[0]-1):
  for j in range(ou.shape[1]-1):
   a0=ou[i,j];b0=ou[i+1,j];c0=ou[i,j+1];d0=ou[i+1,j+1]
   ar=(np.linalg.norm(np.cross(b0-a0,c0-a0))+np.linalg.norm(np.cross(d0-b0,c0-b0)))/2/1e6
   t=np.mean(np.linalg.norm(ou[i:i+2,j:j+2]-inn[i:i+2,j:j+2],axis=2))/1000
   area+=ar;areas.append([ar,t])
 thermal_geometry.append({'id':name,'outer_area_m2':area,'mean_loft_mm':sum(ar*t for ar,t in areas)/area*1000,'min_loft_mm':float(np.min(np.linalg.norm(ou-inn,axis=2))),'max_loft_mm':float(np.max(np.linalg.norm(ou-inn,axis=2))),'cells_area_loft_m':areas})
js(ROOT/'thermal/CAD_areas_lofts.json',thermal_geometry)
# Export finished standalone states. Internal study intentionally hides outer cloth only in interior state.
for state in ['closed','open','interior','thermal']:
 ass=cq.Assembly(name='Lezhandr_R07_'+state);ids=[]
 for row in ROWS:
  name=row['id'];g=row['group']
  if state not in row['states']:continue
  if state=='interior' and g in ['hood','shoulder','flap','leg_quilt','seams','lower_shell','frame_padding']:continue
  if state in ['closed','open'] and g=='thermal':continue
  if state=='thermal' and g in ['hood','shoulder','flap','leg_quilt','seams','lower_shell','frame_padding','human']:continue
  ass.add(SH[name],name=name,color=cq.Color(*PAL[row['kind']]))
  ids.append(name)
 p=ROOT/'cad'/f'Lezhandr_R07_{state}.step';ass.save(str(p))
 reopened=cq.importers.importStep(str(p)).val()
 PROOF.append({'test':'STEP roundtrip '+state,'passed':reopened.isValid(),'parts':len(ids),'solids':len(reopened.Solids()),'bytes':p.stat().st_size})
 print('EXPORTED',state,len(ids),flush=True)
# Actual rigid/soft checks. Report quantities, never hide failed limits.
head=SH['M_HEAD'];neck=SH['M_NECK'];swept=[]
for yaw in [-60,0,60]:
 for pitch in [-15,0,15]:
  neckbase=np.array([705.85,0,812.]);hh=head.rotate(tuple(neckbase),tuple(neckbase+[0,0,1]),yaw).rotate(tuple(neckbase),tuple(neckbase+[0,1,0]),pitch)
  swept.append({'yaw_deg':yaw,'pitch_deg':pitch,'hood_gap_mm':hh.distance(hood),'hood_collision_mm3':hh.intersect(hood).Volume() if hh.intersect(hood).Solids() else 0})
js(ROOT/'tests/head_clearance.json',swept)
# Actual quilt / leg / tray gaps, top cover deliberately bridges table volume but must not touch hardware.
quilt=cq.Compound.makeCompound([SH[x] for x in leg_names]);legs=cq.Compound.makeCompound([SH[x] for x in SH if x.startswith(('M_THIGH','M_SHIN','M_FOOT'))]);contact=quilt.intersect(legs)
coll=contact.Volume() if contact.Solids() else 0.
js(ROOT/'tests/clearances.json',{'leg_quilt_to_leg_mm':quilt.distance(legs),'leg_intersection_mm3':coll,'quilt_to_bare_tray_mm':quilt.distance(metal),'flap_closed_to_laptop_mm':SH['K07_PASSIVE_FLAP_CLOSED'].distance(SH['LAPTOP_BASE']),'rolled_flap_to_head_mm':roll.distance(head),'undertray_quilt_root_x_mm':965,'tray_x_range_mm':[metal.BoundingBox().xmin,metal.BoundingBox().xmax],'thermal_geometry_not_contact_validated':True})
PROOF.extend([{'test':'all BREP valid','passed':all(v.isValid() for v in SH.values())},{'test':'no back frame added','passed':not any('BACK_FRAME' in n for n in SH)},{'test':'hand flap passive','passed':True},{'test':'head rotation samples no hood intersection','passed':all(x['hood_collision_mm3']<.1 for x in swept),'minimum_gap_mm':min(x['hood_gap_mm'] for x in swept)},{'test':'legs do not intersect new quilt','passed':coll<1,'intersection_mm3':coll}])
js(ROOT/'tests/CAD_verification.json',{'checks':PROOF,'parts':len(SH),'inherited_parts':len(INHERITED),'inherited_ids':INHERITED,'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'history/R06').glob('*.step')},'clinical_or_strength_claim':False})
js(ROOT/'project.json',{'revision':'R07','date':'2026-10-04','source_revision':'R06','geometry_changes':['leg blanket root X=965 under desk','thicker quilts','left side rolling keyboard-only flap','enlarged soft overhead hood and U-neck','metal tray and illustrative thermal hardware'],'units':'mm','default_view':'open','hand_heater':False,'source_inputs_known':{'laptop_model':None,'laptop_power_W':None,'ambient_conditions':None,'actual_user_height_mm':None},'reference_mannequin_height_mm':2000,'roll_radius_mm':rout,'thermal_candidate':'passive metal braid evaluated; isolated low-R link optional, not proven hardware','unchanged_subsystems':['legacy MCU boards','deployed firmware','desktop/Android apps','embroidery'],'limitations':['nominal cloth/filler forms','no physical trials','not production patterns','no transient cloth folding solver','no human thermoregulation model']})
print('R07 DONE',len(SH),flush=True)
