#!/usr/bin/env python3
"""R08: named edits to R07, explicit interference audit, continuous textile skins.
Millimetres. No granular, anatomical or dynamic cloth simulation is claimed.
"""
from pathlib import Path
import json, math, hashlib, os
import numpy as np
import cadquery as cq
from scipy.interpolate import PchipInterpolator as P
ROOT=Path(__file__).resolve().parents[1]
BASE=Path(os.getenv('LEZHANDR_R07_ROOT',str(ROOT.parent/'Lezhandr_R07')))
for d in ['cad','patterns','tests','renders','docs','harness','thermal']:(ROOT/d).mkdir(exist_ok=True)
def js(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,default=lambda o:o.item() if isinstance(o,np.generic) else o.tolist()))
META={r['id']:r for r in json.loads((BASE/'cad/model_R07.json').read_text())}
OLD={}
for state in ['open','closed','interior']:
 a=cq.Assembly.load(str(BASE/'cad'/f'Lezhandr_R07_{state}.step'))
 for n,o in a.objects.items():
  if o.obj is not None and n in META:OLD[n]=o.obj.located(o.loc)
PAL={'cloth':(.56,.43,.32),'lining':(.68,.56,.44),'seam':(.40,.31,.23),'fill1':(.77,.68,.56),'fill2':(.61,.62,.48),'contact':(.67,.58,.47),'webbing':(.31,.26,.20),'hardware':(.27,.27,.24),'frame':(.56,.38,.21),'floor':(.32,.27,.23),'tray':(.44,.42,.37),'device':(.16,.16,.15),'screen':(.22,.30,.30),'human':(.77,.79,.74),'white':(.86,.84,.78),'heater':(.72,.43,.28),'wire':(.49,.32,.20),'sensor':(.34,.42,.40)}
SH={};ROWS=[];PANELS=[];ROUTES=[]
def add(n,s,kind,g,states=('open','closed','interior','exit'),note=''):
 print('ADD',n,flush=True)
 if not s.isValid():raise RuntimeError('invalid '+n)
 v,f=s.tessellate(2,.22);b=s.BoundingBox()
 SH[n]=s;ROWS.append({'id':n,'group':g,'kind':kind,'states':list(states),'vertices_mm':[p.toTuple() for p in v],'faces':f,'bounds_mm':[b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax],'solids':len(s.Solids()),'note':note})
 return s
def box(c,d,r=0,ang=0):
 s=cq.Workplane('XY').box(*d)
 if r:s=s.edges().fillet(r)
 return s.val().rotate((0,0,0),(0,1,0),ang).translate(tuple(c))
def face_grid(g):return cq.Face.makeSplineApprox([[cq.Vector(*p) for p in row] for row in g],tol=.02,minDeg=1,maxDeg=3)
def sandwich(n,ou,inn,group,states=('open','closed','interior','exit')):
 ou=np.array(ou);inn=np.array(inn);w=[]
 for a,b in zip(ou,inn):
  ed=[cq.Edge.makeSpline([cq.Vector(*p) for p in a]),cq.Edge.makeLine(cq.Vector(*a[-1]),cq.Vector(*b[-1])),cq.Edge.makeSpline([cq.Vector(*p) for p in b[::-1]]),cq.Edge.makeLine(cq.Vector(*b[0]),cq.Vector(*a[0]))]
  w.append(cq.Wire.assembleEdges(ed))
 print('LOFT',n,len(w),flush=True)
 s=cq.Solid.makeLoft(w,False);add(n,s,'cloth',group,states)
 return s

def panel(n,g,material='outer',parent='',allow=12):
 g=np.array(g);PANELS.append({'id':n,'parent':parent,'material':material,'grid_mm':g.tolist(),'seam_allowance_mm':allow,'quantity':1})

