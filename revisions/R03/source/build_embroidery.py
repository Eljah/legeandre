#!/usr/bin/env python3
"""Object-based redigitizing of the approved logo, mm units.
Real tatami, edge/mesh underlay, rail-to-rail satin, centre/zigzag underlay.
Not a raster-to-stitch converter; semantic paths live in artwork.py.
"""
from pathlib import Path
import re, math, json, csv, sys
import numpy as np
from shapely.geometry import Polygon, LineString, Point, MultiPolygon, GeometryCollection
from shapely import affinity
from shapely.ops import unary_union, substring
from lxml import etree as ET
from PIL import Image,ImageDraw,ImageFont
from artwork import F,S,PALETTE
import machine_formats as mf
ROOT=Path(__file__).resolve().parents[1]
MM=.215; OFF=np.array([8.,6.]); W=144.; H=159.
NS='http://www.w3.org/2000/svg'; INK='http://www.inkscape.org/namespaces/inkscape'; ST='http://inkstitch.org/namespace'
for p in ['machine','previews','docs','tests']: (ROOT/p).mkdir(exist_ok=True)
def parse_path(s,scale=MM,offset=OFF):
    toks=re.findall(r'[MLCQZ]|[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',s)
    i=0; result=[]; points=[]; p=np.zeros(2);start=None
    def num(n):
        nonlocal i
        a=np.array([float(v) for v in toks[i:i+n]]);i+=n;return a
    while i<len(toks):
        cmd=toks[i];i+=1
        if cmd=='M':
            if points:result.append(np.array(points)*scale+offset)
            p=num(2);start=p.copy();points=[p.copy()]
        elif cmd=='L':p=num(2);points.append(p.copy())
        elif cmd in ('C','Q'):
            q=num(6 if cmd=='C' else 4).reshape(-1,2)
            n=max(8,int(sum(np.linalg.norm(b-a) for a,b in zip([p]+list(q[:-1]),q))*scale/.22))
            for t in np.linspace(0,1,n+1)[1:]:
                if cmd=='C':v=(1-t)**3*p+3*(1-t)**2*t*q[0]+3*(1-t)*t*t*q[1]+t**3*q[2]
                else:v=(1-t)**2*p+2*(1-t)*t*q[0]+t*t*q[1]
                points.append(v)
            p=q[-1]
        elif cmd=='Z':
            if np.linalg.norm(points[-1]-start)>1e-9:points.append(start.copy())
            p=start.copy()
        else:raise ValueError(cmd)
    if points:result.append(np.array(points)*scale+offset)
    return result

def polyparts(g):
    if g.is_empty:return []
    if g.geom_type=='Polygon':return [g]
    if hasattr(g,'geoms'):return [p for a in g.geoms for p in polyparts(a)]
    return []
def lineparts(g):
    if g.is_empty:return []
    if g.geom_type in ('LineString','LinearRing'):return [LineString(g)]
    if hasattr(g,'geoms'):return [p for a in g.geoms for p in lineparts(a)]
    return []
def resample(pts,step):
    l=pts if isinstance(pts,LineString) else LineString(pts)
    if l.length<.01:return np.array(l.coords)
    return np.array([l.interpolate(d).coords[0] for d in np.linspace(0,l.length,max(2,math.ceil(l.length/step)+1))])
def pathline(a,close=False):
    return 'M '+' L '.join(f'{x:.4f},{y:.4f}' for x,y in a)+(' Z' if close else '')
def pathpoly(g):
    return ' '.join(pathline(p.exterior.coords,True)+' '+' '.join(pathline(r.coords,True) for r in p.interiors) for p in polyparts(g))
