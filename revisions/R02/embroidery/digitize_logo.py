#!/usr/bin/env python3
"""Approved raster segmentation -> editable vector areas -> actual machine stitches.
Deterministic tatami fill, edge-run underlay, alternating row phase, tie-ins,
tie-offs and trim/jump commands. Requires a physical sew-out; not a production
certification. Native edit sources: logo_objects.svg, logo_manual_stitches.svg.
"""
from pathlib import Path
import csv,json,math
import numpy as np,cv2
from shapely.geometry import Polygon,LineString,MultiPolygon,Point
from shapely.affinity import scale,rotate
from PIL import Image,ImageDraw
from machine_formats import write_dst,write_exp,read_dst,read_exp
ROOT=Path(__file__).resolve().parent
Z=np.load(ROOT/'source/logo_segments.npz');labels=Z['labels'];mask=Z['mask'];pal=Z['palette']
H,W=labels.shape;WIDTH=160.;FACTOR=WIDTH/W;HEIGHT=H*FACTOR
# Thread sequence: light fills, warm fills, gray, dark outlines, navy wordmark last.
ORDER=[0,7,5,6,1,2,3,4]
NAMES=['Ivory / слоновая кость','Skin light / светлый телесный','Warm tan / песочный','Brown / коричневый',
       'Light gray / светло-серый','Dark gray / тёмно-серый','Charcoal / угольный','Navy / синий']
colors=[tuple(map(int,pal[k])) for k in ORDER]
commands=[];blocks=[];objects=[];last=np.array([0.,0.]);color=0

def polygons(k):
 binary=((labels==k)&(mask>0)).astype(np.uint8)
 contours,hierarchy=cv2.findContours(binary,cv2.RETR_CCOMP,cv2.CHAIN_APPROX_SIMPLE)
 if hierarchy is None:return []
 arr=[];hh=hierarchy[0]
 for i,c in enumerate(contours):
  if hh[i][3]!=-1 or len(c)<3:continue
  outer=c[:,0,:]*FACTOR;holes=[];child=hh[i][2]
  while child!=-1:
   cc=contours[child][:,0,:]
   if len(cc)>=3:holes.append(cc*FACTOR)
   child=hh[child][0]
  p=Polygon(outer,holes).buffer(0).simplify(.12,preserve_topology=True)
  for g in (list(p.geoms) if p.geom_type=='MultiPolygon' else [p]):
   if g.geom_type=='Polygon' and g.area>=1.8:arr.append(g)
 return sorted(arr,key=lambda p:-p.area)

def add(cmd,p=None):
 global last
 if p is not None:last=np.array(p,float)
 commands.append((cmd,float(last[0]-WIDTH/2),float(last[1]-HEIGHT/2),color))

def move(p):add('J',p)
def line_to(p,step=3.2):
 p=np.array(p,float);dist=np.linalg.norm(p-last)
 n=max(1,math.ceil(dist/step));start=last.copy()
 for i in range(1,n+1):add('S',start+(p-start)*i/n)

def tie(p,nextp):
 p=np.array(p);d=np.array(nextp)-p;dist=np.linalg.norm(d)
 if dist<.01:d=np.array([.5,0])
 else:d*=min(.6,dist/2)/dist
 move(p);add('S',p);add('S',p+d);add('S',p);add('S',p+d/2)

def ring_path(ring):
 pts=list(ring.coords)
 if len(pts)<2:return
 tie(pts[0],pts[1]);start=len(commands)-4
 for p in pts[1:]:line_to(p,2.8)
 add('T');blocks.append((color,start,len(commands)-1))

