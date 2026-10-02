"""Flatten the *actual sampled* R04 CAD panels by minimizing edge distortion.
Not ExactFlat; uses a sparse nonlinear least-squares fit. All errors are reported.
Only the passive canopy is developable by construction. Draft shell patterns
are not released as a finished production pattern set.
"""
from pathlib import Path
import json,math,csv
import numpy as np
from scipy.optimize import least_squares
from scipy.sparse import coo_matrix
from shapely.geometry import Polygon
import ezdxf
from cloth_solver import grid_faces
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'patterns';(OUT/'pieces').mkdir(exist_ok=True)


def flatten(grid):
    g=np.asarray(grid);nu,nv,_=g.shape;v=g.reshape(-1,3);tri=grid_faces(nu,nv)
    e=np.unique(np.sort(np.vstack([tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]]]),axis=1),axis=0)
    rest=np.linalg.norm(v[e[:,0]]-v[e[:,1]],axis=1)
    us=np.r_[0,np.cumsum(np.mean(np.linalg.norm(np.diff(g,axis=0),axis=2),axis=1))]
    vs=np.r_[0,np.cumsum(np.mean(np.linalg.norm(np.diff(g,axis=1),axis=2),axis=0))]
    x=np.array([[u,w] for u in us for w in vs]);fixed=np.array([0,1,2*((nu-1)*nv)+1]);free=np.setdiff1d(np.arange(x.size),fixed);base=x.ravel().copy()
    inv=np.full(x.size,-1,int);inv[free]=np.arange(len(free))
    def unpack(z):
        a=base.copy();a[free]=z;return a.reshape(-1,2)
    def fun(z):
        xy=unpack(z);length=np.linalg.norm(xy[e[:,1]]-xy[e[:,0]],axis=1)
        return (length-rest)/np.sqrt(rest)
    def jac(z):
        xy=unpack(z);d=xy[e[:,1]]-xy[e[:,0]];le=np.maximum(np.linalg.norm(d,axis=1),1e-10);gr=d/le[:,None]/np.sqrt(rest[:,None])
        rows=[];cols=[];data=[]
        for side,sgn in [(0,-1),(1,1)]:
            for a in [0,1]:
                idx=inv[2*e[:,side]+a];mask=idx>=0
                rows.extend(np.nonzero(mask)[0]);cols.extend(idx[mask]);data.extend(sgn*gr[mask,a])
        return coo_matrix((data,(rows,cols)),shape=(len(e),len(free))).tocsr()
    fit=least_squares(fun,x.ravel()[free],jac=jac,max_nfev=160,ftol=1e-9,xtol=1e-9,gtol=1e-8)
    xy=unpack(fit.x);xy-=xy.min(axis=0);strain=(np.linalg.norm(xy[e[:,1]]-xy[e[:,0]],axis=1)/rest-1)*100
    bound=list(range(nv))+[i*nv+nv-1 for i in range(1,nu)]+list(range((nu-1)*nv+nv-2,(nu-1)*nv-1,-1))+[i*nv for i in range(nu-2,0,-1)]
    polygon=Polygon(xy[bound]);area3=np.sum(np.linalg.norm(np.cross(v[tri[:,1]]-v[tri[:,0]],v[tri[:,2]]-v[tri[:,0]]),axis=1))*.5
    signed=np.cross(xy[tri[:,1]]-xy[tri[:,0]],xy[tri[:,2]]-xy[tri[:,0]])
    metrics={'p95_edge_distortion_pct':float(np.percentile(np.abs(strain),95)),'max_edge_distortion_pct':float(np.max(np.abs(strain))),
             'polygon_valid':bool(polygon.is_valid),'triangle_orientation_consistent':bool(np.all(signed>0) or np.all(signed<0)),
             'area_3d_m2':float(area3/1e6),'area_2d_m2':float(polygon.area/1e6),'solver_nfev':fit.nfev,'solver_success':bool(fit.success),'production_release':False}
    return xy,tri,bound,metrics

def write_piece(id,xy,tri,bound,sa,metrics,desc):
    polygon=Polygon(xy[bound]);cut=polygon.buffer(sa,join_style=2);cutpts=np.array(cut.exterior.coords)
    doc=ezdxf.new('R2010');doc.units=4;m=doc.modelspace()
    for lay,col in [('CUT',7),('SEW',3),('GRAIN',1),('LABEL',7),('DRAFT_MESH',8)]:doc.layers.new(lay,dxfattribs={'color':col})
    m.add_lwpolyline(cutpts.tolist(),close=True,dxfattribs={'layer':'CUT'})
    m.add_lwpolyline(xy[bound].tolist(),close=True,dxfattribs={'layer':'SEW'})
    cen=polygon.representative_point();cx,cy=cen.x,cen.y
    m.add_text(id+' | DRAFT mm',dxfattribs={'height':14,'insert':(cx-50,cy),'layer':'LABEL'})
    m.add_line((cx,cy-80),(cx,cy+80),dxfattribs={'layer':'GRAIN'})
    for a in [-1,1]:m.add_line((cx,cy+a*80),(cx+7,cy+a*65),dxfattribs={'layer':'GRAIN'})
    doc.saveas(OUT/'pieces'/f'{id}.dxf')
    b=cut.bounds;minx,miny,maxx,maxy=b;W=maxx-minx+40;H=maxy-miny+70
    def path(pts):return 'M '+' L '.join(f'{p[0]-minx+20:.3f},{maxy-p[1]+20:.3f}' for p in pts)+' Z'
    S=f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}"><rect width="100%" height="100%" fill="white"/>'
    S+=f'<path d="{path(cutpts)}" fill="#ede9e2" stroke="#222" stroke-width=".7"/><path d="{path(xy[bound])}" fill="none" stroke="#386d80" stroke-width=".7" stroke-dasharray="5 3"/>'
    S+=f'<text x="20" y="{H-30}" font-family="DejaVu Sans" font-size="11">{id}: {desc}</text><text x="20" y="{H-12}" font-family="DejaVu Sans" font-size="9">DRAFT / mm / SA {sa} / max edge error {metrics.get("max_edge_distortion_pct",0):.2f}%</text></svg>'
    (OUT/'pieces'/f'{id}.svg').write_text(S)
    return {'id':id,'vertices_2d_mm':xy.tolist(),'triangles':tri.tolist(),'boundary':bound,'seam_allowance_mm':sa,'metrics':metrics,'description':desc}

