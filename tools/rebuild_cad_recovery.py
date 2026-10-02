#!/usr/bin/env python3
"""Rebuild R05/R06 from verified preserved sources. No redesign or external uploads.
Exports are labelled rebuilt, not byte-exact original PDF/STEP. Original source
hashes are enforced. Input grid coordinates are verified to 1e-8 mm, accommodating
only last-bit libm differences between the original container and Actions runner.
"""
from pathlib import Path
import hashlib,json,math,os,shutil,subprocess,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
HASHES={
'revisions/R05/source/build_r05.py':'e090fa9985a397ff33a0e8512acdd60b5799fe5a04b6d52e5416a1a112515eaf',
'revisions/R06/source/build_r06.py':'ae05002eeaac7bdeaae6cc63af32246837f219ae9394506ab0a5b562926b2d39',
'revisions/R06/source/render_r06.py':'84ec0f25a2e9734920ad12beddbcff5f063318e5095b32fafdcbfa40a632019f',
'revisions/R06/source/develop_samples.py':'0dd54b450171f3b19bdce1bf435b53912eabd7a6764d6e4a4e8b61036862824f',
'revisions/R06/source/verify_r06.py':'ffcfb40f9b0dc3afe86a3d6cdf5b90ff00c9dd20431e1281613c824e5d77bb6d',
'revisions/R06/source/build_report_r06.py':'196434a5350ab6d4fda47b222bfbd7e9c582b228a8b4554dd3fa729cba3235e8'}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(*args):subprocess.run(args,cwd=ROOT,check=True)
def ring(s,q):
 a=1080.;b=435.;c=1180.;head=(1-math.cos(s))/2
 h=155+285*head**4;r=100+22*math.sin(s)**2
 n=np.array([math.cos(s)/a,math.sin(s)/b]);n/=np.linalg.norm(n)
 center=np.array([c+a*math.cos(s),b*math.sin(s),h])
 return center+np.array([n[0]*r*math.cos(q),n[1]*r*math.cos(q),h*math.sin(q)])
def main():
 for p,h in HASHES.items():
  if digest(ROOT/p)!=h:raise RuntimeError('Source differs from preserved original: '+p)
 r05=ROOT/'revisions/R05';r06=ROOT/'revisions/R06'
 for root in [r05,r06]:
  for d in ['cad','patterns','calculations','tests','renders','screenshots','docs','history']:(root/d).mkdir(parents=True,exist_ok=True)
 patches=[]
 for k in range(12):
  for typ,q0,q1,kind in [('O',-math.pi/2,math.pi/2,'outer'),('L',math.pi/2,3*math.pi/2,'lining')]:
   ss=np.linspace(2*math.pi*k/12,2*math.pi*(k+1)/12,11);qq=np.linspace(q0,q1,17)
   grid=np.array([[ring(s,q) for q in qq] for s in ss]).tolist()
   patches.append({'id':f'{typ}{k+1:02}','grid_mm':grid,'material':kind,'seam_allowance_mm':12,'method':'approximate flattening; distortion reported separately'})
 canonical=[]
 for patch in patches:
  a=np.round(np.array(patch['grid_mm']),8);a[np.abs(a)<.5e-8]=0
  canonical.append({'id':patch['id'],'grid_mm':a.tolist()})
 fingerprint=hashlib.sha256(json.dumps(canonical,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 if fingerprint!='752172ec224091a877c9a31b27031d874a8c6b17e935f40358b8956a8ff718c7':raise RuntimeError('R04 geometry differs from original pinned grid')
 p=r05/'history/R04/surfaces_R04.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(patches,ensure_ascii=False,indent=2))
 exact_input=digest(p)=='7106784c8bbdc5f675e4b81e4b915ae376d15274728c09154de43e13edbd04f1'
 print('INPUT_GEOMETRY_VERIFIED precision_mm=1e-8 exact_serialized_bytes=',exact_input,flush=True)
 run(sys.executable,str(r05/'source/build_r05.py'))
 (r06/'history/R05').mkdir(exist_ok=True)
 shutil.copyfile(r05/'cad/Lezhandr_R05_rolled.step',r06/'history/R05/Lezhandr_R05_rolled.step')
 shutil.copyfile(r05/'source/build_r05.py',r06/'history/R05/build_r05.py')
 run(sys.executable,str(r06/'source/build_r06.py'))
 run(sys.executable,str(r06/'source/develop_samples.py'))
 run(sys.executable,str(r06/'source/verify_r06.py'))
 run('xvfb-run','-a',sys.executable,str(r06/'source/render_r06.py'))
 run('bash',str(r06/'source/capture_viewer.sh'))
 run(sys.executable,str(r06/'source/build_report_r06.py'))
 import fitz
 pdf=r06/'docs/Lezhandr_R06_CAD_review.pdf'
 with fitz.open(pdf) as doc:
  if doc.page_count!=14:raise RuntimeError('Unexpected report page count')
  for i in [0,1,8,12]:doc[i].get_pixmap(matrix=fitz.Matrix(1,1)).save(r06/'screenshots'/f'report_page_{i+1:02}.png')
 checks=json.loads((r06/'tests/verification.json').read_text())
 if not checks['all_checks_passed']:raise RuntimeError('CAD verification failed')
 files=[]
 for root in [r05,r06]:
  for p in sorted(root.rglob('*')):
   if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ['.pyc','.zip']:
    files.append({'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p)})
 report={'status':'R05_R06_REBUILT_FROM_ORIGINAL_VERIFIED_SOURCES','workflow_run_id':os.getenv('GITHUB_RUN_ID'),'source_hashes':HASHES,'r04_surface_bytes_match_original':exact_input,'r04_grid_fingerprint_1e8mm':fingerprint,'r06_step_files':len(list((r06/'cad').glob('*.step'))),'r06_checks_passed':checks['passed'],'r06_checks_total':checks['total'],'r06_pdf_pages':14,'files':files,'original_full_snapshot_count':1551,'full_original_snapshot_uploaded':False,'note':'New exports from original code; not a claim of byte-identical original PDF/STEP timestamps or complete historical file transfer. Original files are preserved in the conversation recovery inventory.'}
 out=ROOT/'provenance/CAD_REBUILD_RECOVERY.json';out.parent.mkdir(exist_ok=True);out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print('CAD_RECOVERY_OK',len(files),'files')
if __name__=='__main__':main()