def skins(n,ou,inn,group,split=3,states=('open','closed','interior','exit')):
 s=sandwich(n,ou,inn,group,states)
 ou=np.array(ou);inn=np.array(inn)
 # Pattern surfaces are exactly the same sample grid used for the BREP loft.
 indices=np.linspace(0,ou.shape[1]-1,split+1,dtype=int)
 for k,(a,b) in enumerate(zip(indices[:-1],indices[1:])):
  for layer,g,mat in [('O',ou,'outer'),('I',inn,'lining')]:panel(f'{n}_{layer}{k+1}',g[:,a:b+1],mat,n)
  panel(f'{n}_W{k+1}',(ou[:,a:b+1]+inn[:,a:b+1])/2,'insulation',n,0)
 # End / edge strips close the two skins, rather than invisible open solids.
 for edge,a,b in [('START',ou[0],inn[0]),('END',ou[-1],inn[-1]),('LEFT',ou[:,0],inn[:,0]),('RIGHT',ou[:,-1],inn[:,-1])]:panel(n+'_'+edge,np.stack([a,b],axis=1),'lining',n)
 return s

# Retain R07 desk, mannequin and internal support modules. Do not redraw them from screenshots.
retained=[]
for n,s in OLD.items():
 g=META[n]['group']
 if g in ['lower_shell','hood','shoulder','leg_quilt','thermal','seams','floor']:continue
 if n.startswith('HT07'):continue
 add(n,s,META[n]['kind'],g,META[n]['states'],note='Preserved R07 named geometry');retained.append(n)
def bb_gap(a,b):
 a=a.BoundingBox();b=b.BoundingBox();return math.sqrt(sum(max(0,lo2-hi1,lo1-hi2)**2 for lo1,hi1,lo2,hi2 in [(a.xmin,a.xmax,b.xmin,b.xmax),(a.ymin,a.ymax,b.ymin,b.ymax),(a.zmin,a.zmax,b.zmin,b.zmax)]))
# Non-contact audit of the original thermal receivers.
cache=ROOT/'tests/R07_interferences.json'
r07=json.loads(cache.read_text()) if cache.exists() else []
body={n:s for n,s in OLD.items() if n.startswith('M_')}
for n,s in ([] if cache.exists() else OLD.items()):
 if not n.startswith('HX07_'):continue
 print('AUDIT07',n,flush=True)
 for bn,b in body.items():
  if bb_gap(s,b)>45:continue
  dist=s.distance(b)
  if dist<45:
   vol=sum(z.Volume() for z in s.intersect(b).Solids()) if dist<1e-4 else 0
   r07.append({'part':n,'body':bn,'distance_mm':dist,'intersection_cm3':vol/1000})
js(ROOT/'tests/R07_interferences.json',r07)

# Single smooth lower wrap replaces visible puffer cells; the support chambers remain inside.
xv=np.array([55,150,300,450,650,850,1050,1300,1600,1900,2140,2290,2345.])
W=P(xv,[65,250,400,490,532,545,545,527,496,444,350,205,65]);R=P(xv,[150,410,775,835,780,630,500,409,360,353,346,295,165]);B=P(xv,[40,15,8,8,8,8,8,8,8,8,10,20,50])
G=json.loads((BASE/'cad/sewing_grids_R07.json').read_text());h=G['H07_SOFT_OVERHEAD_HOOD']
ho=np.array(h['outer_mm']);hi=np.array(h['inner_mm'])
# Same sampled seam curve for canopy and lower shell: no floating rear skins.
for k in range(len(ho)):
 delta=max(0,60-ho[k,0,2]);factor=(ho[k,:,1]/max(abs(ho[k,:,1])))**2
 ho[k,:,2]+=delta*factor;hi[k,:,2]+=delta*factor
hx=ho[:,0,0];tail=np.linspace(950,2345,27);allx=np.r_[hx,tail]
wx=np.r_[abs(ho[:,0,1]),[float(W(x)) for x in tail]];rx=np.r_[ho[:,0,2],[float(R(x)) for x in tail]]
W=P(allx,wx);R=P(allx,rx)
ou=[];inn=[]
for x in allx:
 th=np.linspace(-math.pi/2,math.pi/2,33);w=float(W(x));r=float(R(x));z=float(B(x));t=min(38,w*.3) if x<=820 else min(60,w*.42,(r-z)*.45)
 z=min(z,r-t-12)
 ou.append(np.c_[np.full(len(th),x),w*np.sin(th),z+(r-z)*(1-np.cos(th))**4])
 inn.append(np.c_[np.full(len(th),x),(w-t)*np.sin(th),z+t+(r-z-t)*(1-np.cos(th))**4])
