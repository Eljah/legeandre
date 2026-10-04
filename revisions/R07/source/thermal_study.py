#!/usr/bin/env python3
"""R07 conditional heat study: finite-volume tray/pads + lumped envelope.
No CFD, no human thermoregulation, no measured laptop boundary condition.
All reported power is heat, never charger nameplate power.
"""
from pathlib import Path
import json, math, csv
import numpy as np
from scipy.sparse import lil_matrix,diags
from scipy.sparse.linalg import spsolve, factorized
from scipy.optimize import brentq
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'thermal';OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'figure.dpi':140})
def js(name,x):(OUT/name).write_text(json.dumps(x,ensure_ascii=False,indent=2,default=lambda x:x.item() if isinstance(x,np.generic) else x.tolist()))
def csvout(name,rows):
 if not rows:return
 with (OUT/name).open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,rows[0].keys());w.writeheader();w.writerows(rows)
P={'k_copper_W_mK':391.0,'k_NiCr80_W_mK':15.0,'k_Al6061_W_mK':167.0,'rho_Cu_kg_m3':8910.,'rho_Al_kg_m3':2700.,'cp_Al_J_kgK':896.,
   'sigma_W_m2K4':5.670374419e-8,'length_wire_m':.6,'wire_diameter_mm':.2,'wire_count':1000,
   'tray_thickness_m':.002,'tray_length_m':.4135,'tray_width_m':.68,'tray_metal_fraction':.82,
   'tray_h_top_W_m2K':6.,'tray_h_bottom_W_m2K':3.,'tray_eps':.15,'air_under_tray_C':26.,
   'collector_contact_R_K_W':1.5,'collector_ambient_G_W_K':.08,'capturable_fraction_of_laptop_heat':.15,
   'receiver_setpoint_C':31.,'skin_boundary_C':33.,'receiver_clothing_R_m2K_W':.12,'receiver_backing_R_m2K_W':.45,
   'receiver_inplane_k_times_t_W_K':.006,'receiver_heat_capacity_J_m2K':1200.,
   'back_size_m':[.50,.60],'seat_size_m':[.50,.45],'electrical_max_W':[20.,20.,12.],
   'controller_target_C':31.,'controller_software_trip_C':37.,'session_limit_s':1800,
   'envelope_target_microclimate_C':26.,'body_sensible_heat_into_envelope_W':55.,
   'laptop_air_retained_fraction':.15,'quilt_test_resistance_m2K_W':1.2,'quilt_seam_fraction':.10,'quilt_seam_R_m2K_W':.22,
   'inner_outer_surface_R_m2K_W':.18,'back_bottom_effective_area_m2':1.30,'back_bottom_R_m2K_W':1.10,
   'fixed_other_G_W_K':.25,'ventilation_m3_h':4.,'rho_air_kg_m3':1.2,'cp_air_J_kgK':1005.,
   'important':'Project assumptions unless material-property source is cited. 37 C software threshold is not a certified skin limit.'}
js('assumptions.json',P)
# Analytical metal transport bounds: both ends fixed, insulated sides, no contacts.
wireA=1000*math.pi*(.0002/2)**2
options=[('1000 Cu wires, d=0.2 mm',391,wireA,.6),('1000 NiCr wires, d=0.2 mm',15,wireA,.6),('Cu braid total 100 mm2',391,100e-6,.6),('Cu foil 100x0.5 mm',391,50e-6,.6),('2 Al tubes 45x25x2.5 mm',167,2*(.045*.025-.040*.020),1.0)]
bounds=[]
for name,k,A,L in options:
 bounds.append({'option':name,'k_W_mK':k,'area_mm2':A*1e6,'length_m':L,'G_W_K':k*A/L,'Q_at_20K_W':k*A/L*20,'Q_at_5K_W':k*A/L*5,'metal_mass_kg':A*L*(8910 if k==391 else (8300 if k==15 else 2700))})
