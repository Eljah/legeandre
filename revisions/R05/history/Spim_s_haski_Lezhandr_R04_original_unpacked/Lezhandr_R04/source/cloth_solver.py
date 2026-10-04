"""Small, inspectable distance-constraint cloth experiment, SI units.
Executed with NumPy/Numba, NOT the solver of CLO, Blender or ExactFlat.
Uncalibrated edge compliances; a study of drape/clearances, NOT material FEM.
"""
import numpy as np
from numba import njit

def grid_faces(nu,nv):
    out=[]
    for i in range(nu-1):
        for j in range(nv-1):
            a=i*nv+j;b=a+nv
            out.extend(((a,b,b+1),(a,b+1,a+1)))
    return np.asarray(out,dtype=np.int32)

def constraints(p,nu,nv,slack=1.0):
    edges=[];comp=[]
    for i in range(nu):
        for j in range(nv):
            a=i*nv+j
            for di,dj,c in [(1,0,2e-5),(0,1,2e-5),(1,1,1e-4),(1,-1,1e-4),(2,0,.03),(0,2,.03)]:
                ii=i+di;jj=j+dj
                if ii<nu and 0<=jj<nv:
                    edges.append((a,ii*nv+jj));comp.append(c)
    e=np.asarray(edges,np.int32)
    rest=np.linalg.norm(p[e[:,0]]-p[e[:,1]],axis=1)*slack
    return e,rest,np.asarray(comp,np.float64)

@njit(cache=True)
def _integrate(p0,edges,rest,compliance,pins,inv_mass,steps,iterations,dt,floor,ell,damping):
    p=p0.copy(); vel=np.zeros_like(p);n=len(p)
    track=np.zeros((steps,4));saved=np.zeros((5,n,3));sf=np.array([0,steps//4,steps//2,3*steps//4,steps-1])
    lamb=np.zeros(len(edges))
    for step in range(steps):
        old=p.copy()
        for k in range(n):
            if inv_mass[k]>0:
                vel[k,2]-=9.81*dt;p[k]+=dt*vel[k]
        lamb[:]=0
        for it in range(iterations):
            # Alternate order reduces the sweep bias of the Gauss-Seidel solver.
            for ee in range(len(edges)):
                e=ee if it%2==0 else len(edges)-1-ee
                a=edges[e,0];b=edges[e,1]; d=p[b]-p[a]
                length=np.sqrt((d*d).sum());w=inv_mass[a]+inv_mass[b]
                if length<1e-12 or w==0:continue
                alpha=compliance[e]/(dt*dt)
                dl=(-(length-rest[e])-alpha*lamb[e])/(w+alpha)
                lamb[e]+=dl
                corr=(dl/length)*d
                p[a]-=inv_mass[a]*corr;p[b]+=inv_mass[b]*corr
            for k in range(n):
                if inv_mass[k]==0:
                    p[k]=p0[k];continue
                if p[k,2]<floor:p[k,2]=floor
                if ell[3]>0:
                    # One analytic collision envelope, not a deformable human.
                    d=(p[k]-ell[:3])/ell[3:]
                    q=(d*d).sum()
                    if q<1.0:
                        if q<1e-12:d[2]=1.;q=1.
                        p[k]=ell[:3]+(d/np.sqrt(q))*ell[3:]
        for k in range(n):
            if inv_mass[k]>0:vel[k]=(p[k]-old[k])/dt*damping
            else:vel[k,:]=0
        disp=np.sqrt(((p-p0)**2).sum(axis=1));change=np.sqrt(((p-old)**2).sum(axis=1))
        track[step]=np.array([(step+1)*dt,disp.max(),change.max(),np.sqrt((vel*vel).sum(axis=1)).max()])
        for z in range(5):
            if step==sf[z]:saved[z]=p
    return p,track,saved

def solve(p,nu,nv,pins,area,rho=.35,steps=240,iterations=30,dt=1/120,slack=1.002,floor=0,ell=None,damping=.975):
    edges,rest,compliance=constraints(p,nu,nv,slack)
    inv=np.ones(len(p))*len(p)/(area*rho);inv[pins]=0
    if ell is None:ell=np.array([0,0,0,0,0,0.],float)
    out,track,saved=_integrate(p,edges,rest,compliance,np.asarray(pins,np.int32),inv,steps,iterations,dt,floor,np.asarray(ell,float),damping)
    strain=np.linalg.norm(out[edges[:,0]]-out[edges[:,1]],axis=1)/rest-1
    mask=compliance<.01
    metrics={'vertices':len(p),'triangles':2*(nu-1)*(nv-1),'distance_constraints':len(edges),'steps':steps,'iterations_per_step':iterations,
             'velocity_damping_per_step':damping,'dt_s':dt,'time_s':steps*dt,'areal_density_kg_m2':rho,'area_m2':area,'model_mass_kg':area*rho,
             'max_displacement_mm':float(np.max(np.linalg.norm(out-p,axis=1))*1000),
             'mean_displacement_mm':float(np.mean(np.linalg.norm(out-p,axis=1))*1000),
             'last_step_motion_mm':float(track[-1,2]*1000),'last_max_speed_m_s':float(track[-1,3]),
             'structural_strain_p95_pct':float(np.percentile(np.abs(strain[mask]),95)*100),
             'structural_strain_max_pct':float(np.max(np.abs(strain[mask]))*100),
             'max_pin_error_mm':float(np.max(np.linalg.norm(out[pins]-p[pins],axis=1))*1000),
             'note':'Uncalibrated XPBD distance network. No calibrated fabric bending law, foam/DEM, self-collision or thermal solve.'}
    return out,grid_faces(nu,nv),metrics,track,saved