skins('O08_SMOOTH_LOWER',ou,inn,'lower_shell',6)
hood=skins('H08_CANOPY',ho,hi,'hood',4)
# Flexible sole follows this same outline instead of protruding under rear transition.
xs=np.linspace(55,2345,100);left=np.array([[x,-float(W(x)),0] for x in xs]);right=np.array([[x,float(W(x)),0] for x in xs]);outline=np.vstack([left,right[::-1]])
floor=cq.Workplane('XY').polyline([tuple(v[:2]) for v in outline]).close().extrude(62).val();add('F08_FLEXIBLE_SOLE',floor,'cloth','floor')
for layer,z in [('BOTTOM',0),('TOP',62)]:panel('F08_'+layer,[[[x,-float(W(x)),z],[x,float(W(x)),z]] for x in xs],'technical','F08_FLEXIBLE_SOLE')
for side,edge in [('LEFT',left),('RIGHT',right)]:panel('F08_EDGE_'+side,np.stack([edge,edge+[0,0,62]],axis=1),'outer','F08_FLEXIBLE_SOLE')
# Hidden seam guards are inside the joined rail, not full-height curtains across the shell.
for sy in [-1,1]:
 ou=[];inn=[]
 for a in ho:
  top=a[0 if sy<0 else -1].copy();v=np.linspace(-1,1,9)
  g=np.array([top+[0,-sy*9,35*f] for f in v]);ou.append(g);inn.append(g+[0,-sy*8,0])
 skins('G08_BACK_'+str(sy),ou,inn,'rear_gusset',1)
# Rear cap at X=55, beneath canopy and overlapping soft floor.
rear=box((55,0,136),(24,144,220),10);add('G08_REAR_END',rear,'cloth','rear_gusset')
for layer,xx in [('O',43),('I',67)]:panel('G08_REAR_'+layer,np.array([[[xx,-72,26],[xx,72,26]],[[xx,-72,246],[xx,72,246]]]),'outer' if layer=='O' else 'lining','G08_REAR_END')
# Foot end remains the padded R07 cap; reconnect at overlap, no rigid footboard.
if 'O09_PADDED_TOE_BOX' in OLD:add('O08_TOE_CAP',OLD['O09_PADDED_TOE_BOX'],'cloth','lower_shell')

# Smooth continuous leg cover. No periodic puffing; it reaches X=965 underneath desk.
xp=np.array([965,1100,1290,1450,1650,1870,2110,2320.]);C=P(xp,[407,424,461,478,468,436,414,340]);WW=P(xp,[522,529,522,511,482,442,359,145]);E=P(xp,[570,485,415,390,365,359,345,270]);T=P(xp,[43,48,60,75,78,77,70,50])
ou=[];inn=[]
for x in np.linspace(965,2320,33):
 q=np.linspace(-1,1,25);z=float(C(x))-44*q*q+(float(E(x))-float(C(x))+44)*q**6
 a=np.c_[np.full(len(q),x),float(WW(x))*q,z];b=a.copy();b[:,2]-=9+(float(T(x))-9)*(1-q*q)**.65
 ou.append(a);inn.append(b)
