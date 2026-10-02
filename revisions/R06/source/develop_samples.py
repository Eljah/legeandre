#!/usr/bin/env python3
"""Draft metric flattening of three real R06 BREP grid patches.
This is geometry-only edge-length fitting, not drape physics, not production patterns.
Outer and inner skins unfolded separately; 12 mm allowance is provisional.
"""
from pathlib import Path
import json,math
import numpy as np
from scipy.optimize import least_squares
from scipy.sparse import lil_matrix
from shapely.geometry import Polygon
import ezdxf
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
G=json.loads((ROOT/'cad/cover_grids.json').read_text());OUT=ROOT/'patterns';OUT.mkdir(exist_ok=True)
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
records=[]
for id in ['Q02_SHOULDER_BODY','Q04_KEYBOARD_CLOSED','Q06_LEG_CONTINUATION']:
 for layer in ['outer','inner']:
  grid=np.array(G[id][layer+'_grid_mm']);nr,nc,_=grid.shape;N=nr*nc;verts=grid.reshape(-1,3)
  L=np.r_[0,np.cumsum(np.linalg.norm(np.diff(grid[:,nc//2],axis=0),axis=1))]
  V=np.c_[np.zeros(nr),np.cumsum(np.linalg.norm(np.diff(grid,axis=1),axis=2),axis=1)];V-=V[:,nc//2,None]
  UV=np.stack([np.broadcast_to(L[:,None],(nr,nc)),V],axis=-1).reshape(-1,2)
  edges=[]
  for i in range(nr):
   for j in range(nc):
    a=i*nc+j
    for di,dj in [(1,0),(0,1),(1,1),(1,-1)]:
     if 0<=i+di<nr and 0<=j+dj<nc:edges.append((a,(i+di)*nc+j+dj))
  ed=np.array(edges);target=np.linalg.norm(verts[ed[:,0]]-verts[ed[:,1]],axis=1)
  fixed=[2*(nc//2),2*(nc//2)+1,2*((nr-1)*nc+nc//2)+1]
  free=np.setdiff1d(np.arange(2*N),fixed);base=UV.ravel().copy()
  def residual(x):
   p=base.copy();p[free]=x;p=p.reshape(-1,2)
   return (np.linalg.norm(p[ed[:,0]]-p[ed[:,1]],axis=1)-target)/np.sqrt(target)
  jac=lil_matrix((len(ed),len(free)),dtype=int);fm={v:i for i,v in enumerate(free)}
  for k,(a,b) in enumerate(ed):
   for q in [2*a,2*a+1,2*b,2*b+1]:
    if q in fm:jac[k,fm[q]]=1
  sol=least_squares(residual,base[free],jac_sparsity=jac.tocsr(),max_nfev=75,ftol=2e-6,xtol=2e-6,gtol=2e-6)
  base[free]=sol.x;uv=base.reshape(nr,nc,2)
  edgeerr=abs(np.linalg.norm(base.reshape(-1,2)[ed[:,0]]-base.reshape(-1,2)[ed[:,1]],axis=1)-target)/target
  boundary=np.vstack([uv[:,0],uv[-1,1:],uv[-2::-1,-1],uv[0,-2:0:-1]])
  poly=Polygon(boundary);allow=poly.buffer(12,join_style=2);good=poly.is_valid and allow.is_valid
  if not good:raise RuntimeError('Invalid draft polygon '+id+' '+layer)
  name=id+'_'+layer.upper()+'_DRAFT'
  doc=ezdxf.new('R2010');doc.units=4
  for lname,c in [('SEAM',5),('CUT_DRAFT',1),('GRID_REFERENCE',8),('TEXT',7)]:doc.layers.new(lname,dxfattribs={'color':c})
  ms=doc.modelspace();ms.add_lwpolyline(boundary,close=True,dxfattribs={'layer':'SEAM'});ms.add_lwpolyline(np.array(allow.exterior.coords),close=True,dxfattribs={'layer':'CUT_DRAFT'})
  for row in uv:ms.add_lwpolyline(row,dxfattribs={'layer':'GRID_REFERENCE'})
  xy=poly.bounds
  ms.add_text(name,dxfattribs={'height':10,'insert':(xy[0],xy[3]+35),'layer':'TEXT'})
  ms.add_text('MM. PROTOTYPE ONLY. NOT PRODUCTION CUTTING.',dxfattribs={'height':7,'insert':(xy[0],xy[3]+20),'layer':'TEXT'})
  doc.saveas(OUT/(name+'.dxf'))
  # SVG mirrors exact DXF curves, no automatic repaired polygon substitutes.
  xx0,yy0,xx1,yy1=allow.bounds;pad=30;ww=xx1-xx0+2*pad;hh=yy1-yy0+2*pad
  def path(ps):return 'M '+' L '.join(f'{p[0]-xx0+pad:.3f},{yy1-p[1]+pad:.3f}' for p in ps)+' Z'
  svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{ww:.3f}mm" height="{hh:.3f}mm" viewBox="0 0 {ww:.3f} {hh:.3f}"><title>{name}</title><path d="{path(allow.exterior.coords)}" fill="#edf1ee" stroke="#af5544" stroke-width="0.8"/><path d="{path(boundary)}" fill="none" stroke="#38596a" stroke-width="0.6" stroke-dasharray="3 2"/><text x="20" y="18" font-family="sans-serif" font-size="7">DRAFT / {name}</text></svg>'
  (OUT/(name+'.svg')).write_text(svg)
  records.append({'id':id,'layer':layer,'file_stem':name,'grid_2d_mm':uv.tolist(),'seam_outline_mm':boundary.tolist(),'cut_outline_mm':np.array(allow.exterior.coords).tolist(),'allowance_mm':12,'max_edge_distortion_percent':float(edgeerr.max()*100),'rms_edge_distortion_percent':float(np.sqrt(np.mean(edgeerr**2))*100),'solver_success':bool(sol.success),'solver_evaluations':sol.nfev,'polygon_valid':good,'draft_only':True,'two_diagonals_used':True})
  print(name,round(edgeerr.max()*100,3),flush=True)
(OUT/'draft_patterns.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
# Readback audit, not just write-success.
checks=[]
for p in OUT.glob('*.dxf'):
 d=ezdxf.readfile(p);audit=d.audit();checks.append({'file':p.name,'errors':len(audit.errors),'fixes':len(audit.fixes),'units':d.units})
(ROOT/'tests/DXF_draft_audit.json').write_text(json.dumps(checks,indent=2))
# A clean actual vector-pattern raster view for the engineering album.
image=Image.new('RGB',(2350,1450),'#f6f4ee');dr=ImageDraw.Draw(image);font=ImageFont.truetype(FONT,28);small=ImageFont.truetype(FONT,22)
for i,r in enumerate(records):
 col=i//2;row=i%2;x0=col*770+30;y0=row*690+45;poly=np.array(r['cut_outline_mm']);mn=poly.min(0);mx=poly.max(0);scale=min(625/(mx[0]-mn[0]),475/(mx[1]-mn[1]));basept=np.array([x0+80,y0+125]);pp=(poly-mn)*scale+basept
 dr.polygon([tuple(q) for q in pp],fill='#dde6e3',outline='#536e70',width=3)
 sm=(np.array(r['seam_outline_mm'])-mn)*scale+basept;dr.line([tuple(q) for q in sm]+[tuple(sm[0])],fill='#ad6b51',width=2)
 name={'Q02_SHOULDER_BODY':'Плечевой сегмент Q02','Q04_KEYBOARD_CLOSED':'Клапан Q04','Q06_LEG_CONTINUATION':'Ножной сегмент Q06'}[r['id']]
 dr.text((x0,y0),name,font=font,fill='#203c44');dr.text((x0,y0+38),'Наружная оболочка' if r['layer']=='outer' else 'Внутренняя оболочка',font=small,fill='#31545b')
 dr.text((x0,y0+620),f"Макс. искажение рёбер: {r['max_edge_distortion_percent']:.2f}%",font=small,fill='#6b4235')
image.save(ROOT/'renders/draft_patterns.png')
