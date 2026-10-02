#!/usr/bin/env python3
"""Unfold the exported CAD sewing mid-surfaces, then add seam allowances.
No image tracing and no fake nesting. DXF layers: CUT/SEW/NOTCH/GRAIN/ID/CHANNEL.
The geometry source of truth is cad/sewing_surfaces.json (exported by CadQuery).
Rigid triangle unfolding is exact for these boundary-only strips; the smooth
fabric shape after sewing still requires a toile because material mechanics
and seam bulk are not simulated.
"""
from pathlib import Path
import json,csv,math,copy
from collections import defaultdict
import numpy as np
from shapely.geometry import Polygon,LineString
from shapely.affinity import rotate,translate
import ezdxf
import cv2
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'textile'
D=json.loads((ROOT/'cad/sewing_surfaces.json').read_text());RESULT={}

def cross(a,b):return float(a[0]*b[1]-a[1]*b[0])
def intersect(a,b,ra,rb,other=None,first=False):
 delta=b-a;d=float(np.linalg.norm(delta));u=delta/d
 h=(ra*ra-rb*rb+d*d)/(2*d);v=math.sqrt(max(0,ra*ra-h*h));n=np.array([-u[1],u[0]])
 candidates=[a+h*u+v*n,a+h*u-v*n]
 if first:return max(candidates,key=lambda q:q[0])
 sign=cross(delta,other-a)
 return min(candidates,key=lambda q:cross(delta,q-a)*sign)

def flatten(d):
 v=np.array(d['vertices_mm'],float);p=np.zeros((len(v),2))
 if d['strip']:
  p[1]=[0,np.linalg.norm(v[1]-v[0])]
  for i in range(0,len(v)-2,2):
   p[i+2]=intersect(p[i],p[i+1],np.linalg.norm(v[i+2]-v[i]),np.linalg.norm(v[i+2]-v[i+1]),p[i-1] if i else None,first=i==0)
   p[i+3]=intersect(p[i+1],p[i+2],np.linalg.norm(v[i+3]-v[i+1]),np.linalg.norm(v[i+3]-v[i+2]),p[i])
  direction=(p[-1]+p[-2]-p[0]-p[1])/2
  th=math.atan2(direction[1],direction[0]);rot=np.array([[math.cos(th),math.sin(th)],[-math.sin(th),math.cos(th)]])
  p=p@rot.T
 else:
  u=v[1]-v[0];u/=np.linalg.norm(u)
  normal=None
  for q in v[2:]:
   normal=np.cross(u,q-v[0])
   if np.linalg.norm(normal)>1e-8:break
  normal/=np.linalg.norm(normal);vv=np.cross(normal,u)
  p=np.array([[(q-v[0])@u,(q-v[0])@vv] for q in v])
 # Align planar pieces with their principal long direction for grain-aware roll placement.
 if not d['strip']:
  vals,axes=np.linalg.eigh(np.cov(p.T));u=axes[:,int(np.argmax(vals))]
  if u[0]<0:u=-u
  p=p@np.array([[u[0],-u[1]],[u[1],u[0]]])
 p-=p.min(axis=0)
 errors=[]
 for t in d['triangles']:
  for a,b in zip(t,t[1:]+t[:1]):errors.append(abs(np.linalg.norm(p[a]-p[b])-np.linalg.norm(v[a]-v[b])))
 poly=Polygon(p[d['boundary']])
 if not poly.is_valid or poly.area<=0:raise ValueError('Invalid flattened polygon '+d['id'])
 return p,poly,float(max(errors))

def dxf_piece(d,path,origin=(0,0),doc=None):
 own=doc is None
 if own:
  doc=ezdxf.new('R2010');doc.units=4
  for name,col in [('CUT',7),('SEW',5),('NOTCH',1),('GRAIN',3),('ID',7),('CHANNEL',2),('EMBROIDERY',6)]:doc.layers.new(name,dxfattribs={'color':col})
 ms=doc.modelspace();ox,oy=origin
 for key,layer in [('cut','CUT'),('sew','SEW')]:ms.add_lwpolyline([(x+ox,y+oy) for x,y in d[key]],close=True,dxfattribs={'layer':layer})
 for pt in d['notches']:ms.add_circle((pt[0]+ox,pt[1]+oy),1.5,dxfattribs={'layer':'NOTCH'})
 x0,y0,x1,y1=Polygon(d['sew']).bounds
 yy=(y0+y1)/2;xx0=x0+(x1-x0)*.25;xx1=x0+(x1-x0)*.75
 ms.add_line((xx0+ox,yy+oy),(xx1+ox,yy+oy),dxfattribs={'layer':'GRAIN'})
 ms.add_text(d['id']+' / '+d['material']+' / QTY '+str(d['quantity']),dxfattribs={'height':9,'layer':'ID','insert':(xx0+ox,yy+oy+15)})
 if own:doc.saveas(path)
 return doc

