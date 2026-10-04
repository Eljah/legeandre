#!/usr/bin/env python3
"""R02 wiring harness from actual CAD sewing edges and retained R01 connector pinout.
Separate power/sensor channels, service allowance, connector-to-connector cut list.
Polyline centerlines are routing datums, not a bend-radius or EMC qualification.
"""
from pathlib import Path
import json,csv,math
import numpy as np
import cadquery as cq
import ezdxf
ROOT=Path(__file__).resolve().parents[1]
PAN=json.loads((ROOT/'cad/sewing_surfaces.json').read_text());UV=json.loads((ROOT/'textile/patterns_R02.json').read_text())
P=json.loads((ROOT/'project.json').read_text());OUT=ROOT/'harness'

def edge_point(panel,x,uv=False,edge=0):
 d=PAN[panel];ss=d['stations_mm'];v=np.array(UV[panel]['uv_vertices_mm'] if uv else d['vertices_mm'])[edge::2]
 return [float(np.interp(x,ss,v[:,k])) for k in range(v.shape[1])]

def chain(panel,x0,x1):
 xs=[x0]+[x for x in PAN[panel]['stations_mm'] if min(x0,x1)<x<max(x0,x1)]+[x1]
 xs=sorted(set(xs),reverse=x0>x1)
 return [edge_point(panel,x) for x in xs]

def length(ps):return sum(math.dist(a,b) for a,b in zip(ps,ps[1:]))

zones=[]
for i in range(4):
 v=np.array(PAN['HZ'+str(i)]['vertices_mm']);endpoint=(v[0]+v[1])/2
 if i==0:
  a=math.radians(35.2);dx,dz=endpoint[0]-1110,endpoint[2]-120
  endpoint=np.array([1110+math.cos(a)*dx+math.sin(a)*dz,endpoint[1],120-math.sin(a)*dx+math.cos(a)*dz])
 zones.append({'zone':i,'name':P['zones'][i]['name'],'x':float(endpoint[0]),'power_panel':'O03','sensor_panel':'O02','end':endpoint.tolist()})

routes=[];wires=[]

def add_route(id,kind,source,target,points,conductors,gauge,panels='',amps=None):
 geom=length(points);allow=geom*.05+150+80;cut=math.ceil((geom+allow)/10)*10
 d={'id':id,'kind':kind,'source':source,'target':target,'points_mm':points,'geometric_length_mm':round(geom,1),'service_and_termination_allowance_mm':round(cut-geom,1),'cut_length_mm':cut,'conductors':conductors,'conductor_mm2':gauge,'route_panels':panels}
 if amps is not None:
  d['design_current_A']=amps;d['pair_drop_V_at_20C_assumed']=round(2*.0175*(cut/1000)/gauge*amps,3)
 routes.append(d);return d

entry=1200
for z in zones:
 i=z['zone'];endpoint=z['end'];pp=z['power_panel'];sp=z['sensor_panel']
 pts=[[1600,-820,50],[1480,-640,60],edge_point(pp,entry)]+chain(pp,entry,z['x'])[1:]+[endpoint]
 r=add_route(f'HP{i}','POWER',f'A1 JH{i+1}',f'Z{i} keyed 2-pin + thermal fuse',pts,2,.5,pp,P['zones'][i]['watts']/12)
 for pin,net in [(1,f'HEAT{i}'),(2,f'DRAIN{i}')]:wires.append([r['id'],f'A1.JH{i+1}.{pin}',f'Z{i}.P{pin}',net,.5,r['cut_length_mm'],'thermal fuse in P1; no splice in pressure zone'])
 for sn in [0,1]:
  xx=z['x']+(-35 if sn==0 else 35);ep=[endpoint[0]+(-35 if sn==0 else 35),endpoint[1]+25,endpoint[2]-8]
  pts=[[1600,-795,65],[1460,-600,70],edge_point(sp,entry)]+chain(sp,entry,xx)[1:]+[ep]
  n=2*i+sn+1
  r=add_route(f'NTC{i}{sn}','SENSOR',f'A2 JN{n}',f'Z{i} NTC {sn+1}',pts,2,.14,sp)
  for pin,net in [(1,f'NTC{n-1}'),(2,'GND')]:wires.append([r['id'],f'A2.JN{n}.{pin}',f'Z{i}.NTC{sn+1}.{pin}',net,.14,r['cut_length_mm'],'twisted pair; check EMI under PWM'])
 # Existing external thermostat chain must remain independent from MCU.
 pts=[[1600,-790,50],[1490,-600,70],edge_point(sp,entry)]+chain(sp,entry,z['x'])[1:]+[[endpoint[0],endpoint[1]+40,endpoint[2]-5]]
 r=add_route(f'TH{i}','SAFETY',f'K1 NC chain T{i} IN/OUT',f'Z{i} NC thermostat',pts,2,.25,sp)
 for pin,net in [(1,'NC_CHAIN_IN'),(2,'NC_CHAIN_OUT')]:wires.append([r['id'],f'NC_CHAIN.T{i}.{pin}',f'Z{i}.THERMOSTAT.{pin}',net,.25,r['cut_length_mm'],'series safety chain; opens K1 coil; not a GPIO input'])
