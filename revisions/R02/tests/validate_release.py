from pathlib import Path
import json,sys,xml.etree.ElementTree as ET,math,re
import ezdxf
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'embroidery'))
from machine_formats import read_dst,read_exp
patterns=json.loads((R/'textile/patterns_R02.json').read_text());out={}
assert len(patterns)==103
for id in patterns:
 for ext in ['dxf','svg']:assert (R/'textile/pieces'/f'{id}.{ext}').is_file()
audits=[]
for base in ['cad/dxf','textile','harness']:
 for p in (R/base).rglob('*.dxf'):
  d=ezdxf.readfile(p);a=d.audit();audits.append({'file':str(p.relative_to(R)),'errors':len(a.errors),'fixes':len(a.fixes),'units_mm':d.units==4})
assert all(a['errors']==0 and a['fixes']==0 and a['units_mm'] for a in audits)
svg=[]
for base in ['textile','harness','embroidery']:
 for p in (R/base).rglob('*.svg'):
  tree=ET.parse(p);assert tree.getroot().tag.endswith('svg');svg.append(str(p.relative_to(R)))
x=read_dst(R/'embroidery/machine/Spim_s_haski_160mm.dst');y=read_exp(R/'embroidery/machine/Spim_s_haski_160mm.exp')
sx=[a for a in x if a[0]=='S'];sy=[a for a in y if a[0]=='S'];assert sx==sy
maxstep=0.;last=(0,0)
for cmd,xx,yy,col in x:
 if cmd=='S':maxstep=max(maxstep,math.dist(last,(xx,yy))/10)
 last=(xx,yy)
assert maxstep<=3.65
routes=json.loads((R/'harness/routes_R02.json').read_text())
assert all(d['cut_length_mm']>=max(d['geometric_length_mm'],d.get('sleep_geometric_length_mm') or 0) for d in routes)
checks=[]
for name,n in [('core',50),('java',12),('integration',25)]:
 s=(R/f'tests/results/{name}_R02.log').read_text();assert f'TOTAL {n} PASS' in s;checks.append({'suite':name,'passed':n})
prov=json.loads((R/'tests/results/provenance_R02.json').read_text());assert prov['all_preserved_files_identical']
out={'status':'passed digital release checks','pattern_files':len(patterns),'dxf_files_checked':len(audits),'dxf_audits':audits,'svg_xml_parsed':len(svg),'embroidery_decoded_positions_equal':True,'needle_penetrations':len(sx),'max_decoded_normal_stitch_mm':round(maxstep,4),'source_preserved_files':len(prov['preserved_directories']),'software_tests':checks,'hardware_or_fabric_tests':False,'proprietary_CAD_or_embroidery_app_used':False}
(R/'tests/results/release_validation_R02.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in out.items() if k!='dxf_audits'},indent=2))