def svg_piece(d,path):
 cut=np.array(d['cut']);mins=cut.min(axis=0)-20;maxs=cut.max(axis=0)+20;w,h=maxs-mins
 def pts(v):return ' '.join(f'{x-mins[0]:.3f},{h-(y-mins[1]):.3f}' for x,y in v)
 title=d['id']+' / '+d['material']+' / QTY '+str(d['quantity'])
 s=[f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" width="{w:.3f}mm" height="{h:.3f}mm" viewBox="0 0 {w:.3f} {h:.3f}"><title>{title}</title>',
 f'<g id="CUT"><polygon points="{pts(d["cut"])}" fill="none" stroke="#151e25" stroke-width=".5"/></g>',
 f'<g id="SEW"><polygon points="{pts(d["sew"])}" fill="none" stroke="#36566b" stroke-width=".45" stroke-dasharray="4 2"/></g>']
 for x,y in d['notches']:s.append(f'<circle cx="{x-mins[0]:.3f}" cy="{h-(y-mins[1]):.3f}" r="1.5" stroke="#a13737" fill="none" stroke-width=".4"/>')
 s.append(f'<text x="20" y="15" font-family="sans-serif" font-size="8">{title}; SA {d["sa_mm"]} mm; 1:1</text>')
 s.append(f'<path d="M {w*.25:.3f},{h/2:.3f} H {w*.75:.3f}" stroke="#29694d" stroke-width=".6"/><text x="{w*.35:.3f}" y="{h/2-5:.3f}" font-family="sans-serif" font-size="7">GRAIN</text>')
 s.append('</svg>');path.write_text('\n'.join(s))

def draw_poly(c,arr,off,scale=1,stroke=1,fill=0):
 p=c.beginPath();p.moveTo((arr[0][0]+off[0])*mm*scale,(arr[0][1]+off[1])*mm*scale)
 for x,y in arr[1:]:p.lineTo((x+off[0])*mm*scale,(y+off[1])*mm*scale)
 p.close();c.drawPath(p,stroke=stroke,fill=fill)

def pdf_full():
 c=canvas.Canvas(str(OUT/'Lezhandr_R02_patterns_1to1.pdf'))
 for id,d in RESULT.items():
  minx,miny,maxx,maxy=Polygon(d['cut']).bounds;w=maxx-minx+50;h=maxy-miny+65
  c.setPageSize((w*mm,h*mm));c.setFont('Helvetica-Bold',12);c.drawString(20*mm,(h-18)*mm,id+' / '+d['material']+' / qty '+str(d['quantity']))
  c.setFont('Helvetica',9);c.drawString(20*mm,(h-25)*mm,'1:1 mm | SA '+str(d['sa_mm'])+' mm | toile first, no shrinkage compensation')
  off=(25-minx,20-miny);c.setLineWidth(.4);c.setStrokeColorRGB(.1,.13,.16);draw_poly(c,d['cut'],off)
  c.setDash(4,2);c.setStrokeColorRGB(.20,.35,.45);draw_poly(c,d['sew'],off);c.setDash()
  for x,y in d['notches']:c.circle((x+off[0])*mm,(y+off[1])*mm,1.5*mm,stroke=1,fill=0)
  cy=(miny+maxy)/2+off[1];c.setLineWidth(.8);c.line((minx+off[0]+20)*mm,cy*mm,(maxx+off[0]-20)*mm,cy*mm)
  # A 100 mm check ruler where the page has enough space.
  c.setFont('Helvetica',8);c.line(25*mm,10*mm,125*mm,10*mm);c.drawString(25*mm,5*mm,'CHECK 100 mm - print Actual size')
  c.showPage()
 c.save()

