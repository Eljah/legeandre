#!/usr/bin/env python3
"""Programmatic A3 review album. Figures are R06 CAD renders, not generated art."""
from pathlib import Path
import json,math
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from PIL import Image,ImageChops
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/Lezhandr_R06_CAD_review.pdf'
for name,p in [('Reg','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),('Bold','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')]:pdfmetrics.registerFont(TTFont(name,p))
PAGE=(1190.551,841.89);W,H=PAGE;M=44
INK=colors.HexColor('#183841');MUTED=colors.HexColor('#536b70');ACCENT=colors.HexColor('#648486');BG=colors.HexColor('#f5f3ed');PALE=colors.HexColor('#e8efec');WARM=colors.HexColor('#eee5d8')
styles={'body':ParagraphStyle('body',fontName='Reg',fontSize=11.2,leading=16,textColor=INK),'small':ParagraphStyle('small',fontName='Reg',fontSize=9.2,leading=13,textColor=MUTED),'large':ParagraphStyle('large',fontName='Reg',fontSize=13,leading=19,textColor=INK)}
# Bold tagging uses real registered faces, not font substitution.
for st in styles.values():st.bulletFontName='Reg'
pdfmetrics.registerFontFamily('Reg',normal='Reg',bold='Bold',italic='Reg',boldItalic='Bold')
V=json.loads((ROOT/'tests/verification.json').read_text());S=json.loads((ROOT/'calculations/table_stability.json').read_text());F=json.loads((ROOT/'calculations/foot_settings.json').read_text());PAT=json.loads((ROOT/'patterns/draft_patterns.json').read_text());COV=json.loads((ROOT/'calculations/cover_sections.json').read_text());BUILD=json.loads((ROOT/'tests/build_summary.json').read_text())
C=canvas.Canvas(str(OUT),pagesize=PAGE);C.setTitle('Спим с хаски — Лежандр R06: CAD-модель мягкого кокона');C.setAuthor('Спим с хаски / инженерная ревизия R06');C.setSubject('Изменения реальной CAD-сборки R05, рендеры, разрезы и макетные развёртки')
page_count=0

def text(txt,x,y,w,style='body'):
 p=Paragraph(txt,styles[style]);ww,hh=p.wrap(w,1000);p.drawOn(C,x,y-hh);return hh

def page(title,subtitle,section='CAD / R06'):
 global page_count
 page_count+=1;C.setFillColor(colors.white);C.rect(0,0,W,H,fill=1,stroke=0);C.setFillColor(INK);C.rect(0,H-11,W,11,fill=1,stroke=0)
 C.setFillColor(ACCENT);C.setFont('Bold',10);C.drawString(M,H-37,'СПИМ С ХАСКИ  /  ЛЕЖАНДР');C.setFont('Reg',9);C.drawRightString(W-M,H-37,section+'   •   01.10.2026')
 C.setFillColor(INK);C.setFont('Bold',25);C.drawString(M,H-81,title);text(subtitle,M,H-96,W-2*M,'body')
 C.setStrokeColor(colors.HexColor('#d3ddda'));C.line(M,39,W-M,39)
 C.setFont('Reg',8);C.setFillColor(MUTED);C.drawString(M,24,'R06 — геометрический прототип. Поведение ткани, наполнителя и человека под нагрузкой не подтверждено.')
 C.setFont('Bold',10);C.drawRightString(W-M,23,f'{page_count:02d}')
 C.bookmarkPage('p'+str(page_count));C.addOutlineEntry(title,'p'+str(page_count),0,False)

def finish():C.showPage()

def picture(name,x=M,y=150,w=W-2*M,h=550,crop=True):
 p=ROOT/'renders'/name if '/' not in name else ROOT/name
 im=Image.open(p).convert('RGB')
 if crop and 'draft_' not in name and 'screenshots' not in name:
  aa=np.asarray(im);mask=aa.mean(axis=2)<211;ys,xs=np.where(mask)
  if len(xs):
   pad=50;bb=(max(0,int(xs.min())-pad),max(0,int(ys.min())-pad),min(im.width,int(xs.max())+pad),min(im.height,int(ys.max())+pad));im=im.crop(bb)
 iw,ih=im.size;sc=min(w/iw,h/ih);rw=iw*sc;rh=ih*sc;xx=x+(w-rw)/2;yy=y+(h-rh)/2
 C.drawImage(ImageReader(im),xx,yy,rw,rh,mask='auto');return xx,yy,rw,rh

def boxes(items,y=58,h=76):
 gap=14;n=len(items);width=(W-2*M-gap*(n-1))/n
 for i,(title,txt) in enumerate(items):
  x=M+i*(width+gap);C.setFillColor(PALE);C.roundRect(x,y,width,h,8,fill=1,stroke=0);C.setFont('Bold',12);C.setFillColor(INK);C.drawString(x+14,y+h-22,title);text(txt,x+14,y+h-32,width-28,'small')

def twin(left,right,labels,yy=245,hh=440):
 gap=20;ww=(W-2*M-gap)/2
 picture(left,M,yy,ww,hh);picture(right,M+ww+gap,yy,ww,hh)
 for i,lab in enumerate(labels):text(lab,M+i*(ww+gap),yy-7,ww,'body')

def metric(val,label,x,y,w=240):
 C.setFillColor(PALE);C.roundRect(x,y,w,70,8,fill=1,stroke=0);C.setFont('Bold',22);C.setFillColor(INK);C.drawString(x+16,y+37,val);text(label,x+16,y+26,w-32,'small')

# 01
page('Мягкая посадка. Самостоятельный столик.','Обновлённая CAD-сборка R06: без жёсткой спинки, с переставляемым упором стоп и объёмным укрытием-спальником.','ОБЩИЙ ВИД')
picture('work_folded.png',y=151,h=555)
boxes([('Спина без рамы','Три формирующие камеры, свободный контактный мешок и внутренние текстильные тяги.'),('Стопы — по месту','Перемещаемый мягкий упор и пять точек настройки. Столик регулируется отдельно.'),('Один внешний кокон','Верх и низ из одного наружного материала и цвета. Клапан клавиатуры пассивный.')])
finish()
# 02
page('Внутреннее пространство с человеком','Внешнее укрытие скрыто, правая половина мягких объёмов отсечена. Манекен — габаритная модель, не анатомический расчёт.','ПОСАДКА / РАЗРЕЗ')
picture('occupied_cutaway.png',y=155,h=552)
boxes([('B01–B04: мягкая опора','За спиной нет труб, шарниров или натянутой на раму спинки. Показаны посадочные объёмы мешков.'),('P01–P02: таз и бёдра','Отдельная камера ограничивает уход наполнителя к ногам. Переход под бёдрами мягкий.'),('D: только для ноутбука','Слева — две С-консоли. Низ локальной опоры расположен внутри мягкого днища.')])
finish()
# 03
page('Камерная спинка вместо жёсткой конструкции','Разнесённый технический вид: контактный мешок поднят для осмотра; формирующие камеры раздвинуты.','ВНУТРЕННИЙ МОДУЛЬ')
picture('back_chambers.png',y=170,h=536)
boxes([('Формирующий слой','Камеры B01–B03 задают общую форму. Между ними отдельные текстильные перегородки.'),('Контактный слой','B04 обминается под спину независимо от основного профиля. В CAD задан его номинальный объём.'),('Две внутренние тяги','Тяги шириной 44 мм идут по бокам мешков, а не вокруг человека. Фиксаторы пока показаны габаритно.')],h=85)
finish()
# 04
page('Работа и расслабление: две заданные посадки','Сравнение в одном масштабе. Углы 55° и 35° — сценарии формы, а не гарантированная настройка мешка.','НАСТРОЙКА ФОРМЫ')
picture('work_side.png',M,428,W-2*M,278);picture('relax_side.png',M,133,W-2*M,278)
C.setFont('Bold',15);C.setFillColor(INK);C.drawString(M+5,676,'55° / собранная форма');C.drawString(M+5,381,'35° / расслабленная форма')
text('Во втором сценарии столик припаркован на 80 мм вперёд, стопный блок убран. Форма камер задана отдельно; пересыпание гранул, сила затяжки лент, постоянство засыпки и динамика «стекания» не рассчитывались.',M,108,W-2*M,'body')
finish()
# 05
page('С-образный модуль обслуживает только столик','Исходные детали столика и ноутбука импортированы из R05. Опора пересобрана без спинных труб и подкосов.','ЛОКАЛЬНАЯ РАМА')
picture('table_module.png',y=228,h=475)
metric(f"{V['table_tube_mass_kg']:.2f} кг",'Расчётная масса труб; не масса всего кокона.',M,138,280)
metric('955–1565 мм','Продольный диапазон осей жёсткой опоры.',M+299,138,280)
metric(f"{min(r['minimum_margin_mm'] for r in S):.0f} мм",'Минимальный запас центра тяжести до края опорного контура в четырёх статических сценариях.',M+598,138, W-2*M-598)
text('Расчёт собственного веса выполнен для ровного жёсткого пола, без человека и гранул в качестве балласта. Мягкое днище меняет контакт с полом: устойчивость нужно проверить физически. Столик не предназначен для подтягивания при вставании; замки регулировки ещё не спроектированы в деталях.',M,118,W-2*M,'body')
finish()
# 06
page('Переставляемый упор стоп','Три полупрозрачных положения одного мягкого блока. Крепление передаёт усилие внутреннему усиленному днищу, не столику.','НАСТРОЙКА ПО РОСТУ')
picture('foot_adjustment.png',y=234,h=469)
cols=[M,M+242,M+515,M+820]
for x,t in zip(cols,['Ростовой сценарий','Передняя грань упора X','Смещение столика по Z','Положение']):C.setFont('Bold',10);C.setFillColor(INK);C.drawString(x,208,t)
for i,f in enumerate(F):
 y=183-i*27;C.setFont('Reg',11);C.setFillColor(MUTED)
 for x,t in zip(cols,[f"{f['scenario_height_mm']//10} см",f"{f['stop_front_x_mm']:.0f} мм",f"{f['table_delta_z_mm']:+.1f} мм",'исходное' if i==2 else 'иллюстративное']):C.drawString(x,y,t)
text('Диапазон упора — 220 мм; пять точек через 55 мм. Ростовые значения — пропорциональные габаритные сценарии, а не подтверждённый размерный ряд. Длину туловища, продавливание наполнителя, положение головы и подстройку укрытия нужно проверять отдельно.',M,99,W-2*M,'body')
finish()
# 07
page('Пустой кокон: какие объёмы остаются внутри','Разрез без манекена позволяет увидеть мягкую спинку, отдельную тазовую зону, опору голеней и нижние крепления.','ПРОСТРАНСТВО / БЕЗ ЧЕЛОВЕКА')
picture('empty_cutaway.png',y=159,h=548)
boxes([('Нет жёсткой спины','За головой и вдоль спины отсутствует несущая рама. Мягкая форма может меняться.'),('Нет наружных ножек','Нижняя тканевая оболочка лежит на полу; низ столика скрыт в мягком днище.'),('Не модель контакта','Пересечения мягких посадочных объёмов не являются рассчитанным продавливанием. Масса засыпки не назначена.')])
finish()
# 08
page('Укрытие — объёмный спальник, а не лист','Технический разнесённый вид. Плечевой блок и клавиатурный клапан приподняты только для показа швейной конструкции.','ТКАНЕВАЯ ОБОЛОЧКА')
picture('padded_layers.png',y=153,h=554)
boxes([('Одинаковый наружный материал','Цвет и тканевая фактура совпадают с нижним полукоконом. Швы и наполненные камеры формируют рельеф.'),('Две разные поверхности','Наружная и внутренняя оболочки смоделированы отдельно. Толщина в гребне секции достигает 48 мм.'),('Разное наполнение по функции','В опорных мешках — гранулы; в верхнем укрытии — лёгкий объёмный утеплитель. Его марка ещё не выбрана.')])
finish()
# 09
page('Руки укрыты; клавиатура открывается отдельно','Клапан без нагревателя, проводки, каркасных дуг и жёсткой петли. Основное плечевое укрытие остаётся на месте.','КЛАПАН / ДВА СОСТОЯНИЯ')
twin('hands_closed.png','hands_folded.png',['Закрыто: продолжение основного укрытия над кистями.','Отогнуто к человеку: доступ к клавиатуре без раскрытия плеч.'],yy=232,hh=470)
text('Отгиб задан как отдельное геометрическое состояние; работа ткани в складке и сохранение её размеров при складывании ещё не проверены. Свободное пространство для экрана оставлено, но охлаждение конкретного ноутбука и температура рук не рассчитаны.',M,118,W-2*M,'body')
finish()
# 10
page('Правый бок — сторона входа и выхода','Продольное разъёмное соединение предусмотрено справа. Разрез ниже показывает расположение опоры, а не имитирует тканевую симуляцию.','ДОСТУП / ОБСЛУЖИВАНИЕ')
picture('right_access_cutaway.png',y=158,h=549)
boxes([('Столик остаётся в коконе','Для подготовки выхода он сдвигается вперёд на 80 мм вместе с ноутбуком. Показана кинематика, не конструкция направляющей.'),('Нет стойки справа','Несущие стойки находятся слева. Контур борта раскрывается со стороны правой руки.'),('Выход ещё не испытан','Раскрывание борта, перенос веса, постановка ног и доступ к застёжкам требуют полноразмерного макета.')])
finish()
# 11
page('Макетные развёртки получены из новых 3D-поверхностей','Три сегмента: плечо Q02, клапан Q04 и ножная часть Q06. Для каждого отдельно развёрнуты наружная и внутренняя стороны.','CAD → ЧЕРНОВЫЕ ЛЕКАЛА')
picture('draft_patterns.png',M,138,W-2*M,569,crop=False)
mx=max(p['max_edge_distortion_percent'] for p in PAT)
text(f'Это не полный производственный раскрой. Припуск 12 мм — предварительный. Максимальное изменение ребра расчётной сетки среди шести развёрток: <b>{mx:.2f}%</b>. Не проверены общий баланс швов, усадка, растяжение материала и технологическая посадка утеплённого пакета.',M,113,W-2*M,'body')
finish()
# 12
page('Почему внутреннее и наружное лекала разные','Поперечное сечение Q04, X = 1197,5 мм. Контуры сняты с той же геометрии, из которой создан STEP.','СЕЧЕНИЕ УТЕПЛЁННОГО ПАКЕТА')
g=json.loads((ROOT/'cad/cover_grids.json').read_text())['Q04_KEYBOARD_CLOSED'];ou=np.array(g['outer_grid_mm'])[5][:,1:3];inn=np.array(g['inner_grid_mm'])[5][:,1:3]
sc=.90;origin=np.array([W/2,278]);z0=min(ou[:,1].min(),inn[:,1].min())
def path2(a,col,lw):
 p=C.beginPath();xy=(a-np.array([0,z0]))*sc+origin;p.moveTo(*xy[0])
 for q in xy[1:]:p.lineTo(*q)
 C.setStrokeColor(col);C.setLineWidth(lw);C.drawPath(p)
path2(ou,ACCENT,3.2);path2(inn,colors.HexColor('#b28358'),3.2)
# short connectors visualize fill depth from actual vertices.
for i in range(2,len(ou)-2,3):
 a=(ou[i]-[0,z0])*sc+origin;b=(inn[i]-[0,z0])*sc+origin
 C.setStrokeColor(colors.HexColor('#ccd7d2'));C.setLineWidth(1);C.line(*a,*b)
cc=next(q for q in COV if q['id']=='Q04_KEYBOARD_CLOSED')
metric(f"{cc['outer_section_arc_mm']:.1f} мм",'Наружная дуга сечения',M,171,330);metric(f"{cc['inner_section_arc_mm']:.1f} мм",'Внутренняя дуга сечения',M+347,171,330);metric(f"{cc['difference_mm']:.1f} мм",'Разница дуг в этом сечении',M+694,171,W-2*M-694)
text('Зелёный — наружный контур; охристый — внутренний. В середине — номинальные 48 мм наполненного пакета; у бокового шва толщина уменьшается. Числа относятся к дугам сечения, а не к расходу ткани или готовым длинам швов. Технологические перегородки ещё надо согласовать с пробным пошивом.',M,140,W-2*M,'body')
finish()
# 13
page('Проверяемый результат работы с CAD','Настоящий захват экрана собственного интерактивного просмотрщика OpenCASCADE / VTK. Это не интерфейс CLO или SolidWorks.','ПРОГРАММНЫЙ РЕЗУЛЬТАТ')
picture('screenshots/VTK_R06_actual.png',M,162,W-2*M,542,crop=False)
text(f"Из R05 по именам импортировано <b>{BUILD['reused_count']}</b> компонентов столика и ноутбука. В комплекте есть исходник R06, входной STEP R05, новые сборки, сетки, параметры, отчёты проверок и этот PDF. Снимки в альбоме — рендеры CAD-геометрии; фактура ткани процедурная.",M,120,W-2*M,'body')
finish()
# 14
page('Что изменено и что ещё предстоит проверить','Ревизия R06 завершает геометрическую перекомпоновку. Она не заменяет испытания мягкой мебели и нагревательного прибора.','СТАТУС РЕВИЗИИ')
left=M;right=620
text('<b>Выполнено</b>',left,691,510,'large')
text('Удалены спинные трубы, подкосы и натянутая на них спинка. Созданы отдельные гранулярные камеры, контактный мешок, боковые тяги и мягкая тазовая зона. Упор стоп имеет пять положений. Нижняя оболочка и верхнее укрытие получили объём, одинаковую наружную ткань и отдельные поверхности подкладки.',left,654,510,'large')
text(f'<b>{V["passed"]} из {V["total"]}</b> программных проверок прошли. Девять STEP-сборок заново прочитаны OpenCASCADE; шесть DXF макетных лекал прочитаны и проверены отдельно. Удаление спинной рамы и отсутствие нагревателя в клапане проверяются по структуре модели.',left,485,510,'large')
text('<b>Не подтверждено</b>',right,691,W-M-right,'large')
text('Удержание заданного угла, перераспределение гранул, одинаковая засыпка в двух посадках, локальные давления и комфорт. Пределы нагрузки столика, крепления, замки, работа мягкого днища на разных полах. Полный процесс входа и выхода, работа толстого клапана, температура под укрытием и охлаждение ноутбука.',right,654,W-M-right,'large')
text('Макетные лекала не разрешены к производственному раскрою. Наружная оболочка всего кокона ещё не развёрнута и не согласована по швам. Изделие не предназначено для использования под напряжением до проверки нагревательных узлов и независимых защит.',right,485,W-M-right,'large')
C.setFillColor(PALE);C.roundRect(M,157,W-2*M,170,10,fill=1,stroke=0)
text('<b>Следующий проверочный макет</b>',M+20,302,W-2*M-40,'large')
text('Дешёвый чехол, выбранные гранулы с известной массой засыпки, регулируемые тяги и локальная опора столика. Сначала проверить посадку, поддержку стоп, отгиб клапана и выход справа; затем переносить корректировки в лекала.',M+20,269,W-2*M-40,'large')
text('В R06 изменены только CAD, макетные развёртки и документация. Электроника, прошивки, приложения и вышивка предыдущих ревизий не изменялись.',M,118,W-2*M,'body')
finish()
C.save();print(OUT,page_count,flush=True)