js('metal_transport_bounds.json',bounds);csvout('metal_transport_bounds.csv',bounds)
A20=20*.6/(391*20);wire_length_scale=math.sqrt(391*math.pi*.0002**2/4/(10*math.pi*.0002))
js('metal_key_results.json',{'Cu_area_to_carry_20W_over_0_6m_at_20K_mm2':A20*1e6,'Cu_mass_for_that_case_kg':A20*.6*8910,'uninsulated_0_2mm_wire_fin_length_m_h10':wire_length_scale,'scope':'Ideal lower bound on metal mass; real contacts and fin losses worsen result.'})
# Finite-volume grid, no flux on side edges; nodes at cell centers.
def mesh(L,W,dx,k_t):
 nx=round(L/dx);ny=round(W/dx);hx=L/nx;hy=W/ny;n=nx*ny;A=hx*hy
 K=lil_matrix((n,n))
 def link(i,j,g):K[i,i]+=g;K[j,j]+=g;K[i,j]-=g;K[j,i]-=g
 for iy in range(ny):
  for ix in range(nx):
   i=iy*nx+ix
   if ix+1<nx:link(i,i+1,k_t*hy/hx)
   if iy+1<ny:link(i,i+nx,k_t*hx/hy)
 x=(np.arange(nx)+.5)*hx;y=(np.arange(ny)+.5)*hy-W/2
 return K.tocsr(),x,y,A
# Heat deposited at four support-contact regions; metal fraction homogenizes holes.
def tray(Pheat=35,Ta=10,dx=.02,braid=True,emit_map=False):
 k_t=P['k_Al6061_W_mK']*.002*P['tray_metal_fraction'];K,x,y,A=mesh(P['tray_length_m'],P['tray_width_m'],dx,k_t);nx=len(x);ny=len(y);n=nx*ny
 xx,yy=np.meshgrid(x,y);q=np.zeros(n);source_mask=np.zeros((ny,nx),bool)
 for sx in [.095,.280]:
  for sy in [-.177,.177]:source_mask|=(abs(xx-sx)<.025)&(abs(yy-sy)<.018)
 q[source_mask.ravel()]=Pheat*.15/max(1,source_mask.sum())
 tap=np.argmin((xx-.13)**2+(yy+.27)**2);G=.0651666667 if braid else 0.
 T=np.full(n,(Ta+26)/2);it=0
 for it in range(40):
  kel=T+273.15;radG=P['tray_eps']*P['sigma_W_m2K4']*(kel+(Ta+273.15))*(kel**2+(Ta+273.15)**2)*A
  topG=(P['tray_h_top_W_m2K']*A+radG)*P['tray_metal_fraction'];botG=np.full(n,P['tray_h_bottom_W_m2K']*A*P['tray_metal_fraction'])
  diag=topG+botG;rhs=q+topG*Ta+botG*26;diag[tap]+=G;rhs[tap]+=G*31
  M=K+diags(diag);new=spsolve(M,rhs)
  if max(abs(new-T))<1e-8:T=new;break
  T=new
 # Terms calculated from solved balance, both signs reported.
 qoutside=float(np.sum(topG*(T-Ta)));qinside=float(np.sum(botG*(T-26)));qpad=G*(T[tap]-31)
 residual=float(q.sum()-qoutside-qinside-qpad)
 row={'laptop_heat_W':Pheat,'ambient_C':Ta,'assumed_heat_into_tray_W':float(q.sum()),'tray_min_C':float(T.min()),'tray_mean_C':float(T.mean()),'tray_max_C':float(T.max()),'tray_pickup_C':float(T[tap]),'net_to_pad31C_W':float(qpad),'loss_to_outside_W':qoutside,'net_to_inner_air_W':qinside,'balance_residual_W':residual,'cells':n,'iterations':it+1,'link_connected':braid}
 if emit_map:
  np.savez(OUT/f'tray_{int(Ta)}C.npz',temperature_C=T.reshape(ny,nx),x_m=x,y_m=y,heat_W=q.reshape(ny,nx))
  plt.figure(figsize=(9,5));plt.imshow(T.reshape(ny,nx),origin='lower',extent=[0,P['tray_length_m']*1000,-340,340],aspect='auto');plt.colorbar(label='Температура столика, °C');plt.xlabel('Вдоль столика, мм');plt.ylabel('Поперёк, мм');plt.title(f'2D конечные объёмы: {Pheat:g} Вт ноутбук, {Ta:g} °C снаружи\nВ металл условно поступает {q.sum():.2f} Вт');plt.tight_layout();plt.savefig(OUT/'tray_temperature.png');plt.close()
 return row