def nesting():
 groups=defaultdict(list)
 for d in RESULT.values():
  for n in range(d['quantity']):groups[d['material']].append(d)
 stats={};records=[]
 for mat,items in groups.items():
  # Raster-assisted irregular nesting, with 8 mm grid and a 10 mm safety buffer.
  # Grain stays parallel to roll; 90 and 270 degrees only. Exact polygons are
  # checked below; rasterization is never used as the final cutter contour.
  rollw=1500;grid=8.;margin=20;cw=int((rollw-2*margin)//grid)
  maxh=int(sum(max(Polygon(d['cut']).bounds[2]-Polygon(d['cut']).bounds[0],Polygon(d['cut']).bounds[3]-Polygon(d['cut']).bounds[1])+40 for d in items)/grid)+100
  occupied=np.zeros((maxh,cw),np.float32);placed=[];placements=[];maxused=0
  for d in sorted(items,key=lambda d:-Polygon(d['cut']).area):
   choices=[]
   for angle in [90,270]:
    raw=rotate(Polygon(d['cut']),angle,origin=(0,0));b=raw.bounds;poly=translate(raw,10-b[0],10-b[1]);buffered=poly.buffer(10)
    pw=int(math.ceil(buffered.bounds[2]/grid))+1;ph=int(math.ceil(buffered.bounds[3]/grid))+1
    if pw>cw:continue
    stencil=np.zeros((ph,pw),np.uint8)
    coords=np.round(np.array(buffered.exterior.coords)/grid).astype(np.int32);cv2.fillPoly(stencil,[coords],1)
    search_h=min(maxh,maxused+ph+3)
    score=cv2.matchTemplate(occupied[:search_h],stencil.astype(np.float32),cv2.TM_CCORR)
    yy,xx=np.where(score<.25)
    if len(xx):
     best=int(np.argmin(yy*cw+xx));cy,cx=int(yy[best]),int(xx[best]);choices.append((cy,cx,angle,poly,stencil))
   if not choices:raise ValueError('Could not nest '+d['id'])
   cy,cx,angle,poly,stencil=min(choices,key=lambda e:(e[0],e[1]));ph,pw=stencil.shape
   occupied[cy:cy+ph,cx:cx+pw]=np.maximum(occupied[cy:cy+ph,cx:cx+pw],stencil)
   maxused=max(maxused,cy+ph);x=margin+cx*grid;y=margin+cy*grid
   pp=translate(poly,x,y);placed.append((d,pp,x,y));placements.append(angle)
  length=max(p.bounds[3] for d,p,x,y in placed)+20
  area=sum(p.area for d,p,x,y in placed)
  for i,(d,p,x,y) in enumerate(placed):
   for e,q,xx,yy in placed[:i]:
    if p.intersection(q).area>1e-5:raise ValueError('Nesting overlap')
   records.append({'material':mat,'id':d['id'],'roll_width_mm':rollw,'x_mm':round(x,3),'y_mm':round(y,3),'rotation_deg':placements[i]})
  stats[mat]={'pieces':len(placed),'width_mm':rollw,'length_mm':round(length,1),'area_m2':round(area/1e6,3),'utilization_percent':round(100*area/(rollw*length),2),'algorithm':'irregular raster nesting, 8 mm grid, 10 mm buffer, 90/270 deg; exact polygon collision check; not global optimum'}
  doc=ezdxf.new('R2010');doc.units=4;ms=doc.modelspace()
  ms.add_lwpolyline([(0,0),(rollw,0),(rollw,length),(0,length)],close=True)
  s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{rollw}mm" height="{length:.3f}mm" viewBox="0 0 {rollw} {length:.3f}"><rect width="1500" height="{length:.3f}" fill="white" stroke="#283b48" stroke-width="2"/>']
  for d,p,x,y in placed:
   layer=d['id'];doc.layers.new(layer);coords=list(p.exterior.coords)
   ms.add_lwpolyline(coords,close=True,dxfattribs={'layer':layer})
   pt=p.representative_point();ms.add_text(layer,dxfattribs={'height':14,'insert':(pt.x,pt.y)})
   ss=' '.join(f'{xx:.2f},{yy:.2f}' for xx,yy in coords);s.append(f'<polygon points="{ss}" fill="#e6ecef" stroke="#344c5c" stroke-width="1.2"/><text x="{pt.x:.2f}" y="{pt.y:.2f}" font-family="sans-serif" font-size="22">{layer}</text>')
  s.append('</svg>');(OUT/'markers'/f'{mat}_1500.svg').write_text('\n'.join(s));doc.saveas(OUT/'markers'/f'{mat}_1500.dxf')
 with (OUT/'marker_positions.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
 (OUT/'marker_report.json').write_text(json.dumps(stats,indent=2))
 return stats

def main():
 maxerr=0
 for id,d in D.items():
  uv,poly,err=flatten(d);maxerr=max(maxerr,err);sa=d.get('seam_allowance_mm',12)
  cut=poly.buffer(sa,join_style=2,mitre_limit=3)
  if cut.geom_type!='Polygon' or not cut.is_valid:raise ValueError('Bad allowance '+id)
  r={'id':id,'description':d['description'],'material':d['material'],'quantity':d['quantity'],'sa_mm':sa,
     'sew':list(map(list,poly.exterior.coords[:-1])),'cut':list(map(list,cut.exterior.coords[:-1])),
     'uv_vertices_mm':uv.tolist(),'notches':uv[d['boundary']].tolist() if d['strip'] else [],'edge_error_mm':err,'source_panel':id,
     'source_area_m2':poly.area/1e6,'cut_area_m2':cut.area/1e6}
  RESULT[id]=r
  dxf_piece(r,OUT/'pieces'/f'{id}.dxf');svg_piece(r,OUT/'pieces'/f'{id}.svg')
 # Insulation follows shell mid-panels but excludes allowances and is held by pockets.
 for id,r in list(RESULT.items()):
  if id.startswith('O') and id!='OF':
   q=copy.deepcopy(r);q['id']='I'+id[1:];q['material']='insulation';q['sa_mm']=0;q['quantity']=1
   cut=Polygon(r['sew']).buffer(-8,join_style=2)
   if cut.is_empty or cut.geom_type!='Polygon':continue
   q['cut']=list(map(list,cut.exterior.coords[:-1]));q['sew']=q['cut'];q['notches']=[];q['cut_area_m2']=cut.area/1e6
   RESULT[q['id']]=q;dxf_piece(q,OUT/'pieces'/f'{q["id"]}.dxf');svg_piece(q,OUT/'pieces'/f'{q["id"]}.svg')
 # Single export contains CAD mapping and every stitch/notch vertex, not a bitmap.
 (OUT/'patterns_R02.json').write_text(json.dumps(RESULT,ensure_ascii=False,indent=2))
 with (OUT/'patterns_R02.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['id','material','qty','seam_allowance_mm','sew_area_m2','cut_area_m2','max_edge_error_mm','CAD_source_panel'])
  for d in RESULT.values():w.writerow([d['id'],d['material'],d['quantity'],d['sa_mm'],round(d['source_area_m2'],5),round(d['cut_area_m2'],5),f'{d["edge_error_mm"]:.9g}',d['source_panel']])
 # Pair CAD coincident boundary edges to prove matching sew-line lengths.
 edges=defaultdict(list)
 for id,d in D.items():
  uv=np.array(RESULT[id]['uv_vertices_mm']);v=np.array(d['vertices_mm']);ind=d['boundary']
  for a,b in zip(ind,ind[1:]+ind[:1]):
   key=tuple(sorted([tuple(np.round(v[a],5)),tuple(np.round(v[b],5))]))
   edges[key].append((id,float(np.linalg.norm(uv[a]-uv[b])),a,b))
 pairs=[]
 for edge,entries in edges.items():
  if len(entries)==2:
   a,b=entries;pairs.append([a[0],a[2],a[3],b[0],b[2],b[3],a[1],b[1],abs(a[1]-b[1])])
 with (OUT/'seam_pairs.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['piece_A','vertex_A1','vertex_A2','piece_B','vertex_B1','vertex_B2','length_A_mm','length_B_mm','delta_mm']);w.writerows(pairs)
 stats=nesting();pdf_full()
 rep={'CAD_panels':len(D),'cut_patterns_including_insulation':len(RESULT),'max_triangle_edge_error_mm':maxerr,'matched_boundary_segments':len(pairs),
      'max_paired_seam_delta_mm':max((p[-1] for p in pairs),default=0),'all_polygons_valid':True,'all_markers_nonoverlapping':True,
      'cloth_FEM_or_fabric_shrinkage_compensation':False,'material_markers':stats}
 (ROOT/'tests/results/patterns_R02.json').write_text(json.dumps(rep,indent=2));print(json.dumps(rep,indent=2))
if __name__=='__main__':main()
