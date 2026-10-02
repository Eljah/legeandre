from pathlib import Path
import json
from shapely.geometry import LineString, Point, box
from shapely.strtree import STRtree
R=Path(__file__).resolve().parents[1]
for file in (R/'electronics').glob('*netgraph.json'):
 d=json.loads(file.read_text());objects=[[],[]];names=[[],[]];nets=[[],[]]
 def add(g,net,name,l):objects[l].append(g);nets[l].append(net);names[l].append(name)
 for part in d['components']:
  for p in part['pads']:
   # Use actual copper extents. THT pin 1 rectangular, others circular.
   g=box(p['x']-p['sx']/2,p['y']-p['sy']/2,p['x']+p['sx']/2,p['y']+p['sy']/2) if p['num']=='1' or not p['drill'] else Point(p['x'],p['y']).buffer(p['sx']/2)
   for l in ([0,1] if p['drill'] else [0]):add(g,p['net'],part['ref']+'.'+p['num'],l)
 for k,(net,l,a,b,w) in enumerate(d['tracks']):
  add(LineString([a,b]).buffer(w/2),net,'track'+str(k),l)
 for k,(net,x,y) in enumerate(d['vias']):
  for l in [0,1]:add(Point(x,y).buffer(.4),net,'via'+str(k),l)
 violations=[]
 for l in [0,1]:
  tree=STRtree(objects[l])
  for i,g in enumerate(objects[l]):
   for j in tree.query(g.buffer(.299)):
    if j<=i or nets[l][i]==nets[l][j]:continue
    dist=g.distance(objects[l][j])
    if dist<.299:violations.append({'layer':l,'a':names[l][i],'b':names[l][j],'net_a':nets[l][i],'net_b':nets[l][j],'clearance_mm':round(dist,4)})
 out={'board':d['name'],'check':'Independent Shapely copper geometry check, min 0.3 mm; NOT KiCad DRC','issues':violations,'unrouted':len(d['unrouted'])}
 (R/'tests/results'/(d['name']+'_geometry_check.json')).write_text(json.dumps(out,indent=2))
 print(d['name'],len(violations),'clearance issues', 'shorts',sum(v['clearance_mm']==0 for v in violations))