# Assemble vector regions and remove hidden stitching with 0.22 mm registered underlap.
raw=[Polygon(parse_path(f['path'])[0]).buffer(0) for f in F]
future=[unary_union(raw[i+1:]) for i in range(len(raw))]
fillobjs=[]; outlineobjs=[]
for i,f in enumerate(F):
    visible=raw[i].difference(future[i].buffer(-.22)).buffer(0)
    for j,p in enumerate(polyparts(visible)):
        if p.area>.32:
            fillobjs.append(dict(**f,id2=f['id']+f'_{j}',geom=p,owner=i,kind='tatami'))
ids={f['id']:i for i,f in enumerate(F)}
for s in S:
    line=LineString(parse_path(s['path'])[0])
    owner=ids.get(s['id'][:-5]) if s['id'].endswith('_edge') else None
    if owner is not None:
        # Stitch only visible sections of the old silhouette; never draw a back dog through the face.
        line=line.difference(future[owner].buffer(.10))
    for j,l in enumerate(lineparts(line)):
        if l.length>.35:
            outlineobjs.append(dict(**s,id2=s['id']+f'_{j}',geom=l,kind='satin'))
# Lettering is built from actual narrow satin columns, not tatami-filled font outlines.
def addcol(name,points,width=1.60,color='navy',scale=1,offset=(0,0)):
    a=parse_path(points,scale,np.array(offset))[0]
    outlineobjs.append(dict(id=name,id2=name,color=color,width=width,geom=LineString(a),kind='satin'))
GLYPHS={
 'С':['M 7.5 1.0 C 4.5 -1.0 0 0.5 0 5 C 0 9.5 4.5 11 7.5 9'],
 'п':['M 0 10 L 0 1.5 Q 4 -.5 7.5 1.5 L 7.5 10'],
 'и':['M 0 .8 L 0 10 L 7.5 .8 L 7.5 10'],
 'м':['M 0 10 L 0 .8 L 4 7 L 8 .8 L 8 10'],
 'с':['M 7.2 1.4 C 3.5 -1 0 1.2 0 5.3 C 0 9.4 4 11 7.2 8.8'],
 'х':['M 0 .8 L 7.5 10','M 7.5 .8 L 0 10'],
 'а':['M 7 3 C 4 -1.5 0 1.0 0 5.5 C 0 10.5 5 11.5 7 7','M 7 1.0 L 7 10'],
 'к':['M 0 .8 L 0 10','M 7.5 .8 L .3 5.5 L 7.5 10'],
}
x=18.0
for k,ch in enumerate('Спим с хаски'):
    if ch==' ':x+=4;continue
    dy=-2.0*((x+4-72)/54)**2
    for j,p in enumerate(GLYPHS[ch]):addcol(f'letter_{k}_{ch}_{j}',p,1.65,offset=(x,138+dy))
    x+=10.0
# Paw marks beside caption, sewn in satin columns.
for side,cx in [('left',10),('right',132)]:
    addcol('caption_paw_'+side,f'M {cx-1} 143 Q {cx} 141 {cx+1} 143',2.2)
    for k,(dx,dy) in enumerate([(-2.5,-2),(-.8,-3.2),(1,-3),(2.7,-1.8)]):
        addcol('caption_toe_'+side+str(k),f'M {cx+dx} {141+dy} L {cx+dx+.1} {141+dy+.6}',.85)
# A satin sewn perimeter, NOT a Merrow overlocked edge. Twill is the ground.
BORDER='M 19 3.5 L 125 3.5 C 135 3.5 140.5 10 140.5 20 L 140.5 139 C 140.5 151 131 155.5 120 155.5 L 24 155.5 C 13 155.5 3.5 151 3.5 139 L 3.5 20 C 3.5 10 9 3.5 19 3.5 Z'
addcol('patch_satin_border',BORDER,2.8)
borderobj=outlineobjs.pop()
# Semantic color order. Each fill is clipped against objects in front, preventing blanket full coverage.
COLOR_ORDER=['navy','charcoal','gray','brown','tan','skin','ivory','coral']
objects=[]
for col in COLOR_ORDER:
    objects.extend([o for o in fillobjs if o['color']==col])
