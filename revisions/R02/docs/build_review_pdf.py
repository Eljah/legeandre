#!/usr/bin/env python3
"""Engineering review from exported CAD, exact pattern polygons and decoded stitches."""
from pathlib import Path
import json,csv,math,io
import numpy as np
import ezdxf
from PIL import Image,ImageChops
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3,landscape
from reportlab.lib.colors import HexColor,Color
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph,Table,TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from shapely.geometry import Polygon
R=Path(__file__).resolve().parents[1];OUT=R/'docs';OUT.mkdir(exist_ok=True)
fonts=Path('/usr/share/fonts/truetype/dejavu')
pdfmetrics.registerFont(TTFont('DV',str(fonts/'DejaVuSans.ttf')))
pdfmetrics.registerFont(TTFont('DVB',str(fonts/'DejaVuSans-Bold.ttf')))
pdfmetrics.registerFontFamily('DV',normal='DV',bold='DVB',italic='DV',boldItalic='DVB')
W,H=landscape(A3);M=42;INK=HexColor('#203642');MUTED=HexColor('#576b73');ACC=HexColor('#bc623f');PALE=HexColor('#edf2f4');BLUE=HexColor('#326a85')
c=canvas.Canvas(str(OUT/'Lezhandr_R02_review.pdf'),pagesize=(W,H));c.setTitle('Спим с хаски — Лежандр R02: CAD, раскрой, жгуты, вышивка');c.setAuthor('Engineering revision R02')
styles={}
for name,size,leading,col in [('body',12,18,INK),('small',9.5,14,MUTED),('label',11,15,INK),('big',18,25,INK)]:
 styles[name]=ParagraphStyle(name,fontName='DV',fontSize=size,leading=leading,textColor=col,spaceAfter=8)

def txt(text,x,y,w,style='body'):
 p=Paragraph(text,styles[style]);ww,hh=p.wrap(w,H);p.drawOn(c,x,y-hh);return y-hh-10

def header(n,title,subtitle):
 c.setFillColor(INK);c.rect(0,H-27,W,27,fill=1,stroke=0)
 c.setFillColor(HexColor('#ffffff'));c.setFont('DVB',9);c.drawString(M,H-18,'СПИМ С ХАСКИ  /  ЛЕЖАНДР R02');c.setFont('DV',9);c.drawRightString(W-M,H-18,'01.10.2026  •  ЦИФРОВОЙ ИНЖЕНЕРНЫЙ ПРОТОТИП')
 c.setFillColor(INK);c.setFont('DVB',27);c.drawString(M,H-78,title)
 txt(subtitle,M,H-94,W-2*M,'small')
 c.setStrokeColor(HexColor('#ced8dc'));c.line(M,36,W-M,36)
 c.setFont('DV',8);c.setFillColor(MUTED);c.drawString(M,22,'Изменение загруженного проекта R01. Физические испытания не проводились.');c.drawRightString(W-M,22,f'{n:02d} / 09')

def image(path,x,y,w,h,crop=False):
 im=Image.open(path).convert('RGB')
 if crop:
  bg=Image.new('RGB',im.size,im.getpixel((0,0)));d=ImageChops.difference(im,bg).convert('L');d=d.point(lambda x:255 if x>24 else 0);bb=d.getbbox()
  if bb:
   l,t,rr,b=bb;bb=(max(0,l-30),max(0,t-30),min(im.width,rr+30),min(im.height,b+30));im=im.crop(bb)
 scale=min(w/im.width,h/im.height);iw,ih=im.width*scale,im.height*scale
 c.drawImage(ImageReader(im),x+(w-iw)/2,y+(h-ih)/2,width=iw,height=ih)

def note(text,x,y,w,h=80):
 c.setFillColor(PALE);c.roundRect(x,y,w,h,7,fill=1,stroke=0);txt(text,x+14,y+h-13,w-28,'small')

def table(rows,x,y,widths,fs=10):
 st=ParagraphStyle('table',fontName='DV',fontSize=fs,leading=fs*1.35,textColor=INK)
 data=[[Paragraph(str(v),st) for v in r] for r in rows]
 t=Table(data,colWidths=widths,hAlign='LEFT');t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),PALE),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,0),.8,BLUE),('LINEBELOW',(0,1),(-1,-1),.35,HexColor('#d6dfe2'))]));ww,hh=t.wrap(sum(widths),H);t.drawOn(c,x,y-hh);return y-hh