add_route('BAT_MAIN','POWER','external BMS fuse F0','external power module',[[1250,-850,90],[1410,-850,90],[1600,-820,50]],2,1.5,amps=8)
add_route('USB_DATA','USB','ESP32-S3 native USB','laptop DATA port',[[1600,-820,45],[1470,-620,50],edge_point('O03',1200),[1220,-360,400],[1300,-195,447]],0,0,'O03')
add_route('USB_PD','USB','external USB-C PD SOURCE','laptop power port',[[1600,-845,45],[1480,-630,50],edge_point('O03',1200),[1340,-360,405],[1330,-195,447]],0,0,'O03')
add_route('ARM_PANEL','CONTROL','MCU GPIO / ARM / display','E11 accessible local controller',[[1600,-800,50],[1480,-620,50],edge_point('O02',1200),[1130,-510,355]],6,.14,'O02')

# A back-zone carrier moves when the foam wedge is removed.  Recompute the
# sleeping-mode branch; size each wire for the longer of the two routes.
for d in routes:
 d['active_in_sleep']=d['id'] not in ['HP3','NTC30','NTC31','TH3','USB_DATA','USB_PD']
 ps=[list(q) for q in d['points_mm']]
 if d['id'] in ['HP0','NTC00','NTC01','TH0']:
  x,y,z=ps[-1];a=math.radians(35.2);dx,dz=x-1110,z-120
  end=[1110+math.cos(a)*dx-math.sin(a)*dz,y,120+math.sin(a)*dx+math.cos(a)*dz]
  ps=ps[:3]+chain(d['route_panels'],entry,end[0])[1:]+[end]
 d['points_sleep_mm']=ps
 d['sleep_geometric_length_mm']=round(length(ps),1) if d['active_in_sleep'] else None
 longest=max(length(d['points_mm']),length(ps) if d['active_in_sleep'] else 0)
 d['cut_length_mm']=math.ceil((longest*1.05+230)/10)*10
 d['service_and_termination_allowance_mm']=round(d['cut_length_mm']-longest,1)
 if 'design_current_A' in d:
  d['pair_drop_V_at_20C_assumed']=round(2*.0175*(d['cut_length_mm']/1000)/d['conductor_mm2']*d['design_current_A'],3)
for w in wires:w[5]=next(d['cut_length_mm'] for d in routes if d['id']==w[0])

(OUT/'routes_R02.json').write_text(json.dumps(routes,ensure_ascii=False,indent=2))
with (OUT/'harness_cut_list.csv').open('w',encoding='utf-8-sig',newline='') as f:
 fields=list(dict.fromkeys([k for k in routes[0] if k not in ['points_mm','points_sleep_mm']]+['design_current_A','pair_drop_V_at_20C_assumed']))
 w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(routes)
