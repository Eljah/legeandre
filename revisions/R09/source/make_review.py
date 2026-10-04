#!/usr/bin/env python3
"""Actual VTK views and a reviewed digital-pattern dossier. No generated artwork."""
from pathlib import Path
import importlib.util,json,math,hashlib
import numpy as np
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.platypus import Paragraph,Table,TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from PIL import Image
R=Path(__file__).resolve().parents[1];BASE=R.parent/'R08'
P=json.loads((R/'patterns/pieces.json').read_text());S=json.loads((R/'tests/summary.json').read_text());V=json.loads((R/'tests/verification.json').read_text());E=json.loads((R/'cad/inner_sewing_envelopes.json').read_text());M=json.loads((R/'patterns/markers.json').read_text());SMALL=json.loads((R/'tests/small_panel_review.json').read_text())
spec=importlib.util.spec_from_file_location('preserved_r08_renderer',BASE/'source/render_r08.py');render=importlib.util.module_from_spec(spec);spec.loader.exec_module(render)
import vtk

def savewin(w,path):
    w.SetOffScreenRendering(1);w.Render();f=vtk.vtkWindowToImageFilter();f.SetInput(w);f.Update();wr=vtk.vtkPNGWriter();wr.SetFileName(str(path));wr.SetInputConnection(f.GetOutputPort());wr.Write();w.Finalize()

def drawline(r,points,radius=1.5):
    pts=vtk.vtkPoints();cells=vtk.vtkCellArray();cells.InsertNextCell(len(points)+1)
    for i,p in enumerate(points):pts.InsertNextPoint(*p);cells.InsertCellPoint(i)
    cells.InsertCellPoint(0);pd=vtk.vtkPolyData();pd.SetPoints(pts);pd.SetLines(cells);tube=vtk.vtkTubeFilter();tube.SetInputData(pd);tube.SetRadius(radius);tube.SetNumberOfSides(5)
    mp=vtk.vtkPolyDataMapper();mp.SetInputConnection(tube.GetOutputPort());ac=vtk.vtkActor();ac.SetMapper(mp);ac.GetProperty().SetColor(.31,.22,.15);ac.GetProperty().SetAmbient(.5);r.AddActor(ac)

savewin(render.scene('open','foot',1800,1200),R/'renders/R08_preserved_shape.png')
w=render.scene('open','foot',1800,1200);ren=w.GetRenderers().GetFirstRenderer()
for p in P:
    if p['material']=='outer' and p['edge_modes'] is None:drawline(ren,p['xyz_border_mm'],1.8)
savewin(w,R/'renders/pattern_seam_map.png')
# Inspect new sewn bag envelopes with old outer shell hidden; old human shown only as reference.
oldrows=render.ROWS;render.ROWS=[r for r in oldrows if r['group'] in ['human','frame','laptop','desk','floor']]
w=render.scene('open','head',1800,1200);ren=w.GetRenderers().GetFirstRenderer()
for env in E:
    a=np.array(env['rings_mm']);nr,nc=a.shape[:2];faces=[]
    for i in range(nr-1):
        for j in range(nc):
            k=(j+1)%nc;faces.extend([[i*nc+j,(i+1)*nc+j,i*nc+k],[(i+1)*nc+j,(i+1)*nc+k,i*nc+k]])
    faces.extend([[0,j+1,j] for j in range(1,nc-1)])
    b=(nr-1)*nc;faces.extend([[b,b+j,b+j+1] for j in range(1,nc-1)])
    render.actor(ren,{'vertices_mm':a.reshape(-1,3).tolist(),'faces':faces,'kind':'lining'},opacity=.82)
    for j in range(nc):
        # Open longitudinal stitch path, displayed without inventing an application screenshot.
        pts=a[:,j];drawline(ren,np.vstack([pts,pts[::-1]]),.75)
savewin(w,R/'renders/inner_bags_and_reference.png');render.ROWS=oldrows