def drawpoly(pts,x,y,scale,fill=PALE,stroke=INK):
 p=c.beginPath();p.moveTo(x+pts[0][0]*scale,y+pts[0][1]*scale)
 for xx,yy in pts[1:]:p.lineTo(x+xx*scale,y+yy*scale)
 p.close();c.setFillColor(fill);c.setStrokeColor(stroke);c.setLineWidth(.6);c.drawPath(p,fill=1,stroke=1)

# 1. Large actual CAD view, with no background platform pretending to be a part.
header(1,'Мягкий напольный кокон','Рабочее положение. Вид получен из изменённой CadQuery / OpenCascade-сборки, а не генерацией изображения.')
image(R/'cad/renders/work_head.png',M,105,780,590,True)
x=845;y=H-160
for title,body in [('Нет рамы и ножек','Наружная тканевая оболочка и гибкая подложка лежат на полу; нижняя срединная поверхность — Z=0.'),('Опора — мягкие вставки','Матрас 96 мм, съёмный пенный клин 35,2°, мягкие боковые опоры. Их жёсткость под нагрузкой ещё не подобрана.'),('Полка сохранена из R01','Съёмная вентилируемая вставка 460 × 720 × 12 мм. Это не несущий каркас кокона.'),('Размер модели','2360 × 1036 × 831 мм, без внешнего аккумуляторного модуля. Полезная длина матраса — 2200 мм.')]:
 y=txt('<b>'+title+'</b>',x,y,W-M-x,'body');y=txt(body,x,y+4,W-M-x,'small')-8
note('Линии корпуса — швейные границы. Равномерная CAD-заливка не означает металл или твёрдый пластик. Поверхности показывают номинальную форму без расчёта драпировки.',M,51,780,57)
c.showPage()

# 2.
header(2,'Положение для сна','Те же швейные поверхности; верхний клапан возвращён. Головное отверстие не закрывается.')
image(R/'cad/renders/sleep_head.png',M,170,790,510,True)
y=H-165;x=850
for a,b in [('01  Отключить','Нагрев и питание ноутбука выключить. Снять ноутбук, полку и накрывайку для рук.'),('02  Вынуть клин','Съёмный пенный клин спинки и мягкие боковые опоры убрать; спальная поверхность остаётся низкой и плоской.'),('03  Закрыть клапан','O06A…O11A с соответствующей подкладкой соединяются с боковыми частями разъёмной застёжкой.'),('04  Оставить лицо открытым','Нет затягивающего шнура вокруг шеи. Нагрев в состоянии SLEEP программно отключён.')]:
 y=txt('<b>'+a+'</b>',x,y,W-M-x);y=txt(b,x,y+4,W-M-x,'small')-8
note('Это ручная перекомпоновка мягких деталей, а не автоматический механизм. Ненагреваемый макет должен подтвердить удобный вход/выход, положение шеи, возможность лежать с вытянутыми ногами и отсутствие сползания.',M,66,1090,82)
c.showPage()

# 3.
header(3,'Внутреннее устройство и электроника','Технический прозрачный вид. Оранжевый — носители кассет и оси проводки; полупрозрачные детали не являются прозрачной тканью.')
image(R/'cad/renders/work_section.png',M,110,790,565,True)
y=H-160;x=850
rows=[['Узел','Принято в R02'],['Зоны 0 / 1','Туловище / ноги: по 20 Вт'],['Зоны 2 / 3','Стопы 12 Вт / руки 8 Вт'],['Питание нагрева','12 В, 60 Вт суммарно'],['Аккумулятор','Модуль R01 снаружи утеплителя'],['Платы A1 / A2','Сохранены из исходного архива'],['Контроллер E11','На доступной боковой поверхности']]
y=table(rows,x,y,[110,185],10)-18
txt('Геометрия кассеты не заменяет расчёт горячих точек. Сама резистивная нить здесь не превращена в программу вышивки. Электронику нельзя зашивать в тёплый мешок или прижимать телом.',x,y,295,'small')
note('Сохранены логика независимого отключения и программный запрет нагрева во сне. Тепловые, влажностные, электрические и пожарные испытания R02 не выполнены. Не проводить первое включение с человеком внутри.',M,52,1090,60)
c.showPage()

