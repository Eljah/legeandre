#!/usr/bin/env python3
"""Import verified project bytes, never run CAD/firmware from the payload.
Temporary transport lives outside Git. Every delivered project file is committed
separately. The target is a fixed review branch; main and unrelated paths are not
changed. Request pins the hash; expiring URLs are read from an owner PR comment.
"""
from __future__ import annotations
from pathlib import Path, PurePosixPath
import concurrent.futures, datetime, hashlib, json, os, re, shutil
import subprocess, tarfile, tempfile, urllib.request, urllib.parse

ROOT=Path(__file__).resolve().parents[1]
REPO='Eljah/legeandre'
BRANCH='sync/r01-r06-20261002'
BASE='58e41ccf59d600797559f154038b58cd840c0312'

def git(*args: str) -> str:
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''):h.update(b)
    return h.hexdigest()

def safe_rel(name: str) -> PurePosixPath:
    p=PurePosixPath(name)
    if p.is_absolute() or not p.parts or '..' in p.parts or '.git' in p.parts or '\\' in name:
        raise ValueError('Unsafe archive path')
    if p.suffix.lower()=='.zip':raise ValueError('ZIP archives must be expanded, not committed')
    if p.parts[0] not in {'revisions','assets','attachments','variants','provenance','tools','README.md','CURRENT.json','TRANSFER_STATUS.md','.gitattributes'}:
        raise ValueError('Unexpected archive root')
    if str(p).startswith('tools/') and str(p)!='tools/verify_snapshot.py':
        raise ValueError('Unexpected executable in transport tools directory')
    return p

def download(entry: dict, dest: Path) -> Path:
    url=entry['url'];u=urllib.parse.urlsplit(url)
    if u.scheme!='https' or not u.hostname or not u.hostname.endswith('.oaiusercontent.com'):
        raise ValueError('Unexpected transport endpoint')
    print('::add-mask::'+url,flush=True)
    req=urllib.request.Request(url,headers={'User-Agent':'legeandre-file-import/1.0'})
    try:
        with urllib.request.urlopen(req,timeout=180) as inp,dest.open('wb') as out:
            shutil.copyfileobj(inp,out,1024*1024)
    except Exception as e:
        raise RuntimeError('Transport download failed; refresh the temporary URL') from None
    if dest.stat().st_size!=entry['bytes'] or sha256(dest)!=entry['sha256']:
        raise ValueError('Transport part checksum mismatch')
    print(f"Downloaded and verified part {entry['part']}",flush=True)
    return dest

