#!/usr/bin/env python3
"""Rebuild missing R04/R05 patterns and reports without changing existing CAD.
Original sources are retained byte-for-byte. Two archival-path-only adaptations
are explicit below. New exports are not represented as historical byte copies.
"""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,tempfile,time
import pymupdf as fitz
from PIL import Image,ImageGrab
ROOT=Path(__file__).resolve().parents[1]
BRANCH='sync/r01-r06-20261002'
HASHES={
 'revisions/R04/source/build_report.py':'701b0a99e08311eeedc7899ab9f6388c98f706594e07018e95eaf8d47c672706',
 'revisions/R04/source/make_patterns.py':'53b7ade595f9c2570f8f32b248876b1d760862d44ec05089ce0a9f6e6da4c7b6',
 'revisions/R04/source/check_package.py':'9f99af7d0564f067d1aa5dd6afb0ef6f0a2ccc7cb2fd2530745a3f6cb687ed99',
 'revisions/R05/source/build_report_r05.py':'1a5de001df92922e077d6afb97a3cb418e6b2cb747e1181cae3afacfae4453a9',
 'revisions/R05/source/make_patterns_r05.py':'cdddfd587df99dda3b0664e8c6a2e2ce20a3d56ac9735611486ec408ff7073de',
 'revisions/R05/source/verify_r05.py':'cb6a8de67f28b2b50674d5ed432e4dcd73ac6a031d53f8af4abe2da8e4655fec'}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(*args,cwd=None):
 print('RUN',*map(str,args),flush=True)
 subprocess.run(list(map(str,args)),cwd=cwd or ROOT,check=True,timeout=500)
def py(p):run(sys.executable,p,cwd=p.parent.parent)
def adapted(p,old,new):
 source=p.read_text()
 if source.count(old)!=1:raise ValueError('Adapter anchor mismatch: '+str(p))
 ns={'__file__':str(p),'__name__':'__main__'}
 sys.path.insert(0,str(p.parent))
 try:exec(compile(source.replace(old,new),str(p),'exec'),ns)
 finally:sys.path.pop(0)
def capture(args,target,env,inkscape=False):
 target.parent.mkdir(parents=True,exist_ok=True)
 log=target.with_suffix('.log')
 with log.open('w') as f:
  app=subprocess.Popen(list(map(str,args)),env=env,stdout=f,stderr=subprocess.STDOUT)
  try:
   time.sleep(12)
   if app.poll() is not None:raise RuntimeError('Viewer exited before screenshot: '+str(args))
   if inkscape:
    ids=subprocess.check_output(['xdotool','search','--onlyvisible','--class','Inkscape'],env=env,text=True).split()
    if not ids:raise RuntimeError('Inkscape window missing')
    wid=ids[-1]
    subprocess.run(['xdotool','windowsize',wid,'1560','1020'],env=env,check=True)
    subprocess.run(['xdotool','windowactivate','--sync',wid],env=env,check=True)
    subprocess.run(['xdotool','key','5'],env=env,check=True)
    time.sleep(3)
   ImageGrab.grab(xdisplay=env['DISPLAY']).save(target)
  finally:
   app.terminate()
   try:app.wait(timeout=5)
   except subprocess.TimeoutExpired:app.kill();app.wait()