# 4.
header(4,'Раскрой вычислен из CAD','Каждому лекалу соответствует исходная 3D-панель, её треугольники и те же пронумерованные вершины после развёртки.')
pat=json.loads((R/'textile/patterns_R02.json').read_text());d=pat['O03'];pts=np.array(d['cut']);lo=pts.min(0);hi=pts.max(0);sx=1000/(hi[0]-lo[0]);sy=235/(hi[1]-lo[1]);sc=min(sx,sy)
xx=M+25-lo[0]*sc;yy=410-lo[1]*sc;drawpoly(pts,xx,yy,sc)
q=c.beginPath();p=d['sew'];q.moveTo(xx+p[0][0]*sc,yy+p[0][1]*sc)
for a,b in p[1:]:q.lineTo(xx+a*sc,yy+b*sc)
q.close();c.setStrokeColor(BLUE);c.setDash(3,2);c.drawPath(q);c.setDash()
for a,b in d['notches']:c.setFillColor(ACC);c.circle(xx+a*sc,yy+b*sc,1.5,fill=1,stroke=0)
txt('<b>O03 — продольный клин оболочки</b>',M,695,650)
txt('Сплошная граница: CUT. Синяя: SEW. Точки: метки совмещения. Изображение на этом листе уменьшено; печать 1:1 — в отдельном PDF.',M,670,1090,'small')
rows=[['Выход','Содержание'],['79 CAD-панелей','Оболочка, подкладка, чехлы мягких вставок, полка, накрывайка, носители кассет'],['103 детали раскроя','79 панелей и 24 вкладыша утеплителя; каждый контур DXF/SVG отдельно'],['699 пар сегментов','Проверены совпадающие границы соседних CAD-панелей и их длины в развёртке'],['Припуски','12 мм на шов; утеплитель без припуска и с внутренним отступом 8 мм'],['Форматы','DXF R2010 (мм), SVG (мм), JSON соответствия 3D↔2D, PDF 1:1']]
table(rows,M,345,[235,855],10.5)
note('Сохранение рёбер выполнено с численной погрешностью менее 10⁻⁸ мм. Это точность операции над моделью, НЕ точность ткани или пошива. Усадка, объём шва и растяжение не рассчитывались.',M,49,1090,58)
c.showPage()

# 5. Read actual nested DXF polygons, not guessed rectangles.
header(5,'Реальная раскладка на полотне 1500 мм','Непересечение контуров проверено. Раскладка эвристическая, не доказанно минимальная; односторонний ворс требует отдельного режима.')
markers=json.loads((R/'textile/marker_report.json').read_text())
label={'outer':'Внешняя ткань','lining':'Подкладка','cushion':'Чехлы вставок','insulation':'Утеплитель','floor':'Тканевое дно','mesh':'Сетка полки','heater_carrier':'Носители кассет'}
for i,mat in enumerate(['outer','lining','cushion','insulation']):
 x=M+i*178;y=145;ww=147;hh=485;s=min(ww/1500,hh/markers[mat]['length_mm']);doc=ezdxf.readfile(R/'textile/markers'/f'{mat}_1500.dxf')
 c.setFont('DVB',10);c.setFillColor(INK);c.drawString(x,674,label[mat]);c.setFont('DV',9);c.drawString(x,657,f"{markers[mat]['length_mm']/1000:.2f} м · {markers[mat]['pieces']} дет.")
 for ent in doc.modelspace().query('LWPOLYLINE'):
  pp=[(q[0],q[1]) for q in ent.get_points()];drawpoly(pp,x,y,s,HexColor('#ffffff') if ent.dxf.layer=='0' else PALE)
 c.setFont('DV',8);c.setFillColor(MUTED);c.drawString(x,y-16,'1500 мм')
rows=[['Материал','Длина','Заполнение']]
for mat in ['outer','lining','floor','cushion','mesh','heater_carrier','insulation']:
 d=markers[mat];rows.append([label[mat],f"{d['length_mm']/1000:.2f} м",f"{d['utilization_percent']:.1f}%"])
table(rows,790,660,[152,85,70],10)
txt('Длины относятся к отдельным видам материала. Это не закупочная смета: запас на усадку, брак, пробный пошив и полосы кабель-каналов добавляется отдельно.',790,340,300,'small')
note('Раскладка сохранена как редактируемые замкнутые контуры DXF и SVG. Для резки брать готовый маркер нужного материала, для переносов швов и надсечек — индивидуальные лекала.',M,55,1090,64)
c.showPage()

