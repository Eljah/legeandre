"""Independent geometric electrical continuity check; not a native KiCad DRC."""
from pathlib import Path
import json
from shapely.geometry import Point,LineString,box
from shapely.strtree import STRtree
R=Path(__file__).resolve().parents[1]
for file in (R/'electronics').glob('*_netgraph.json'):
 d=json.loads(file.read_text());obj=[];bridge={}
 def add(layer,name,net,g):
  i=len(obj);obj.append((layer,name,net,g));bridge.setdefault(name,[]).append(i)
 for c in d['components']:
  for p in c['pads']:
   g=box(p['x']-p['sx']/2,p['y']-p['sy']/2,p['x']+p['sx']/2,p['y']+p['sy']/2) if p['num']=='1' or not p['drill'] else Point(p['x'],p['y']).buffer(p['sx']/2)
   for layer in ([0,1] if p['drill'] else [0]):add(layer,c['ref']+'.'+p['num'],p['net'],g)
 for k,(net,l,a,b,w) in enumerate(d['tracks']):add(l,'track'+str(k),net,LineString([a,b]).buffer(w/2))
 for k,(net,x,y) in enumerate(d['vias']):
  for l in [0,1]:add(l,'via'+str(k),net,Point(x,y).buffer(.4))
 parent=list(range(len(obj)))
 def root(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 def join(i,j):parent[root(j)]=root(i)
 for ids in bridge.values():
  for j in ids[1:]:join(ids[0],j)
 for l in [0,1]:
  ix=[i for i,a in enumerate(obj)if a[0]==l];geoms=[obj[i][3]for i in ix];tree=STRtree(geoms)
  for k,i in enumerate(ix):
   g=obj[i][3]
   for j0 in tree.query(g.buffer(1e-6)):
    j=ix[j0]
    if j>i and obj[j][2]==obj[i][2] and g.distance(obj[j][3])<1e-6:join(i,j)
 nets={}
 for i,(_,name,net,g) in enumerate(obj):nets.setdefault(net,set()).add(root(i))
 bad={n:len(v)for n,v in nets.items()if len(v)>1}
 out={'board':d['name'],'method':'copper geometry continuity including plated holes/vias, 1e-6 mm tolerance; NOT KiCad DRC','nets':len(nets),'disconnected_nets':bad}
 (R/'tests/results'/(d['name']+'_connectivity.json')).write_text(json.dumps(out,indent=2));print(d['name'],out)
 if bad:raise SystemExit(1)