leg=skins('L08_CONTINUOUS_COVER',ou,inn,'leg_quilt',4,('open','closed','interior'))
# Cut shoulder from a smooth shell, retaining wide R07 neck and keyboard access.
xx=np.array([620,700,810,950,1080]);CH=P(xx,[904,897,820,712,622]);CW=P(xx,[float(W(x)) for x in xx]);CE=P(xx,[float(R(x))+10 for x in xx])
# Separate side wings leave the neck free; lower bridge spans chest to keyboard.
for sy in [-1,1]:
 ou=[];inn=[]
 for x in np.linspace(625,1020,23):
  inner=238*math.sqrt(max(0,1-((x-670)/270)**2)) if x<940 else 0
  yy=np.linspace(inner*sy,float(CW(max(620,x)))*sy,13)
  z=float(CE(x))+(float(CH(x))-float(CE(x)))*np.sqrt(np.maximum(0,1-(yy/float(CW(x)))**2))
  a=np.c_[np.full(len(yy),x),yy,z];b=a.copy();b[:,2]-=20+20*(1-np.abs(yy)/float(CW(x)))
  if sy<0:a=a[::-1];b=b[::-1]
  ou.append(a);inn.append(b)
 skins('S08_WRAP_'+str(sy),ou,inn,'shoulder',2,('open','closed','interior'))
# Retain forearm gussets; they are matte and have no external quilting lines.
for n in ['G07_FOREARM_GUSSET_-1','G07_FOREARM_GUSSET_1']:
 g=G[n];skins(n.replace('G07','G08'),g['outer_mm'],g['inner_mm'],'shoulder',1,('open','closed','interior'))
# New patterns for unchanged passive flap (rolled state is same piece, not a second cut).
g=G['K07_PASSIVE_FLAP_CLOSED'];panel('K08_FLAP_OUTER',g['outer_mm'],'outer','K07_PASSIVE_FLAP_CLOSED');panel('K08_FLAP_LINING',g['inner_mm'],'lining','K07_PASSIVE_FLAP_CLOSED');panel('K08_FLAP_INSULATION',(np.array(g['outer_mm'])+g['inner_mm'])/2,'insulation','K07_PASSIVE_FLAP_CLOSED',0)

# Relocate soft electric cassettes using the real torso coordinate frame; no metal heat link through body.
p=json.loads((BASE/'history/R06/poses.json').read_text())['work'];H=np.array(p['hip']);S=np.array(p['shoulder']);n=np.array(p['n']);u=np.array(p['u'])
center=(H+S)/2-n*129.5
back=box(center,(5,420,500),1,ang=-35)
add('EH08_BACK_CASSETTE',back,'heater','heater',note='Flexible electrically insulated mat envelope, not a metal support. 129.5 mm behind torso axis; negative Y rotation fixes R07 error.')
seat=box((1110,0,108),(365,420,5),1);add('EH08_SEAT_CASSETTE',seat,'heater','heater',note='Flexible mat beneath body envelope. Real liner/contact geometry requires pressure test.')
# Power/controls stay outside insulation, left side, not at the exit.
add('J08_SERVICE_BLOCK',box((780,-633,162),(160,86,96),12),'hardware','service',note='External removable low voltage junction; source battery/DC-DC remain outside cocoon.')
# No thermally conductive connection from cold tabletop to body in the baseline.
# Passive laptop heat is sensed; local heater controller acts on receiver NTCs, not CPU temperature.
# Zipper route is mechanically heavy-duty coil hidden by flap, not a delicate dress invisible zipper.
ziprows=[]
for name,sy,xa,xb,role in [('Z01_MAIN_RIGHT',1,820,2230,'two-way coil opening, inner and outer pulls'),('Z02_HOOD_SERVICE',-1,180,820,'hood detachable service joint'),('Z03_FILL_SERVICE',-1,580,1020,'double internal fill access'),('Z04_ELECTRIC_SERVICE',-1,720,1000,'removable wire channel flap')]:
 x=np.linspace(xa,xb,33);pts=np.array([[t,sy*(float(W(t))-5),float(R(t))+19 if name!='Z04_ELECTRIC_SERVICE' else 115] for t in x]);length=float(np.linalg.norm(np.diff(pts,axis=0),axis=1).sum())
 edge=cq.Edge.makeSpline([cq.Vector(*t) for t in pts]);add(name,edge,'seam','zipper',note=role);ROWS[-1]['polyline_mm']=pts.tolist();ROWS[-1]['radius_mm']=1.1
 ziprows.append({'id':name,'length_seam_mm':length,'blank_order_mm':math.ceil((length+70)/50)*50,'points_mm':pts.tolist(),'role':role,'draft_guard_width_mm':65,'end_padding_mm':35})
 # Flat tape and guard patterns have directly calculated path lengths.
 for suffix,width,mat in [('GUARD',65,'lining'),('TAPE',30,'technical')]:panel(name+'_'+suffix,[[[0,0,0],[width,0,0]],[[0,length,0],[width,length,0]]],mat,name)