# Decoration in colour blocks, then continuous navy lettering and perimeter last.
for col in ['tan','brown','coral','charcoal','navy']:
    objects.extend([o for o in outlineobjs if o['color']==col])
objects.append(borderobj)
# The underlay and top stitch functions return contiguous needle paths.
def subdivide(a,b,maxlen=3.0):
    n=max(1,math.ceil(np.linalg.norm(np.array(b)-a)/maxlen))
    return [np.array(a)+(np.array(b)-a)*t/n for t in range(1,n+1)]
def boundary_route(poly,start,end):
    """Buried contour travel along the nearest shared boundary, not jumps on every row."""
    a=np.asarray(start);b=np.asarray(end)
    if poly.buffer(.04).covers(LineString([a,b])):
        return np.array([a]+subdivide(a,b,2.8))
    best=None
    for pg in polyparts(poly):
        for ring in [pg.exterior,*pg.interiors]:
            r=LineString(ring.coords)
            if r.distance(Point(a))>1.15 or r.distance(Point(b))>1.15:continue
            da=r.project(Point(a));db=r.project(Point(b));L=r.length
            lo,hi=sorted((da,db))
            mid=np.array(substring(r,lo,hi).coords)
            endseg=np.array(substring(r,hi,L).coords)
            startseg=np.array(substring(r,0,lo).coords)
            alt=np.vstack([endseg,startseg[1:]])
            choices=[mid,alt[::-1]] if da<=db else [mid[::-1],alt]
            for ch in choices:
                arr=np.vstack([a,ch,b]);length=np.sum(np.linalg.norm(np.diff(arr,axis=0),axis=1))
                if best is None or length<best[0]:best=(length,arr)
    if best is None or best[0]>max(14,math.dist(a,b)*4):return None
    curve=LineString(best[1]).simplify(.08)
    result=[np.array(curve.coords[0])]
    for p in np.array(curve.coords)[1:]:
        if np.linalg.norm(p-result[-1])<.28:continue
        result.extend(subdivide(result[-1],p,2.8))
    if np.linalg.norm(result[-1]-b)>.05:result.append(b)
    return np.array(result)

def tatami_paths(poly,angle,pitch=.42,stitchlen=3.0):
    rot=affinity.rotate(poly,-angle,origin=(0,0)); mnx,mny,mxx,mxy=rot.bounds
    rows=[]; rownum=0
    for y in np.arange(mny+pitch/2,mxy,pitch):
        segments=sorted(lineparts(rot.intersection(LineString([(mnx-1,y),(mxx+1,y)]))),key=lambda l:l.bounds[0])
        if rownum%2:segments.reverse()
        for seg in segments:
            a,b=seg.bounds[0],seg.bounds[2]
            if b-a<.3:continue
            phase=(rownum%4)*stitchlen/4
            grid=np.arange(math.floor((a-phase)/stitchlen)*stitchlen+phase,b,stitchlen)
            xs=[a]+[v for v in grid if v>a+.3 and v<b-.3]+[b]
            if rownum%2:xs=xs[::-1]
            arr=np.array([[xx,y] for xx in xs]);th=math.radians(angle)
            arr=arr@np.array([[math.cos(th),math.sin(th)],[-math.sin(th),math.cos(th)]])
            rows.append(arr)
        rownum+=1
    # Connect within the same shape only. Outside travel must be jumped/trimmed.
    result=[];current=[]
    for arr in rows:
        route=boundary_route(poly,current[-1],arr[0]) if current else None
        if current and route is not None:
            current.extend(route[1:]);current.extend(arr[1:])
        else:
            if current:result.append(np.array(current))
            current=list(arr)
    if current:result.append(np.array(current))
    return result

def rails(line,step,width):
    a=resample(line,step)
    # Avoid winding fine corners with identical penetrations: averaged local tangents.
    t=np.gradient(a,axis=0);norm=np.linalg.norm(t,axis=1);norm[norm<1e-9]=1
    n=np.column_stack([-t[:,1],t[:,0]])/norm[:,None]
    left=a+n*(width/2);right=a-n*(width/2)
    return a,left,right

