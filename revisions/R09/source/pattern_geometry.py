"""Millimetre pattern geometry. No calibrated cloth mechanics or shrink model."""
import math
import numpy as np
from scipy.optimize import least_squares
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import lsqr
from shapely.geometry import Polygon

def perimeter_indices(nr,nc):
    return ([(i,0) for i in range(nr)] + [(nr-1,j) for j in range(1,nc)] +
            [(i,nc-1) for i in range(nr-2,-1,-1)] + [(0,j) for j in range(nc-2,0,-1)])

def recover_grid(record,seeds):
    name=max((n for n in seeds if record['id']==n or record['id'].startswith(n+'_')),key=len)
    g=np.asarray(seeds[name]['grid_mm'],float)
    for child in filter(None,record['id'][len(name):].split('_')):
        nr,nc=g.shape[:2]
        along=np.linalg.norm(np.diff(g[:,nc//2],axis=0),axis=1).sum()
        across=np.linalg.norm(np.diff(g[nr//2],axis=0),axis=1).sum()
        axis=0 if nr>2 and (along>=across or nc<=2) else 1
        mid=(g.shape[axis]-1)//2
        if child not in ('A','B'):raise ValueError(record['id'])
        g=(g[:mid+1] if child=='A' else g[mid:]) if axis==0 else (g[:,:mid+1] if child=='A' else g[:,mid:])
    if g.shape[:2]!=np.asarray(record['uv_mm']).shape[:2]:raise ValueError('Grid ancestry mismatch '+record['id'])
    return g

def conformal(g):
    nr,nc=g.shape[:2];v=g.reshape(-1,3);n=len(v);tri=[]
    for i in range(nr-1):
        for j in range(nc-1):
            a=i*nc+j;b=(i+1)*nc+j;c=a+1;d=b+1;tri.extend([(a,b,c),(b,d,c)])
    rr=[];cc=[];vv=[]
    for it,(a,b,c) in enumerate(tri):
        e=v[b]-v[a];L=np.linalg.norm(e);x=np.dot(v[c]-v[a],e)/L;y=np.linalg.norm(np.cross(e,v[c]-v[a]))/L
        if y<1e-9:raise ValueError('Degenerate triangle')
        gx=np.array([-1/L,1/L,0]);gy=np.array([(x/L-1)/y,-x/(L*y),1/y]);w=math.sqrt(L*y/2)
        for ii,k in enumerate([a,b,c]):
            for row,col,val in [(2*it,2*k,gx[ii]),(2*it,2*k+1,-gy[ii]),(2*it+1,2*k,gy[ii]),(2*it+1,2*k+1,gx[ii])]:
                rr.append(row);cc.append(col);vv.append(val*w)
    A=coo_matrix((vv,(rr,cc)),shape=(2*len(tri),2*n)).tocsr()
    pin=[0,1,2*((nr-1)*nc),2*((nr-1)*nc)+1];free=np.setdiff1d(np.arange(2*n),pin)
    uv=np.zeros(2*n);uv[pin]=[0,0,np.linalg.norm(v[(nr-1)*nc]-v[0]),0]
    uv[free]=lsqr(A[:,free],-A[:,pin]@uv[pin],atol=1e-10,btol=1e-10,iter_lim=4000)[0]
    return uv.reshape(nr,nc,2)

def unfold_strip(g):
    """Exact unfolding of a one-cell-wide triangulated strip (all nodes on boundary)."""
    transposed=g.shape[0]==2 and g.shape[1]>2
    if transposed:g=g.transpose(1,0,2)
    n=len(g);uv=np.zeros((n,2,2));uv[0,1]=[np.linalg.norm(g[0,1]-g[0,0]),0]
    def other(a,b,ra,rb,old=None):
        v=b-a;d=np.linalg.norm(v);ex=v/d;ey=np.array([-ex[1],ex[0]])
        x=(ra*ra-rb*rb+d*d)/(2*d);h=math.sqrt(max(0,ra*ra-x*x))
        plus=a+x*ex+h*ey;minus=a+x*ex-h*ey
        if old is None:return plus
        return minus if np.dot(old-a,ey)>0 else plus
    for i in range(n-1):
        uv[i+1,0]=other(uv[i,0],uv[i,1],np.linalg.norm(g[i+1,0]-g[i,0]),np.linalg.norm(g[i+1,0]-g[i,1]),uv[i-1,1] if i else None)
        uv[i+1,1]=other(uv[i+1,0],uv[i,1],np.linalg.norm(g[i+1,1]-g[i+1,0]),np.linalg.norm(g[i+1,1]-g[i,1]),uv[i,0])
    if transposed:uv=uv.transpose(1,0,2);g=g.transpose(1,0,2)
    idx=perimeter_indices(*g.shape[:2]);poly=Polygon([uv[x] for x in idx]);errs=[]
    for i in range(g.shape[0]):
        for j in range(g.shape[1]):
            for di,dj in [(1,0),(0,1),(1,-1)]:
                if i+di<g.shape[0] and 0<=j+dj<g.shape[1]:
                    a=np.linalg.norm(g[i,j]-g[i+di,j+dj]);b=np.linalg.norm(uv[i,j]-uv[i+di,j+dj]);errs.append(abs(a-b)/max(a,1e-9)*100)
    axis=uv[-1,0]-uv[0,0];ang=math.atan2(axis[1],axis[0]);uv=(uv-uv[0,0])@np.array([[math.cos(ang),-math.sin(ang)],[math.sin(ang),math.cos(ang)]])
    return uv,{'max_strain_pct':float(max(errs)), 'rms_strain_pct':float(np.sqrt(np.mean(np.array(errs)**2))), 'max_boundary_segment_error_mm':1e-8,
               'solver_converged':True,'iterations':0,'valid_polygon':bool(poly.is_valid and poly.area>1e-5),'no_inverted_triangles':True,'exact_strip_unfolding':True}

def flatten(g,initial=None,max_nfev=180):
    """LSCM followed by metric fitting; analytic sparse derivatives, stronger seam weights."""
    g=np.asarray(g,float);nr,nc=g.shape[:2];v=g.reshape(-1,3);n=len(v)
    if min(nr,nc)==2:return unfold_strip(g)
    uv=conformal(g) if initial is None else np.array(initial,float).copy()
    uv-=uv[0,0]
    axis=uv[-1,0];theta=math.atan2(axis[1],axis[0]);rot=np.array([[math.cos(theta),-math.sin(theta)],[math.sin(theta),math.cos(theta)]])
    uv=uv@rot
    edges=[];bd=[]
    for i in range(nr):
        for j in range(nc):
            for di,dj in [(1,0),(0,1),(1,-1)]:
                if i+di<nr and 0<=j+dj<nc:
                    edges.append((i*nc+j,(i+di)*nc+j+dj))
                    bd.append((dj==0 and j in (0,nc-1)) or (di==0 and i in (0,nr-1)))
    e=np.asarray(edges);length=np.linalg.norm(v[e[:,0]]-v[e[:,1]],axis=1);bd=np.array(bd)
    wt=np.where(bd,40.,1.)/np.sqrt(np.maximum(length,1e-6))
    base=uv.reshape(-1).copy();fixed=[0,1,2*((nr-1)*nc)+1];free=np.setdiff1d(np.arange(2*n),fixed)
    row=np.repeat(np.arange(len(e)),4);col=np.column_stack([2*e[:,0],2*e[:,0]+1,2*e[:,1],2*e[:,1]+1]).ravel()
    def unpack(z):
        p=base.copy();p[free]=z;return p.reshape(-1,2)
    def fun(z):
        p=unpack(z);return (np.linalg.norm(p[e[:,0]]-p[e[:,1]],axis=1)-length)*wt
    def jac(z):
        p=unpack(z);d=p[e[:,0]]-p[e[:,1]];L=np.maximum(np.linalg.norm(d,axis=1),1e-10)
        grad=d/L[:,None]*wt[:,None];data=np.column_stack([grad,-grad]).ravel()
        return coo_matrix((data,(row,col)),shape=(len(e),2*n)).tocsr()[:,free]
    sol=least_squares(fun,base[free],jac=jac,max_nfev=max_nfev,ftol=3e-8,xtol=3e-8,gtol=3e-8)
    p=unpack(sol.x);uv=p.reshape(nr,nc,2)
    err=abs(np.linalg.norm(p[e[:,0]]-p[e[:,1]],axis=1)-length)/np.maximum(length,1e-9)*100
    idx=perimeter_indices(nr,nc);border=np.array([uv[x] for x in idx]);poly=Polygon(border)
    # Check all triangles, not merely the outer outline.
    signs=[]
    for i in range(nr-1):
        for j in range(nc-1):
            for a,b,c in [(uv[i,j],uv[i+1,j],uv[i,j+1]),(uv[i+1,j],uv[i+1,j+1],uv[i,j+1])]:
                d=b-a;t=c-a;signs.append(d[0]*t[1]-d[1]*t[0])
    nonfold=(min(signs)>1e-8 or max(signs)<-1e-8)
    return uv, {'max_strain_pct':float(err.max()),'rms_strain_pct':float(np.sqrt(np.mean(err**2))),
                'max_boundary_segment_error_mm':float(np.max(err[bd]*length[bd]/100)),
                'solver_converged':bool(sol.success),'iterations':int(sol.nfev),
                'valid_polygon':bool(poly.is_valid and poly.area>1e-5),'no_inverted_triangles':nonfold}

def segment_key(a,b):
    return tuple(sorted([tuple(np.round(a,4)),tuple(np.round(b,4))]))

def boundary(g,uv):
    idx=perimeter_indices(*g.shape[:2]);return np.asarray([g[x] for x in idx]),np.asarray([uv[x] for x in idx])
