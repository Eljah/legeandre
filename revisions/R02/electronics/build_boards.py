#!/usr/bin/env python3
"""Generate native KiCad PCB + legacy editable schematic from one net graph.
Draft placement and conservative two-layer routing. KiCad ERC/DRC still required.
"""
from pathlib import Path
import json,math,csv,uuid,heapq
from collections import defaultdict
import numpy as np
from scipy.ndimage import distance_transform_edt, binary_dilation
import svgwrite
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'electronics';OUT.mkdir(exist_ok=True)
def uid():return str(uuid.uuid4())
def q(s):return '"'+str(s).replace('"',"'")+'"'
class Board:
 def __init__(self,name,w,h):self.name=name;self.w=w;self.h=h;self.parts=[];self.nets={};self.tracks=[];self.vias=[];self.unrouted=[]
 def part(self,ref,value,x,y,pins,kind='R',rot=0):
  n=len(pins);local=[]
  if kind.startswith('DIP'):
   half=n//2
   for i in range(half):local.append((str(i+1),-3.81,(i-(half-1)/2)*2.54,1.6,1.6,.8))
   for i in range(half):local.append((str(n-i),3.81,(i-(half-1)/2)*2.54,1.6,1.6,.8))
  elif kind=='SO16':
   for i in range(8):local.append((str(i+1),-2.7,(i-3.5)*1.27,1.55,.6,0))
   for i in range(8):local.append((str(16-i),2.7,(i-3.5)*1.27,1.55,.6,0))
  elif kind=='TO220':local=[('1',-2.54,0,1.7,1.7,1),('2',0,0,1.7,1.7,1),('3',2.54,0,1.7,1.7,1)]
  elif kind=='TERM':local=[(str(i+1),(i-(n-1)/2)*5.08,0,2.4,2.4,1.2) for i in range(n)]
  elif kind=='HEADER':local=[(str(i+1),0,(i-(n-1)/2)*2.54,1.6,1.6,.85) for i in range(n)]
  elif kind=='R':local=[('1',-3.81,0,1.7,1.7,.8),('2',3.81,0,1.7,1.7,.8)]
  else:local=[('1',-2.54,0,1.7,1.7,.8),('2',2.54,0,1.7,1.7,.8)]
  pads=[]
  for num,px,py,sx,sy,drill in local:
   if rot==90:px,py=-py,px;sx,sy=sy,sx
   net=pins.get(num,'NC_'+ref+'_'+num)
   if net not in self.nets:self.nets[net]=len(self.nets)+1
   pads.append({'num':num,'x':x+px,'y':y+py,'lx':px,'ly':py,'sx':sx,'sy':sy,'drill':drill,'net':net})
  self.parts.append({'ref':ref,'value':value,'x':x,'y':y,'pads':pads,'kind':kind,'footprint':f'Husky_{kind}_{n}'})
 def export(self):
  name=self.name
  pre=f'(kicad_pcb (version 20240108) (generator "lezhandr_generator")\n(general (thickness 1.6))\n(paper "A3")\n(layers (0 "F.Cu" signal) (31 "B.Cu" signal) (34 "B.Paste" user) (35 "F.Paste" user) (36 "B.SilkS" user "b.silkscreen") (37 "F.SilkS" user "f.silkscreen") (38 "B.Mask" user) (39 "F.Mask" user) (44 "Edge.Cuts" user))\n(setup (pad_to_mask_clearance 0.05))\n'
  out=[pre,'(net 0 "")']+[f'(net {i} {q(n)})' for n,i in self.nets.items()]
  pretty=OUT/(name+'.pretty');pretty.mkdir(exist_ok=True)
  for p in self.parts:
   f=[f'(footprint {q(p["footprint"])} (layer "F.Cu") (at {p["x"]} {p["y"]}) (uuid {uid()})',f'(fp_text reference {q(p["ref"])} (at 0 -7) (layer "F.SilkS") (effects (font (size 1.1 1.1) (thickness 0.15))))',f'(fp_text value {q(p["value"])} (at 0 7) (layer "F.SilkS") hide (effects (font (size 1 1) (thickness 0.15))))']
   for pad in p['pads']:
    typ='thru_hole' if pad['drill'] else 'smd';shape='rect' if not pad['drill'] or pad['num']=='1' else 'circle'
    layers='"*.Cu" "*.Mask"' if pad['drill'] else '"F.Cu" "F.Paste" "F.Mask"'
    drill=f'(drill {pad["drill"]})' if pad['drill'] else ''
    f.append(f'(pad {q(pad["num"])} {typ} {shape} (at {pad["lx"]} {pad["ly"]}) (size {pad["sx"]} {pad["sy"]}) {drill} (layers {layers}) (net {self.nets[pad["net"]]} {q(pad["net"])}))')
   f.append(')');out+=f
   # Footprint library variant, local coordinates already in pads; orientation encoded in name per instance.
   lib='\n'.join(f).replace(f'(at {p["x"]} {p["y"]})','(at 0 0)',1)
   (pretty/(p['ref']+'.kicad_mod')).write_text(lib)
  for net,layer,a,b,width in self.tracks:out.append(f'(segment (start {a[0]:.4f} {a[1]:.4f}) (end {b[0]:.4f} {b[1]:.4f}) (width {width}) (layer "{["F.Cu","B.Cu"][layer]}") (net {self.nets[net]}))')
  for net,x,y in self.vias:out.append(f'(via (at {x:.4f} {y:.4f}) (size 0.8) (drill 0.4) (layers "F.Cu" "B.Cu") (net {self.nets[net]}))')
  for a,b in [((0,0),(self.w,0)),((self.w,0),(self.w,self.h)),((self.w,self.h),(0,self.h)),((0,self.h),(0,0))]:out.append(f'(gr_line (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) (stroke (width .05) (type default)) (layer "Edge.Cuts"))')
  out.append(f'(gr_text {q(name+" R01 - BENCH ONLY - DRC REQUIRED")} (at {self.w/2} {self.h-3}) (layer "F.SilkS") (effects (font (size 1.1 1.1) (thickness .17))))')
  out.append(')');(OUT/(name+'.kicad_pcb')).write_text('\n'.join(out))
  (OUT/(name+'.kicad_pro')).write_text(json.dumps({'meta':{'filename':name+'.kicad_pro','version':1},'board':{'design_settings':{'rules':{'min_clearance':0.3,'min_track_width':0.3,'min_via_diameter':0.8}}}},indent=2))
  (OUT/(name+'_netgraph.json')).write_text(json.dumps({'name':name,'size_mm':[self.w,self.h],'components':self.parts,'tracks':self.tracks,'vias':self.vias,'unrouted':self.unrouted},indent=2))
  with (OUT/(name+'_BOM.csv')).open('w',newline='',encoding='utf-8-sig') as ff:
   w=csv.writer(ff);w.writerow(['Reference','Value/requirement','Footprint','X_mm','Y_mm']);
   for p in self.parts:w.writerow([p['ref'],p['value'],p['footprint'],p['x'],p['y']])
  self.schematic();self.render()
 def schematic(self):
  # Self-contained legacy Eeschema file. Current KiCad imports and can save as .kicad_sch.
  lib=['EESchema-LIBRARY Version 2.4','#encoding utf-8']
  sch=['EESchema Schematic File Version 4',f'LIBS:{self.name}-cache','EELAYER 29 0','EELAYER END','$Descr A0 46811 33110','encoding utf-8','Sheet 1 1',f'Title "{self.name}: R01 prototype electrical netlist"','Date "2026-09-30"','Rev "R01 - NOT FOR PRODUCTION"','$EndDescr']
  cols=7
  for k,p in enumerate(self.parts):
   n=len(p['pads']);s='C_'+p['ref'];hh=max(300,(n+1)*60)
   lib.extend([f'# {s}',f'DEF {s} {p["ref"][0]} 0 40 Y Y 1 F N',f'F0 "{p["ref"][0]}" 0 {hh+150} 60 H V C CNN',f'F1 "{s}" 0 {hh+50} 60 H V C CNN','DRAW',f'S -600 {hh} 600 {-hh} 0 1 10 f'])
   x=2500+(k%cols)*6200;y=2300+(k//cols)*2700
   for i,pad in enumerate(p['pads']):
    yy=int((n-1)*60-i*120);net=pad['net'];label=net if not net.startswith('NC_') else '~'
    lib.append(f'X {label} {pad["num"]} -900 {yy} 300 R 45 45 1 1 P')
    px=x-900;py=y-yy
    if net.startswith('NC_'):sch.append(f'NoConn ~ {px} {py}')
    else:sch.extend([f'Text Label {px-900} {py} 0 40 ~ 0',net,'Wire Wire Line',f'\t{px-900} {py} {px} {py}'])
   lib.extend(['ENDDRAW','ENDDEF'])
   sch.extend(['$Comp',f'L {self.name}-cache:{s} {p["ref"]}',f'U 1 1 {k+1:08X}',f'P {x} {y}',f'F 0 "{p["ref"]}" H {x} {y-hh-160} 60 0000 C CNN',f'F 1 "{p["value"]}" H {x} {y-hh-60} 50 0000 C CNN',f'F 2 "{self.name}:{p["ref"]}" H {x} {y} 50 0001 C CNN',f'\t1 {x} {y}','\t1 0 0 -1','$EndComp'])
  lib+=['#End Library'];sch+=['$EndSCHEMATC'];(OUT/(self.name+'-cache.lib')).write_text('\n'.join(lib));(OUT/(self.name+'.sch')).write_text('\n'.join(sch))
 def render(self):
  import cairosvg
  scale=6;d=svgwrite.Drawing(str(OUT/(self.name+'_layout.svg')),size=(self.w*scale,self.h*scale),viewBox=f'0 0 {self.w} {self.h}')
  d.add(d.rect((0,0),(self.w,self.h),fill='#eef3ef',stroke='#253d37',stroke_width=.4))
  for net,l,a,b,w in self.tracks:d.add(d.line(a,b,stroke=['#b45747','#4c729b'][l],stroke_width=w,opacity=.70))
  for net,x,y in self.vias:d.add(d.circle((x,y),.4,fill='#ccb35f',stroke='#333',stroke_width=.1))
  for p in self.parts:
   xs=[t['x'] for t in p['pads']];ys=[t['y'] for t in p['pads']]
   d.add(d.rect((min(xs)-1.5,min(ys)-1.5),(max(xs)-min(xs)+3,max(ys)-min(ys)+3),fill='none',stroke='#283b30',stroke_width=.2))
   for pad in p['pads']:
    d.add(d.rect((pad['x']-pad['sx']/2,pad['y']-pad['sy']/2),(pad['sx'],pad['sy']),fill='#d0b86c',stroke='#715722',stroke_width=.1))
    if pad['drill']:d.add(d.circle((pad['x'],pad['y']),pad['drill']/2,fill='#f8f8f8'))
   d.add(d.text(p['ref'],insert=(p['x'],min(ys)-2),font_size=1.8,text_anchor='middle',font_family='DejaVu Sans',fill='#122d23'))
  for net,a,b in self.unrouted:d.add(d.line(a,b,stroke='#d820c6',stroke_width=.2,stroke_dasharray='1,1'))
  d.add(d.text(self.name+' / R01 / DRC REQUIRED',insert=(4,self.h-3),font_size=2.2,font_family='DejaVu Sans'))
  d.save();cairosvg.svg2png(url=str(OUT/(self.name+'_layout.svg')),write_to=str(OUT/(self.name+'_layout.png')),scale=1.6)
 def route(self):
  # A* on a 0.5 mm grid with conservative rounded keepouts; off-grid pad stubs are emitted.
  step=.25;nx=int(self.w/step)+1;ny=int(self.h/step)+1
  occ=np.zeros((2,nx,ny),dtype=np.int32);coords=defaultdict(list)
  def stamp(layer,x,y,r,net):
   gx=x/step;gy=y/step;rr=int(math.ceil(r/step))+1
   xi=int(round(gx));yi=int(round(gy))
   for xx in range(max(0,xi-rr),min(nx,xi+rr+1)):
    for yy in range(max(0,yi-rr),min(ny,yi+rr+1)):
     if (xx-gx)**2+(yy-gy)**2<=(r/step)**2:occ[layer,xx,yy]=net
  for p in self.parts:
   for a in p['pads']:
    net=self.nets[a['net']];layers=[0,1] if a['drill'] else [0]
    for l in layers:
     if a['num']=='1' or not a['drill']:
      x0=max(0,int(math.floor((a['x']-a['sx']/2-.2)/step)));x1=min(nx,int(math.ceil((a['x']+a['sx']/2+.2)/step))+1)
      y0=max(0,int(math.floor((a['y']-a['sy']/2-.2)/step)));y1=min(ny,int(math.ceil((a['y']+a['sy']/2+.2)/step))+1)
      occ[l,x0:x1,y0:y1]=net
     else:stamp(l,a['x'],a['y'],a['sx']/2+.3,net)
    coords[a['net']].append((a['x'],a['y'],layers))
  nets=sorted(coords,key=lambda x:(0 if x in ['GND','H12','RAW12'] else 1,-len(coords[x])))
  routed=0
  for name in nets:
   pads=coords[name]
   if name.startswith('NC_') or len(pads)<2:continue
   nid=self.nets[name];width=1.6 if self.name.startswith('A1') and (name in ['PGND','H12'] or name.startswith(('DRAIN','HEAT'))) else .35
   # Build minimum-distance tree between pad centers.
   connected=[pads[0]];todo=pads[1:]
   while todo:
    ai,bi=min(((i,j) for i in range(len(connected)) for j in range(len(todo))),key=lambda ij:math.dist(connected[ij[0]][:2],todo[ij[1]][:2]))
    a=connected[ai];b=todo.pop(bi);connected.append(b)
    other=(occ!=0)&(occ!=nid)
    block=np.empty_like(other);clear=np.empty(other.shape,dtype=float)
    for l in [0,1]:
     clear[l]=distance_transform_edt(~other[l])*step
     block[l]=clear[l] < width/2+.45
    block[:,:3,:]=True;block[:,-3:,:]=True;block[:,:,:3]=True;block[:,:,-3:]=True
    ax,ay=int(round(a[0]/step)),int(round(a[1]/step));bx,by=int(round(b[0]/step)),int(round(b[1]/step))
    starts=[(l,ax,ay) for l in a[2]];goals={(l,bx,by) for l in b[2]}
    for s in starts+list(goals):block[s]=False
    queue=[];dist={};parent={}
    def h(x,y):return abs(x-bx)+abs(y-by)
    for s in starts:dist[s]=0;heapq.heappush(queue,(h(ax,ay),0,s))
    end=None;expanded=0
    while queue and expanded<180000:
     _,cost,s=heapq.heappop(queue)
     if dist.get(s)!=cost:continue
     if s in goals:end=s;break
     expanded+=1;l,x,y=s
     for dl,dx,dy,costadd in [(0,1,0,1),(0,-1,0,1),(0,0,1,1),(0,0,-1,1),(1,0,0,15)]:
      nn=(1-l,x,y) if dl else (l,x+dx,y+dy)
      ll,xx,yy=nn
      if xx<0 or yy<0 or xx>=nx or yy>=ny or block[nn]:continue
      if dl:
       # Via clearance uses a larger footprint than a signal trace.
       if min(clear[0,xx,yy],clear[1,xx,yy]) < .85:continue
      nc=cost+costadd
      if nc<dist.get(nn,1e30):dist[nn]=nc;parent[nn]=s;heapq.heappush(queue,(nc+h(xx,yy),nc,nn))
    if end is None:self.unrouted.append((name,a[:2],b[:2]));continue
    path=[end]
    while path[-1] in parent:path.append(parent[path[-1]])
    path.reverse();self.tracks.append((name,path[0][0],a[:2],(ax*step,ay*step),width))
    # merge straight route runs
    start=path[0];last=path[0];direction=None
    for node in path[1:]:
     if node[0]!=last[0]:
      if start!=last:self.tracks.append((name,last[0],(start[1]*step,start[2]*step),(last[1]*step,last[2]*step),width))
      self.vias.append((name,node[1]*step,node[2]*step));stamp(0,node[1]*step,node[2]*step,.55,nid);stamp(1,node[1]*step,node[2]*step,.55,nid);start=node;direction=None
     else:
      d=(node[1]-last[1],node[2]-last[2])
      if direction is not None and d!=direction:
       self.tracks.append((name,last[0],(start[1]*step,start[2]*step),(last[1]*step,last[2]*step),width));start=last
      direction=d
     stamp(node[0],node[1]*step,node[2]*step,width/2+.2,nid);last=node
    if start!=last:self.tracks.append((name,last[0],(start[1]*step,start[2]*step),(last[1]*step,last[2]*step),width))
    self.tracks.append((name,path[-1][0],(bx*step,by*step),b[:2],width));routed+=1
  (ROOT/'tests/results'/f'{self.name}_routing.json').write_text(json.dumps({'routed_connections':routed,'unrouted_connections':len(self.unrouted),'tracks':len(self.tracks),'vias':len(self.vias),'formal_KiCad_DRC':False,'warning':'Grid router is not a substitute for DRC; do not fabricate.'},indent=2))
  print(self.name,'routed',routed,'unrouted',len(self.unrouted),flush=True)

def make_power():
 b=Board('A1_4zone_power',145,122)
 b.part('J1','12V: SAFE / GND / RAW',15,109,{'1':'H12','2':'PGND','3':'RAW12'},'TERM')
 b.part('RSTAR','0R logic/power star',15,78,{'1':'GND','2':'PGND'},rot=90)
 b.part('J2','PWM0..3 / GND',9,31,{'1':'PWM0','2':'PWM1','3':'PWM2','4':'PWM3','5':'GND'},'HEADER')
 for g,x in enumerate([45,105]):
  b.part(f'U{g+1}','TC4427EPA',x,32,{'1':f'NC_U{g+1}_1','2':f'PWM{g*2}','3':'GND','4':f'PWM{g*2+1}','5':f'DRIVE{g*2+1}','6':'RAW12','7':f'DRIVE{g*2}','8':f'NC_U{g+1}_8'},'DIP8')
  b.part(f'C{g*2+1}','100n / 50V',x+13,32,{'1':'RAW12','2':'GND'},'C',90)
  b.part(f'C{g*2+2}','10u / 25V',x+13,40,{'1':'RAW12','2':'GND'},'C',90)
 for z,x in enumerate([28,59,90,121]):
  b.part(f'R{z*3+1}','47R',x,62,{'1':f'DRIVE{z}','2':f'GATE{z}'})
  b.part(f'R{z*3+2}','100k gate pulldown',x+9,73,{'1':f'GATE{z}','2':'GND'},rot=90)
  b.part(f'R{z*3+3}','10k input pulldown',x,49,{'1':f'PWM{z}','2':'GND'},rot=90)
  b.part(f'Q{z+1}','STP55NF06L',x,82,{'1':f'GATE{z}','2':f'DRAIN{z}','3':'PGND'},'TO220')
  b.part(f'F{z+1}',f'{[2.5,2.5,1.6,1.0][z]}A DC fuse - footprint VERIFY',x,95,{'1':'H12','2':f'HEAT{z}'},'C')
  b.part(f'JH{z+1}',f'Heater Z{z}',x,110,{'1':f'HEAT{z}','2':f'DRAIN{z}'},'TERM')
 return b

def make_interface():
 b=Board('A2_sensor_watchdog',200,160)
 for i,x in enumerate([18+21*z for z in range(8)]):
  b.part(f'JN{i+1}','10k B3950 NTC',x,12,{'1':f'NTC{i}','2':'GND'},'HEADER',90)
  b.part(f'RP{i+1}','10k 1%',x,28,{'1':'3V3','2':f'NTC{i}'},rot=90)
  b.part(f'RS{i+1}','100R',x,43,{'1':f'NTC{i}','2':f'ADC{i}'},rot=90)
  b.part(f'CN{i+1}','100n',x,58,{'1':f'ADC{i}','2':'GND'},'C',90)
  b.part(f'JA{i+1}',f'ESP ADC {i}',x,70,{'1':f'ADC{i}','2':'GND'},'HEADER',90)
 b.part('JP1','3V3 / GND / WD / PERMIT',13,91,{'1':'3V3','2':'GND','3':'WD','4':'PERMIT'},'HEADER')
 b.part('U1','74HC123D SO16',44,104,{'1':'GND','2':'WD','3':'PERMIT','4':'NC_U1_4','5':'NC_U1_5','6':'NC_U1_6','7':'NC_U1_7','8':'GND','9':'GND','10':'GND','11':'GND','12':'NC_U1_12','13':'WD_OK','14':'CEXT','15':'RCEXT','16':'3V3'},'SO16')
 b.part('RW1','470k 1%',60,90,{'1':'3V3','2':'RCEXT'})
 b.part('CW1','2.2u low leakage',62,103,{'1':'RCEXT','2':'CEXT'},'C')
 b.part('CU1','100n',39,90,{'1':'3V3','2':'GND'},'C')
 b.part('RPD1','100k',23,115,{'1':'PERMIT','2':'GND'},rot=90)
 b.part('RPD2','100k',23,132,{'1':'WD','2':'GND'},rot=90)
 b.part('U2','TC4427EPA',88,104,{'1':'NC_U2_1','2':'WD_OK','3':'GND','4':'GND','5':'NC_U2_5','6':'RAW12','7':'RELAY_DRIVE','8':'NC_U2_8'},'DIP8')
 b.part('CU2','100n',104,103,{'1':'RAW12','2':'GND'},'C',90)
 b.part('RG1','47R',87,122,{'1':'RELAY_DRIVE','2':'RELAY_GATE'})
 b.part('RPD3','100k',104,126,{'1':'RELAY_GATE','2':'GND'},rot=90)
 b.part('Q1','STP55NF06L',88,137,{'1':'RELAY_GATE','2':'COIL_MINUS','3':'GND'},'TO220')
 b.part('JK1','External K1 coil after NC chain',121,140,{'1':'COIL_PLUS','2':'COIL_MINUS'},'TERM')
 b.part('DK1','1N4007 A=1 K=2',120,123,{'1':'COIL_MINUS','2':'COIL_PLUS'},'R')
 b.part('JP2','RAW12 / GND',14,148,{'1':'RAW12','2':'GND'},'TERM')
 # Voltage sensing: pins are output ADC, battery or 12 V input, and GND. No MCU pin ever sees raw battery.
 for k,x,rt,in_net,out_net in [(1,157,'100k','BAT24','BAT_ADC'),(2,183,'47k','RAW12','H12_ADC')]:
  b.part(f'JV{k}','Sense IN / GND',x,89,{'1':in_net,'2':'GND'},'HEADER',90)
  b.part(f'RT{k}',rt+' 1%',x,105,{'1':in_net,'2':out_net},rot=90)
  b.part(f'RB{k}','10k 1%',x,123,{'1':out_net,'2':'GND'},rot=90)
  b.part(f'CV{k}','100n',x+8,125,{'1':out_net,'2':'GND'},'C',90)
  b.part(f'JO{k}','ESP voltage ADC / GND',x,142,{'1':out_net,'2':'GND'},'HEADER',90)
 return b
if __name__=='__main__':
 for b in [make_power(),make_interface()]:b.route();b.export()

# R01 local KiCad library tables are generated alongside boards.
if __name__ == '__main__':
 from pathlib import Path as _Path
 _root=_Path(__file__).resolve().parent
 _names=['A1_4zone_power','A2_sensor_watchdog']
 (_root/'sym-lib-table').write_text('(sym_lib_table\n'+''.join(' (lib (name "'+n+'-cache")(type "Legacy")(uri "${KIPRJMOD}/'+n+'-cache.lib")(options "")(descr "R01 netgraph symbols"))\n' for n in _names)+')\n')
 (_root/'fp-lib-table').write_text('(fp_lib_table\n'+''.join(' (lib (name "'+n+'")(type "KiCad")(uri "${KIPRJMOD}/'+n+'.pretty")(options "")(descr "R01 generated footprints"))\n' for n in _names)+')\n')
