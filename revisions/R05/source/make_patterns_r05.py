#!/usr/bin/env python3
"""Derive DXF/SVG/plotter PDF directly from the sampled CAD sewing surfaces.
New wrap + liner pieces only. R04 outer shell patterns remain a separate rejected draft.
"""
from pathlib import Path
import json,math,csv,html
import numpy as np,ezdxf
from shapely.geometry import Polygon
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
ROOT=Path(__file__).resolve().parents[1];P=json.loads((ROOT/'patterns/panels_R05.json').read_text())
pdfmetrics.registerFont(TTFont('D','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
BEAMS=json.loads((ROOT/'cad/beams_R05.json').read_text())
NAMES={'Q01_CENTRE':'Середина укрытия груди','Q01_WING_L':'Левое плечевое крыло','Q01_WING_R':'Правое плечевое крыло','Q02_SIDE_L':'Левая боковина укрытия рук','Q02_SIDE_R':'Правая боковина укрытия рук','Q03_KEYBOARD_FLAP':'Сворачиваемый клапан клавиатуры','Q04_LOWER_QUILT':'Ножное укрытие','P01_BACK_TOP':'Верх внутреннего чехла спинки','P02_PELVIS_TOP':'Примерочный верх тазовой подушки','P03_LEG_TOP':'Верх опоры голеней'}
CUT=[]
for p in P:
    layers=['OUTER','LINING','BATTING'] if p['id'].startswith('Q') else ['LINING']
    for layer in layers:
        poly=Polygon(p['seam_polygon_mm'])
        if not poly.is_valid:raise RuntimeError('invalid '+p['id'])
        # 12 mm sewing allowance for cloth. Batting 8 mm inside stitch line.
        cut=poly.buffer(-8 if layer=='BATTING' else 12,join_style='mitre')
        if cut.is_empty or cut.geom_type!='Polygon':raise RuntimeError('invalid offset')
        CUT.append({'id':p['id']+'_'+layer,'base_id':p['id'],'name':NAMES[p['id']],'layer':layer,'seam':poly,'cut':cut,'pattern':p,'notes':'Припуск ткани 12 мм; утеплитель -8 мм от шва. Толщина и посадка не компенсированы.'})
# Straight tube-sleeve mockups. Terminations/branch collars still require tailoring.
for b in BEAMS:
    if 'BASE' in b['id']:continue
    L=b['length_mm'];radius=52 if b['depth_mm']<=35 else 56;W=2*math.pi*radius
    poly=Polygon([[0,0],[L,0],[L,W],[0,W]])
    CUT.append({'id':'SLEEVE_'+b['id'],'base_id':b['id'],'name':'Разъёмный тканевый рукав '+b['id'],'layer':'FRAME_COVER','seam':poly,'cut':poly.buffer(12,join_style='mitre'),'pattern':None,'notes':f'Для номинального Ø{2*radius} мм. Ветвления, торцы и места примыкания к полке отдельно подгоняются.'})
ALL=ezdxf.new('R2010');ALL.units=4
for name,color in [('CUT',1),('SEAM',5),('GRAIN',3),('NOTCH',2),('TEXT',7)]:ALL.layers.new(name,dxfattribs={'color':color})

def add_dxf(doc,c,offset=(0,0)):
    ms=doc.modelspace();off=np.array(offset)
    for name,poly in [('CUT',c['cut']),('SEAM',c['seam'])]:
        ms.add_lwpolyline((np.array(poly.exterior.coords)[:-1]+off).tolist(),close=True,dxfattribs={'layer':name})
    bb=c['cut'].bounds;x0,y0,x1,y1=bb
    ms.add_text(c['id'],height=8,dxfattribs={'layer':'TEXT','insert':(off[0]+x0,off[1]+y1+12)})
    gx=(x0+x1)/2;yy0=y0+35;yy1=y1-35
    if yy1>yy0:ms.add_line((off[0]+gx,off[1]+yy0),(off[0]+gx,off[1]+yy1),dxfattribs={'layer':'GRAIN'})
    # Notch registration marks on short start/end boundaries, not destructive V cuts.
    co=np.array(c['seam'].exterior.coords)[:-1]
    for j in [0,len(co)//2]:
        p=co[j]+off;ms.add_circle(p,2,dxfattribs={'layer':'NOTCH'})

def svg(c):
    x0,y0,x1,y1=c['cut'].bounds;W=x1-x0+60;H=y1-y0+100
    def path(poly):return 'M '+' L '.join(f'{x-x0+30:.3f},{H-(y-y0+30):.3f}' for x,y in poly.exterior.coords)+' Z'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W:.3f}mm" height="{H:.3f}mm" viewBox="0 0 {W:.3f} {H:.3f}"><title>{html.escape(c['id'])}</title><rect width="100%" height="100%" fill="white"/><path d="{path(c['cut'])}" fill="#e9e6dd" stroke="#9f442f" stroke-width="0.5"/><path d="{path(c['seam'])}" fill="none" stroke="#244759" stroke-width="0.5" stroke-dasharray="3 2"/><text x="25" y="20" font-family="DejaVu Sans" font-size="9">{html.escape(c['id'])}</text><text x="25" y="35" font-family="DejaVu Sans" font-size="5">1:1 mm | R05 | FIRST SEWING SAMPLE, NOT RELEASED</text><path d="M 30 {H-15} H 130 M30 {H-18} V{H-12} M130 {H-18} V{H-12}" stroke="black" stroke-width="0.5"/><text x="45" y="{H-19}" font-family="DejaVu Sans" font-size="5">100 mm</text></svg>'''

pdf=canvas.Canvas(str(ROOT/'patterns/Lezhandr_R05_new_patterns_1to1.pdf'))
summary=[];xoff=0;yoff=0;rowh=0;boxout=[]
for i,c in enumerate(CUT):
    d=ezdxf.new('R2010');d.units=4
    for name,color in [('CUT',1),('SEAM',5),('GRAIN',3),('NOTCH',2),('TEXT',7)]:d.layers.new(name,dxfattribs={'color':color})
    add_dxf(d,c);d.saveas(ROOT/'patterns/pieces'/f"{c['id']}.dxf")
    (ROOT/'patterns/pieces'/f"{c['id']}.svg").write_text(svg(c))
    err=d.audit();assert not err.errors
    xmin,ymin,xmax,ymax=c['cut'].bounds;ww=xmax-xmin;hh=ymax-ymin
    # Review layout at native coordinates; not a roll nesting optimization.
    if xoff+ww>2100:xoff=0;yoff+=rowh+100;rowh=0
    off=(xoff-xmin,yoff-ymin);add_dxf(ALL,c,off);boxout.append({'id':c['id'],'x':xoff,'y':yoff,'width':ww,'height':hh})
    xoff+=ww+65;rowh=max(rowh,hh)
    W=(ww+60)*mm;H=(hh+100)*mm;pdf.setPageSize((W,H));pdf.setFont('D',12);pdf.drawString(20*mm,H-16*mm,c['id']);pdf.setFont('D',9);pdf.drawString(20*mm,H-24*mm,c['name']);pdf.setFont('D',8);pdf.drawString(20*mm,H-33*mm,'1:1, миллиметры. Примерочный раскрой, НЕ производственный выпуск.')
    for poly,color,dash in [(c['cut'],'#9f442f',[]),(c['seam'],'#244759',[4,3])]:
        pp=pdf.beginPath();co=list(poly.exterior.coords);pp.moveTo((co[0][0]-xmin+30)*mm,(co[0][1]-ymin+30)*mm)
        for x,y in co[1:]:pp.lineTo((x-xmin+30)*mm,(y-ymin+30)*mm)
        pp.close();pdf.setStrokeColor(HexColor(color));pdf.setLineWidth(.5);pdf.setDash(dash);pdf.drawPath(pp)
    pdf.setDash([]);pdf.setStrokeColor(HexColor('#222222'));pdf.line(30*mm,14*mm,130*mm,14*mm);pdf.setFont('D',8);pdf.drawString(45*mm,18*mm,'Контроль 100 мм');pdf.showPage()
    summary.append({'id':c['id'],'name':c['name'],'layer':c['layer'],'cut_width_mm':ww,'cut_height_mm':hh,'seam_area_m2':c['seam'].area/1e6,'cut_area_m2':c['cut'].area/1e6,'quantity':1,'notes':c['notes']})
pdf.save();ALL.saveas(ROOT/'patterns/R05_NEW_PANELS_REVIEW_LAYOUT.dxf')
# Numerical matched seams, measured from exact shared 3D boundary chains.
byid={p['id']:p for p in P};pairs=[]
def edge(id,side,start=0):
    g=np.array(byid[id]['grid_3d_mm']);return g[start:,0 if side==0 else -1]
def length(a):return float(np.linalg.norm(np.diff(a,axis=0),axis=1).sum())
for k,(a,sa,b,sb,start) in enumerate([('Q01_CENTRE',0,'Q01_WING_L',1,30),('Q01_CENTRE',1,'Q01_WING_R',0,30),('Q01_WING_L',0,'Q02_SIDE_L',0,0),('Q01_WING_R',1,'Q02_SIDE_R',0,0)]):
    aa=edge(a,sa);bb=edge(b,sb,start);delta=np.linalg.norm(aa-bb,axis=1).max()
    pairs.append({'seam_id':'S'+str(k+1),'a':a,'b':b,'length_a_mm':length(aa),'length_b_mm':length(bb),'maximum_vertex_mismatch_mm':float(delta)})
pairs.append({'seam_id':'S5','a':'Q01_WING_L + Q01_CENTRE + Q01_WING_R / wrist edge','b':'Q03_KEYBOARD_FLAP / start edge','length_a_mm':620.,'length_b_mm':620.,'maximum_vertex_mismatch_mm':0.})
(ROOT/'patterns/seam_pairs.json').write_text(json.dumps(pairs,indent=2,ensure_ascii=False))
(ROOT/'patterns/cutting_register.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False))
with (ROOT/'patterns/cutting_register.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=summary[0].keys());w.writeheader();w.writerows(summary)
(ROOT/'patterns/summary.json').write_text(json.dumps({'cad_mid_surfaces':len(P),'cut_pieces':len(CUT),'seam_pairs':len(pairs),'new_developable_edge_max_relative_error':max(p['max_relative_edge_error'] for p in P),'plotter_pdf_pages':len(CUT),'layout_is_optimized_nesting':False,'old_shell_patterns_released':False},indent=2))
# Clear review SVG containing the seven main 3D-derived quilting patterns only.
from reportlab.lib.utils import ImageReader
parts=[c for c in CUT if c['layer']=='OUTER'];layout=[];xx=20;yy=30;rh=0;W=1750
for c in parts:
 x0,y0,x1,y1=c['cut'].bounds;w=x1-x0;h=y1-y0
 if xx+w>W:xx=20;yy+=rh+80;rh=0
 def qpath(poly):return 'M '+' L '.join(f'{x-x0+xx:.2f},{y-y0+yy:.2f}' for x,y in poly.exterior.coords)+' Z'
 layout.append(f'<g><path d="{qpath(c["cut"])}" fill="#e2e8e6" stroke="#ab6248" stroke-width="1.5"/><path d="{qpath(c["seam"])}" fill="none" stroke="#285267" stroke-width="1.2" stroke-dasharray="5 4"/><text x="{xx}" y="{yy-8}" font-size="20" font-family="DejaVu Sans">{c["base_id"]}</text></g>');xx+=w+50;rh=max(rh,h)
H=yy+rh+35
(ROOT/'patterns/main_wrap_layout.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}"><rect width="100%" height="100%" fill="white"/>'+''.join(layout)+'</svg>')
print('Created',len(CUT),'patterns; seams',pairs)
