#!/usr/bin/env python3
"""Independent release gates for the digital sample set (not material/product approval)."""
from pathlib import Path
from collections import Counter,defaultdict
import json,hashlib,copy
import numpy as np
from shapely.geometry import Polygon,box
R=Path(__file__).resolve().parents[1];BASE=R.parent/'R08'
def js(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
P=json.loads((R/'patterns/pieces.json').read_text());SEG=json.loads((R/'patterns/seam_segments.json').read_text());CHAINS=json.loads((R/'patterns/seam_chains.json').read_text());M=json.loads((R/'patterns/markers.json').read_text());OPS=json.loads((R/'patterns/edge_operations.json').read_text());checks=[]
def check(n,v,detail=None):
    checks.append({'test':n,'passed':bool(v),'detail':detail})
def validate_ids(p):
    ids=[q['id'] for q in p]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate panel ID')
def validate_seams(p,ss):
    known={q['id'] for q in p}
    for s in ss:
        if len(s['members'])!=2 or any(m['panel'] not in known for m in s['members']):raise ValueError('Unpaired seam')
        a,b=s['members'];delta=abs(a['flat_mm']-b['flat_mm'])
        if delta>0.15:raise ValueError('Seam metric mismatch')
def validate_marker(m):
    for mat,r in m.items():
        polys=[]
        for v in r['placements']:
            p=Polygon(v['outline_mm'])
            if not p.is_valid or not box(0,0,r['length_mm'],r['width_mm']).covers(p):raise ValueError('Marker bounds')
            for q in polys:
                if p.intersects(q) and p.intersection(q).area>1e-5:raise ValueError('Marker overlap')
            polys.append(p)
validate_ids(P);validate_seams(P,SEG);validate_marker(M)
check('Unique panel IDs',True,len(P));check('Every physical boundary segment has exactly two matching members',True,len(SEG))
for p in P:
    check('Polygon '+p['id'],Polygon(p['sew_outline_mm']).is_valid and Polygon(p['cut_outline_mm']).is_valid)
check('Metric error <=2% on the triangular surface edges',all(q['stats']['max_strain_pct']<=2.001 for q in P))
check('No inverted pattern triangles',all(q['stats']['no_inverted_triangles'] for q in P))
check('Seam chain mismatch <=2 mm',all(s['mismatch_mm']<=2 for s in CHAINS),max(s['mismatch_mm'] for s in CHAINS))
# Accounting is not just a count: each piece boundary edge must occur exactly once in either ledger.
counts=Counter((m['panel'],m['index']) for s in SEG for m in s['members'])
counts.update((o['panel'],o['edge']) for o in OPS)
expected={(p['id'],i) for p in P for i in range(len(p['sew_outline_mm']))}
check('No undeclared or double-assigned cut edge',set(counts)==expected and all(n==1 for n in counts.values()),{'expected':len(expected),'declared':len(counts)})
placements=Counter((mat,a['id']) for mat,r in M.items() for a in r['placements'])
check('All copies nested',all(placements[(p['material'],p['id'])]==p['quantity'] for p in P),sum(placements.values()))
check('No nesting overlap or roll overrun',True)
check('No rotation against nap',all(a['rotation_deg']==0 for r in M.values() for a in r['placements']))
for rel,h in json.loads((R/'tests/input_hashes.json').read_text()).items():check('Preserved R08 input '+rel,hashlib.sha256((BASE/rel).read_bytes()).hexdigest()==h)
# The main data may contain genuine manual accessory operations but no unrecognized catch-all value.
allowed={'insert_free_cut','hem','fold','attachment','zipper_half','folded_longitudinal_seam','accessory_seam','accessory_zipper'}
check('Every free edge has an explicit operation',all(e['operation'] in allowed for e in OPS))
for name in ['cad_envelopes.json','dxf_readback.json']:
    data=json.loads((R/'tests'/name).read_text())
    check('Independent readback '+name,(data['valid_after_import'] and data['solids']==16) if name.startswith('cad') else all(x['units']==4 and x['errors']==0 and x['fixes']==0 for x in data))
# Do not conceal inconvenient small details: separately report the real minimum dimensions.
small=[]
for p in P:
    d=np.ptp(np.array(p['sew_outline_mm']),axis=0)
    if min(d)<20 and p['material'] not in ('webbing','technical','insulation'):small.append({'id':p['id'],'sew_dimensions_mm':d.tolist(),'note':'small technical seam panel: sample sewing required'})
js(R/'tests/small_panel_review.json',small)
# Negative controls demonstrate that test gates are capable of detecting faults.
negative=[]
for name,func in [
 ('duplicate ID rejected',lambda:validate_ids(P+[P[0]])),
 ('missing mating piece rejected',lambda:validate_seams(P[1:],SEG)),
 ('damaged seam length rejected',lambda:validate_seams(P,[{**SEG[0],'members':[dict(SEG[0]['members'][0],flat_mm=SEG[0]['members'][1]['flat_mm']+4),SEG[0]['members'][1]]}])),
 ('overlapping marker rejected',lambda:validate_marker({'test':{'width_mm':1500,'length_mm':100,'placements':[{'outline_mm':[[10,10],[80,10],[80,80],[10,80]]}]*2}}))]:
    try:func();negative.append({'test':name,'passed':False})
    except ValueError:negative.append({'test':name,'passed':True})
checks+=negative
js(R/'tests/verification.json',{'passed':sum(c['passed'] for c in checks),'total':len(checks),'all_passed':all(c['passed'] for c in checks),'checks':checks,'manufacturing_approved':False,'small_panel_count':len(small)})
if not all(c['passed'] for c in checks):raise RuntimeError('Verification gate failed')
print('VERIFIED',len(checks),'checks; small-panel review',len(small),flush=True)
