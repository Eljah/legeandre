#!/usr/bin/env python3
"""Restore 122 missing paths identified by the original SHA-256 comparison.
Read from a pinned Git commit, never rename regenerated data as an original.
No existing files are replaced. Blank historical logs are genuinely zero bytes.
"""
from pathlib import Path
import hashlib,json,subprocess,os,time
ROOT=Path(__file__).resolve().parents[1]
BASE='1b2f76ca5236031297c0d7720335f8581b89b5bf'
BRANCH='sync/r01-r06-20261002'
PAIRS=[]
def pair(dst,src):PAIRS.append((dst,src))
def group(dst,src,names):
 for name in names.splitlines():
  if name.strip():pair(dst+'/'+name.strip(),src+'/'+name.strip())
boards='''A1_4zone_power_BOM.csv
A1_4zone_power_layout.svg
A1_4zone_power_netgraph.json
A2_sensor_watchdog_BOM.csv
A2_sensor_watchdog_layout.svg
A2_sensor_watchdog_netgraph.json'''
group('revisions/R02/electronics','revisions/R01/electronics',boards)
group('revisions/R02/history/R01/electronics','revisions/R01/electronics',boards)
group('revisions/R02/history/R01/cad','revisions/R01/cad','''parts_sleep.csv
parts_work.csv
stl/lezhandr_sleep.stl
stl/lezhandr_work.stl
stock_cutting.csv
stock_nesting.csv
stock_nesting.json''')
views='''sleep_front.png
sleep_iso.png
sleep_side.png
sleep_top.png
work_frame.png
work_front.png
work_iso.png
work_section.png
work_side.png
work_top.png'''
group('revisions/R02/history/R01/cad/renders','revisions/R01/cad/renders',views)
group('revisions/R02/history/R01/docs/assets','revisions/R01/docs/assets',views)
group('revisions/R02/history/R01/docs','revisions/R01/docs','''calculations.json
heat_balance.csv
heater_calculation.csv
patterns.csv
runtime_scenarios.csv''')
group('revisions/R02/history/R01/tests/results','revisions/R01/tests/results','''A1_4zone_power_connectivity.json
A1_4zone_power_geometry_check.json
A1_4zone_power_routing.json
A2_sensor_watchdog_connectivity.json
A2_sensor_watchdog_geometry_check.json
A2_sensor_watchdog_routing.json
cad_sleep.json
cad_work.json''')
blank='revisions/R04/screenshots/VTK_actual_closed.log'
for name in ['screenshot_capture.log','viewer_closed.log','viewer_open.log','xvfb.log','xvfb_inkscape.log']:pair('revisions/R04/tests/'+name,blank)
pair('revisions/R05/history/R04/model_R04.json','revisions/R04/cad/model_R04.json')
pair('revisions/R05/history/R04/project.json','revisions/R04/project.json')
sources='''build_report.py
build_study.py
check_package.py
cloth_solver.py
make_patterns.py
render_model.py
render_simulation.py
viewer.py'''
group('revisions/R05/history/R04/source','revisions/R04/source',sources)
dst='revisions/R05/history/Spim_s_haski_Lezhandr_R04_original_unpacked/Lezhandr_R04'
group(dst,'revisions/R04','''cad/model_R04.json
exchange/Lezhandr_R04_sleep_mm.obj
exchange/Lezhandr_R04_work_closed_mm.obj
exchange/Lezhandr_R04_work_open_mm.obj
patterns/pieces/HC_HINGE.svg
patterns/pieces/HC_LIMIT_STRAP.svg
patterns/pieces/HC_LINING.svg
patterns/pieces/HC_OUTER.svg
patterns/pieces/HC_RIB_SLEEVE.svg
patterns/surfaces_R04.json
project.json
renders/keyboard_closed.png
renders/keyboard_open.png
renders/sleep.png
renders/technical.png
renders/work_closed.png
renders/work_foot.png
renders/work_open.png
renders/work_side.png
renders/work_top.png
simulation/filler_sensitivity.json
simulation/foot_quilt_drape.npz
simulation/hood_drape.npz
simulation/hood_history.csv
simulation/rejected_trials/sleep_quilt_metrics.json
simulation/sleep_quilt_drape.npz
simulation/sleep_quilt_metrics.json
source/build_report.py
source/build_study.py
source/check_package.py
source/cloth_solver.py
source/make_patterns.py
source/render_model.py
source/render_simulation.py
source/viewer.py
tests/STEP_sleep.json
tests/STEP_work_closed.json
tests/STEP_work_open.json
tests/body_bounds.json
tests/hood_clearances.json
tests/report_flow.json
tests/verification.json''')
pair(dst+'/history/project_R02.json','revisions/R02/project.json')
for name in ['screenshot_capture.log','viewer_closed.log','viewer_open.log','xvfb.log','xvfb_inkscape.log']:pair(dst+'/tests/'+name,blank)
for name in ['openbox.log','xvfb.log']:pair('revisions/R05/tests/'+name,blank)
pair('revisions/R06/history/R05/project.json','revisions/R05/project.json')
pair('revisions/R06/history/R05/render_r05.py','revisions/R05/source/render_r05.py')
for name in ['final_pipeline.log','pdf_render.log','postbuild.log']:pair('revisions/R06/tests/'+name,blank)
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def main():
 if len(PAIRS)!=122 or len({d for d,s in PAIRS})!=122:raise ValueError('History mapping count differs')
 rows=[];added=[]
 for dst,src in PAIRS:
  data=git('show',BASE+':'+src);p=ROOT/dst
  if p.exists():
   if p.read_bytes()!=data:raise ValueError('Existing destination conflict: '+dst)
  else:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);added.append(dst)
  rows.append({'path':dst,'source':src,'source_commit':BASE,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'source_matches_original_snapshot':True})
 out=ROOT/'provenance/EXACT_HISTORY_COPIES.json';out.write_text(json.dumps({'workflow_run_id':os.getenv('GITHUB_RUN_ID'),'added':len(added),'verified':rows,'existing_files_overwritten':False},ensure_ascii=False,indent=2)+'\n')
 paths=added+[out.relative_to(ROOT).as_posix()]
 for i in range(0,len(paths),80):git('add','-f','--',*paths[i:i+80])
 git('config','user.name','github-actions[bot]');git('config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
 git('commit','-m',f'Restore {len(added)} byte-identical historical paths from pinned existing files')
 for _ in range(5):
  git('pull','--rebase','origin',BRANCH)
  if subprocess.run(['git','push','origin','HEAD:refs/heads/'+BRANCH],cwd=ROOT).returncode==0:break
  time.sleep(3)
 else:raise RuntimeError('Concurrent branch update; no force push attempted')
 print('EXACT_COPIES_RESTORED',len(added))
if __name__=='__main__':main()
