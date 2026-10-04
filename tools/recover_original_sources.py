#!/usr/bin/env python3
"""Restore ONLY complete, SHA-256-verified original files from known GitHub bytes.
The source payload is never executed. The incomplete final tar entry is rejected.
No external storage, no network hosts except api.github.com, no main branch writes.
"""
from pathlib import Path, PurePosixPath
import base64,hashlib,io,json,lzma,os,subprocess,tarfile,urllib.request
REPO='Eljah/legeandre';BRANCH='sync/r01-r06-20261002'
SHAS=['4ef78f7aab0c247d375246d49782900833b51953','091f0d93b0d8cb59f1ea56fc511d135b3ad60508','65a42021c6fb97faf113616de709d8f548dfa5f5','e0cec51802a117c07c7f2743c7995ac4b5502c77','41824cd30743af79f6135acd31ece0e9cab8592f','56642f8507e2c910d61e3c3b0c7b7b8dc964a704','02092f1f3518f585e3c875b91c587a096fe4cf5c','19519cecc0375446378c62c1682a33ddfdb2f99f','25e6e0139b8cb402605e63ac04ce95f39f1300cc','1f3e5205a7bc075c7d18180e94ba04d84c17993c','f5e88bcbbe735ef01a83729d0c618ca675625412']
PREFIX_SHA256='5b33412c234fc6f9e702fb9683d2156388b696fe0f565364dd2592d5a38a7ba2'
MANIFEST_SHA256='2d595942a045b58237233cd68150aa783541c58bd94e24804a70b5f797007f93'
def sha(data):return hashlib.sha256(data).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],text=True).strip()
def main():
 if os.environ.get('GITHUB_REPOSITORY')!=REPO or os.environ.get('GITHUB_REF')!='refs/heads/'+BRANCH:raise RuntimeError('Wrong repository/ref')
 start=git('rev-parse','HEAD');parts=[]
 for h in SHAS:
  request=urllib.request.Request('https://api.github.com/repos/'+REPO+'/git/blobs/'+h,headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json'})
  with urllib.request.urlopen(request,timeout=60) as r:obj=json.load(r)
  b=base64.b64decode(obj['content']);actual=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
  if len(b)!=12000 or actual!=h:raise ValueError('Object mismatch')
  parts.append(b)
 compressed=b''.join(parts)
 if sha(compressed)!=PREFIX_SHA256:raise ValueError('Prefix mismatch')
 # We intentionally restore complete records, not claim a complete XZ stream.
 expanded=lzma.LZMADecompressor(memlimit=128*1024*1024).decompress(compressed,max_length=2*1024*1024)
 if len(expanded)!=865148:raise ValueError('Unexpected decoded length')
 tf=tarfile.open(fileobj=io.BytesIO(expanded),mode='r:');first=tf.next()
 if first.name!='paths.json' or first.size!=73868:raise ValueError('Unexpected manifest')
 manifest_bytes=expanded[first.offset_data:first.offset_data+first.size]
 if sha(manifest_bytes)!=MANIFEST_SHA256:raise ValueError('Manifest checksum mismatch')
 manifest=json.loads(manifest_bytes)
 if manifest['format']!='legeandre-source-seed-v1' or len(manifest['files'])!=559:raise ValueError('Manifest format')
 objects={}
 while True:
  try:m=tf.next()
  except tarfile.ReadError:break
  if m is None:break
  if not m.isfile() or len(m.name)!=64 or any(c not in '0123456789abcdef' for c in m.name):raise ValueError('Unexpected data record')
  end=m.offset_data+m.size
  if end>len(expanded):break
  b=expanded[m.offset_data:end]
  if sha(b)!=m.name:raise ValueError('Record checksum mismatch')
  objects[m.name]=b
 if len(objects)!=160:raise ValueError('Unexpected recovered object count')
 restored=[]
 for path,h in manifest['files']:
  rel=PurePosixPath(path)
  if rel.is_absolute() or '..' in rel.parts or '.git' in rel.parts or '\\' in path or len(rel.parts)<3 or rel.parts[0]!='revisions' or rel.parts[1] not in ['R01','R02','R03','R04','R05','R06']:raise ValueError('Invalid project path')
  if h not in objects:continue
  p=Path(path);b=objects[h]
  if p.exists() and p.read_bytes()!=b:raise ValueError('Existing file differs: '+path)
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
  restored.append({'path':path,'sha256':h,'bytes':len(b)})
 if len(restored)!=460:raise ValueError('Recovered path count mismatch')
 for row in restored:
  if sha(Path(row['path']).read_bytes())!=row['sha256']:raise ValueError('Write verification failed')
 report=Path('provenance/SOURCE_SEED_RECOVERY.json');report.parent.mkdir(exist_ok=True)
 result={'status':'460_ORIGINAL_FILES_RECOVERED_NOT_FULL_SNAPSHOT','original_files_restored':460,'unique_content_objects':160,'manifest_sha256':MANIFEST_SHA256,'partial_stream_sha256':PREFIX_SHA256,'source_seed_total':559,'full_snapshot_total':1551,'source_code_executed':False,'main_modified':False,'force_push':False,'workflow_run_id':os.environ['GITHUB_RUN_ID'],'files':restored}
 report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 paths=[x['path'] for x in restored]+[str(report)]
 for i in range(0,len(paths),100):git('add','-f','--',*paths[i:i+100])
 if git('ls-remote','origin','refs/heads/'+BRANCH).split()[0]!=start:raise RuntimeError('Concurrent branch change; not pushing')
 git('config','user.name','github-actions[bot]');git('config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
 git('commit','-m','Restore 460 original electronics, firmware, application and CAD source files with SHA-256 verification')
 git('push','origin','HEAD:refs/heads/'+BRANCH)
 print('RESTORED',len(restored),'COMMIT',git('rev-parse','HEAD'))
if __name__=='__main__':main()
