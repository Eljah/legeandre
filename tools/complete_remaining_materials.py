#!/usr/bin/env python3
"""GitHub-only completion. Preserve existing designs; distinguish originals,
rebuilt exports and unavailable historical raster attachments explicitly.
"""
from pathlib import Path, PurePosixPath
from collections import Counter, defaultdict
import base64, concurrent.futures, datetime, hashlib, io, json, lzma, os, shutil
import subprocess, sys, tempfile, urllib.error, urllib.request
ROOT=Path(__file__).resolve().parents[1]
REPO='Eljah/legeandre';BRANCH='sync/r01-r06-20261002'
MANIFEST_BLOBS=['91f7254bf8ba10192016746b23b728b9bc036768','eabf0fdbe83c1c4812ae0b6c43c1fe8b30f1130b','8aae80336cc6f3b45308ba7eea52bd9e9c9a3985']
MANIFEST_SHA='04e25f3eee0d759a135538b8254c1620b7a5763de3b797b795058df2c7e82256'

def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
def digest(b):return hashlib.sha256(b).hexdigest()
def blobsha(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def fetch(sha,optional=False):
 req=urllib.request.Request(f'https://api.github.com/repos/{REPO}/git/blobs/{sha}',headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json','User-Agent':'legeandre-material-audit'})
 try:
  with urllib.request.urlopen(req,timeout=60) as f:d=json.load(f)
 except urllib.error.HTTPError as e:
  if optional and e.code==404:return None
  raise
 b=base64.b64decode(d['content'])
 if blobsha(b)!=sha:raise ValueError('Git blob checksum mismatch')
 return b

def inventory():
 paths=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
 return {p:blobsha((ROOT/p).read_bytes()) for p in paths if p and (ROOT/p).is_file()}

def safe(path):
 p=PurePosixPath(path)
 if p.is_absolute() or '..' in p.parts or '.git' in p.parts or '\\' in path:raise ValueError('Unsafe path')
 if p.suffix.lower()=='.zip':raise ValueError('Project archives must not be committed')
 return ROOT/path

def main():
 if os.getenv('GITHUB_REPOSITORY')!=REPO or git('branch','--show-current')!=BRANCH:raise RuntimeError('Wrong checkout')
 if git('status','--porcelain'):raise RuntimeError('Dirty checkout')
 parent=git('rev-parse','HEAD');main_before=git('ls-remote','origin','refs/heads/main').split()[0]
 r06_before={p.relative_to(ROOT).as_posix():digest(p.read_bytes()) for p in (ROOT/'revisions/R06').rglob('*') if p.is_file()}
 packed=b''.join(fetch(h) for h in MANIFEST_BLOBS)
 if digest(packed)!=MANIFEST_SHA:raise ValueError('Original manifest integrity failure')
 lines=lzma.decompress(packed).decode('utf-8').splitlines();expected=[]
 for line in lines:
  sha,size,path=line.split(' ',2);safe(path);expected.append({'path':path,'bytes':int(size),'git_blob_sha1':sha})
 if len(expected)!=1551:raise ValueError('Unexpected original inventory size')
 mp=ROOT/'provenance/EXPECTED_ORIGINAL_FILES.tsv';mp.write_text('\n'.join(lines)+'\n',encoding='utf-8')
 changes=['provenance/EXPECTED_ORIGINAL_FILES.tsv'];operations=[];before=inventory();bysha=defaultdict(list)
 for p,h in before.items():bysha[h].append(p)
 # Recover exact originals left as unreferenced Git objects by earlier transfers.
 absent={r['git_blob_sha1']:r for r in expected if not bysha.get(r['git_blob_sha1'])}
 def optional(h):return h,fetch(h,optional=True)
 recovered={}
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
  for h,data in pool.map(optional,absent):
   if data is not None:recovered[h]=data
 for r in expected:
  path=r['path'];sha=r['git_blob_sha1'];dest=safe(path)
  if dest.exists() and blobsha(dest.read_bytes())==sha:continue
  source=bysha.get(sha,[])
  data=(ROOT/source[0]).read_bytes() if source else recovered.get(sha)
  if data is None:continue
  actual=path if not dest.exists() else 'variants/original_snapshot/'+path
  out=safe(actual)
  if out.exists() and out.read_bytes()!=data:raise RuntimeError('Variant collision '+actual)
  if not out.exists():
   out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data);changes.append(actual)
   operations.append({'path':actual,'original_path':path,'method':'EXACT_ORIGINAL_BYTES','sha256':digest(data)})
  bysha[sha].append(actual)
 print('Original object recovery completed',len(operations),flush=True)
 # Recreate old R02 embroidery from original segmentation and original digitizer.
 # Use an isolated working copy. Never replace the current R03 design/codec.
 with tempfile.TemporaryDirectory(prefix='legeandre-r02-') as td:
  stage=Path(td)/'R02';shutil.copytree(ROOT/'revisions/R02',stage)
  original_codec=ROOT/'variants/original_snapshot/revisions/R02/embroidery/machine_formats.py'
  if original_codec.is_file():shutil.copyfile(original_codec,stage/'embroidery/machine_formats.py')
  for d in ['source','previews','machine']:(stage/'embroidery'/d).mkdir(parents=True,exist_ok=True)
  subprocess.run([sys.executable,str(stage/'embroidery/digitize_logo.py')],cwd=stage,check=True)
  import numpy as np
  from PIL import Image
  seg=np.load(stage/'embroidery/source/logo_segments.npz')
  Image.fromarray(seg['pal'][seg['labels']]).save(stage/'embroidery/previews/logo_quantized.png')
  for p in sorted((stage/'embroidery').rglob('*')):
   if not p.is_file() or '__pycache__' in p.parts or p.suffix in {'.pyc','.zip'}:continue
   rel='revisions/R02/'+p.relative_to(stage).as_posix();dest=safe(rel)
   if dest.exists():continue
   dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest);changes.append(rel)
   orig=next((r for r in expected if r['path']==rel),None)
   operations.append({'path':rel,'method':'R02_REBUILT_FROM_ORIGINAL_SEGMENTATION','sha256':digest(dest.read_bytes()),'byte_exact_original':bool(orig and blobsha(dest.read_bytes())==orig['git_blob_sha1'])})
  # Regenerate the missing old engineering album from its preserved source.
  # Reuse actual CAD renders and validated pattern/harness geometry, not AI art.
  for d in ['docs','tests/results']:(stage/d).mkdir(parents=True,exist_ok=True)
  subprocess.run([sys.executable,str(stage/'docs/build_review_pdf.py')],cwd=stage,check=True)
  for name in ['Lezhandr_R02_review.pdf','Lezhandr_R02_patterns_1to1.pdf']:
   p=stage/'docs'/name;rel='revisions/R02/docs/'+name;dest=safe(rel)
   if not dest.exists():shutil.copyfile(p,dest);changes.append(rel);operations.append({'path':rel,'method':'REPORT_REBUILT_FROM_PRESERVED_SOURCE','sha256':digest(dest.read_bytes()),'byte_exact_original':False})
 # The same R03 report is also requested at its original docs/ location.
 p=ROOT/'revisions/R03/Spim_s_haski_R03_sew_sheet.pdf';dest=ROOT/'revisions/R03/docs/Spim_s_haski_R03_sew_sheet.pdf'
 if p.is_file() and not dest.exists():
  dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest);rel=dest.relative_to(ROOT).as_posix();changes.append(rel);operations.append({'path':rel,'method':'ALIAS_OF_CURRENT_R03_REPORT','sha256':digest(dest.read_bytes()),'byte_exact_original':False})
 for rel,h in r06_before.items():
  if digest((ROOT/rel).read_bytes())!=h:raise RuntimeError('R06 design was changed: '+rel)
 # Verify PDF structure and generate actual page previews for review.
 import fitz
 qc=ROOT/'provenance/completion_previews';qc.mkdir(exist_ok=True)
 pdf=ROOT/'revisions/R02/docs/Lezhandr_R02_review.pdf'
 with fitz.open(pdf) as doc:
  if doc.page_count!=9:raise RuntimeError('Unexpected R02 PDF page count')
  for i in [0,1,5,7]:
   dest=qc/f'R02_report_page_{i+1:02}.png';doc[i].get_pixmap(matrix=fitz.Matrix(.7,.7)).save(dest);changes.append(dest.relative_to(ROOT).as_posix())
 # The audit deliberately keeps nonidentical regenerated exports separate from
 # originals, and lists still-unavailable raster attachments instead of hiding them.
 actual=inventory()
 for p in changes:actual[p]=blobsha((ROOT/p).read_bytes())
 bysha=defaultdict(list)
 for p,h in actual.items():bysha[h].append(p)
 rows=[];counts=Counter()
 for r in expected:
  p=r['path'];h=r['git_blob_sha1'];other=bysha.get(h,[])
  status='EXACT_AT_ORIGINAL_PATH' if actual.get(p)==h else ('EXACT_ORIGINAL_ELSEWHERE' if other else ('PRESENT_NONIDENTICAL_EXPORT' if p in actual else 'MISSING_ORIGINAL'))
  row=dict(r,status=status)
  if other and actual.get(p)!=h:row['exact_locations']=other
  if p in actual:row['published_git_blob_sha1']=actual[p]
  rows.append(row);counts[status]+=1
 report={'status':'AUDITED_REMAINDER_WITH_EXPLICIT_GAPS','repository':REPO,'branch':BRANCH,'parent_commit':parent,'workflow_run_id':os.getenv('GITHUB_RUN_ID'),'verified_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'expected_original_files':len(expected),'classification_counts':dict(counts),'new_paths':changes,'operations':operations,'existing_R06_files_unchanged':len(r06_before),'main_before':main_before,'force_push':False,'external_uploads':False,'rows':rows,'note':'Byte identity, regenerated export and unavailable original raster are different states. Historical source logs are not newly executed tests.'}
 out=ROOT/'provenance/REMAINING_FILES_AUDIT.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');changes.append(out.relative_to(ROOT).as_posix())
 missing=[r for r in rows if r['status']=='MISSING_ORIGINAL']
 text=['# Remaining original attachments','',f'Expected originals: {len(expected)}. Still missing: {len(missing)}.','', 'These entries are not silently replaced with generated images. Current R06 was preserved.','', '| Size, bytes | Original path |','|---:|---|']+[f"| {r['bytes']} | `{r['path']}` |" for r in missing]
 out=ROOT/'provenance/REMAINING_ORIGINALS.md';out.write_text('\n'.join(text)+'\n',encoding='utf-8');changes.append(out.relative_to(ROOT).as_posix())
 for i in range(0,len(changes),60):git('add','-f','--',*changes[i:i+60])
 git('config','user.name','github-actions[bot]');git('config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
 git('commit','-m','Restore historical R02 embroidery and PDF; publish complete original-file audit without modifying R06')
 git('push','origin','HEAD:refs/heads/'+BRANCH);commit=git('rev-parse','HEAD')
 if git('ls-remote','origin','refs/heads/'+BRANCH).split()[0]!=commit:raise RuntimeError('Push readback failed')
 if git('ls-remote','origin','refs/heads/main').split()[0]!=main_before:raise RuntimeError('Main changed concurrently')
 print('SUCCESS',commit,dict(counts),flush=True)
 if os.getenv('GITHUB_STEP_SUMMARY'):
  with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f:f.write(f'# Materials added and audited\n\nCommit `{commit}`.\n\nOriginal files: {len(expected)}. Classification: `{dict(counts)}`.\n\nExisting R06 unchanged. Remaining originals are explicitly listed in provenance/REMAINING_ORIGINALS.md.\n')
if __name__=='__main__':main()