with (OUT/'wire_termination_list.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['harness','from_pin','to_pin','net','copper_mm2','wire_cut_length_mm','note']);w.writerows(wires)
# CAD routes: actual 3D BREP wires in their own STEP, not a flattened schematic image.
ass=cq.Assembly(name='Lezhandr_R02_harness')
col={'POWER':(.85,.25,.16),'SENSOR':(.16,.37,.73),'SAFETY':(.5,.24,.6),'USB':(.15,.2,.24),'CONTROL':(.2,.65,.42)}
for d in routes:
 unique=[d['points_mm'][0]]
 for p in d['points_mm'][1:]:
  if math.dist(p,unique[-1])>1e-6:unique.append(p)
 wire=cq.Wire.makePolygon([cq.Vector(*p) for p in unique],close=False)
 if not wire.isValid():raise ValueError(d['id'])
 ass.add(wire,name=d['id'],color=cq.Color(*col[d['kind']]))
ass.save(str(OUT/'harness_R02.step'))
sleep_ass=cq.Assembly(name='Lezhandr_R02_harness_sleep')
for d in routes:
 if not d['active_in_sleep']:continue
 unique=[d['points_sleep_mm'][0]]
 for q in d['points_sleep_mm'][1:]:
  if math.dist(q,unique[-1])>1e-6:unique.append(q)
 wire=cq.Wire.makePolygon([cq.Vector(*q) for q in unique],close=False)
 sleep_ass.add(wire,name=d['id'],color=cq.Color(*col[d['kind']]))
sleep_ass.save(str(OUT/'harness_sleep_R02.step'))
# Overlay channel axes on the true unfolded O03/O02 patterns using identical vertex mapping.
for panel,name in [('O03','POWER_CHANNEL'),('O02','SENSOR_CHANNEL')]:
 d=UV[panel];cut=np.array(d['cut']);lo=cut.min(axis=0)-30;hi=cut.max(axis=0)+30;w,h=hi-lo
 doc=ezdxf.readfile(ROOT/'textile/pieces'/f'{panel}.dxf');ms=doc.modelspace()
 pts=[edge_point(panel,x,True) for x in PAN[panel]['stations_mm']]
 # Axes coincide with a seam datum. Sleeve is stitched into its allowance, not through a heater.
 ms.add_lwpolyline(pts,dxfattribs={'layer':'CHANNEL'});doc.saveas(OUT/f'{name}_on_{panel}.dxf')
 def points(v):return ' '.join(f'{x-lo[0]:.2f},{h-(y-lo[1]):.2f}' for x,y in v)
 s=f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.2f}mm" height="{h:.2f}mm" viewBox="0 0 {w:.2f} {h:.2f}"><polygon points="{points(d["cut"])}" fill="#eef1f3" stroke="#253c48" stroke-width=".7"/><polyline points="{points(pts)}" fill="none" stroke="#b75a30" stroke-width="2"/><text x="25" y="18" font-family="sans-serif" font-size="10">{name} / {panel} / 1:1 mm</text></svg>'
 (OUT/f'{name}_on_{panel}.svg').write_text(s)
# Textile sleeves are cut from their measured CAD seam paths, not electrical cable allowance.
rows=[]
for id,panel in [('HC_POWER','O03'),('HC_SENSOR','O02')]:
 ll=length([edge_point(panel,x) for x in PAN[panel]['stations_mm']]);rows.append([id,panel,math.ceil(ll+40),60,40,'10 mm stitch margin per side; two open ends; not a tight drawcord'])
with (OUT/'textile_channel_cut_list.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['id','CAD_datum_panel','cut_length_mm','cut_width_mm','finished_channel_width_mm','note']);w.writerows(rows)
# Coil-chain logic is retained; drawings cannot substitute for external hardware verification.
report={'harnesses':len(routes),'individual_terminated_wires':len(wires),'all_routes_from_CAD_datums':True,'sleep_routes_recomputed':True,'cut_length_basis':'maximum work/sleep length + 5% + 230 mm','all_cut_lengths_ge_geometric':all(d['cut_length_mm']>=d['geometric_length_mm'] for d in routes),
 'minimum_measured_channel_datum_separation_mm':min(math.dist(edge_point('O03',x),edge_point('O02',x)) for x in PAN['O03']['stations_mm']),
 'routing_status':'polyline planning routes; bend radius, shielding, connector SKU, strain relief and wet tests pending',
 'usb':'buy complete shielded USB/PD cables; do not cut these to the CSV length. Select next longer qualified cable.',
 'body_battery_status':'retained R01 battery and power boxes moved outside insulation onto floor; not a hot textile pocket'}
(ROOT/'tests/results/harness_R02.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
