#!/usr/bin/env python3
"""Restore original individual files from verified Git blobs in this repository.
Existing files stay immutable. A differing historical original is kept under
variants/original_snapshot, never silently replacing a current version.
"""
from pathlib import Path, PurePosixPath
import base64, concurrent.futures, datetime, hashlib, io, json, lzma, os
import subprocess, tarfile, urllib.request
ROOT=Path(__file__).resolve().parents[1]
REPO='Eljah/legeandre';BRANCH='sync/r01-r06-20261002'
BLOBS=['00d3e186123dfb171f0823d2e0486f02318f1e25','ad5754a3404d142d63fcb40508c7a0205bba20fe','d2e65434e83b4c5c673ee5ef141c5967801eeda4','0697786acf86ec54460b907122ac062e0039a8ba','133c74f80f2ee36819dc42d0109a19266689486e','9a6a05adf2a764cc6c1e5bbfec52a4a4e63c7687','be750016fe52a5c69e730c692995f804385f4546','edd3ac49f7353191a871707125de730918b9229c','1e738999c62f743401e8324cdc60c2b9afbd90cd']
EXPECTED='2a62ac777af6926ed46936efe330b4215dfd2e2eefdf3d25a5af3bebc75a02e5'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
def sha256(b):return hashlib.sha256(b).hexdigest()
def gitsha(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def fetch_blob(sha):
 req=urllib.request.Request(f'https://api.github.com/repos/{REPO}/git/blobs/{sha}',headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json','User-Agent':'legeandre-original-recovery'})
 with urllib.request.urlopen(req,timeout=60) as stream:d=json.load(stream)
 if d['encoding']!='base64':raise ValueError('Unexpected blob encoding')
 b=base64.b64decode(d['content'])
 if gitsha(b)!=sha:raise ValueError('Git blob integrity failure '+sha)
 return b

def main():
 if os.getenv('GITHUB_REPOSITORY')!=REPO or git('branch','--show-current')!=BRANCH:raise RuntimeError('Wrong checkout')
 if git('status','--porcelain'):raise RuntimeError('Dirty checkout')
 parent=git('rev-parse','HEAD');main_before=git('ls-remote','origin','refs/heads/main').split()[0]
 before={p.relative_to(ROOT).as_posix():sha256(p.read_bytes()) for p in (ROOT/'revisions/R06').rglob('*') if p.is_file()}
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:packed=b''.join(pool.map(fetch_blob,BLOBS))
 if len(packed)!=96588 or sha256(packed)!=EXPECTED:raise ValueError('Combined transport hash mismatch')
 raw=lzma.decompress(packed)
 if len(raw)>2*1024*1024:raise ValueError('Unexpected payload size')
 files=[];seen=set();new=[];variants=[]
 with tarfile.open(fileobj=io.BytesIO(raw),mode='r:') as tf:
  for member in tf:
   rel=PurePosixPath(member.name)
   if not member.isfile() or member.issym() or member.islnk():raise ValueError('Regular files only')
   if rel.is_absolute() or '..' in rel.parts or '.git' in rel.parts or '\\' in member.name:raise ValueError('Unsafe path')
   if rel.parts[0] not in {'revisions','provenance'} or rel.suffix.lower()=='.zip':raise ValueError('Unexpected path')
   if member.name in seen:raise ValueError('Duplicate path')
   seen.add(member.name);data=tf.extractfile(member).read()
   if len(data)!=member.size:raise ValueError('Size mismatch')
   original_rel=str(rel);dest=ROOT/original_rel
   if dest.exists() and dest.read_bytes()!=data:
    rel=PurePosixPath('variants/original_snapshot')/rel
    variants.append({'original_path':original_rel,'preserved_current_sha256':sha256(dest.read_bytes()),'original_variant_path':str(rel)})
    dest=ROOT/str(rel)
   if dest.exists() and dest.read_bytes()!=data:raise RuntimeError('Historical variant already differs: '+str(rel))
   if not dest.exists():new.append(str(rel))
   dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
   files.append({'path':str(rel),'original_path':original_rel,'bytes':len(data),'sha256':sha256(data),'git_blob_sha1':gitsha(data)})
 if len(files)!=136:raise ValueError('Unexpected number of original files')
 for rel,h in before.items():
  if sha256((ROOT/rel).read_bytes())!=h:raise RuntimeError('Existing R06 changed: '+rel)
 report={'status':'ORIGINAL_REMAINDER_BYTES_VERIFIED','parent_commit':parent,'workflow_run_id':os.getenv('GITHUB_RUN_ID'),'verified_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files_verified':len(files),'new_original_files':len(new),'existing_R06_files_unchanged':len(before),'transport_sha256':EXPECTED,'files':files,'variants_preserved':variants,'main_before':main_before,'engineering_tests_rerun':False,'historical_logs_are_not_new_tests':True,'project_archives_tracked':False,'external_uploads':False,'force_push':False}
 report_path=ROOT/'provenance/ORIGINAL_REMAINDER_SEED.json';report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 paths=[f['path'] for f in files]+['provenance/ORIGINAL_REMAINDER_SEED.json']
 for i in range(0,len(paths),60):git('add','-f','--',*paths[i:i+60])
 for f in files:
  if git('rev-parse',':'+f['path'])!=f['git_blob_sha1']:raise RuntimeError('Index changed original file')
 git('config','user.name','github-actions[bot]');git('config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
 git('commit','-m',f'Restore {len(new)} missing original files and historical variants; preserve existing R06')
 git('push','origin','HEAD:refs/heads/'+BRANCH);commit=git('rev-parse','HEAD')
 if git('ls-remote','origin','refs/heads/'+BRANCH).split()[0]!=commit:raise RuntimeError('Remote verification failed')
 if git('ls-remote','origin','refs/heads/main').split()[0]!=main_before:raise RuntimeError('Main changed concurrently')
 print(f'SUCCESS originals={len(files)} newly_added={len(new)} commit={commit} R06_preserved={len(before)}')
 if os.getenv('GITHUB_STEP_SUMMARY'):
  with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as s:s.write(f'# Original files restored\n\n{len(new)} new individual files; {len(files)} SHA-256 and Git object checks.\n\nCommit `{commit}`. Existing R06 unchanged. Historical logs are not new engineering tests.\n')
if __name__=='__main__':main()
