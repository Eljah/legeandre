#!/usr/bin/env python3
from pathlib import Path
import math,json,csv
R=Path(__file__).resolve().parents[1];p=json.loads((R/'project.json').read_text())
rho=1.09 # ohm mm2/m, Nikrothal80 datasheet; use only in engineering estimate
wire_d=.15;area=math.pi*wire_d**2/4;ohms_per_m=rho/area
rows=[]
for z in p['zones']:
 branches=round(z['watts']/2);branchR=72;length=branchR/ohms_per_m
 rows.append({**z,'parallel_branches':branches,'branch_R_ohm':branchR,'branch_length_m':length,'total_wire_m':length*branches,'current_A':12/z['ohms'],'W_per_m2':z['watts']/z['area_m2'],'full_power_at_13_2V_W':13.2**2/z['ohms']})
I=(.035**4-.031**4)/12;Z=I/(.035/2);F=120*9.81*1.5/2;L=.82
beam={'section_mm':'35x35x2','model':'simply supported single rail, one central force, conservative whole occupant shared by 2 rails; not assembly FEA','span_m':L,'force_N':F,'I_m4':I,'max_moment_Nm':F*L/4,'stress_MPa':F*L/4/Z/1e6,'deflection_mm':F*L**3/(48*69e9*I)*1000,'yield_strength':'not assumed; material/temper certificates required','pin_hinge_welds_fatigue_tip_stability':'NOT VALIDATED'}
energy=[]
for name,heat,laptop in [('Light',25,30),('Typical_assumption',40,45),('Maximum',60,100)]:
 demand=heat/.92+laptop/.9+2;energy.append({'case':name,'heat_W':heat,'laptop_W':laptop,'battery_input_W':demand,'hours':512*.8/demand})
thermal=[]
for ambient,gap in [(10,10),(0,15),(-10,40)]:
 # Scenario, no human thermal/comfort validation. Target effective warm-side 30 C.
 q=(2.5/1.25+.9/1.2)*(30-ambient)+gap
 thermal.append({'ambient_C':ambient,'assumed_gap_loss_W':gap,'envelope_loss_W':q,'useful_body_heat_assumed_W':60,'needed_electric_W':max(0,q-60),'available_W':60})
report={'heater_estimate':rows,'beam_screening':beam,'battery_scenarios':energy,'heat_balance_scenarios':thermal,'model_limitations':'No FEM/CFD, no clothing comfort model, no skin temperature validation. Wire geometry is a procurement/bench specification, NOT instructions to sew bare wire into clothing.'}
(R/'docs/calculations.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
for name,data in [('heater_calculation',rows),('runtime_scenarios',energy),('heat_balance',thermal)]:
 with (R/'docs'/f'{name}.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
print(json.dumps(report,ensure_ascii=False,indent=2))