def object_paths(o):
    paths=[]
    if o['kind']=='tatami':
        g=o['geom']
        # Project-specific compensation 0.16 mm. Avoid flooding holes and superimposed fills.
        g=g.buffer(.16,join_style=1)
        inset=g.buffer(-.75)
        for p in polyparts(inset):
            if p.area>6:
                paths.append(('edge_underlay',resample(LineString(p.exterior.coords),2.2)))
        if g.area>35:
            for p in tatami_paths(g.buffer(-.65),o['angle']+90,1.8,3.4):paths.append(('mesh_underlay',p))
        for p in tatami_paths(g,o['angle'],.42,3.0):paths.append(('tatami',p))
    else:
        line=o['geom'];w=o['width'];length=line.length
        a,L,R=rails(line,.20,w+.24)
        ctr=resample(line,1.8)
        paths.append(('center_underlay',np.concatenate([ctr,ctr[-2::-1]])))
        if w>=2.4:
            ca,ll,rr=rails(line,1.1,max(.8,w-1))
            under=np.array([ll[i] if i%2==0 else rr[i] for i in range(len(ca))])
            paths.append(('zigzag_underlay',under))
        # A true satin is one full rail-to-rail stitch per penetration, not short raster fill.
        top=np.array([L[i] if i%2==0 else R[i] for i in range(len(a))])
        paths.append(('satin',top))
    return paths

# Export editable object geometry. Paths are in physical mm, no fonts are embedded.
def svgroot():return ET.Element('{'+NS+'}svg',nsmap={None:NS,'inkscape':INK,'inkstitch':ST},width=f'{W}mm',height=f'{H}mm',viewBox=f'0 0 {W} {H}')
sv=svgroot(); title=ET.SubElement(sv,'{'+NS+'}title');title.text='Спим с хаски — R03: ручная объектная оцифровка'
meta=ET.SubElement(sv,'{'+NS+'}metadata');meta.text='Tatami .42 mm / 3.0 mm; satin .40 mm peak-to-peak, +.12 mm per side; trial sew-out required. Source retains semantic rails and filled areas.'
plain=svgroot()
# Preview substrate is a non-embroidery element only in the display copy.
ET.SubElement(plain,'{'+NS+'}rect',x='0',y='0',width=str(W),height=str(H),fill='#f8f6ee')
for k,o in enumerate(objects):
    color=PALETTE[o['color']][0]
    group=ET.SubElement(sv,'{'+NS+'}g',id=f'obj{k:03d}');group.set('{'+INK+'}label',f'{k+1:03d} {o["id2"]} [{o["kind"]}]')
    p=ET.SubElement(group,'{'+NS+'}path',id=f'p{k:03d}')
    if o['kind']=='tatami':
        d=pathpoly(o['geom']);p.set('d',d);p.set('style',f'fill:{color};stroke:none;fill-rule:evenodd')
        for name,value in [('fill_method','auto_fill'),('angle',o['angle']),('row_spacing_mm',.42),('max_stitch_length_mm',3),('fill_underlay','true'),('fill_underlay_row_spacing_mm',1.8),('fill_underlay_angle',o['angle']+90)]:p.set('{'+ST+'}'+name,str(value))
        ET.SubElement(plain,'{'+NS+'}path',d=d,fill=color,**{'fill-rule':'evenodd'})
    else:
        a,L,R=rails(o['geom'],.9,o['width'])
        p.set('d',pathline(L)+' '+pathline(R));p.set('style',f'fill:none;stroke:{color};stroke-width:.15')
        for name,value in [('satin_column','true'),('zigzag_spacing_mm',.4),('pull_compensation_mm',.12),('center_walk_underlay','true'),('zigzag_underlay','true' if o['width']>=2.4 else 'false')]:p.set('{'+ST+'}'+name,str(value))
        ET.SubElement(plain,'{'+NS+'}path',d=pathline(o['geom'].coords),fill='none',stroke=color,**{'stroke-width':str(o['width']+.24),'stroke-linecap':'round','stroke-linejoin':'round'})
    p.set('{'+ST+'}trim_after','true')