# Electrical routes constrained to left of the person and separate from right exit.
paths={
 'W01_POWER_TO_DESK':[[780,-633,162],[850,-585,175],[1040,-565,290],[1110,-550,470],[1210,-440,505],[1280,-270,525]],
 'W02_USB_DATA':[[780,-645,175],[910,-600,190],[1050,-583,320],[1160,-558,510],[1270,-450,545],[1320,-280,555]],
 'W03_BACK_HEATER':[[780,-615,145],[680,-480,180],[580,-390,340],[600,-305,500],[float(center[0]),-230,float(center[2])]],
 'W04_SEAT_HEATER':[[780,-620,120],[925,-480,90],[1090,-345,82],[1110,-230,108]],
 'W05_BACK_NTC':[[780,-600,185],[695,-450,240],[655,-330,420],[float(center[0])+25,-235,float(center[2])+35]],
 'W06_SEAT_NTC':[[780,-600,130],[905,-440,120],[1090,-325,110],[1150,-235,100]]}
for name,points in paths.items():
 e=cq.Edge.makeSpline([cq.Vector(*v) for v in points]);curve=np.array([v.toTuple() for v in e.discretize(100)]) if hasattr(e,'discretize') else np.array([e.positionAt(t).toTuple() for t in np.linspace(0,1,100)])
 add(name,e,'wire' if 'NTC' not in name else 'sensor','harness');ROWS[-1]['polyline_mm']=curve.tolist();ROWS[-1]['radius_mm']=3
 length=e.Length();service=250 if name in ['W01_POWER_TO_DESK','W02_USB_DATA'] else 120
 d=np.diff(curve,axis=0);a=np.linalg.norm(d,axis=1);cross=np.linalg.norm(np.cross(d[:-1],d[1:]),axis=1);rad=a[:-1]*a[1:]*np.linalg.norm(curve[2:]-curve[:-2],axis=1)/(2*np.maximum(cross,1e-12))
 ROUTES.append({'id':name,'centerline_length_mm':length,'service_allowance_mm':service,'cut_length_mm':math.ceil((length+service+80)/25)*25,'estimated_min_radius_mm':float(rad.min()),'diameter_design_mm':6,'points_mm':curve.tolist(),'part':'factory USB cable' if name=='W02_USB_DATA' else 'flexible low-voltage cable; exact wire and connector rating pending','right_exit_crossed':bool((curve[:,1]>0).any())})
 panel(name+'_CHANNEL',[[[0,0,0],[50,0,0]],[[0,length,0],[50,length,0]]],'technical',name)
# Position service loops at left of desk; not loose in the fill. 80 mm park stroke reserves 250 mm.
js(ROOT/'harness/routes.json',ROUTES);js(ROOT/'harness/zippers.json',ziprows)

js(ROOT/'cad/model_R08.json',ROWS);js(ROOT/'cad/palette.json',PAL);js(ROOT/'patterns/panel_grids.json',PANELS)
# Interference audit, heat mats vs each body part; hard parts vs body. Soft fill overlap classified separately.
checks=[];pairs=[]
people={n:s for n,s in SH.items() if n.startswith('M_')}
for name in ['EH08_BACK_CASSETTE','EH08_SEAT_CASSETTE','J08_SERVICE_BLOCK','T07_AL_PERFORATED_TRAY']:
 for bn,b in people.items():
  s=SH[name];dist=s.distance(b);v=sum(z.Volume() for z in s.intersect(b).Solids()) if dist<1e-4 else 0
  pairs.append({'part':name,'body':bn,'distance_mm':dist,'intersection_cm3':v/1000})
