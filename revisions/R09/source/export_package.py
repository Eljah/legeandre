#!/usr/bin/env python3
"""Export all individual cut files, module/seam ledgers, CAD envelope and review PDFs."""
from pathlib import Path
from collections import Counter,defaultdict
import csv,json,math,hashlib,html
import numpy as np
from shapely.geometry import Polygon
import ezdxf
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph,Table,TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from PIL import Image
R=Path(__file__).resolve().parents[1];BASE=R.parent/'R08';MM=72/25.4
pdfmetrics.registerFont(TTFont('Reg','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('Bold','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
P=json.loads((R/'patterns/pieces.json').read_text());S=json.loads((R/'patterns/seam_chains.json').read_text());SUMMARY=json.loads((R/'tests/summary.json').read_text());OPS=json.loads((R/'patterns/hardware_operations.json').read_text())

def js(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def stroke(c,pts,scale=MM,shift=(0,0),fill=0):
    pts=(np.array(pts)+shift)*scale;p=c.beginPath();p.moveTo(*pts[0]);
    for xy in pts[1:]:p.lineTo(*xy)
    p.close();c.drawPath(p,stroke=1,fill=fill)

# Export each cutting file, not just a single archive or screenshot.
plot=canvas.Canvas(str(R/'docs/Lezhandr_R09_Patterns_P1_1to1.pdf'));plot.setTitle('Lezhandr R09 P1 - 1:1 digital pattern set')
dxf_checks=[];cutrows=[]
for q in P:
    id=q['id'];uv=np.array(q['sew_outline_mm']);cut=np.array(q['cut_outline_mm']);mn=cut.min(0);mx=cut.max(0);dim=mx-mn
    doc=ezdxf.new('R2010');doc.units=4;ms=doc.modelspace()
    for name,col in [('CUT',1),('SEW',5),('GRAIN',3),('NOTCH',2),('LABEL',7),('ATTACHMENT',4)]:doc.layers.new(name,dxfattribs={'color':col})
    ms.add_lwpolyline(cut,close=True,dxfattribs={'layer':'CUT'});ms.add_lwpolyline(uv,close=True,dxfattribs={'layer':'SEW'})
    c=np.array(Polygon(uv).representative_point().coords[0]);L=min(80,max(10,dim[0]/3))
    ms.add_line(c-[L/2,0],c+[L/2,0],dxfattribs={'layer':'GRAIN'});ms.add_line(c+[L/2,0],c+[L/2-5,3],dxfattribs={'layer':'GRAIN'})
    ms.add_text(id,dxfattribs={'height':6,'insert':tuple(c),'layer':'LABEL'})
    for n in q['notches']:
        ms.add_circle(n['uv_mm'],1,dxfattribs={'layer':'NOTCH'})
        ms.add_text(n['seam'],dxfattribs={'height':3,'insert':tuple(np.array(n['uv_mm'])+[2,2]),'layer':'LABEL'})
    for m in q['attachment_marks']:
        ms.add_circle(m['uv_mm'],1.5,dxfattribs={'layer':'ATTACHMENT'})
    path=R/'patterns/dxf'/f'{id}.dxf';doc.saveas(path);rd=ezdxf.readfile(path);a=rd.audit()
    dxf_checks.append({'id':id,'units':rd.units,'errors':len(a.errors),'fixes':len(a.fixes)})
    margin=24;w=max(210,dim[0]+2*margin);h=max(297,dim[1]+2*margin+28);shift=-mn+[margin,margin]
    plot.setPageSize((w*MM,h*MM));plot.setFont('Bold',10);plot.drawString(12*MM,(h-12)*MM,id)
    plot.setFont('Reg',8);plot.drawString(12*MM,(h-19)*MM,f"{q['material']} | qty {q['quantity']} | seam {q['seam_allowance_mm']} mm | P1 SAMPLE")
    plot.setLineWidth(.45);stroke(plot,cut,shift=shift);plot.setDash(3,2);stroke(plot,uv,shift=shift);plot.setDash()
    for n in q['notches']:
        xy=(np.array(n['uv_mm'])+shift)*MM;plot.circle(*xy,1*MM,stroke=1,fill=0);plot.setFont('Reg',5);plot.drawString(xy[0]+2,xy[1]+2,n['seam'])
    plot.setFont('Reg',7);plot.line(12*MM,12*MM,112*MM,12*MM);plot.drawString(12*MM,15*MM,'100 mm - print at 100%, do not fit page')
    plot.showPage()
    def sp(poly):return 'M '+' L '.join(f'{x-mn[0]+margin:.3f},{mx[1]-y+margin:.3f}' for x,y in poly)+' Z'
    marks=''.join(f'<circle cx="{n["uv_mm"][0]-mn[0]+margin:.3f}" cy="{mx[1]-n["uv_mm"][1]+margin:.3f}" r="1" fill="none" stroke="#655446"/>' for n in q['notches'])
    (R/'patterns/svg'/f'{id}.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.3f}mm" height="{h:.3f}mm" viewBox="0 0 {w:.3f} {h:.3f}"><title>{html.escape(id)}</title><path d="{sp(cut)}" fill="#eee4d8" stroke="#594534" stroke-width=".4"/><path d="{sp(uv)}" fill="none" stroke="#645647" stroke-width=".3" stroke-dasharray="3 2"/>{marks}<text x="12" y="12" font-family="sans-serif" font-size="5">{html.escape(id)} / P1 / mm</text></svg>')
    cutrows.append({'id':id,'module':q['module'],'material':q['material'],'quantity':q['quantity'],'seam_mm':q['seam_allowance_mm'],'area_m2':Polygon(cut).area/1e6,'x_length_mm':dim[0],'y_width_mm':dim[1],'strain_pct':q['stats']['max_strain_pct']})
plot.save();js(R/'tests/dxf_readback.json',dxf_checks)
with (R/'patterns/cut_list.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(cutrows[0]));w.writeheader();w.writerows(cutrows)
with (R/'patterns/sew_pairs.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['seam','module','panel_A','panel_B','A_mm','B_mm','ease_mm','operation'])
    for q in S:w.writerow([q['id'],q['module'],*q['panels'],*[q['length_mm'][p] for p in q['panels']],q['mismatch_mm'],q['operation']])

# Conservative grain-preserving shelf layout, 1500 mm raw roll, 15 mm selvedges.
markers={};pmap={p['id']:p for p in P}
for material in sorted({p['material'] for p in P}):
    variants=[]
    for p in P:
        if p['material']!=material:continue
        for i in range(p['quantity']):variants.append((p,i+1))
    variants.sort(key=lambda x:np.ptp(np.array(x[0]['cut_outline_mm']),axis=0)[0],reverse=True)
    x=15.;y=15.;shelf=0.;out=[]
    for p,copy in variants:
        poly=np.array(p['cut_outline_mm']);mn=poly.min(0);mx=poly.max(0);L,W=mx-mn
        if W+30>1500:raise ValueError('Roll width exceeded '+p['id'])
        if y+W+15>1500:y=15;x+=shelf+20;shelf=0
        translation=np.array([x,y])-mn
        out.append({'id':p['id'],'copy':copy,'translation_mm':translation.tolist(),'outline_mm':(poly+translation).tolist(),'rotation_deg':0})
        y+=W+20;shelf=max(shelf,L)
    roll=x+shelf+15;markers[material]={'width_mm':1500,'length_mm':roll,'placements':out,'optimal':False,'selvedge_mm':15}
    doc=ezdxf.new('R2010');doc.units=4;ms=doc.modelspace()
    for a in out:ms.add_lwpolyline(a['outline_mm'],close=True);pos=np.array(a['outline_mm']).mean(0);ms.add_text(a['id'],dxfattribs={'insert':tuple(pos),'height':8})
    doc.saveas(R/'patterns/markers'/f'{material}_1500mm.dxf')
    paths=''.join('<path d="M '+' L '.join(f'{x:.2f},{y:.2f}' for x,y in a['outline_mm'])+' Z" fill="#e5d5c5" stroke="#6d5640" stroke-width="1"/>' for a in out)
    (R/'patterns/markers'/f'{material}_1500mm.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{roll}mm" height="1500mm" viewBox="0 0 {roll} 1500"><title>{material} marker, not optimal</title>{paths}</svg>')
js(R/'patterns/markers.json',markers)

# Named manufacturing modules and mounting instructions; overlays are not disguised as edge-to-edge seams.
parents=sorted({p['module'] for p in P});assembly=[]
for name in parents:
    if name=='F08_FLEXIBLE_SOLE':parent='PRODUCT';operation='root flexible floor'
    elif name.startswith('B09_'):parent='F08_FLEXIBLE_SOLE';operation='removable inner cover, protected service zip and webbing anchors; no loose granules'
    elif name.startswith('H08'):parent='O08_SMOOTH_LOWER';operation='hood at common CAD rail, split detachable service fastening'
    elif name.startswith('O08'):parent='F08_FLEXIBLE_SOLE';operation='lower shell mounted on flexible floor, hidden attachment seam'
    elif name.startswith('G08_BACK'):parent='O08_SMOOTH_LOWER';operation='inside overlap guard at hood rail'
    elif name.startswith(('S08','G08_FOREARM','L08')):parent='O08_SMOOTH_LOWER';operation='left permanent soft join; right release attachment, never a wire crossing'
    elif name=='K07_PASSIVE_FLAP_CLOSED':parent='G08_FOREARM_GUSSET_-1';operation='left roll-back hinge seam; remains separate from main exit release'
    elif name.startswith(('Z0','W0','J09','WEB09','PULL09','EH09')):parent='F08_FLEXIBLE_SOLE';operation='per accessory edge ledger and R08 left-side route; serviceable'
    else:parent='O08_SMOOTH_LOWER';operation='protected internal sewn mounting'
    assembly.append({'module':name,'mounted_to':parent,'operation':operation,'pattern_ids':[p['id'] for p in P if p['module']==name]})
js(R/'patterns/assembly_modules.json',assembly)

# An actual CAD supplement from the sampled bag ribs; not a picture passed off as a CAD model.
import cadquery as cq
ass=cq.Assembly(name='R09_inner_sewing_envelopes');valid=[]
for e in json.loads((R/'cad/inner_sewing_envelopes.json').read_text()):
    rings=np.array(e['rings_mm']);wires=[cq.Wire.makePolygon([cq.Vector(*p) for p in row],close=True) for row in rings]
    shape=cq.Solid.makeLoft(wires,True)
    if not shape.isValid():raise ValueError('Invalid sewing envelope '+e['id'])
    ass.add(shape,name=e['id'],color=cq.Color(.65,.52,.39));valid.append({'id':e['id'],'valid':True,'volume_l':shape.Volume()/1e6})
step=R/'cad/Lezhandr_R09_Internal_Sewing_Envelopes.step';ass.save(str(step));sh=cq.importers.importStep(str(step)).val()
js(R/'tests/cad_envelopes.json',{'valid_after_import':sh.isValid(),'solids':len(sh.Solids()),'items':valid,'reference':'ruled approximation of R08 soft components, original R08 not overwritten'})
print('EXPORT_DONE',len(P),'patterns',len(S),'seams',flush=True)
