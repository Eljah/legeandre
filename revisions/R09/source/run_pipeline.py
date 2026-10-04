#!/usr/bin/env python3
"""Run the auditable sample-cut pipeline. Does not change or execute electronics."""
from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT.parent/'R08'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def snapshot(root):return {p.relative_to(root).as_posix():sha(p) for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
def save(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
    before=snapshot(BASE)
    for name in ['finalize_patterns.py','export_package.py','verify_package.py','make_review.py']:
        args=[sys.executable,str(ROOT/'source'/name)]
        if name=='make_review.py':args=['xvfb-run','-a']+args
        print('RUN',name,flush=True);subprocess.run(args,cwd=ROOT.parents[1],check=True)
    after=snapshot(BASE)
    if before!=after:raise RuntimeError('R08 files changed')
    import fitz
    pages={}
    for p in sorted((ROOT/'docs').glob('*.pdf')):
        with fitz.open(p) as doc:
            if doc.is_encrypted or not doc.page_count:raise RuntimeError('Unreadable PDF')
            pages[p.name]=doc.page_count
    summary=json.loads((ROOT/'tests/summary.json').read_text())
    verification=json.loads((ROOT/'tests/verification.json').read_text())
    if not verification['all_passed']:raise RuntimeError('Verification failed')
    if pages.get('Lezhandr_R09_Patterns_P1_1to1.pdf')!=summary['pattern_types']:raise RuntimeError('Plotter page count')
    if pages.get('Lezhandr_R09_Pattern_Completion.pdf')!=9:raise RuntimeError('Review page count')
    report={'status':'DIGITAL_SAMPLE_CUT_SET_BUILT_AND_CHECKED','workflow_run_id':os.getenv('GITHUB_RUN_ID'),
      'workflow_commit':os.getenv('GITHUB_SHA'),'verified_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'summary':summary,'checks_passed':verification['passed'],'checks_total':verification['total'],
      'pdf_pages':pages,'preserved_R08_files':len(before),'R08_unchanged':True,
      'manufacturing_approved':False,'engineering_scope':'Geometry, cut outlines, seam graph, copies and exports; no physical sew-out, fabric calibration or product certification'}
    save(ROOT/'tests/ACTIONS_RESULT.json',report)
    files=[]
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file() or any(x in p.parts for x in ['_work','__pycache__']) or p.suffix in ['.pyc','.pickle'] or p.name=='MANIFEST_SHA256.json':continue
        if p.stat().st_size>=99*1024*1024:raise RuntimeError('Output too large for regular Git '+str(p))
        if p.suffix.lower() in ['.ttf','.otf','.woff','.woff2']:raise RuntimeError('Font files must not be distributed')
        files.append({'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)})
    save(ROOT/'MANIFEST_SHA256.json',{'files':files,'file_count':len(files),'R08_unchanged':True,'source_commit':'a40b3730fcb924dd086d1c2088c60cb4972a96c2'})
    print('R09_PIPELINE_SUCCESS',json.dumps(report,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
