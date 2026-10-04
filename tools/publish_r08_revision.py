#!/usr/bin/env python3
"""Publish verified R07/R08 source and generated files exclusively in GitHub.
Prior revisions remain immutable. Output is an ordinary unpacked file tree.
"""
from pathlib import Path, PurePosixPath
import base64, datetime, hashlib, json, lzma, os, shutil, subprocess, sys, urllib.request
ROOT=Path(__file__).resolve().parents[1]
REPO='Eljah/legeandre'; BRANCH='sync/r01-r06-20261002'
SEEDS=[
 {'parts':['9bdf269e98917c3192a7132b15e2daafbe747d86'],'sha256':'363df692ec3c34df341441067b3d0e986d6b9832207500bbe66902433e58095c'},
 {'parts':['88291092771e359515940d41523cb2960cfd1b3c','7180bf0cb86eb4afcc4023dd9f3afaa18bf95261'],'sha256':'66cf03fad3c5e9e17a35d1cd875869b16779e924847a4f9e44e855b53c889eba'}]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(*args,env=None):
 print('RUN',' '.join(map(str,args)),flush=True)
 subprocess.run(list(map(str,args)),cwd=ROOT,check=True,env=env)
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
def write(p,data):
 p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def old_snapshot():
 return {p.relative_to(ROOT).as_posix():digest(p) for r in ['R01','R02','R03','R04','R05','R06'] for p in (ROOT/'revisions'/r).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
def publish(paths,message):
 paths=sorted(set(paths))
 for i in range(0,len(paths),90):run('git','add','-f','--',*paths[i:i+90])
 if subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode==0:return git('rev-parse','HEAD')
 git('config','user.name','github-actions[bot]')
 git('config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
 run('git','commit','-m',message)
 run('git','pull','--rebase','origin',BRANCH)
 run('git','push','origin','HEAD:refs/heads/'+BRANCH)
 sha=git('rev-parse','HEAD')
 if git('ls-remote','origin','refs/heads/'+BRANCH).split()[0]!=sha:raise RuntimeError('Remote SHA mismatch')
 print('PUBLISHED',sha,flush=True)
 return sha

def main():
 if os.getenv('GITHUB_REPOSITORY')!=REPO or os.getenv('GITHUB_REF')!='refs/heads/'+BRANCH:raise RuntimeError('Unexpected target')
 main_before=git('ls-remote','origin','refs/heads/main').split()[0]
 old=old_snapshot();source_rows=[]
 for seed in SEEDS:
  payload=b''
  for sha in seed['parts']:
   req=urllib.request.Request(f'https://api.github.com/repos/{REPO}/git/blobs/{sha}',headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json','User-Agent':'legeandre-r08-builder'})
   with urllib.request.urlopen(req,timeout=90) as response:data=json.load(response)
   b=base64.b64decode(data['content'])
   actual=hashlib.sha1(f'blob {len(b)}\0'.encode()+b).hexdigest()
   if actual!=sha:raise RuntimeError('Git source blob changed')
   payload+=b
  if hashlib.sha256(payload).hexdigest()!=seed['sha256']:raise RuntimeError('Source bundle checksum failed')
  for entry in json.loads(lzma.decompress(payload)):
   rel=PurePosixPath(entry['path']);b=entry['text'].encode('utf-8')
   if rel.is_absolute() or '..' in rel.parts or rel.parts[:2] not in [('revisions','R07'),('revisions','R08')]:raise ValueError('Unsafe source path')
   if hashlib.sha256(b).hexdigest()!=entry['sha256']:raise RuntimeError('Source bytes changed '+str(rel))
   p=ROOT/str(rel);p.parent.mkdir(parents=True,exist_ok=True)
   if p.exists() and p.read_bytes()!=b:raise RuntimeError('Existing source differs: '+str(rel))
   p.write_bytes(b)
   source_rows.append({'path':str(rel),'sha256':entry['sha256'],'bytes':len(b)})
 write(ROOT/'provenance/R08_SOURCE_IMPORT.json',{'sources':source_rows,'seeds':SEEDS,'source':'Preserved conversation CAD source transferred through Git objects only','run_id':os.getenv('GITHUB_RUN_ID')})
 source_commit=publish([r['path'] for r in source_rows]+['provenance/R08_SOURCE_IMPORT.json'],'Preserve original R07 and new R08 CAD, pattern, harness and thermal sources')
 r07=ROOT/'revisions/R07';r08=ROOT/'revisions/R08';r06=ROOT/'revisions/R06'
 for r in [r07,r08]:
  for d in ['cad','tests','patterns','thermal','harness','renders','docs','history']:(r/d).mkdir(parents=True,exist_ok=True)
 h=r07/'history/R06';h.mkdir(parents=True,exist_ok=True)
 for src,dst in [('cad/Lezhandr_R06_work.step','Lezhandr_R06_work.step'),('cad/Lezhandr_R06_occupied_interior.step','Lezhandr_R06_occupied_interior.step'),('cad/model_R06.json','model_R06.json'),('calculations/poses.json','poses.json')]:
  a=r06/src;b=h/dst
  if b.exists() and digest(b)!=digest(a):raise RuntimeError('R07 inherited input differs')
  shutil.copyfile(a,b)
 if not (r07/'cad/model_R07.json').exists():run(sys.executable,r07/'source/build_r07.py')
 run(sys.executable,r07/'source/thermal_study.py')
 env=os.environ.copy();env['LEZHANDR_R07_ROOT']=str(r07)
 for script in ['build_r08.py','patterns_r08.py','thermal_r08.py']:run(sys.executable,r08/'source'/script,env=env)
 run('xvfb-run','-a',sys.executable,r08/'source/render_r08.py',env=env)
 run(sys.executable,r08/'source/render_r08.py','--capture',env=env)
 run(sys.executable,r08/'source/report_r08.py',env=env)
 run(sys.executable,r08/'source/validate_r08.py',env=env)
 if old_snapshot()!=old:raise RuntimeError('An earlier revision changed')
 cad=json.loads((r08/'tests/CAD_checks.json').read_text())
 pat=json.loads((r08/'tests/pattern_checks.json').read_text())
 v=json.loads((r08/'tests/verification.json').read_text())
 if not v['all_passed']:raise RuntimeError('R08 validation failed')
 current=json.loads((ROOT/'CURRENT.json').read_text())
 current.update(cad_revision='R08',thermal_revision='R08',pattern_release='R08_P0_NOT_PRODUCTION',passive_laptop_metal_link_enabled=False,production_ready=False,legacy_fourth_channel_disabled_in_firmware=False)
 write(ROOT/'CURRENT.json',current)
 (ROOT/'R08_INDEX.md').write_text('''# Лежандр R08: исправления геометрии и новый текстильный облик

[PDF-отчёт, 16 листов A3](revisions/R08/docs/Lezhandr_R08_CAD_Cutting_Assembly.pdf) · [CAD](revisions/R08/cad) · [Рендеры](revisions/R08/renders) · [Раскрой P0](revisions/R08/patterns) · [Жгуты и молнии](revisions/R08/harness) · [Тепловые расчёты](revisions/R08/thermal)

![Новая CAD-сборка](revisions/R08/renders/work_open.png)

Подтверждённые пересечения приёмников R07 с манекеном устранены. В R08 нет длинного металлического теплоотвода через тело. Капюшон и нижний чехол имеют общую пространственную кромку; наружные поверхности матовые, сепийные и без внешней поперечной пуховой стёжки.

Это цифровой инженерный прототип. Раскрой новых поверхностей имеет статус P0: измерения ткани и примерочный пошив не выполнены; внутренние мешки наполнителя не переаттестованы. Выход показан габаритно, без расчёта вставания. Электроника и прошивки предыдущих ревизий не переделаны; нагрев на человеке и во сне не разрешён.

[Сборка и выход](revisions/R08/docs/ASSEMBLY_EXIT_WIRING_RU.md) · [Проверки](revisions/R08/tests/verification.json) · [Происхождение и публикация](provenance/R08_PUBLICATION.json)

R01–R06 сохранены без изменений. R07 добавлена как сохранённый исходный код с заново выполненными CAD/тепловыми экспортами; это не новая конструктивная итерация R07. R08 — отдельная новая ревизия. Файлы в Git размещены по отдельности, не архивом.
''',encoding='utf-8')
 files=[]
 for r in [r07,r08]:
  for p in sorted(r.rglob('*')):
   if not p.is_file() or '__pycache__' in p.parts or p.suffix=='.pyc' or 'pdf_qc' in p.parts:continue
   if p.suffix.lower() in ['.zip','.ttf','.otf','.woff','.woff2']:raise RuntimeError('Disallowed output '+str(p))
   if p.stat().st_size>99*1024*1024:raise RuntimeError('Oversized file '+str(p))
   files.append({'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p)})
 report={'status':'R08_BUILT_VALIDATED_READY_TO_COMMIT','source_commit':source_commit,'run_id':os.getenv('GITHUB_RUN_ID'),'run_url':f'https://github.com/{REPO}/actions/runs/'+os.getenv('GITHUB_RUN_ID',''),'verified_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'earlier_revision_files_unchanged':len(old),'main_before':main_before,'force_push':False,'individual_files':len(files),'files':files,'cad_check_count':len(cad['checks']),'digital_validation':{'passed':v['passed'],'total':v['total']},'pattern_checks':pat,'scope':'Nominal CAD geometry, digital seam/metric audit, finite-volume heat balances. Not manufacturing or human-safety approval. Legacy electronics unchanged.'}
 write(ROOT/'provenance/R08_PUBLICATION.json',report)
 commit=publish([r['path'] for r in files]+['CURRENT.json','R08_INDEX.md','provenance/R08_PUBLICATION.json'],'Publish R08 corrected CAD, sepia renders, P0 cutting, exit/harness design and thermal report')
 if git('ls-remote','origin','refs/heads/main').split()[0]!=main_before:raise RuntimeError('Main changed concurrently')
 with open(os.environ['GITHUB_STEP_SUMMARY'],'a',encoding='utf-8') as f:
  f.write(f'# R08 published\n\nCommit `{commit}`\n\n{len(files)} individual files. Validation {v["passed"]}/{v["total"]}. Patterns {pat["patterns"]}. Earlier revisions unchanged.\n\nPattern status P0; not production-approved.\n')
 print('SUCCESS',commit,'FILES',len(files),flush=True)
if __name__=='__main__':main()
