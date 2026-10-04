"""Independent final-file checks; does not certify physical sewability."""
from pathlib import Path
import json,math,hashlib,csv
from collections import Counter
from lxml import etree
import machine_formats as mf
R=Path(__file__).resolve().parents[1]
D=R/'machine/Spim_s_haski_R03_140x156.dst';E=R/'machine/Spim_s_haski_R03_140x156.exp'
a,b=mf.read_dst(D),mf.read_exp(E)
sa=[x for x in a if x[0]=='S'];sb=[x for x in b if x[0]=='S'];assert sa==sb
assert len(sa)==50691
assert sum(x[0]=='C' for x in a)==12
assert all(math.isfinite(float(z)) for c,x,y,col in a for z in (x,y))
assert all(a[i][0]!='S' or a[i-1][0]!='S' or a[i][1:3]!=a[i-1][1:3] for i in range(1,len(a)))
root=etree.parse(str(R/'Spim_s_haski_R03_editable.svg'))
ns={'s':'http://www.w3.org/2000/svg','i':'http://inkstitch.org/namespace'}
sat=root.xpath('//s:path[@i:satin_column="true"]',namespaces=ns)
fill=root.xpath('//s:path[@i:fill_method="auto_fill"]',namespaces=ns)
assert len(sat)==108 and len(fill)==61
for p in sat:
    assert p.get('d').count('M ')==2
    l,r=p.get('d').split('M ')[1:]
    assert l.count(' L ')==r.count(' L ')
assert root.getroot().get('viewBox')=='0 0 144.0 159.0'
# Source and binary production reports agree on total needle count.
rows=list(csv.DictReader((R/'machine/thread_sequence.csv').open(encoding='utf-8-sig')))
assert sum(int(r['needle_points']) for r in rows)==len(sa)
result=dict(DST_EXP_equal=True,stitches=len(sa),colors=8,color_changes=12,editable_tatami=len(fill),editable_satin=len(sat),rails_equal_node_counts=True,consecutive_repeated_needles=0,nominal_canvas_mm=[144,159],physical_sewout=False,inkstitch_run=False,files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (D,E,R/'Spim_s_haski_R03_editable.svg')})
(R/'tests/final_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False,indent=2))