ET.ElementTree(sv).write(str(ROOT/'Spim_s_haski_R03_editable.svg'),encoding='utf-8',xml_declaration=True)
ET.ElementTree(plain).write(str(ROOT/'previews/logo_vector.svg'),encoding='utf-8',xml_declaration=True)

# Generate with object metadata, colour blocks and safe jump decisions.
commands=[];segmentmeta=[];current=None;ci=-1;active=None;colorblocks=[];stats=[]
def emit(cmd,p,tag,oid):
    new=(cmd,float(p[0])-W/2,float(p[1])-H/2,ci)
    if cmd=='S' and commands and commands[-1][0]=='S' and all(round(commands[-1][k]*10)==round(new[k]*10) for k in (1,2)):
        return
    commands.append(new)
    segmentmeta.append((tag,oid))
def sew_path(arr,tag,o):
    global current
    if len(arr)<2:return
    arr=np.array(arr)
    # remove repeated points, including duplicates introduced at path closure.
    arr=arr[np.r_[True,np.linalg.norm(np.diff(arr,axis=0),axis=1)>.08]]
    if len(arr)<2:return
    start=arr[0]
    dist=np.linalg.norm(start-current) if current is not None else float('inf')
    # Only within same object's body can a short sewn travel be buried safely.
    route=boundary_route(o['geom'].buffer(.18),current,start) if current is not None and o['kind']=='tatami' else None
    if current is not None and o['kind']=='satin' and dist<3 and o['geom'].buffer(o['width']/2+.14).covers(LineString([current,start])):
        route=np.array([current]+subdivide(current,start,2.8))
    if route is not None:
        for p in route[1:]:emit('S',p,'buried_travel',o['id2'])
    else:
        if current is not None:emit('T',current,'trim',o['id2'])
        emit('J',start,'jump',o['id2'])
        # A small forward-back lock into the path, not a fixed knot at one point.
        v=arr[1]-start;v=v/max(np.linalg.norm(v),1e-9)*min(.55,np.linalg.norm(v))
        for p in [start,start+v,start+v*.15,start+v]:emit('S',p,'tie_in',o['id2'])
    for p in arr[1:]:emit('S',p,tag,o['id2'])
    current=arr[-1]
for o in objects:
    if active!=o['color']:
        if active is not None:emit('C',current,'color_change',o['id2'])
        ci+=1;active=o['color'];colorblocks.append(dict(block=ci+1,color=active,hex=PALETTE[active][0],name=PALETTE[active][1]))
        current=None
    n0=len(commands)
    paths=object_paths(o)
    for tag,arr in paths:sew_path(arr,tag,o)
    if current is not None:
        # Tie-off along last stitch direction, minimum excursion .45 mm.
        a=paths[-1][1];v=a[-1]-a[-2];v=v/max(np.linalg.norm(v),1e-9)*min(.5,np.linalg.norm(v))
        for p in [current-v,current-v*.2,current]:emit('S',p,'tie_off',o['id2'])
    stats.append(dict(index=len(stats)+1,id=o['id2'],kind=o['kind'],color=active,block=ci+1,stitches=sum(c[0]=='S' for c in commands[n0:]),area_mm2=round(o['geom'].area,2) if o['kind']=='tatami' else None,length_mm=round(o['geom'].length,2) if o['kind']=='satin' else None,width_mm=o.get('width'),angle=o.get('angle')))