# 6.
header(6,'Жгутование связано с швейными швами','Маршруты лежат на CAD-базах O03 / O02. Для зоны спинки пересчитаны оба положения; заготовка учитывает больший маршрут.')
rr=json.loads((R/'harness/routes_R02.json').read_text());rows=[['Жгут','Назначение','Работа, мм','Сон, мм','Заготовка, мм']]
for d in rr:
 name={'POWER':'Питание','SENSOR':'NTC-датчик','SAFETY':'Независимый термостат','USB':'Готовый кабель','CONTROL':'Местная панель'}[d['kind']]
 rows.append([d['id'],name,f"{d['geometric_length_mm']:.0f}",'—' if d['sleep_geometric_length_mm'] is None else f"{d['sleep_geometric_length_mm']:.0f}",d['cut_length_mm']])
table(rows,M,688,[98,185,100,100,120],9)
x=690;y=680
for title,body in [('20 маршрутов','Включая готовые USB-кабели и внешнее питание. Отдельная ведомость 32 проводников относится к четырём нагревательным зонам, датчикам и термостатам.'),('Формула запаса','Максимум длины работы/сна × 1,05 + 230 мм, с округлением до 10 мм. Это проектный монтажный запас, не результат обмеров физического макета.'),('Каналы на раскрое','POWER_CHANNEL_on_O03.dxf и SENSOR_CHANNEL_on_O02.dxf содержат линии, перенесённые через те же 3D↔2D вершины.'),('Готовые USB / USB-C PD','Не резать по ведомости. Выбирать готовую сборку ближайшей большей длины и проверять её токовый режим.'),('Ещё требуется','Радиусы изгиба, крепления и разгрузка натяжения, подбор разъёмов, герметизация, испытание помех при PWM и контроль температур проводки.')]:
 y=txt('<b>'+title+'</b>',x,y,440);y=txt(body,x,y+4,440,'small')-5
c.showPage()