def main() -> None:
    request_path=ROOT/'tools/import_request.json'
    if not request_path.exists():print('No import request; nothing to do.');return
    request=json.loads(request_path.read_text(encoding='utf-8'))
    if os.environ.get('GITHUB_REPOSITORY')!=REPO or os.environ.get('GITHUB_REF')!='refs/heads/'+BRANCH:
        raise RuntimeError('Unexpected repository or branch')
    start=git('rev-parse','HEAD')
    if git('ls-remote','origin','refs/heads/'+BRANCH).split()[0]!=start:
        raise RuntimeError('Branch changed while starting; retry from new head')
    git('merge-base','--is-ancestor',BASE,start)
    changed=set(git('diff','--name-only',BASE,start).splitlines())
    allowed={'.github/workflows/import-materials.yml','tools/import_materials.py','tools/import_request.json'}
    if changed-allowed:raise RuntimeError('Unexpected changes after known base: '+repr(changed-allowed))
    if git('status','--porcelain'):raise RuntimeError('Checkout is not clean')
    main_before=git('ls-remote','origin','refs/heads/main').split()[0]
    comment_id=int(request['comment_id'])
    req=urllib.request.Request(f'https://api.github.com/repos/{REPO}/issues/comments/{comment_id}',headers={
        'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json','User-Agent':'legeandre-file-import/1.0'})
    with urllib.request.urlopen(req,timeout=30) as r:comment=json.load(r)
    if comment.get('user',{}).get('login')!='Eljah':raise ValueError('Transport comment must be authored by repository owner')
    match=re.search(r'```json\s*(\{.*?\})\s*```',comment['body'],re.S)
    if not match:raise ValueError('Transport manifest absent from comment')
    spec=json.loads(match.group(1))
    if spec['bundle_sha256']!=request['bundle_sha256'] or spec['snapshot_manifest_sha256']!=request['snapshot_manifest_sha256']:
        raise ValueError('Transport manifest differs from pinned request')
    with tempfile.TemporaryDirectory(prefix='legeandre-import-') as td:
        tmp=Path(td);payload=tmp/'payload';payload.mkdir()
        entries=sorted(spec['parts'],key=lambda e:e['part'])
        if [e['part'] for e in entries]!=list(range(1,len(entries)+1)):raise ValueError('Invalid transport order')
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            futures=[pool.submit(download,e,tmp/f"part-{e['part']:02}") for e in entries]
            parts=[f.result() for f in futures]
        package=tmp/'transport.tar.gz'
        with package.open('wb') as out:
            for p in parts:
                with p.open('rb') as inp:shutil.copyfileobj(inp,out,1024*1024)
        if package.stat().st_size!=spec['bundle_bytes'] or sha256(package)!=spec['bundle_sha256']:
            raise ValueError('Combined transport checksum mismatch')
        paths=[];total=0
        with tarfile.open(package,'r:gz') as tf:
            for member in tf:
                rel=safe_rel(member.name)
                if not member.isfile() or member.issym() or member.islnk():raise ValueError('Only regular files accepted')
                total+=member.size
                if member.size>100*1024*1024 or total>2*1024**3 or len(paths)>5000:raise ValueError('Payload size limit')
                dest=payload/str(rel)
                if dest.exists():raise ValueError('Duplicate archive path')
                dest.parent.mkdir(parents=True,exist_ok=True)
                with tf.extractfile(member) as inp,dest.open('wb') as out:shutil.copyfileobj(inp,out,1024*1024)
                paths.append(str(rel))
        mf=payload/'provenance/SNAPSHOT_SHA256.json'
        if sha256(mf)!=spec['snapshot_manifest_sha256']:raise ValueError('Snapshot manifest mismatch')
        manifest=json.loads(mf.read_text(encoding='utf-8'))
        if manifest['file_count']!=request['original_file_count']:raise ValueError('Snapshot file count mismatch')
        for row in manifest['files']:
            p=payload/str(safe_rel(row['path']))
            if not p.is_file() or p.stat().st_size!=row['bytes'] or sha256(p)!=row['sha256']:
                raise ValueError('Source checksum mismatch: '+row['path'])
        # Reject unplanned overwrites, except the four integration/navigation files.
        replace={'README.md','TRANSFER_STATUS.md','CURRENT.json','tools/verify_snapshot.py'}
        for path in paths:
            old=ROOT/path;new=payload/path
            if old.exists() and old.read_bytes()!=new.read_bytes() and path not in replace:
                raise RuntimeError('Unexpected existing file conflict: '+path)
        for path in paths:
            target=ROOT/path;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(payload/path,target)
        print(f"Copied {len(paths)} individual files; original snapshot {manifest['file_count']} files",flush=True)
    # The script above is all that executes: no simulation or firmware is run.
    subprocess.run(['python','tools/verify_snapshot.py'],cwd=ROOT,check=True)
    request_path.unlink()
    for i in range(0,len(paths),150):git('add','-f','--',*paths[i:i+150])
    git('add','-u','--','tools/import_request.json')
    index=subprocess.check_output(['git','ls-files','--stage','-z'],cwd=ROOT)
    blobs={}
    for rec in index.split(b'\0'):
        if not rec:continue
        meta,path=rec.split(b'\t',1);mode,blob,stage=meta.split();blobs[path.decode('utf-8')]=blob.decode('ascii')
    for row in manifest['files']:
        if blobs.get(row['path'])!=row['git_blob_sha1']:raise ValueError('Git index changed bytes: '+row['path'])
    if any(p.lower().endswith('.zip') for p in blobs):raise ValueError('Unexpected ZIP in repository index')
    result={
        'status':'VERIFIED_FILE_TREE_IMPORT','repository':REPO,'branch':BRANCH,
        'original_files_verified_sha256':manifest['file_count'],
        'original_files_verified_git_blob':manifest['file_count'],
        'source_bytes':manifest['bytes'],'individual_payload_files':len(paths),
        'source_mappings':len(json.loads((ROOT/'provenance/SOURCE_MAP.json').read_text())['files']),
        'snapshot_manifest_sha256':spec['snapshot_manifest_sha256'],
        'transport_sha256':spec['bundle_sha256'],'project_zip_files_tracked':0,
        'parent_commit':start,'main_before':main_before,
        'workflow_run_id':os.environ.get('GITHUB_RUN_ID'),
        'verified_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'engineering_tests_rerun':False,'force_push':False,
        'verification_scope':'File bytes and Git objects, not product safety or CAD rebuild'}
    report=ROOT/'provenance/IMPORT_VERIFICATION.json';report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    git('add','-f','--','provenance/IMPORT_VERIFICATION.json')
    git('config','user.name','github-actions[bot]')
    git('config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
    git('commit','-m',f"Import {manifest['file_count']} original project files as an unpacked R01-R06 tree")
    commit=git('rev-parse','HEAD')
    git('push','origin','HEAD:refs/heads/'+BRANCH)
    remote=git('ls-remote','origin','refs/heads/'+BRANCH).split()[0]
    if remote!=commit:raise RuntimeError('Remote branch does not match imported commit')
    main_after=git('ls-remote','origin','refs/heads/main').split()[0]
    if main_after!=main_before:raise RuntimeError('Main changed concurrently; inspect before merging')
    tracked=len([p for p in git('ls-files','-z').split('\0') if p])
    print(f'SUCCESS commit={commit} original_files={manifest["file_count"]} tracked_entries={tracked} main_unchanged={main_after}',flush=True)
    summary=os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary,'a') as f:
            f.write(f'# File tree synchronized\n\nCommit `{commit}`\n\n{manifest["file_count"]} original files verified by SHA-256 and Git blob SHA.\n\nNo project ZIP tracked. Main unchanged. Engineering simulations were not rerun.\n')

if __name__=='__main__':main()