trayrows=[tray(w,t) for t in [0,10,20] for w in [10,35,65]];tray(35,10,emit_map=True)
js('tray_cases.json',trayrows);csvout('tray_cases.csv',trayrows)
conv=[tray(35,10,dx=dx) for dx in [.04,.02,.01]];js('mesh_convergence_tray.json',conv)
# Thermally isolated collector, controlled receiver temperature 31 C, one-way coupling.
# R of low-R option is a specification target, NOT a rated commercial heat pipe.
def collector(laptopW=35,Tcase=42,Ta=10,G=.5):
 cap=laptopW*P['capturable_fraction_of_laptop_heat'];Gc=1/P['collector_contact_R_K_W'];Ga=P['collector_ambient_G_W_K'];Ts=31.
 def equation(t):return min(cap,max(0,Gc*(Tcase-t)))-Ga*(t-Ta)-max(0,G*(t-Ts))
 if cap==0 or Tcase<=Ta:return {'collector_C':Ta,'recovered_W':0.,'source_captured_W':0.,'collector_loss_W':0.,'balance_residual_W':0.}
 tc=brentq(equation,Ta,Tcase)
 q=max(0,G*(tc-Ts));qc=min(cap,max(0,Gc*(Tcase-tc)));qa=Ga*(tc-Ta)
 return {'collector_C':tc,'recovered_W':q,'source_captured_W':qc,'collector_loss_W':qa,'balance_residual_W':qc-qa-q}
crec=[]
for ta in [0,10,20]:
 for w,tcase in [(10,33),(35,42),(65,50)]:
  for name,G in [('Cu_1000_threads',391*wireA/.6),('Cu_100mm2',391*100e-6/.6),('isolated_lowR_target',.5)]:
   crec.append(dict(ambient_C=ta,laptop_heat_W=w,assumed_case_C=tcase,transport=name,G_total_W_K=G,**collector(w,tcase,ta,G)))
js('isolated_collector_cases.json',crec);csvout('isolated_collector_cases.csv',crec)
# 2D distributed receiver, fixed 33 C clothed-skin boundary and backing towards ambient.
# Sensible body heat emerges from the flux; not counted as another source here.
def receiver(which='back',Ta=10,Qrec=1.,Pelec=0.,dx=.025,with_map=False):
 W,L=P[which+'_size_m'];K,x,y,A=mesh(L,W,dx,P['receiver_inplane_k_times_t_W_K']);ny=len(y);nx=len(x);n=nx*ny
 top=np.full(n,A/P['receiver_clothing_R_m2K_W']);bottom=np.full(n,A/P['receiver_backing_R_m2K_W']);M=K+diags(top+bottom)
 xx,yy=np.meshgrid(x,y)
 # Distributed bus along left margin: specified layout, not a perfectly isothermal fabric.
 contact=(yy<-.17)&(xx>.1*L)&(xx<.9*L)
 qrec=np.zeros(n);qrec[contact.ravel()]=Qrec/contact.sum()
 pmap=np.full(n,Pelec/n)
 rhs=top*33+bottom*Ta+qrec+pmap
 T=spsolve(M,rhs)
 qs=float(np.sum(top*(33-T)));ql=float(np.sum(bottom*(T-Ta)))
 row={'zone':which,'ambient_C':Ta,'recovered_heat_W':Qrec,'electric_heat_W':Pelec,'Tmin_C':float(T.min()),'Tmean_C':float(T.mean()),'Tmax_C':float(T.max()),'heat_from_skin_W':qs,'loss_to_backing_W':ql,'balance_residual_W':Qrec+Pelec+qs-ql,'cells':n}
 if with_map:
  np.savez(OUT/f'{which}_receiver.npz',temperature_C=T.reshape(ny,nx),x_m=x,y_m=y)
  plt.figure(figsize=(8,5));plt.imshow(T.reshape(ny,nx),origin='lower',extent=[0,L*1000,-W*500,W*500],aspect='auto');plt.colorbar(label='Температура поверхности, °C');plt.xlabel('Длина, мм');plt.ylabel('Ширина, мм');plt.title(f'{"Спина" if which=="back" else "Сиденье"}: тепло по краевому коллектору\n{Qrec:.2f} Вт от ноутбука + {Pelec:.2f} Вт электронагрев');plt.tight_layout();plt.savefig(OUT/f'{which}_receiver_map.png');plt.close()
 return row
padrows=[]
for ta in [0,10,20]:
 qr=collector(35,42,ta,.5)['recovered_W']
 for zone in ['back','seat']:
  base=receiver(zone,ta,qr/2,0)
  # Uniform electric mat targets AREA MEAN, not minimum; coldest/hottest separately printed.
  L,W=P[zone+'_size_m'];A=L*W;Gtot=A*(1/.12+1/.45)
  power=np.clip((31-base['Tmean_C'])*Gtot,0,20)
  row=receiver(zone,ta,qr/2,power,with_map=ta==10);padrows.append(row)
