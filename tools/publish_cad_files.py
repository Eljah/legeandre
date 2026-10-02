#!/usr/bin/env python3
"""Recover missing CAD files in GitHub only; keep existing R05/R06 untouched.
Original source bytes are restored from hash-addressed GitHub Git blobs. Missing
exports are rebuilt, not claimed to be byte-identical historical exports.
"""
from pathlib import Path
import base64, datetime, hashlib, json, os, subprocess, sys, urllib.request, zlib
ROOT=Path(__file__).resolve().parents[1]
REPO='Eljah/legeandre'
BRANCH='sync/r01-r06-20261002'
SEEDS={
 '9fff17bd30e6000617b4e83bfe3e868e8c1bfd46':'revisions/R04/source/build_study.py',
 '627a5637b443c26a7e46a7f08d60f5e042bc3256':'revisions/R04/source/cloth_solver.py',
 '8cc351b638c93bcd11e982712ef84afd28628b5d':'revisions/R04/source/render_model.py',
 '2c431a8eea82a44e5063e21419f3ddd77655b380':'revisions/R02/project.json',
 'ca82522422fad648e2544ef32604786ab6b1edb8':'revisions/R02/harness/routes_R02.json'}
HASHES={
 'revisions/R01/cad/source/build_cad.py':'3c629a814287ecb280a97240bb8c5f3a962d8f637b1ff02dc8897a84d7d37da8',
 'revisions/R02/cad/source/build_cad.py':'2113db7313510d02ecec5f72d44bc7a6dc27ac48800e751ba88caa4f55d144c6',
 'revisions/R04/source/build_study.py':'9062651179d9dfd2d9238bff1effe6310415980fad2ae2875302a198510cc326',
 'revisions/R04/source/cloth_solver.py':'e957a35a90c150c01cd2f8dbff31daeed50268cb052ffcbb93bca743f04d8fc9',
 'revisions/R04/source/render_model.py':'1080c4cfaf39529aba5c8c07fb9f5ad0b7f536765f1aa49ff28e65230238eeca'}

def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()

def run(*args):
 print('RUN',*args,flush=True)
 subprocess.run(args,cwd=ROOT,check=True)

def git(*args):
 return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()

def restore():
 for sha,path in SEEDS.items():
  request=urllib.request.Request(f'https://api.github.com/repos/{REPO}/git/blobs/{sha}',headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json','User-Agent':'legeandre-cad-recovery'})
  with urllib.request.urlopen(request,timeout=60) as f:response=json.load(f)
  packed=base64.b64decode(response['content'])
  if hashlib.sha1(f'blob {len(packed)}\0'.encode()+packed).hexdigest()!=sha:raise ValueError('Transport Git SHA mismatch')
  row=json.loads(zlib.decompress(packed));data=row['content'].encode('utf-8')
  if row['path']!=path or hashlib.sha256(data).hexdigest()!=row['sha256']:raise ValueError('Source checksum mismatch '+path)
  p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True)
  if p.exists() and p.read_bytes()!=data:raise ValueError('Existing source conflict '+path)
  p.write_bytes(data)
  print('ORIGINAL_SOURCE_RESTORED',path,len(data),flush=True)
 for p,h in HASHES.items():
  if digest(ROOT/p)!=h:raise ValueError('Original CAD builder changed: '+p)