results=[]
for d in json.loads((OUT/'surfaces_R04.json').read_text()):
    xy,t,b,met=flatten(d['grid_mm']);r=write_piece(d['id'],xy,t,b,12,met,'outer shell' if d['id'][0]=='O' else 'lining');results.append(r)
    print(d['id'],met,flush=True)
# Passive cover: exact cylindrical development based on the INITIAL reference cloth.
g=np.load(ROOT/'simulation/hood_drape.npz')['initial_m'].reshape(25,49,3)*1000
arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(g[0],axis=0),axis=1))]
xy=np.array([[x-g[0,0,0],v] for x in g[:,0,0] for v in arc]);tri=grid_faces(25,49)
b=list(range(49))+[i*49+48 for i in range(1,25)]+list(range(24*49+47,24*49-1,-1))+[i*49 for i in range(23,0,-1)]
for id in ['HC_OUTER','HC_LINING']:
    met={'max_edge_distortion_pct':0.0,'p95_edge_distortion_pct':0.0,'production_release':False,'note':'Cylindrical nominal development; simulation slack is NOT a measured fabric shrink allowance.'}
    results.append(write_piece(id,xy,tri,b,12,met,'passive canopy; NO HEATER'))
# Not sewn through a heating mat: trim strips and hinge.
for id,L,W,qty in [('HC_HINGE',360,50,1),('HC_RIB_SLEEVE',arc[-1],36,2),('HC_LIMIT_STRAP',800,25,2)]:
    vv=np.array([[0,0],[L,0],[L,W],[0,W]],float);tt=np.array([[0,1,2],[0,2,3]])
    met={'max_edge_distortion_pct':0.,'quantity':qty,'production_release':False}
    results.append(write_piece(id,vv,tt,[0,1,2,3],0,met,'trim strip; quantity '+str(qty)))
(OUT/'patterns_R04.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
with (OUT/'distortion_report.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f);w.writerow(['id','p95_edge_distortion_pct','max_edge_distortion_pct','production_release']);w.writerows([(d['id'],d['metrics'].get('p95_edge_distortion_pct',0),d['metrics']['max_edge_distortion_pct'],False) for d in results])
# Show an intentionally UNNESTED review layout, not a false optimal marker.
cols=4;W=1600;cellw=400;cellh=650;H=math.ceil(len(results)/cols)*cellh
master=ezdxf.new('R2010');master.units=4;m=master.modelspace();svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}"><rect width="100%" height="100%" fill="white"/>']
for idx,d in enumerate(results):
    xy=np.array(d['vertices_2d_mm']);poly=Polygon(xy[d['boundary']]);cut=poly.buffer(d['seam_allowance_mm'],join_style=2)
    bounds=cut.bounds;size=np.array([bounds[2]-bounds[0],bounds[3]-bounds[1]]);scale=min((cellw-30)/size[0],(cellh-80)/size[1],1)
    ox=(idx%cols)*cellw+15;oy=(idx//cols)*cellh+35
    pts=np.array(cut.exterior.coords);pts=(pts-np.array(bounds[:2]))*scale+np.array([ox,oy])
    path='M '+' L '.join(f'{x:.2f},{y:.2f}' for x,y in pts)+' Z'
    svg.append(f'<path d="{path}" fill="#ede9e2" stroke="#2b424d" stroke-width="1"/><text x="{ox}" y="{oy-12}" font-size="13" font-family="DejaVu Sans">{d["id"]} / review scale {scale:.3f}</text>')
    # DXF 1:1 off to the side is intentionally not a cut marker.
    offset=np.array([(idx%4)*1800,(idx//4)*1800]);pp=np.array(cut.exterior.coords)+offset
    m.add_lwpolyline(pp.tolist(),close=True);m.add_text(d['id']+' DRAFT',dxfattribs={'insert':offset.tolist(),'height':25})
svg.append('</svg>');(OUT/'review_layout.svg').write_text(''.join(svg));master.saveas(ROOT/'exchange'/'R04_DRAFT_patterns_1to1.dxf')
report={'panels':len(results),'shell_panels':24,'canopy_and_trim_patterns':5,'max_shell_edge_error_pct':max(r['metrics']['max_edge_distortion_pct'] for r in results[:24]),'not_a_cutting_marker':True,'not_production_released':True}
(OUT/'summary.json').write_text(json.dumps(report,indent=2));print(report)