js('receiver_cases.json',padrows);csvout('receiver_cases.csv',padrows)
js('mesh_convergence_receiver.json',[receiver('back',10,1.5,9,dx) for dx in [.05,.025,.0125]])
# Envelope: use CAD areas of each quilt exactly once, not two skins, not both flap positions.
geo=json.loads((OUT/'CAD_areas_lofts.json').read_text());Aleg=sum(g['outer_area_m2'] for g in geo if g['id'].startswith('L07'))
# Shoulder areas are legacy parts, estimate extracted BREP external area outside double skins separately.
Aupper=.85;Acover=Aleg+Aupper
js('envelope_area_basis.json',{'leg_quilt_outer_area_from_CAD_m2':Aleg,'shoulder_area_assumption_m2':Aupper,'total_quilt_area_used_m2':Acover,'hood_open_head_zone':'Not treated as airtight insulation; leakage treated independently. Head physiology excluded.'})
def envelope(Ta=10,R=1.2,Vdot=4,Ppc=35):
 f=.10;Rsurf=.18;U=(1-f)/(R+Rsurf)+f/(.22+Rsurf)
 Gq=Acover*U;Gb=1.3/1.1;Gvent=1.2*1005*Vdot/3600;G=Gq+Gb+Gvent+.25
 dT=26-Ta;ql=G*dT;qr=collector(Ppc,42 if Ppc==35 else (33 if Ppc==10 else 50),Ta,.5)['recovered_W'] if Ppc else 0
 qair=Ppc*.15;body=55.;need=max(0,ql-body-qair-qr)
 return {'ambient_C':Ta,'quilt_effective_R_m2K_W':R,'air_leak_m3_h':Vdot,'quilt_area_m2':Acover,'G_quilt_W_K':Gq,'G_backing_W_K':Gb,'G_vent_W_K':Gvent,'loss_at_26C_W':ql,'assumed_body_sensible_W':body,'assumed_laptop_air_W':qair,'laptop_recovered_W':qr,'additional_heat_needed_W':need,'heater_budget_W':52.,'budget_shortfall_W':max(0,need-52),'predicted_microclimate_at_max_C':Ta+(body+qair+qr+52)/G,'important':'Conditional uniform-air heat balance. Not body core temperature or a sleeping-bag rating; not additive to receiver table.'}
erows=[envelope(ta,R,v) for ta in [-10,0,10,20] for R in [.60,.868,1.20,1.80] for v in [1,4,12]]
js('envelope_sweep.json',erows)
csvout('envelope_sweep.csv',erows)
# Temperature-triggered electric backup; loss of laptop heat is an efficiency event, never a permission override.
# Back and seat only, 12 W foot channel is not in this transient, accounting is explicit.
def transient(dt=1.):
 areas=np.array([.3,.225]);C=areas*1200;Gs=areas/.12;Gb=areas/.45
 T=np.full(2,10.);I=np.zeros(2);rows=[]
 for step in range(int(2100/dt)+1):
  t=step*dt;pc=35 if t<900 else 0
  qr=collector(35,42,10,.5)['recovered_W'] if pc else 0
  enabled=t<1800
  e=31-T;I=np.clip(I+.010*e*dt,0,20)
  power=np.clip(6*e+I,0,20)
  if not enabled:power[:]=0;I[:]=0
  power[T>=37]=0
  rec=np.array([qr/2,qr/2]);new=(C/dt*T+Gs*33+Gb*10+rec+power)/(C/dt+Gs+Gb)
  if step%max(1,round(10/dt))==0:rows.append({'time_s':t,'laptop_heat_W':pc,'recovered_W':qr,'back_C':float(new[0]),'seat_C':float(new[1]),'electric_back_W':float(power[0]),'electric_seat_W':float(power[1]),'session_enabled':enabled})
  T=new
 return rows