for name,path in [('R','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),('B','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')]:pdfmetrics.registerFont(TTFont(name,path))
pdfmetrics.registerFontFamily('R',normal='R',bold='B')
PAGE=(1190.55,841.89);W,H=PAGE;INK=colors.HexColor('#473529');MUTED=colors.HexColor('#776758');PALE=colors.HexColor('#f1e9df');LINE=colors.HexColor('#d1bfaa')
c=canvas.Canvas(str(R/'docs/Lezhandr_R09_Pattern_Completion.pdf'),pagesize=PAGE);c.setTitle('Лежандр R09 — цифровой комплект раскроя P1');num=0
styles={'text':ParagraphStyle('text',fontName='R',fontSize=12,leading=18,textColor=INK),'small':ParagraphStyle('small',fontName='R',fontSize=10,leading=14,textColor=INK)}
def text(s,x,y,w,style='text'):
    p=Paragraph(s,styles[style]);_,h=p.wrap(w,1000);p.drawOn(c,x,y-h);return h

def page(title,sub):
    global num
    num+=1;c.setFillColor(colors.white);c.rect(0,0,W,H,fill=1,stroke=0);c.setFillColor(INK);c.rect(0,H-10,W,10,fill=1,stroke=0)
    c.setFont('B',10);c.drawString(44,H-36,'СПИМ С ХАСКИ / ЛЕЖАНДР / R09 / P1');c.setFont('R',9);c.drawRightString(W-44,H-36,'04.10.2026 · мм')
    c.setFont('B',25);c.drawString(44,H-80,title);text(sub,44,H-100,W-88)
    c.setStrokeColor(LINE);c.line(44,40,W-44,40);c.setFont('R',8);c.setFillColor(MUTED);c.drawString(44,24,'Полный цифровой набор для макета. Свойства ткани, давление наполнителя и безопасность изделия не подтверждены отшивом.')
    c.drawRightString(W-44,24,f'{num:02d}');c.bookmarkPage(f'p{num}');c.addOutlineEntry(title,f'p{num}',0,False)
def image(path,x=44,y=150,w=W-88,h=550):
    im=Image.open(path).convert('RGB');arr=np.array(im);ys,xs=np.where(arr.mean(axis=2)<205)
    if len(xs):im=im.crop((max(0,int(xs.min())-45),max(0,int(ys.min())-45),min(im.width,int(xs.max())+45),min(im.height,int(ys.max())+45)))
    iw,ih=im.size;s=min(w/iw,h/ih);c.drawImage(ImageReader(im),x+(w-iw*s)/2,y+(h-ih*s)/2,iw*s,ih*s)
def table(rows,x,y,width,colwidths=None):
    vals=[[Paragraph(str(v),styles['small']) for v in row] for row in rows]
    t=Table(vals,colWidths=colwidths or [width/len(rows[0])]*len(rows[0]));t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),PALE),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),10),('LINEBELOW',(0,0),(-1,-1),.4,LINE)]));_,h=t.wrap(width,700);t.drawOn(c,x,y-h);return h