def main():
 if os.environ.get('GITHUB_REPOSITORY')!=REPO or os.environ.get('GITHUB_REF')!='refs/heads/'+BRANCH:raise RuntimeError('Unexpected target')
 before={p.relative_to(ROOT).as_posix():digest(p) for r in ['R05','R06'] for p in (ROOT/'revisions'/r).rglob('*') if p.is_file()}
 start=git('rev-parse','HEAD');main_before=git('ls-remote','origin','refs/heads/main').split()[0]
 restore()
 for r in ['R01','R02']:
  root=ROOT/'revisions'/r
  for sub in ['cad/step','cad/stl','cad/dxf','cad/renders','tests/results']:(root/sub).mkdir(parents=True,exist_ok=True)
  if not (root/'cad/step/lezhandr_work.step').exists():
   run('xvfb-run','-a',sys.executable,str(root/'cad/source/build_cad.py'))
  if r=='R01' and not (root/'cad/renders/work_section.png').exists():run('xvfb-run','-a',sys.executable,str(root/'cad/source/section_cut.py'))
 root=ROOT/'revisions/R04'
 if not (root/'cad/Lezhandr_R04_work_closed.step').exists():run('xvfb-run','-a',sys.executable,str(root/'source/build_study.py'))
 if not (root/'renders/work_open.png').exists():run('xvfb-run','-a',sys.executable,str(root/'source/render_model.py'))
 # Re-read ALL standalone STEP assemblies, including the already published latest design.
 import cadquery as cq
 expected_counts={'R01':2,'R02':2,'R04':3,'R05':7,'R06':9}
 geometry=[]
 for rev,count in expected_counts.items():
  paths=sorted((ROOT/'revisions'/rev/'cad').rglob('*.step'))
  if len(paths)!=count:raise ValueError(f'{rev}: expected {count} STEP assemblies, got {len(paths)}')
  for p in paths:
   shape=cq.importers.importStep(str(p)).val()
   if not shape.isValid():raise ValueError('Invalid STEP '+str(p))
   b=shape.BoundingBox();geometry.append({'path':p.relative_to(ROOT).as_posix(),'valid':True,'solids':len(shape.Solids()),'faces':len(shape.Faces()),'bounds_mm':[b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax],'bytes':p.stat().st_size,'sha256':digest(p)})
   print('STEP_READBACK_OK',geometry[-1]['path'],flush=True)
 for path,sha in before.items():
  if digest(ROOT/path)!=sha:raise ValueError('Existing R05/R06 changed unexpectedly: '+path)
 import ezdxf
 dxf=[]
 for rev in expected_counts:
  for p in (ROOT/'revisions'/rev/'cad').rglob('*.dxf'):
   d=ezdxf.readfile(p);a=d.audit()
   if a.errors or a.fixes:raise ValueError('DXF audit issue '+str(p))
   dxf.append(p.relative_to(ROOT).as_posix())
 source_analogue=json.loads((ROOT/'provenance/CAD_ORIGINAL_SIGNATURES.json').read_text())
 comparisons=[]
 for old in source_analogue:
  current=next(x for x in geometry if x['path']==old['path'])
  delta=max(abs(a-b) for a,b in zip(current['bounds_mm'],old['bounds_mm']))
  ok=current['faces']==old['faces'] and current['solids']==old['solids'] and delta<0.02
  comparisons.append({'path':old['path'],'topology_and_bounds_match':ok,'max_bounds_delta_mm':delta,'original_sha256':old['original_sha256'],'published_sha256':current['sha256'],'byte_exact_original':old['original_sha256']==current['sha256']})
  if not ok:raise ValueError('Rebuilt geometry differs from original signature: '+old['path'])
 file_roots=['revisions/R01/cad','revisions/R01/tests/results','revisions/R02/cad','revisions/R02/tests/results','revisions/R04/cad','revisions/R04/source','revisions/R04/renders','revisions/R04/simulation','revisions/R04/exchange','revisions/R04/tests','revisions/R04/patterns']
 payload=list(SEEDS.values())
 for root in file_roots:
  for p in (ROOT/root).rglob('*'):
   if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ['.pyc','.zip','.nbc','.nbi']:
    if p.stat().st_size>99*1024**2:raise ValueError('Oversized Git file')
    payload.append(p.relative_to(ROOT).as_posix())
 payload=sorted(set(payload))
 for i in range(0,len(payload),80):git('add','-f','--',*payload[i:i+80])
 changed=git('diff','--cached','--name-only').splitlines()
 report={'status':'CAD_ASSEMBLIES_PUBLISHED_AND_READBACK_VERIFIED','repository':REPO,'branch':BRANCH,'parent_commit':start,'workflow_run_id':os.environ['GITHUB_RUN_ID'],'verified_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'step_counts':expected_counts,'step_total':len(geometry),'step_files':geometry,'dxf_files_audited':dxf,'source_sha256':HASHES,'original_signature_comparisons':comparisons,'existing_R05_R06_files_preserved':len(before),'changed_payload_files':changed,'project_zip_files_added':0,'export_provenance':'Missing exports rebuilt from byte-verified original sources in Actions; existing R05/R06 not changed. Export timestamps and raster encoders may differ from old attachments.','scope':'CAD and CAD-related views only. Full historical PDF/embroidery/software synchronization is a separate task.','force_push':False,'main_before':main_before}
 out=ROOT/'provenance/CAD_PUBLISH_VERIFICATION.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 git('add','--',str(out.relative_to(ROOT)))
 git('config','user.name','github-actions[bot]');git('config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
 git('commit','-m','Publish missing historical CAD files and verify all 23 R01-R06 STEP assemblies')
 git('pull','--rebase','origin',BRANCH);git('push','origin','HEAD:refs/heads/'+BRANCH)
 commit=git('rev-parse','HEAD')
 if git('ls-remote','origin','refs/heads/'+BRANCH).split()[0]!=commit:raise ValueError('Remote commit mismatch')
 if git('ls-remote','origin','refs/heads/main').split()[0]!=main_before:raise ValueError('Main changed concurrently')
 print('CAD_PUBLISHED_SUCCESS',commit,len(changed),'files; 23 STEP valid; R06 unchanged',flush=True)
 with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f:f.write(f'# CAD published\n\nCommit `{commit}`\n\n23 STEP assemblies reopened successfully. {len(changed)} payload paths added. Existing R05/R06 files unchanged. No ZIP committed.\n')
if __name__=='__main__':main()