def main():
 for name,h in HASHES.items():
  if digest(ROOT/name)!=h:raise ValueError('Original source checksum differs: '+name)
 preserved={p.relative_to(ROOT).as_posix():digest(p) for p in (ROOT/'revisions/R06').rglob('*') if p.is_file()}
 report={'source_sha256':HASHES,'workflow_run_id':os.getenv('GITHUB_RUN_ID'),'added':[],'groups':[],'failures':[],
 'adapters':['R04 report: omit the final copy to /mnt/data; output remains in revision/docs.',
 'R05 verifier: run checks before the final archival ZIP checksum step; verify the emitted result explicitly. No ZIP is introduced in Git.',
 'Recovered PDF receives a bottom-margin provenance line; preserved historical text and design remain, actual run metadata is in this report.'],
 'existing_CAD_overwritten':False,'new_engineering_design':False}
 with tempfile.TemporaryDirectory() as td:
  tmp=Path(td)
  for rev in ['R04','R05']:shutil.copytree(ROOT/'revisions'/rev,tmp/rev)
  for rev in ['R04','R05']:
   r=tmp/rev
   for d in ['docs','screenshots','patterns/pieces','renders','tests','history','calculations']:(r/d).mkdir(parents=True,exist_ok=True)
   try:
    if rev=='R04':
     if not (r/'project.json').exists():
      p=json.loads((r/'history/project_R02.json').read_text())
      p['revision']='R04 cloth/hinged-cover study';p['hand_heater']={'installed':False,'power_W':0,'wiring':False}
      p['zones']=[z for z in p['zones'] if z['id']!=3]
      p['hood']={'type':'passive fabric flip-up canopy','x_limits_mm':[965,1325],'half_width_mm':335,'rise_mm':165,'hinge_z_mm':545,'open_angle_deg':105,'hinge_side':'+Y','electrical_parts':0,'unheated':True}
      p['model_status']='Nominal surface model + uncalibrated cloth drape experiment. No CLO/Rhino/Blender run.'
      (r/'project.json').write_text(json.dumps(p,indent=2,ensure_ascii=False))
     py(r/'source/make_patterns.py');run('xvfb-run','-a',sys.executable,r/'source/render_simulation.py')
     py(r/'source/check_package.py')
     pattern=r/'patterns/pieces/HC_OUTER.svg';layout=r/'patterns/review_layout.svg'
    else:
     py(r/'source/make_patterns_r05.py');run('xvfb-run','-a',sys.executable,r/'source/render_r05.py')
     py(r/'source/check_pad_interference.py')
     p=r/'source/verify_r05.py';source=p.read_text();cut="archive=ROOT/'history/Spim_s_haski_Lezhandr_R04_original.zip'"
     if source.count(cut)!=1:raise ValueError('Unexpected R05 verifier trailer')
     exec(compile(source.split(cut)[0],str(p),'exec'),{'__file__':str(p),'__name__':'__main__'})
     pattern=r/'patterns/main_wrap_layout.svg';layout=pattern
    checks=json.loads((r/'tests/verification.json').read_text())
    if checks['passed']!=checks['total']:raise RuntimeError('Verification failed: '+rev)
    run('inkscape',layout,'--export-type=png','--export-width=1700','--export-filename='+str(r/'renders/pattern_layout.png'))
    env={**os.environ,'DISPLAY':':94','NO_AT_BRIDGE':'1'}
    x=subprocess.Popen(['Xvfb',':94','-screen','0','1600x1100x24','-nolisten','tcp'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(2)
    wm=subprocess.Popen(['openbox'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(1)
    try:
     if rev=='R04':
      for state in ['closed','open']:capture([sys.executable,r/'source/viewer.py','--state',state],r/f'screenshots/VTK_actual_{state}.png',env)
      capture(['inkscape','--with-gui','--app-id-tag=R04Restore',pattern],r/'screenshots/Inkscape_actual_HC_OUTER.png',env,True)
     else:
      capture([sys.executable,r/'source/render_r05.py','--viewer','cutaway'],r/'screenshots/VTK_R05_actual.png',env)
      capture(['inkscape','--with-gui','--app-id-tag=R05Restore',pattern],r/'screenshots/Inkscape_R05_actual.png',env,True)
    finally:
     wm.terminate();x.terminate();wm.wait(timeout=5);x.wait(timeout=5)
    if rev=='R04':
     adapted(r/'source/build_report.py',"shutil.copyfile(OUT,'/mnt/data/Lezhandr_R04_modeling_report.pdf')",'# Export remains in docs; no off-repository copy.')
     pdf=r/'docs/Lezhandr_R04_modeling_report.pdf';expected=12
     from reportlab.pdfgen import canvas
     from reportlab.lib.units import mm
     pieces=json.loads((r/'patterns/patterns_R04.json').read_text());pp=next(p for p in pieces if p['id']=='HC_OUTER')
     import numpy as np
     from shapely.geometry import Polygon
     xy=np.array(pp['vertices_2d_mm']);poly=Polygon(xy[pp['boundary']]);cutpoly=poly.buffer(12,join_style=2);a,b,c,d=cutpoly.bounds
     cv=canvas.Canvas(str(r/'patterns/HC_OUTER_plotter_DRAFT_1to1.pdf'),pagesize=((c-a+60)*mm,(d-b+85)*mm))
     for po in [cutpoly,poly]:
      path=cv.beginPath();pts=list(po.exterior.coords);path.moveTo((pts[0][0]-a+30)*mm,(pts[0][1]-b+30)*mm)
      for px,pyy in pts[1:]:path.lineTo((px-a+30)*mm,(pyy-b+30)*mm)
      cv.drawPath(path)
     cv.setFont('Helvetica',10);cv.drawString(25*mm,(d-b+62)*mm,'HC_OUTER - DRAFT 1:1 mm - 12 mm allowance')
     cv.line(25*mm,15*mm,125*mm,15*mm);cv.drawString(25*mm,8*mm,'CHECK 100 mm / print actual size');cv.save()
    else:
     py(r/'source/build_report_r05.py');pdf=r/'docs/Lezhandr_R05_design_report.pdf';expected=14
    with fitz.open(pdf) as doc:
     if doc.page_count!=expected:raise ValueError('Unexpected PDF page count')
     for i,page in enumerate(doc):
      page.insert_text((36,page.rect.height-5),'Rebuilt in GitHub Actions from preserved source; see provenance/LATE_DOCUMENT_COMPLETION.json.',fontsize=6,color=(.25,.3,.3))
      if i in [0,3,expected-2]:page.get_pixmap(matrix=fitz.Matrix(.6,.6)).save(r/'screenshots'/f'restored_report_page_{i+1:02}.png')
     out=pdf.with_suffix('.checked.pdf');doc.save(out)
    out.replace(pdf)
    report['groups'].append({'revision':rev,'checks':checks['total'],'report_pages':expected})
    for p in sorted(r.rglob('*')):
     if not p.is_file() or '__pycache__' in p.parts or p.suffix in ['.pyc','.zip']:continue
     dst=ROOT/'revisions'/rev/p.relative_to(r)
     if dst.exists():continue
     if p.stat().st_size>=99*1024*1024:raise ValueError('Oversized output')
     if p.suffix=='.pdf':
      with fitz.open(p) as doc:
       if doc.page_count<1:raise ValueError('Empty PDF')
       doc[0].get_pixmap(matrix=fitz.Matrix(.1,.1))
     dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dst)
     report['added'].append({'path':dst.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p),'origin':'regenerated from preserved sources and existing CAD'})
   except Exception as e:
    import traceback;traceback.print_exc();report['failures'].append({'revision':rev,'error':str(e)})
 for name,h in preserved.items():
  if digest(ROOT/name)!=h:raise ValueError('R06 unexpectedly changed: '+name)
 report['R06_existing_files_unchanged']=len(preserved)
 out=ROOT/'provenance/LATE_DOCUMENT_COMPLETION.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 paths=[x['path'] for x in report['added']]+[str(out.relative_to(ROOT))]
 for i in range(0,len(paths),100):run('git','add','-f','--',*paths[i:i+100])
 run('git','config','user.name','github-actions[bot]');run('git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
 run('git','commit','-m',f'Publish {len(report["added"])} missing R04/R05 textile patterns, renders and PDF reports')
 for attempt in range(5):
  run('git','pull','--rebase','origin',BRANCH)
  if subprocess.run(['git','push','origin','HEAD:refs/heads/'+BRANCH],cwd=ROOT).returncode==0:break
  time.sleep(3)
 else:raise RuntimeError('Unable to push without concurrent branch change')
 print('ADDED',len(report['added']),'FAILURES',report['failures'],flush=True)
 if report['failures']:raise SystemExit(1)
if __name__=='__main__':main()