def done():c.showPage()
page('Раскрой доведён до единого цифрового комплекта','Основа — текущая R08 в GitHub, commit a40b3730. Наружную форму и предыдущие расчёты не перезаписывали.')
image(R/'renders/R08_preserved_shape.png')
text(f"<b>{S['pattern_types']} типов деталей / {S['cut_pieces']} экземпляров</b>. {S['internal_envelopes']} замкнутых внутренних чехлов. На каждой кромке задано стачивание, застёжка, подгибка, крепление или свободный край вставки.",44,127,W-88);done()
page('Теперь шов — это запись с парой и длиной','Карта границ на действительной CAD-геометрии. Линии ниже — технологические стыки, не сквозная стёжка утепления.')
image(R/'renders/pattern_seam_map.png');text('Рендер гладкого чехла не отменяет конструктивные швы. Наружные поверхности R08 сохранены; число деталей и реальные линии показаны в комплекте, а не скрыты ради бесшовного вида.',44,120,W-88);done()
page('Закрыты отсутствовавшие торцы и клапан','Чехол — не только две большие поверхности. Все торцевые соединения теперь имеют собственные детали.')
rows=[['Узел','Что добавлено','Назначение кромок'],['Днище F08','Две торцевые детали между TOP, BOTTOM и боковыми полосами','Пары по одним и тем же 3D-узлам'],['Задний торец G08','Четыре соединительные полосы между наружным и внутренним слоями','Закрытый шестисторонний чехол'],['Клавиатурный клапан K08','Стартовая, конечная и две боковые полосы','Замкнутый мягкий пакет; открывание не поднимает ткань к лицу'],['Молнии Z01–Z04','По две обтачки, напуск и ограничивающие детали торцов','Обе стороны цепи учтены; концы и припуски не потеряны'],['Проводка W01–W06','Рукава, подгибка открытых концов, разгрузки натяжения','Не прокладывать внутри свободной засыпки или через правый выход']]
table(rows,44,674,W-88,[215,440,W-88-655]);text('Совпадающие координаты разных сборочных узлов больше не считаются автоматически одним четырёхслойным швом. Сначала замыкается каждый самостоятельный чехол; его крепление к соседнему узлу задаётся отдельной операцией.',44,270,W-88);done()
page('Внутренние мешки, подушки и защитные чехлы','16 отдельных оболочек построены по сечениям сохранённой CAD-тесселляции. Они имеют реальные сервисные застёжки.')
image(R/'renders/inner_bags_and_reference.png');text('Это отдельные швейные оболочки с продольными клиньями, а не проверка распределения гранул. У концов введён записанный в данных отступ до 5 мм, чтобы избежать несшиваемых точечных полюсов. Между сечениями — линейчатая аппроксимация.',44,130,W-88);done()
page('Сопряжение лекал проверяется численно','Насечки двух соседних деталей построены по одним и тем же сегментам трёхмерного шва.')
rows=[['Проверка','Полученное значение'],['Физические парные сегменты',S['seam_segments']],['Непрерывные цепочки стачивания',S['seam_chains']],['Неопределённые физические кромки',S['unclassified_physical_edges']],['Максимальная разница длин сегмента',f"{S['max_seam_segment_mismatch_mm']:.5f} мм"],['Максимальная разница всей цепочки',f"{S['max_seam_chain_mismatch_mm']:.5f} мм"],['Максимальный остаток метрики треугольной поверхности',f"{S['max_metric_strain_pct']:.3f}%"],['Программные проверки',f"{V['passed']} / {V['total']}"],['Контрпримеры','Дубликат, отсутствующая пара, повреждённая длина и пересечение раскладки отклоняются']]
table(rows,44,678,W-88,[640,W-88-640]);text('2% здесь — невязка цифрового развёртывания, а не разрешённое растяжение ткани. Плотность и усадка конкретного материала не подставлялись вымышленными числами.',44,125,W-88);done()
page('Масштаб 1:1, маркировка и направление ворса','В каждом DXF/SVG есть контур реза и шва. В PDF сохранён физический масштаб, на каждом листе — контрольные 100 мм.')
# Nine real pattern contours, not stylized decorative pattern illustrations.
sel=[p for p in P if p['id'].startswith(('K08','K09','F09','G09'))][:9]
for i,p in enumerate(sel):
    x=44+(i%3)*365;y=200+(2-i//3)*165;uv=np.array(p['cut_outline_mm']);mn=uv.min(0);d=np.ptp(uv,axis=0);sc=min(310/max(d[0],1),110/max(d[1],1));a=(uv-mn)*sc+[x+10,y+30]
    path=c.beginPath();path.moveTo(*a[0]);
    for pt in a[1:]:path.lineTo(*pt)
    path.close();c.setFillColor(PALE);c.setStrokeColor(INK);c.drawPath(path,fill=1,stroke=1);text(p['id'],x,y+20,340,'small')
text('Печатать без «вписать в страницу». Прямоугольник 100 мм должен измеряться как 100 мм. Припуск основного стачивания — 12 мм. Для ворсовой сепийной ткани поворот на 90° запрещён в раскладке.',44,120,W-88);done()
page('Раскладки по материалам','Полотно 1500 мм, отступ от кромок 15 мм. Учитывается каждый экземпляр. Повороты против направления ворса не используются.')
rows=[['Материал','Длина раскладки, м','Размещено деталей']]+[[k,f"{v['length_mm']/1000:.2f}",len(v['placements'])] for k,v in M.items()]
table(rows,44,670,W-88,[420,330,W-88-750]);text('Это проверенная консервативная полочная раскладка, не доказанный минимальный расход. В цифры не включены усадка, брак ткани и отдельные испытательные образцы. До закупки сверить ширину реального рулона.',44,250,W-88);done()
page('Открывание, сервис и последовательность пошива','Правый пользовательский выход и левый ввод проводов сохранены из R08; их роли не объединяются одной молнией.')
rows=[['Этап','Операция'],['1','Сшить внутренние чехлы; установить сервисные молнии и внутренние защитные планки. Не засыпать гранулы до проверки швов.'],['2','Собрать гибкое днище, нижний чехол, капюшон и защитные внутренние накладки.'],['3','Собрать отдельные пакеты утепления и подкладки. Не делать наружную сквозную стёжку ради фиксации наполнителя.'],['4','Втачать две половины основных застёжек по парным станциям. Правый борт должен раскрываться независимо от малого клавиатурного клапана.'],['5','Пришить левосторонние рукава и разгрузки. Коммерческие USB/PD кабели не разрезать и не сшивать с нагревательными кассетами.'],['6','Установить мягкие опоры и подножный блок; проверить выход с выключенным прибором и ноутбуком на припаркованном столике.']]
table(rows,44,670,W-88,[100,W-188]);text('Плоскости крепления аксессуаров — отдельный реестр операций, а не ложно «спаренные» кромки по одинаковым координатам на плоском чертеже.',44,130,W-88);done()
page('Граница завершения: P1, не серийный выпуск','Цифровые данные доведены и воспроизводимо проверены. Производственные свойства не объявляются проверенными программным тестом.')
text('<b>Выполнено.</b> Все лекала, торцы, внутренние чехлы, застёжки, таблицы кромок, парные насечки, раскладки и дополнительный STEP швейных оболочек включены. R08 не изменялась.',44,675,W-88)
text('<b>Остаётся физическая приёмка.</b> Проба выбранной ткани на растяжение и усадку, отшив полного чехла, корректировка прибавок под сжатый утеплитель, проверка молний и наполнения. Внешний гладкий вид и посадка не доказаны одним совпадением длин швов.',44,575,W-88)
text(f'<b>Сложность не скрыта.</b> В реестре отдельно отмечены {len(SMALL)} малых технических панелей с одним из габаритов линии шва меньше 20 мм; это узкие полосы и клинья, а не детали меньше 20 × 20 мм. Их нужно оценить на отшиве; число панелей не выдано за оптимальную технологию.',44,465,W-88)
text('<b>Нет нового допуска к эксплуатации с нагревом.</b> Платы, прошивки, температурные пороги и расчёты нагрузки этой работой не изменялись. Выполнение GitHub Actions подтверждает обработку файлов и проверку геометрии, а не пожарную или физиологическую безопасность.',44,350,W-88)
text('Происхождение: revisions/R08 в Eljah/legeandre, commit a40b3730fcb924dd086d1c2088c60cb4972a96c2. Исходные хеши — tests/input_hashes.json; машинные результаты — tests/verification.json. Все результаты публикуются обычными файлами в revisions/R09.',44,210,W-88,'small');done()
c.save()
# Read back pages and render QA thumbnails; inspect the actual outputs, not just PDF write success.
import fitz
qc=R/'_work/pdf_qc';qc.mkdir(parents=True,exist_ok=True)
with fitz.open(R/'docs/Lezhandr_R09_Pattern_Completion.pdf') as d:
    for i,p in enumerate(d):p.get_pixmap(matrix=fitz.Matrix(.55,.55)).save(qc/f'p{i+1:02}.png')
    count=d.page_count
js={'pages':count,'all_pages_rendered':True,'view_source':'Actual R08 tessellation and new R09 seam/bag data, VTK; no image generation'}
(R/'tests/pdf_readback.json').write_text(json.dumps(js,indent=2)+'\n')
print('REVIEW_DONE',count,'pages',flush=True)