checks.append({'name':'Relocated cassettes and table do not intersect reference person','passed':all(v['intersection_cm3']<.001 for v in pairs)})
# Full hard module check is separate from thermal correction, excludes keycap/hand intended contact.
hard=[r for r in ROWS if r['group'] in ['frame','hardware','service','desk']]
cp=cq.Compound.makeCompound([b for n,b in people.items() if not n.startswith('M_HAND')]);ch=cq.Compound.makeCompound([SH[r['id']] for r in hard]);checks.append({'name':'Bare frame vs person','distance_mm':ch.distance(cp),'passed':ch.distance(cp)>0})
seam_error=max(float(np.linalg.norm(np.array(ou1)-np.array(ou2))) for ou1,ou2 in zip(ho[:,0],np.array(PANELS[0]['grid_mm'])[:len(hx),0]))
checks.append({'name':'Shared canopy/lower-shell sewing rail','passed':seam_error<1e-5,'max_node_gap_mm':seam_error})
# Top seam join uses the same hood rail, with explicit overlap (rather than pixels painted over hole).
for sy in [-1,1]:
 dist=SH['G08_BACK_'+str(sy)].distance(hood);checks.append({'name':'Rear gusset sewn hood overlap '+str(sy),'passed':dist<.05,'gap_mm':dist})
checks.append({'name':'No legacy conductive heat link enabled','passed':not any(n.startswith(('HT07','HX07','T07_OPTIONAL')) for n in SH)})
checks.append({'name':'Right exit has no cable route','passed':not any(r['right_exit_crossed'] for r in ROUTES)})
js(ROOT/'tests/interference_pairs.json',pairs)
# STEP export; cutaway is an inspection state, not a material removal in the product.
for state in ['open','closed','interior','exit']:
 a=cq.Assembly(name='Lezhandr_R08_'+state)
 for r in ROWS:
  if state not in r['states']:continue
  g=r['group'];name=r['id'];s=SH[name]
  if state=='interior' and g in ['hood','rear_gusset','lower_shell','shoulder','leg_quilt','flap','zipper','frame_padding']:continue
  if state in ['open','closed'] and g in ['heater','harness']:continue
  if state=='exit':
   if g in ['shoulder','flap','leg_quilt']:continue
   if g in ['desk','laptop']:s=s.translate((80,0,0))
   if g in ['lower_shell','rear_gusset','hood']:
    s=s.intersect(box((1200,-1000,650),(5000,2000,2500)))
  a.add(s,name=name,color=cq.Color(*PAL[r['kind']]))
 path=ROOT/'cad'/('Lezhandr_R08_'+state+'.step');a.save(str(path));read=cq.importers.importStep(str(path)).val()
 checks.append({'name':'STEP readback '+state,'passed':read.isValid(),'bytes':path.stat().st_size,'solids':len(read.Solids())})
js(ROOT/'cad/model_R08.json',ROWS);js(ROOT/'cad/palette.json',PAL);js(ROOT/'patterns/panel_grids.json',PANELS)
js(ROOT/'tests/CAD_checks.json',{'checks':checks,'all_passed':all(x['passed'] for x in checks),'retained_R07_components':retained,'nominal_body_height_mm':2000,'posture_count':1,'limitations':'Soft fill contacts and egress motion not validated; there is no automatic 25 mm safety guarantee under compression.'})
js(ROOT/'project.json',{'revision':'R08','source':'R07','hand_heater':False,'passive_metal_link_enabled':False,'palette':'matte sepia','pattern_release':'P0 digital prototype; fabric calibration and sample sewing required','assembly_states':['open','closed','interior','exit'],'unchanged':['legacy PCB/firmware','embroidery'],'geometry_source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (BASE/'cad').glob('*.step')}})
print('R08 DONE',len(ROWS),len(PANELS),checks,flush=True)