tr=transient();js('transient.json',tr);csvout('transient.csv',tr)
plt.figure(figsize=(9,4.8));plt.plot([r['time_s']/60 for r in tr],[r['back_C'] for r in tr],label='Спина');plt.plot([r['time_s']/60 for r in tr],[r['seat_C'] for r in tr],label='Сиденье');plt.axvline(15,linestyle='--',label='Ноутбук перестал давать тепло');plt.axvline(30,linestyle=':',label='Окончание сеанса');plt.xlabel('Время, мин');plt.ylabel('Температура приёмной поверхности, °C');plt.title('Расчётный переходный процесс / снаружи 10 °C');plt.legend();plt.grid(alpha=.25);plt.tight_layout();plt.savefig(OUT/'transient_temperature.png');plt.close()
plt.figure(figsize=(9,4.8));plt.plot([r['time_s']/60 for r in tr],[r['electric_back_W']+r['electric_seat_W'] for r in tr],label='Два электрических мата');plt.plot([r['time_s']/60 for r in tr],[r['recovered_W'] for r in tr],label='Получено от ноутбука');plt.axvline(15,linestyle='--');plt.axvline(30,linestyle=':');plt.xlabel('Время, мин');plt.ylabel('Мощность, Вт');plt.title('Догрев компенсирует дефицит, а не заменяет защиты');plt.legend();plt.grid(alpha=.25);plt.tight_layout();plt.savefig(OUT/'transient_power.png');plt.close()
plt.figure(figsize=(9,5));
for R in [.60,.868,1.20,1.80]:
 yy=[envelope(ta,R,4)['additional_heat_needed_W'] for ta in [-10,0,10,20]]
 plt.plot([-10,0,10,20],yy,marker='o',label=f'R утеплителя = {R:g} м²К/Вт')
plt.axhline(52,linestyle='--',label='Проектный предел догрева 52 Вт');plt.ylabel('Требуемый догрев для микроклимата 26 °C, Вт');plt.xlabel('Наружная температура, °C');plt.title('Расчётные потери / утечка воздуха 4 м³/ч');plt.legend(fontsize=9);plt.grid(alpha=.25);plt.tight_layout();plt.savefig(OUT/'envelope_heat_requirement.png');plt.close()
# Fin analysis curve: known temperature at origin, distributed transverse losses to Ta.
xx=np.linspace(0,.6,200);lc=wire_length_scale
Twire=10+30*np.cosh((.6-xx)/lc)/np.cosh(.6/lc)
plt.figure(figsize=(9,4.5));plt.plot(xx*1000,Twire);plt.xlabel('Расстояние вдоль Cu-проволоки 0,2 мм, мм');plt.ylabel('Температура, °C');plt.title('Неизолированная нить: у основания 40 °C, воздух 10 °C, h=10 Вт/(м²К)');plt.grid(alpha=.25);plt.tight_layout();plt.savefig(OUT/'wire_fin.png');plt.close()
# Sensitivity of the isolated option: validates value range, not an approved heat exchanger.
sens=[]
for rc in [.5,1.5,5,15]:
 for ga in [.03,.08,.25]:
  oldrc=P['collector_contact_R_K_W'];oldga=P['collector_ambient_G_W_K'];P['collector_contact_R_K_W']=rc;P['collector_ambient_G_W_K']=ga
  sens.append(dict(Rcontact_K_W=rc,Gambient_W_K=ga,**collector(35,42,10,.5)))
  P['collector_contact_R_K_W']=oldrc;P['collector_ambient_G_W_K']=oldga
js('collector_sensitivity.json',sens)
# Verification independent balance and grid studies; fails do not get relabelled as pass.
checks=[{'test':'tray energy balance','passed':max(abs(r['balance_residual_W']) for r in trayrows)<1e-6},
 {'test':'collector energy balance','passed':max(abs(r['balance_residual_W']) for r in crec)<1e-7},
 {'test':'receiver energy balance','passed':max(abs(r['balance_residual_W']) for r in padrows)<1e-7},
 {'test':'capture never exceeds laptop heat allocation','passed':all(r['source_captured_W']<=r['laptop_heat_W']*.15+1e-8 for r in crec)},
 {'test':'thermal disconnect forbids reverse heat flow','passed':all(r['recovered_W']>=0 for r in crec)},
 {'test':'timeout 30 min removes electric power','passed':all(r['electric_back_W']==0 and r['electric_seat_W']==0 for r in tr if r['time_s']>=1800)},
 {'test':'calculated pad temperature below software trip in these cases','passed':all(r['Tmax_C']<37 for r in padrows)},
 {'test':'refined tray peak difference < 0.8 C','passed':abs(conv[-1]['tray_max_C']-conv[-2]['tray_max_C'])<.8,'delta_C':abs(conv[-1]['tray_max_C']-conv[-2]['tray_max_C'])}]
js('verification.json',{'checks':checks,'passed':sum(c['passed'] for c in checks),'total':len(checks),'does_not_validate':['skin safety','device cooling','CFD','cloth compression','thermal interfaces','real heater temperatures','human comfort']})
print('THERMAL DONE',len(erows),'envelope scenarios',flush=True)
print('MAIN ENVELOPE', [envelope(ta) for ta in [0,10,20]],flush=True)
print('MAIN METAL',bounds,flush=True)