if current is not None:emit('T',current,'trim','end');emit('E',current,'end','end')
# Store actual machine commands separately from generated stitch metadata.
pathdst=ROOT/'machine/Spim_s_haski_R03_140x156.dst';pathexp=ROOT/'machine/Spim_s_haski_R03_140x156.exp'
normalized=mf.write_dst(commands,pathdst,'SPIM_HASKI_R03');mf.write_exp(commands,pathexp)
A=mf.read_dst(pathdst);B=mf.read_exp(pathexp)
ss=lambda a:[c for c in a if c[0]=='S']
assert ss(A)==ss(B), 'DST/EXP readback mismatch'
assert ss(A)==ss(normalized), 'Encoding altered needle points'
assert len([c for c in A if c[0]=='C'])==len(colorblocks)-1
with (ROOT/'source/stitch_plan.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f);w.writerow(['command','x_mm','y_mm','color_block_zero_based','stitch_type','object'])
    for c,m in zip(commands,segmentmeta):w.writerow([*c,*m])
with (ROOT/'source/objects.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=list(stats[0]));w.writeheader();w.writerows(stats)
with (ROOT/'machine/thread_sequence.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=list(colorblocks[0])+['needle_points']);w.writeheader()
    for b in colorblocks:w.writerow(dict(**b,needle_points=sum(c[0]=='S' and c[3]==b['block']-1 for c in normalized)))
# Decode preview strictly from the delivered DST, not an imaginary textile photograph.
def decoded_preview(records,path,pxmm=10,thread_width=.22):
    im=Image.new('RGB',(round(W*pxmm),round(H*pxmm)), '#F8F6EE');d=ImageDraw.Draw(im)
    last=(W/2*pxmm,H/2*pxmm)
    for cmd,x,y,col in records:
        p=((x/10+W/2)*pxmm,(y/10+H/2)*pxmm)
        if cmd=='S':
            color=colorblocks[min(col,len(colorblocks)-1)]['hex']
            d.line([last,p],fill=color,width=max(1,round(thread_width*pxmm)))
        if cmd in ('S','J'):last=p
    im.save(path)
decoded_preview(A,ROOT/'previews/decoded_DST_paths.png',pxmm=12,thread_width=.12)
decoded_preview(A,ROOT/'previews/decoded_DST.png',pxmm=12,thread_width=.36)
xs=[c[1]/10 for c in A if c[0]=='S'];ys=[c[2]/10 for c in A if c[0]=='S']
lengths=[];last=(0,0)
for cmd,x,y,col in A:
    if cmd=='S':lengths.append(math.dist(last,(x,y))/10)
    if cmd in ('S','J'):last=(x,y)
from collections import Counter
counts=Counter(m[0] for c,m in zip(commands,segmentmeta) if c[0]=='S')
consecutive_zero=sum(A[i][0]=='S' and A[i-1][0]=='S' and A[i][1:3]==A[i-1][1:3] for i in range(1,len(A)))
assert consecutive_zero==0
report=dict(consecutive_duplicate_needles=consecutive_zero,design='Спим с хаски R03',method='manual semantic object redigitizing; custom Python engine, Inkscape-compatible SVG; no physical sewout',needle_points=len(ss(A)),colors=len(PALETTE),color_blocks=len(colorblocks),color_changes=len(colorblocks)-1,trim_requests=sum(c[0]=='T' for c in commands),dimensions_mm=[round(max(xs)-min(xs),1),round(max(ys)-min(ys),1)],tatami_objects=sum(o['kind']=='tatami' for o in objects),satin_columns=sum(o['kind']=='satin' for o in objects),stitch_types=dict(counts),max_stitch_mm=round(max(lengths),4),zero_length_points=sum(l<.01 for l in lengths),percent_under_0_3mm=round(sum(l<.3 for l in lengths)/len(lengths)*100,2),DST_EXP_identical_needle_points=True,row_spacing_mm=.42,tatami_max_stitch_mm=3,satin_peak_to_peak_mm=.4,satin_width_compensation_per_side_mm=.12,physical_sewout=False,inkstitch_engine_executed=False)
(ROOT/'tests/validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
