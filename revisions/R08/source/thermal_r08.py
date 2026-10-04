#!/usr/bin/env python3
"""R08 heat balance after removal of passive metal link. Assumptions are not test data."""
from pathlib import Path
import json,csv
import numpy as np
from scipy.sparse import lil_matrix,diags
from scipy.sparse.linalg import spsolve
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'thermal'
P={'passive_laptop_to_body_G_W_K':0,'target_receiver_C':31,'assumed_skin_boundary_C':33,'lining_R_m2K_W':[.12,.35,.75],'backing_R_m2K_W':.45,'inplane_k_times_thickness_W_K':.006,'reference_ambient_C':10,'heating_power_limits_W':{'back':20,'seat':20},'baseline_model':'Steady 2D finite volumes; imposed skin temperature, not human thermoregulation. No long metal heat path exists in R08. No manufacturer mat qualified.','envelope_target_C':26,'body_sensible_W':55,'laptop_heat_W':35,'retained_air_fraction':[0,.15,.3],'quilt_R_m2K_W':[.8,1.2,1.6],'air_changes_m3_h':[4,10,20],'through_seam_fraction_assumed':.04,'through_seam_R_m2K_W':.22,'surface_R_m2K_W':.18,'software_cutoff_candidate_C':37,'sleep_heating_allowed':False}
(OUT/'assumptions.json').write_text(json.dumps(P,indent=2))
rows=[];checks=[]
def solve(L,W,ambient,Rbody,power,spacing):
 nx=round(L/spacing);ny=round(W/spacing);hx=L/nx;hy=W/ny;A=hx*hy;n=nx*ny;K=lil_matrix((n,n));kt=P['inplane_k_times_thickness_W_K']
 for y in range(ny):
  for x in range(nx):
   i=y*nx+x
   for j,g in ([(i+1,kt*hy/hx)] if x+1<nx else [])+([(i+nx,kt*hx/hy)] if y+1<ny else []):K[i,i]+=g;K[j,j]+=g;K[i,j]-=g;K[j,i]-=g
 bodyG=A/Rbody;backG=A/P['backing_R_m2K_W'];M=K.tocsr()+diags(np.full(n,bodyG+backG));xx,yy=np.meshgrid(np.arange(nx),np.arange(ny));mask=(xx>=1)&(xx<nx-1)&(yy>=1)&(yy<ny-1);q=mask.ravel()*power/mask.sum();rhs=q+bodyG*33+backG*ambient;T=spsolve(M,rhs)
 residual=power+bodyG*np.sum(33-T)-backG*np.sum(T-ambient)
 return T.reshape(ny,nx),float(residual)
for name,L,W in [('back',.5,.42),('seat',.365,.42)]:
 for Ta in [0,10,20]:
  for Rbody in P['lining_R_m2K_W']:
   t0,_=solve(L,W,Ta,Rbody,0,.02);t1,_=solve(L,W,Ta,Rbody,1,.02);gain=t1.mean()-t0.mean();q=max(0,min(20,(31-t0.mean())/gain));t,res=solve(L,W,Ta,Rbody,q,.02)
   row={'zone':name,'ambient_C':Ta,'lining_R_m2K_W':Rbody,'area_m2':L*W,'laptop_direct_W':0,'heater_W':q,'min_C':float(t.min()),'mean_C':float(t.mean()),'max_C':float(t.max()),'residual_W':res};rows.append(row);checks.append(abs(res)<1e-7)
   if Ta==10 and Rbody==.35:
    np.savez(OUT/(name+'_receiver.npz'),temperature_C=t,length_m=L,width_m=W)
    plt.figure(figsize=(8,5));plt.imshow(t,origin='lower',extent=[0,L*1000,0,W*1000],aspect='auto');plt.colorbar(label='Temperature, C');plt.title(f'R08 {name}: direct laptop heat = 0 W; electric heat {q:.2f} W');plt.xlabel('mm');plt.ylabel('mm');plt.tight_layout();plt.savefig(OUT/(name+'_receiver.png'),dpi=170);plt.close()
# Grid convergence at the same imposed power, not a change in design demand.
conv=[]
ref=next(r for r in rows if r['zone']=='back' and r['ambient_C']==10 and r['lining_R_m2K_W']==.35)
for dx in [.04,.02,.01]:
 t,r=solve(.5,.42,10,.35,ref['heater_W'],dx);conv.append({'dx_m':dx,'mean_C':float(t.mean()),'max_C':float(t.max()),'balance_W':r})
# Compute visible cover area from sampled CAD skins, excluding duplicate seam strips/liners.
panels=json.loads((ROOT/'patterns/panel_grids.json').read_text());area=0;areas={}
for o in panels:
 if o['material']!='outer' or not o['parent'].startswith(('L08','S08','H08')):continue
 g=np.array(o['grid_mm']);a=g[:-1,:-1];b=g[1:,:-1];c=g[:-1,1:];d=g[1:,1:];A=float((np.linalg.norm(np.cross(b-a,c-a),axis=2).sum()+np.linalg.norm(np.cross(d-b,c-b),axis=2).sum())*.5e-6);area+=A;areas[o['id']]=A
sweep=[]
for Ta in [0,10,20]:
 for R in P['quilt_R_m2K_W']:
  for vent in P['air_changes_m3_h']:
   for fraction in P['retained_air_fraction']:
    G=area*(.96/(R+.18)+.04/(.22+.18))+1.3/1.28+.25+1.2*1005*vent/3600
    demand=max(0,G*(26-Ta)-55-35*fraction)
    sweep.append({'ambient_C':Ta,'R_m2K_W':R,'airflow_m3_h':vent,'laptop_retained_fraction':fraction,'heat_loss_W':G*(26-Ta),'body_assumption_W':55,'laptop_assumption_W':35*fraction,'electric_deficit_W':demand,'within_52W_budget':demand<=52})
for path,data in [('receiver_cases.json',rows),('grid_convergence.json',conv),('envelope_sweep.json',sweep),('CAD_area_basis.json',{'cover_area_m2':area,'panel_areas_m2':areas,'note':'Nominal surfaces include hood. Open face and actual air exchange remain unmeasured; not a sleeping-bag rating.'})]: (OUT/path).write_text(json.dumps(data,indent=2))
for filename,data in [('receiver_cases.csv',rows),('envelope_sweep.csv',sweep)]:
 with (OUT/filename).open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,data[0].keys());w.writeheader();w.writerows(data)
(OUT/'verification.json').write_text(json.dumps({'all_energy_balances_pass':all(checks),'cases':len(rows),'max_abs_residual_W':max(abs(r['residual_W']) for r in rows),'direct_heat_link_removed':True,'hardware_control_updated':False,'physiological_validation':False},indent=2))
print('THERMAL',len(rows),len(sweep),'area',area,flush=True)
