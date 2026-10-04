#!/usr/bin/env python3
"""Flatten all R08 surface panels. Checks do not substitute fabric/sample validation."""
from pathlib import Path
import json,math,csv
import numpy as np
from scipy.optimize import least_squares
from scipy.sparse import lil_matrix,coo_matrix
from scipy.sparse.linalg import lsqr
from shapely.geometry import Polygon,LineString
from shapely import affinity
import ezdxf
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'patterns';panels=json.loads((P/'panel_grids.json').read_text());records=[];edges={}
# Rebuild only declared patterns; never leave rejected adaptive split outputs.
for old in list(P.glob('*.dxf'))+list(P.glob('*.svg')):old.unlink()
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';pdfmetrics.registerFont(TTFont('D',FONT))
def key(a,b):return tuple(sorted([tuple(np.round(a,4)),tuple(np.round(b,4))]))
def flatten(g):
 nr,nc,_=g.shape;n=nr*nc;v=g.reshape(-1,3)
 # Least-squares conformal initial map, not accumulated widths on a bent centreline.
 triangles=[]
 for i in range(nr-1):
  for j in range(nc-1):
   a=i*nc+j;b=(i+1)*nc+j;c=i*nc+j+1;d=(i+1)*nc+j+1;triangles += [(a,b,c),(b,d,c)]
 row=[];col=[];val=[]
 for ti,(a,b,c) in enumerate(triangles):
  e=v[b]-v[a];L=np.linalg.norm(e);x=np.dot(v[c]-v[a],e)/L;y=np.linalg.norm(np.cross(e,v[c]-v[a]))/L
  if y<1e-9:raise RuntimeError('Degenerate source triangle')
  gx=np.array([-1/L,1/L,0]);gy=np.array([(x/L-1)/y,-x/(L*y),1/y]);weight=math.sqrt(L*y/2)
  for ii,k in enumerate([a,b,c]):
   for rr,cc,vv in [(2*ti,2*k,gx[ii]),(2*ti,2*k+1,-gy[ii]),(2*ti+1,2*k,gy[ii]),(2*ti+1,2*k+1,gx[ii])]:row.append(rr);col.append(cc);val.append(vv*weight)
 A=coo_matrix((val,(row,col)),shape=(2*len(triangles),2*n)).tocsr();pin=[0,1,2*((nr-1)*nc),2*((nr-1)*nc)+1];xpin=np.array([0,0,np.linalg.norm(v[(nr-1)*nc]-v[0]),0]);free0=np.setdiff1d(np.arange(2*n),pin);flat=np.zeros(2*n);flat[pin]=xpin;flat[free0]=lsqr(A[:,free0],-A[:,pin]@xpin,atol=1e-9,btol=1e-9,iter_lim=5000)[0];uv=flat.reshape(-1,2)
 ed=[];weights=[]
 for i in range(nr):
  for j in range(nc):
   for di,dj in [(1,0),(0,1),(1,1),(1,-1)]:
    ii=i+di;jj=j+dj
    if ii<nr and 0<=jj<nc:
     ed.append((i*nc+j,ii*nc+jj));isbound=(dj==0 and j in [0,nc-1]) or (di==0 and i in [0,nr-1]);weights.append(10 if isbound else 1)
 ed=np.array(ed);length=np.linalg.norm(v[ed[:,1]]-v[ed[:,0]],axis=1);weight=np.array(weights)/np.sqrt(np.maximum(length,1))
 flatlength=np.linalg.norm(uv[ed[:,0]]-uv[ed[:,1]],axis=1);uv*=float(np.dot(flatlength,length)/np.dot(flatlength,flatlength))
 fixed=[0,1,2*((nr-1)*nc)+1];free=np.setdiff1d(np.arange(n*2),fixed);base=uv.ravel().copy();idx={x:i for i,x in enumerate(free)}
 jac=lil_matrix((len(ed),len(free)),dtype=int)
 for k,(a,b) in enumerate(ed):
  for q in [2*a,2*a+1,2*b,2*b+1]:
   if q in idx:jac[k,idx[q]]=1
 def fun(x):
  o=base.copy();o[free]=x;o=o.reshape(-1,2);return (np.linalg.norm(o[ed[:,0]]-o[ed[:,1]],axis=1)-length)*weight
 sol=least_squares(fun,base[free],jac_sparsity=jac.tocsr(),max_nfev=160,ftol=2e-6,xtol=2e-6,gtol=2e-6)
 base[free]=sol.x;uv=base.reshape(nr,nc,2);uv=uv[:,:,::-1] # grain direction along roll length
 err=np.abs(np.linalg.norm(uv.reshape(-1,2)[ed[:,1]]-uv.reshape(-1,2)[ed[:,0]],axis=1)-length)/np.maximum(length,1e-8)
 border=np.vstack([uv[:,0],uv[-1,1:],uv[-2::-1,-1],uv[0,-2:0:-1]])
 return uv,border,err,sol