# 7.
header(7,'Логотип переведён в машинные стежки','Не новый рисунок: сохранены лицо, окружающие хвосты и надпись одобренного изображения. Мелкая имитация текстуры нитей упрощена.')
image(R/'embroidery/preview_from_DST.png',M,85,610,590)
txt('<b>Слева — траектории из заново прочитанного DST</b>',M,72,680,'small')
x=700;image(R/'embroidery/source/approved_logo_crop.png',x,445,190,220)
txt('Одобренный исходный фрагмент',x,440,220,'small')
rep=json.loads((R/'embroidery/embroidery_report.json').read_text())
rows=[['Параметр','Результат'],['Поле вышивки','158,9 × 160,6 мм'],['Проколы / цвета','52 197 / 8'],['Смены / обрезки','7 / 470 запросов'],['Выход','DST + EXP'],['Редактирование','Области SVG, ручные узлы SVG, команды CSV'],['Минимум поля пялец','170 × 175 мм полезного поля']]
table(rows,910,664,[99,137],9)
threads=list(csv.DictReader((R/'embroidery/threadlist.csv').open(encoding='utf-8-sig')))
for i,t in enumerate(threads):
 xx=x+(i%4)*110;yy=371-(i//4)*61;c.setFillColor(HexColor(t['RGB']));c.rect(xx,yy,80,24,fill=1,stroke=0);c.setFont('DV',8);c.setFillColor(INK);c.drawString(xx,yy-14,f"{i+1}. {t['RGB']}")
txt('Цвета назначать по threadlist.csv. Обратное чтение DST и EXP подтвердило совпадение всех проколов. Эта проверка не заменяет просмотр на вашей машине и пробный отшив.',x,215,438,'body')
note('Не масштабировать готовые стежки до маленького шеврона. Первый образец — отдельный лоскут со стабилизатором, без утеплителя и электрических элементов. Команды обрезки зависят от машины.',x,65,440,93)
c.showPage()

# 8.
header(8,'Застёжки, швы и место нашивки','Технологический маршрут — в TEXTILE_ASSEMBLY_RU.md; линии застёжек и размещения логотипа — в DXF, а не только на иллюстрации.')
# Draw OHEAD with actual frame in exact unfolded coordinates.
doc=ezdxf.readfile(R/'textile/embroidery_placement_on_OHEAD.dxf');items=list(doc.modelspace().query('LWPOLYLINE'));coords=[(p[0],p[1]) for e in items for p in e.get_points()];aa=np.array(coords);lo=aa.min(0);hi=aa.max(0);sc=min(470/(hi[0]-lo[0]),430/(hi[1]-lo[1]));x=M+15-lo[0]*sc;y=220-lo[1]*sc
for e in items:
 pts=[(q[0],q[1]) for q in e.get_points()]
 if e.dxf.layer=='CUT':drawpoly(pts,x,y,sc)
 else:
  q=c.beginPath();q.moveTo(x+pts[0][0]*sc,y+pts[0][1]*sc)
  for a,b in pts[1:]:q.lineTo(x+a*sc,y+b*sc)
  q.close();c.setStrokeColor(ACC if e.dxf.layer=='EMBROIDERY' else BLUE);c.setLineWidth(1.4);c.drawPath(q)
txt('<b>OHEAD: торцевой текстильный элемент</b>',M,685,510)
txt('Оранжевая рамка 170 × 175 мм — проверенная зона нашивки. Вся рамка находится внутри линии стачивания. Пришивать до монтажа электрики.',M,177,500,'small')
x=605;y=685
for title,body in [('Сначала — макет','Проверить положение тела, вход/выход, устойчивость ноутбука и вентиляцию. Плотность пены и фиксация мягкого клина пока не подтверждены испытанием.'),('Съёмный верхний клапан','O06A…O11A / L06A…L11A. 24 граничных сегмента описаны в closure_plan.csv. Сумма линий под застёжку — 2623,66 мм; обработка края у головы — 847,70 мм. Это не готовая закупочная длина молнии.'),('Безопасный порядок шитья','Сначала вышивка и пустые текстильные каналы. Затем съёмный утеплитель и носители кассет. Никогда не прошивать иглой нагреватель, датчик, предохранитель или кабель.'),('Распределение слоёв','Внешняя ткань / утеплитель / внутренний чехол. Под телом — матрас и гибкая подложка, не доска. Посадку слоёв и объём припусков уточнить на макете.'),('Сервисный доступ','Швы доступа к клину, матрасу и кассетам должны оставаться разъёмными. Питание отключается до складывания или снятия любого носителя.')]:
 y=txt('<b>'+title+'</b>',x,y,530);y=txt(body,x,y+4,530,'small')-4
c.showPage()

# 9.
header(9,'Проверки и границы готовности','В архиве есть исходники, отчёты проверок, сохранённая R01 и построчная разница CAD. Здесь перечислены выполненные действия, не планы.')
rows=[['Проверено','Результат'],['Наследование исходного архива','144 файла электроники, прошивки, приложений и дистрибутива побайтно совпадают с R01; SHA-256 сохранены'],['Новые STEP-сборки','Экспорт и повторный импорт успешны; BREP-геометрия валидна в обоих положениях'],['Лекала и маркеры','103 контура; проверены развёртка, парные границы и отсутствие наложений при раскладке'],['DXF / SVG','119 DXF: аудит без ошибок и исправлений, единицы мм; 114 SVG: разбор XML; два SVG открыты в Inkscape'],['Нагревательное ядро C++','Повторная сборка и 50 успешных проверок, включая OFF при SLEEP и неисправностях'],['Java → симулятор ядра','12 проверок протокола + 25 сквозных проверок через настоящий Java-транспорт'],['DST / EXP','52 197 проколов: два файла прочитаны заново, координаты и порядок цветов совпали']]
y=table(rows,M,690,[250,840],11)
note('<b>Не выполнено:</b> физический пошив, отшив логотипа, испытания под нагрузкой, моделирование ткани/пены и контактных давлений, испытания подогрева в складках и во влажной среде, проверка реального ESP32/Android/USB/BLE, новые KiCad ERC/DRC.',M,130,1090,96)
txt('Результат — изменённый инженерный цифровой прототип для дальнейшей макетной проверки. Не подтверждённое серийное изделие и не комплект для немедленного использования под напряжением с человеком.',M,105,1090,'body')
c.showPage();c.save()
print(OUT/'Lezhandr_R02_review.pdf')