def tatami(p,rowspacing=.43,angle=0):
 from scipy.spatial import cKDTree
 if p.is_empty:return
 if p.geom_type=='MultiPolygon':
  for sub in p.geoms:tatami(sub,rowspacing,angle)
  return
 q=rotate(p,-angle,origin=(0,0));a=math.radians(angle);c=math.cos(a);sn=math.sin(a)
 world=lambda xy:np.array([xy[0]*c-xy[1]*sn,xy[0]*sn+xy[1]*c])
 x0,y0,x1,y1=q.bounds;spans=[]
 for row,y in enumerate(np.arange(y0+rowspacing/2,y1,rowspacing)):
  g=q.intersection(LineString([(x0-2,y),(x1+2,y)]))
  segs=[g] if g.geom_type=='LineString' else [v for v in getattr(g,'geoms',[]) if v.geom_type=='LineString']
  for seg in segs:
   if seg.length>=.35:spans.append((world(seg.coords[0]),world(seg.coords[-1]),row))
 if not spans:return
 # Nearest unsewn span ordering: completes one branch before jumping to another.
 # This avoids a trim on every row adjacent to a hole in a dog/letter silhouette.
 endpoints=np.array([v for aa,bb,row in spans for v in (aa,bb)])
 tree=cKDTree(endpoints);used=np.zeros(len(spans),bool);left=len(spans);blockstart=None
 rings=[LineString(r.coords) for r in [p.exterior,*p.interiors]]
 while left:
  k=min(12,len(endpoints));chosen=None
  while chosen is None:
   dist,inds=tree.query(last,k=k)
   for ind in np.atleast_1d(inds):
    if not used[int(ind)//2]:chosen=int(ind);break
   if chosen is None:k=min(len(endpoints),k*2)
  si,reverse=divmod(chosen,2);used[si]=True;left-=1
  aa,bb,row=spans[si];A,B=(bb,aa) if reverse else (aa,bb)
  connected=False
  if blockstart is not None:
   connector=LineString([last,A])
   if np.linalg.norm(last-A)<=4.0 and p.buffer(.04).covers(connector):line_to(A,2.0);connected=True
   else:
    for ln in rings:
     if ln.distance(Point(last))<.15 and ln.distance(Point(A))<.15:
      t0,t1=ln.project(Point(last)),ln.project(Point(A));L=ln.length
      forward=(t1-t0)%L;backward=(t0-t1)%L;distance=min(forward,backward);direction=1 if forward<=backward else -1
      if distance<15:
       for step in np.linspace(0,distance,max(2,math.ceil(distance/2)+1))[1:]:
        qpt=ln.interpolate((t0+direction*step)%L);line_to([qpt.x,qpt.y],2.0)
       line_to(A,2.0);connected=True;break
   if not connected and np.linalg.norm(last-A)<=7:move(A);add('S',A);connected=True
  if not connected:
   if blockstart is not None:add('T');blocks.append((color,blockstart,len(commands)-1))
   tie(A,B);blockstart=len(commands)-4
  length=float(np.linalg.norm(B-A));direction=(B-A)/length;phase=(row%3+1)*.8
  for d in np.arange(phase,length,3.):line_to(A+direction*d,3.2)
  line_to(B,3.2)
 if blockstart is not None:
  if len(commands)>2:
   pre=np.array([commands[-2][1]+WIDTH/2,commands[-2][2]+HEIGHT/2]);end=last.copy();dv=pre-end;ln=np.linalg.norm(dv)
   if ln>.2:dv*=min(.5,ln)/ln;add('S',end+dv);add('S',end)
  add('T');blocks.append((color,blockstart,len(commands)-1))

def svg_path(p):
 out=[]
 for ring in [p.exterior,*p.interiors]:
  pts=list(ring.coords);out.append('M '+' L '.join(f'{x:.3f},{y:.3f}' for x,y in pts)+' Z')
 return ' '.join(out)

for color,k in enumerate(ORDER):
 if color:add('C')
 ps=polygons(k)
 for i,p in enumerate(ps):
  # Small compensation is explicit and adjustable, and requires fabric-specific sew-out.
  p=p.buffer(.10,join_style=1).simplify(.07)
  angle=[20,-20,35,-35,15,-15,0,0][color]
  objects.append({'color':color,'geometry':p,'angle':angle})
  # Edge-run underlay. Large areas get a sparse tatami underlay before top fill.
  inner=p.buffer(-.6)
  if inner.geom_type=='Polygon' and inner.area>6:ring_path(inner.exterior)
  if p.area>120:tatami(p.buffer(-.7),2.0,angle+90)
  tatami(p,.43,angle)
add('E')

cmds=write_dst(commands,ROOT/'machine/Spim_s_haski_160mm.dst')
write_exp(commands,ROOT/'machine/Spim_s_haski_160mm.exp')
roundtrips={}
expected=[(x,y,c) for cmd,x,y,c in cmds if cmd=='S']
for name,reader in [('dst',read_dst),('exp',read_exp)]:
 rr=reader(ROOT/f'machine/Spim_s_haski_160mm.{name}');got=[(x,y,c) for cmd,x,y,c in rr if cmd=='S']
 assert got==expected,(name,len(got),len(expected))
 assert sum(cmd=='C' for cmd,x,y,c in rr)==7
 roundtrips[name]={'read_back_ok':True,'needle_positions_identical':True,'needle_penetrations':len(got),'color_changes':7}

# Editable regions, suitable as input to Inkscape + Ink/Stitch; no embedded bitmap.
svg=[f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkstitch="http://inkstitch.org/namespace" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" width="{WIDTH}mm" height="{HEIGHT:.3f}mm" viewBox="0 0 {WIDTH} {HEIGHT:.3f}"><title>Спим с хаски — traced approved logo</title>']
for ci,rgb in enumerate(colors):
 hexcol='#%02x%02x%02x'%rgb;svg.append(f'<g id="thread_{ci+1}" inkscape:groupmode="layer" inkscape:label="{ci+1:02} {NAMES[ci]}">')
 for i,o in enumerate(objects):
  if o['color']==ci:svg.append(f'<path id="region_{i}" d="{svg_path(o["geometry"])}" fill="{hexcol}" fill-rule="evenodd" inkstitch:fill_method="auto_fill" inkstitch:row_spacing_mm="0.43" inkstitch:max_stitch_length_mm="3.2" inkstitch:angle="{o["angle"]}"/>')
 svg.append('</g>')
svg.append('</svg>');(ROOT/'logo_objects.svg').write_text('\n'.join(svg))
# Manual stitch project records actual needle positions and jump breaks from normalized commands.
svg=[f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkstitch="http://inkstitch.org/namespace" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" width="{WIDTH}mm" height="{HEIGHT:.3f}mm" viewBox="0 0 {WIDTH} {HEIGHT:.3f}"><title>Спим с хаски — exact manual stitches</title>']
for ci,rgb in enumerate(colors):
 svg.append(f'<g id="needle_{ci+1}" inkscape:groupmode="layer" inkscape:label="{ci+1:02} {NAMES[ci]}">');chunk=[];n=0
 def flush():
  global chunk,n
  if len(chunk)>1:
   d='M '+' L '.join(f'{x/10+WIDTH/2:.3f},{y/10+HEIGHT/2:.3f}' for x,y in chunk)
   svg.append(f'<path id="stitch_{ci}_{n}" d="{d}" fill="none" stroke="#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}" stroke-width=".24" inkstitch:stroke_method="manual_stitch" inkstitch:trim_after="false"/>');n+=1
  chunk=[]
 for cmd,x,y,col in cmds:
  if col!=ci:continue
  if cmd=='S':chunk.append((x,y))
  elif cmd in ('T','C','J','E'):flush()
 flush();svg.append('</g>')
svg.append('</svg>');(ROOT/'logo_manual_stitches.svg').write_text('\n'.join(svg))

# Draw preview ONLY from the decoded DST, after the binary roundtrip.
rr=read_dst(ROOT/'machine/Spim_s_haski_160mm.dst');pixels=8
im=Image.new('RGB',(int((WIDTH+8)*pixels),int((HEIGHT+8)*pixels)),(250,250,247));draw=ImageDraw.Draw(im);prev=(0,0)
for cmd,x,y,col in rr:
 xy=((x/10+WIDTH/2+4)*pixels,(y/10+HEIGHT/2+4)*pixels)
 if cmd=='S':draw.line([prev,xy],fill=colors[col],width=2)
 prev=xy
im.save(ROOT/'preview_from_DST.png')
with (ROOT/'stitches.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['index','command','x_mm_centered','y_mm_centered','thread_index'])
 for i,(cmd,x,y,col) in enumerate(cmds):w.writerow([i,cmd,x/10,y/10,col+1])
with (ROOT/'threadlist.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['sequence','name','RGB','needle_penetrations','stitched_length_m_approx','catalog'])
 for ci,rgb in enumerate(colors):
  ll=0.;lastxy=np.array([0,0])
  for cmd,x,y,col in cmds:
   xy=np.array([x,y])
   if cmd=='S' and col==ci:ll+=np.linalg.norm(xy-lastxy)/10000
   lastxy=xy
  w.writerow([ci+1,NAMES[ci],'#%02x%02x%02x'%rgb,sum(cmd=='S' and col==ci for cmd,x,y,col in cmds),round(ll,2),'Select physical thread by sample; no invented catalog ID'])
S=np.array([(x,y) for cmd,x,y,col in cmds if cmd=='S'])/10
report={'source':'approved_logo_crop.png from prior user-approved generated sheet','nominal_width_mm':WIDTH,'actual_sewn_bbox_mm':(S.max(axis=0)-S.min(axis=0)).tolist(),
        'thread_colors':8,'color_changes':7,'vector_regions':len(objects),'needle_penetrations':len(expected),'trim_requests':sum(c[0]=='T' for c in cmds),
        'max_stitch_length_limit_mm':3.5,'tatami_row_spacing_mm':.43,'compensation_mm':.10,'hoop_required':'usable field at least 170 x 175 mm; nominal 200 x 200 only if machine supports it',
        'roundtrip':roundtrips,'physical_sew_out_performed':False,'formats':['DST','EXP'],'inkstitch_extension_executed':False,
        'notice':'Binary files produced by supplied deterministic digitizer/codec, not by renaming an image. Inkscape SVG edit sources included. DST trim behavior and colors require machine setup.'}
(ROOT/'embroidery_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