pdf=canvas.Canvas(str(P/'R08_patterns_P0_1to1.pdf'))
queue=list(panels);k=0
while queue:
 item=queue.pop(0);g=np.array(item['grid_mm']);uv,border,err,sol=flatten(g);poly=Polygon(border)
 if not poly.is_valid or err.max()>.02:
  nr,nc,_=g.shape
  # Insert explicit cutting seams, never silently stretch or repair a polygon.
  along=np.linalg.norm(np.diff(g[:,nc//2],axis=0),axis=1).sum();across=np.linalg.norm(np.diff(g[nr//2],axis=0),axis=1).sum()
  axis=0 if nr>2 and (along>=across or nc<=2) else 1
  if g.shape[axis]<=2:raise RuntimeError('Need manual dart '+item['id'])
  middle=(g.shape[axis]-1)//2
  a=g[:middle+1] if axis==0 else g[:,:middle+1];b=g[middle:] if axis==0 else g[:,middle:]
  for suffix,data in [('A',a),('B',b)]:
   child=dict(item);child['id']=item['id']+'_'+suffix;child['grid_mm']=data.tolist();child['split_note']='Explicit additional seam to keep sampled metric error below 2 percent';queue.insert(0,child)
  print('SPLIT',item['id'],round(float(err.max())*100,2),'axis',axis,flush=True);continue
 k+=1
 cut=poly.buffer(item['seam_allowance_mm'],join_style=2);bb=cut.bounds
 record={k:v for k,v in item.items() if k!='grid_mm'};record.update({'seam_polygon_mm':border.tolist(),'cut_polygon_mm':list(cut.exterior.coords),'uv_mm':uv.tolist(),'max_metric_distortion_percent':100*float(err.max()),'rms_metric_distortion_percent':100*float(np.sqrt(np.mean(err**2))),'solver_success':bool(sol.success),'outer_area_m2':poly.area/1e6,'cut_width_mm':bb[2]-bb[0],'cut_length_mm':bb[3]-bb[1]})
 # Record shared mesh boundary lengths to audit pairwise seam metric, including edge bands.
 if item['material']!='insulation':
  nr,nc,_=g.shape
  for edge in [[(i,0) for i in range(nr)],[(nr-1,j) for j in range(nc)],[(i,nc-1) for i in range(nr)],[(0,j) for j in range(nc)]]:
   for a,b in zip(edge[:-1],edge[1:]):
    t=key(g[a],g[b]);edges.setdefault(t,[]).append({'id':item['id'],'flat_mm':float(np.linalg.norm(uv[a]-uv[b])),'three_d_mm':float(np.linalg.norm(g[a]-g[b]))})
 records.append(record)
 doc=ezdxf.new('R2010');doc.units=4;ms=doc.modelspace()
 for layer,color in [('CUT',1),('SEAM',5),('GRAIN',3),('NOTCH',2),('ID',7)]:doc.layers.new(layer,dxfattribs={'color':color})
 ms.add_lwpolyline(record['cut_polygon_mm'],close=True,dxfattribs={'layer':'CUT'});ms.add_lwpolyline(border,close=True,dxfattribs={'layer':'SEAM'})
 cx=(bb[0]+bb[2])/2;cy=(bb[1]+bb[3])/2;ms.add_line((cx,cy-40),(cx,cy+40),dxfattribs={'layer':'GRAIN'})
 ms.add_text(item['id'],dxfattribs={'height':8,'insert':(bb[0],bb[3]+20),'layer':'ID'})
 # Notches projected from exactly matching 3D sample locations; do not cut past seam.
 for ii,jj in [(len(g)//2,0),(len(g)//2,len(g[0])-1),(0,len(g[0])//2),(-1,len(g[0])//2)]:
  q=uv[ii,jj];ms.add_circle(q,1.5,dxfattribs={'layer':'NOTCH'})
 path=P/(item['id']+'.dxf');doc.saveas(path);a=ezdxf.readfile(path).audit()
 if a.errors or a.fixes:raise RuntimeError('DXF audit '+item['id'])
 pad=28;ww=bb[2]-bb[0]+pad*2;hh=bb[3]-bb[1]+pad*2
 def svgpath(ps):return 'M '+' L '.join(f'{x-bb[0]+pad:.3f},{bb[3]-y+pad:.3f}' for x,y in ps)+' Z'
 (P/(item['id']+'.svg')).write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{ww}mm" height="{hh}mm" viewBox="0 0 {ww} {hh}"><title>{item["id"]}</title><path d="{svgpath(record["cut_polygon_mm"])}" fill="#eee4d6" stroke="#6f5742" stroke-width=".7"/><path d="{svgpath(border)}" fill="none" stroke="#5f6a62" stroke-width=".5" stroke-dasharray="3 2"/><text x="20" y="16" font-family="sans-serif" font-size="7">{item["id"]} / P0 / mm</text></svg>')
 # Real-size plotting; all shapes and allowances in millimetres.
 mm=72/25.4;pdf.setPageSize((max(210,ww)*mm,max(297,hh+40)*mm));pdf.setFont('D',9)
 pdf.drawString(12*mm,(max(297,hh+40)-10)*mm,item['id']+' | '+item['material']+' | 1:1 / P0')
 def drawpoly(ps,gray):
  pdf.setStrokeGray(gray);p=pdf.beginPath();v=np.array(ps)-[bb[0]-pad,bb[1]-pad];p.moveTo(*(v[0]*mm))
  for xy in v[1:]:p.lineTo(*(xy*mm))
  p.close();pdf.drawPath(p,stroke=1,fill=0)
 drawpoly(record['cut_polygon_mm'],.15);pdf.setDash(4,3);drawpoly(border,.4);pdf.setDash()
 pdf.line(12*mm,12*mm,112*mm,12*mm);pdf.drawString(12*mm,16*mm,'100 mm - print at 100%');pdf.showPage()
 print('PATTERN',k,item['id'],round(record['max_metric_distortion_percent'],2),flush=True)
pdf.save()
# Matched common source segments only, distinguish unpaired edge bands and intentional openings.
seams=[]
for key_,rr in edges.items():
 ids={v['id'] for v in rr}
 if len(ids)>1:
  seams.append({'source_segment_mm':key_,'members':rr,'max_mismatch_mm':max(v['flat_mm'] for v in rr)-min(v['flat_mm'] for v in rr)})
# Grain-constrained, bounding-box strip packing; conservatively no overlapping cut shapes.
nest=[];rollwidth=1500
for material in sorted({r['material'] for r in records}):
 subset=[r for r in records if r['material']==material];subset.sort(key=lambda r:r['cut_length_mm'],reverse=True);x=15;y=15;shelf=0
 for r in subset:
  w=r['cut_width_mm'];h=r['cut_length_mm']
  if w+30>rollwidth:raise RuntimeError('Pattern exceeds 1500 mm roll: '+r['id'])
  if x+w+15>rollwidth:x=15;y+=shelf+25;shelf=0
  nest.append({'id':r['id'],'material':material,'x_mm':x,'y_mm':y,'width_mm':w,'height_mm':h,'rotation_deg':0});x+=w+25;shelf=max(shelf,h)
for p,data in [('patterns_registry.json',records),('seam_audit.json',seams),('nesting.json',nest)]: (P/p).write_text(json.dumps(data,ensure_ascii=False,indent=2))
with (P/'cut_list.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['ID','material','qty','allowance_mm','width_mm','length_mm','distortion_percent'])
 for r in records:w.writerow([r['id'],r['material'],1,r['seam_allowance_mm'],round(r['cut_width_mm'],1),round(r['cut_length_mm'],1),round(r['max_metric_distortion_percent'],3)])
report={'patterns':len(records),'matched_seam_segments':len(seams),'max_seam_mismatch_mm':max((s['max_mismatch_mm'] for s in seams),default=0),'max_metric_distortion_percent':max(r['max_metric_distortion_percent'] for r in records),'over_2_percent':[r['id'] for r in records if r['max_metric_distortion_percent']>2],'roll_width_mm':1500,'production_approved':False,'coverage':'All new gridded outer skins, lining, insulation, gussets, closure guards, channels and passive flap. Inherited internal granular bag patterns are not requalified.'}
(ROOT/'tests/pattern_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(report,flush=True)
