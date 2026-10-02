#!/usr/bin/env python3
"""Programmatic A3 engineering album and 1:1 A0 prototype patterns.
Only generated assets/own CAD and primary-source references are used.
"""
from pathlib import Path
import json,csv,math,html
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3,A0,landscape
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph,Table,TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image,ImageChops
R=Path(__file__).resolve().parents[1]; D=R/'docs';D.mkdir(exist_ok=True)
for face,filename in [('DejaVu','DejaVuSans.ttf'),('DejaVu-Bold','DejaVuSans-Bold.ttf'),('DejaVu-Mono','DejaVuSansMono.ttf')]:
 pdfmetrics.registerFont(TTFont(face,'/usr/share/fonts/truetype/dejavu/'+filename))
pdfmetrics.registerFontFamily('DejaVu',normal='DejaVu',bold='DejaVu-Bold',italic='DejaVu',boldItalic='DejaVu-Bold')
INK=colors.HexColor('#152A36');MID=colors.HexColor('#52656F');ACC=colors.HexColor('#C17B35');PALE=colors.HexColor('#EDF2F4');LINE=colors.HexColor('#CBD5DA')
W,H=landscape(A3); M=40
c=canvas.Canvas(str(D/'Lezhandr_R01_engineering_album.pdf'),pagesize=(W,H));c.setTitle('Спим с хаски — ЛЕЖАНДР R01. Инженерный альбом');c.setAuthor('Проект «Спим с хаски» / R01')
page=0
style=ParagraphStyle('body',fontName='DejaVu',fontSize=12,leading=18,textColor=INK,spaceAfter=8)
def p(text,x,y,w,size=12,leading=None):
 st=ParagraphStyle('p',parent=style,fontSize=size,leading=leading or size*1.42)
 q=Paragraph(text,st);_,h=q.wrap(w,10000);q.drawOn(c,x,y-h);return y-h-10

def head(title,sub=''):
 global page
 if page:c.showPage()
 page+=1;c.setFillColor(INK);c.rect(0,H-15,W,15,fill=1,stroke=0)
 c.setFont('DejaVu',10);c.drawString(M,H-39,'СПИМ С ХАСКИ   /   ЛЕЖАНДР')
 c.setFont('DejaVu-Bold',24);c.drawString(M,H-75,title)
 if sub:p(sub,M,H-91,W-2*M,10)
 c.setStrokeColor(LINE);c.line(M,36,W-M,36)
 c.setFillColor(MID);c.setFont('DejaVu',8);c.drawString(M,22,'R01 • 30.09.2026 • СТЕНДОВЫЙ ПРОТОТИП • НЕ ПРОИЗВОДСТВЕННЫЙ РЕЛИЗ')
 c.drawRightString(W-M,22,f'{page:02d}')

def table(data,x,y,widths,size=11):
 st=ParagraphStyle('cell',parent=style,fontSize=size,leading=size*1.35)
 cells=[[Paragraph(html.escape(str(v)).replace('\n','<br/>'),st) for v in row] for row in data]
 t=Table(cells,colWidths=widths,repeatRows=1,hAlign='LEFT');t.setStyle(TableStyle([
 ('BACKGROUND',(0,0),(-1,0),PALE),('LINEBELOW',(0,0),(-1,0),1,ACC),('LINEBELOW',(0,1),(-1,-1),.4,LINE),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
 _,hh=t.wrap(sum(widths),H);assert y-hh>43,(page,y,hh)
 t.drawOn(c,x,y-hh);return y-hh-15

def img(path,x,y,w,h,crop=True):
 path=R/path
 if crop and 'cad/renders' in str(path):
  im=Image.open(path).convert('RGB');bg=Image.new('RGB',im.size,im.getpixel((0,0)))
  mask=ImageChops.difference(im,bg).convert('L').point(lambda v:255 if v>14 else 0)
  bb=mask.getbbox()
  if bb:
   bb=(max(0,bb[0]-25),max(0,bb[1]-25),min(im.width,bb[2]+25),min(im.height,bb[3]+25))
   (D/'assets').mkdir(exist_ok=True);out=D/'assets'/path.name;im.crop(bb).save(out);path=out
 with Image.open(path) as im:iw,ih=im.size
 scale=min(w/iw,h/ih);ww,hh=iw*scale,ih*scale;c.drawImage(str(path),x+(w-ww)/2,y+(h-hh)/2,ww,hh,mask='auto')

def photo_page(title,name,note,sub='Вид получен из той же твердотельной сборки CadQuery / OpenCASCADE; не генеративная иллюстрация.'):
 head(title,sub);img('cad/renders/'+name+'.png',M,80,W-2*M,H-220);p(note,M,70,W-2*M,10)

def box(txt,x,y,w,h,accent=False,size=12):
 c.setFillColor(PALE if not accent else colors.HexColor('#F6EADB'));c.setStrokeColor(LINE);c.roundRect(x,y,w,h,7,fill=1,stroke=1);p(txt,x+12,y+h-12,w-24,size)

def arrow(x1,y1,x2,y2):
 c.setStrokeColor(INK);c.setFillColor(INK);c.setLineWidth(1.3);c.line(x1,y1,x2,y2)
 ang=math.atan2(y2-y1,x2-x1);path=c.beginPath();path.moveTo(x2,y2)
 for a in [-.45,.45]:path.lineTo(x2-8*math.cos(ang+a),y2-8*math.sin(ang+a))
 path.close();c.drawPath(path,fill=1,stroke=0)
P=json.loads((R/'project.json').read_text());calc=json.loads((D/'calculations.json').read_text());cw=json.loads((R/'tests/results/cad_work.json').read_text());cs=json.loads((R/'tests/results/cad_sleep.json').read_text())
head('ЛЕЖАНДР','Утеплённое рабочее место на балконе, трансформируемое в спальное место')
img('cad/renders/work_iso.png',M,178,W-2*M,520)
p('<b>3D CAD • платы • прошивка • Java Desktop • Android Java</b>',M,163,W-2*M,17)
p('Ревизия R01 содержит проверяемые исходники и стендовую демонстрацию. Человеческие, тепловые и аппаратные испытания не проведены. Непрерывный нагрев во сне не разрешён.',M,126,W-2*M,12)
p('2200 мм по схеме секций   |   4 зоны / 60 Вт при 12 В   |   внешний источник 512 Вт·ч   |   USB + BLE',M,72,W-2*M,11)
head('01 / Что именно спроектировано','Граница между выполненным цифровым прототипом и ещё не выпущенным физическим изделием')
y=table([['Узел','Предоставлено','Предел готовности'],['Механика','2 STEP-сборки, STL, DXF, CAD-исходник; 100 / 92 валидных тела','Нет расчёта всей рамы, испытания нагрузки и полной деталировки замков'],['Мягкая часть','Оболочки кокона, подушки, боковины, накрывайка; макетные A0-развёртки','Посадка, молнии, окно рук и воздуховоды ноутбука требуют примерки'],['Электроника','A1: 4 силовых канала; A2: 8 NTC и watchdog; схемы, BOM и PCB','Не выполнены KiCad ERC/DRC; PD, BMS, DC/DC — внешние покупные модули'],['Прошивка','Общее C++17-ядро + ESP32-S3 Arduino/BLE/USB-часть','50 нативных тестов; аппаратный ESP32 binary не собран'],['Приложения','Собранный Java JAR; исходники Android Java; общий H1','12 Java-тестов + 25 интеграционных; Android APK не собран']],M,H-140,[175,440,W-2*M-615])
p('<b>Принятые предположения:</b> рост 200 см, масса для предварительного расчёта 120 кг; полезная ширина 600 мм; конкретные балкон, ноутбук, батарея и материалы текстиля не обмерены и не выбраны.',M,y,W-2*M,12)
p('Алюминиевая рама заменяет прежний вариант с ПВХ. Ощущение кресла-мешка создают съёмные мягкие боковины и подушки. Жёсткая часть держит геометрию, а не полагается на наполнитель.',M,y-80,W-2*M,12)
photo_page('02 / Работа: общая компоновка','work_iso','Серое — несущий каркас; охристое — опоры и нагреватели; сине-серое полупрозрачное — текстильные оболочки. Прозрачность введена только для пояснения устройства.')
photo_page('03 / Работа: вид сбоку','work_side','Спинка 40° к горизонтали, ножная секция −8°. Ось шарнира сиденья Z=420 мм; полка Z=715 мм. Размеры — проектные, эргономическая примерка не выполнена.')
photo_page('04 / Работа: вид сверху','work_top','Мягкая часть до 820 мм; полный габарит с боковым контроллером — около 860 мм. Сигнальные и силовые жгуты требуют отдельной прокладки и разгрузки натяжения.')
photo_page('05 / Работа: вид с торца','work_front','Ширина между проектными ограничениями тела — 600 мм; подушки 650 мм. Вентиляция ноутбука должна оставаться сообщённой с наружным воздухом.')
photo_page('06 / Несущий каркас и опоры','work_frame','Основные трубы 35×35×2 мм, три секции с гнутыми ламелями. Телескопические подкосы и шарниры — компоновочные тела; отверстия, щеки и фиксаторы ещё требуют рабочих чертежей.')
photo_page('07 / Продольный полуразрез','work_section','Операция Boolean intersection Y≥0 выполнена над BREP-деталями. Нагреватели находятся на верхней оболочке, не под нагруженными точками тела. Коллизии всей трансформации не проверены.','Реальный геометрический полуразрез исходной CAD-сборки; ближняя половина удалена.')
photo_page('08 / Сон: общая компоновка','sleep_iso','Спинка и ноги выведены в одну плоскость. Полка снята и припаркована сбоку, накрывайка рук удалена. В режиме SLEEP все нагревательные выходы выключены.')
photo_page('09 / Сон: вид сбоку','sleep_side','850 + 550 + 800 = 2200 мм — кинематическая длина секций; крайние поверхности этой сборки занимают 2180 мм. Сон с нагревом не выпущен в R01.')
photo_page('10 / Сон: вид сверху','sleep_top','С припаркованной полкой полный габарит около 2180 × 891 мм. Это не минимальный размер балкона: дополнительно нужен проход и свободный выход.')
photo_page('11 / Сон: вид с торца','sleep_front','Ручное складывание только без человека, с отключённым нагревом и снятым ноутбуком. Перед нагрузкой оба боковых фиксатора должны быть механически зафиксированы.')
head('12 / Нагревательные кассеты','Нихром принят как расчётная гипотеза вместо неуточнённой «неодимовой нити»')
data=[['CAD / зона','P при 12 В','R','Поверхность CAD','Плотность мощности']]
for z in P['zones']:data.append([f'EH{z["id"]} / {z["name"]}',f'{z["watts"]} Вт',f'{z["ohms"]} Ом',f'{z["area_m2"]} м²',f'{z["watts"]/z["area_m2"]:.1f} Вт/м²'])
y=table(data,M,H-140,[240,150,150,210,W-2*M-750])
p('Панели повторяют внутреннюю поверхность верхней оболочки. Их площадь задана как длина фактической ломаной CAD-дуги × длина панели. Это устраняет несогласованность между формой панели и расчётом удельной мощности.',M,y,530,12)
p('Нагреватель для закупки: полностью изолированная гибкая кассета с проверенным изгибом, термозащитой и текстильным применением. Расчёт NiCr-проволоки в CSV — оценка электрической схемы, а не разрешение пришивать голую проволоку к ткани.',M,y-125,530,12)
box('<b>Защита каждой зоны</b><br/>2 NTC в разных точках; независимый NC-термостат в цепи K1; отдельный силовой термопредохранитель. Точная расстановка и номиналы подтверждаются испытаниями.',620,y-126,525,126,True)
box('<b>Не выдавать уставку за температуру кожи</b><br/>R01: уставка 28–37 °C, авария по датчику 40 °C. При 13,2 В мощность резистивной панели на 21% выше, чем при 12 В. Термостат 43 °C и fuse 60 °C — только предварительные номиналы.',620,y-302,525,158)
p('Источник материала: Kanthal Nikrothal 80 [1]. Область испытаний гибкого нагревательного изделия: IEC 60335-2-17 [2]; соответствие не установлено.',M,76,W-2*M,10)
head('13 / Питание и автономность','Силовая часть вынесена из тёплого кокона; управление и питание ноутбука разделены')
box('<b>Внешняя батарея</b><br/>8S LiFePO4<br/>25,6 В / 20 А·ч<br/>BMS + подходящее ЗУ',45,540,245,145,True)
box('<b>DC/DC</b><br/>стабилизированные 12 В<br/>≥100 Вт, ограничение тока и OVP',380,570,290,110)
box('<b>A2 + K1 → A1</b><br/>4 нагревательные зоны<br/>60 Вт при 12 В',805,570,325,110)
box('<b>USB-C PD SOURCE</b><br/>покупной модуль ≤100 Вт<br/>не PD-trigger/sink',380,405,290,110)
box('<b>Ноутбук</b><br/>совместимый PD-вход<br/>отдельный USB DATA → MCU',805,405,325,110)
arrow(290,625,380,625);arrow(670,625,805,625);arrow(290,565,335,565);arrow(335,565,335,460);arrow(335,460,380,460);arrow(670,460,805,460)
rows=[['Сценарий (предположение)','Нагрев / ноутбук','Расчётная автономность']]
for a,name in zip(calc['battery_scenarios'],['Небольшое потребление','Средний пример','Полная мощность']):rows.append([name,f'{a["heat_W"]} / {a["laptop_W"]} Вт',f'{a["hours"]:.2f} ч'])
y=table(rows,M,355,[450,300,W-2*M-750])
p('Модель: 512 Вт·ч × 0,8 полезной доли; КПД нагрева 0,92, PD 0,90; электроника 2 Вт. Холод, старение и реальная нагрузка не учтены. Энергия на несколько часов не отменяет ограничения R01: 30 минут WORK, затем физическое подтверждение.',M,y,W-2*M,11)
p('230 В внутрь текстиля не заводятся. Батарея, PD SOURCE и DC/DC в данном комплекте заданы требованиями; конкретные серийные модули и зарядка не выбраны.',M,74,W-2*M,10)
for idx,name,title,size in [(14,'A1_4zone_power','A1 / силовая плата','145 × 122 мм'),(15,'A2_sensor_watchdog','A2 / датчики и watchdog','200 × 160 мм')]:
 head(f'{idx:02d} / {title}',f'Трассировка из электрического графа проекта. {size}. Изображение не является скриншотом KiCad.')
 img('electronics/'+name+'_layout.png',M,80,745,635,False)
 x=825;ww=320;y=H-150
 if idx==14:
  texts=['<b>4 канала PWM</b><br/>STP55NF06L + TC4427. Логические входы 3,3 В, драйверы затворов питаются 12 В.','<b>Питание</b><br/>H12 после K1; RAW12 для драйверов. PGND и сигнальная GND соединены через RSTAR.','<b>Предохранители ветвей</b><br/>2,5 / 2,5 / 1,6 / 1,0 А — проектные значения, требующие сверки с кассетами и проводкой.']
 else:
  texts=['<b>8 NTC</b><br/>10 kΩ B3950, по два на зону; делители, RC-фильтры и выводы ADC.','<b>Аппаратный watchdog</b><br/>74HC123, TC4427 и Q1 управляют внешней катушкой K1. Активный высокий 1Q — pin 13.','<b>Контроль питания</b><br/>BAT 100k/10k, RAW12 47k/10k. Нужна проверка входов ADC при снятом питании MCU.']
 for t in texts:y=p(t,x,y,ww,12)-13
 y=p('<b>Результат собственной проверки</b><br/>0 нетрассированных пар; 0 нарушений межсетевого зазора 0,3 мм.',x,y,ww,12)-10
 p('<b>Не выполнено:</b> штатные KiCad ERC/DRC, подбор точных footprint, токовые/тепловые испытания и крепёж. Gerber не выпущен.',x,y,ww,12)
head('16 / Независимое отключение','Контур нагрева должен размыкаться не только программной командой')
boxes=[('RAW12',40,615,135),('E-STOP NC',205,615,165),('FOLD NC',400,615,165),('T0…T3 NC',595,615,190),('Катушка K1',825,615,280)]
for txt,x,y,w in boxes:box(txt,x,y,w,65,False,13)
for a,b in zip(boxes,boxes[1:]):arrow(a[1]+a[3],647,b[1],647)
box('MCU<br/>PERMIT + WD',80,425,240,105);box('74HC123<br/>таймаут heartbeat',420,425,270,105);box('TC4427 + Q1<br/>коммутация катушки',815,425,290,105)
arrow(320,480,420,480);arrow(690,480,815,480);arrow(960,530,960,615)
p('Внешняя NC-цепь включена в плюс катушки. Q1 коммутирует её минус. Силовой NO-контакт K1 выдаёт H12 на A1. Отдельные термопредохранители стоят в силовых цепях кассет. Время аппаратного watchdog нужно измерить на плате.',M,386,W-2*M,13)
y=table([['Событие','Реакция R01'],['Нет PING 5 секунд / зависший цикл / плохой датчик','PWM=0; PERMIT=0; авария защёлкнута'],['Складывание / влага / разрыв внешнего контакта','Нагрев не запускается или отключается'],['STOP / режим сна / окончание 30 минут','Выходы выключены; следующему нагреву нужна физическая ARM'],['Новый сеанс после аварии','Исправить причину; физическая ARM, затем START из приложения']],M,280,[500,W-2*M-500])
p('Недопустимы: питание 12/24 В на GPIO; соединение возвратов JHn.2 с GND; объединение внешнего 5 В и USB VBUS ноутбука. Полная внешняя коммутация: electronics/SAFETY_WIRING.md.',M,y,W-2*M,10)
head('17 / Java Desktop и Android','Скриншот реально запущенного JAR; аппаратный USB и Android здесь ещё не испытаны')
img('docs/desktop-running.png',M,245,730,430,False)
x=815;ww=330;y=H-145
for text in ['<b>Настольное приложение</b><br/>Java 17 / Swing. Деморежим, TCP к нативному ядру, USB через jSerialComm; температуры, PWM и CSV.','<b>Android Java</b><br/>BLE, защищённое сопряжение, SCAN/CONNECT permissions, сборка уведомлений по LF. Исходники, без собранного APK.','<b>Один протокол H1</b><br/>START, PREHEAT, STOP, SLEEP, PING, GET. Удалённой ARM/RESET нет. Одновременно использовать один клиент.']:
 y=p(text,x,y,ww,12)-18
box('Запуск готового настольного файла:<br/><font name="DejaVu-Mono">java -jar dist/lezhandr-desktop-demo.jar</font><br/><br/>USB в этом offline-JAR требует добавить jSerialComm; Maven-сборка с зависимостью предусмотрена в pom.xml, но здесь не выполнялась.',M,92,730,132)
p('BLE-приложение не поддерживает обогрев фоновым сервисом: при уходе с экрана отправляет STOP и прекращает PING. iOS не реализовано.',815,200,330,11)
head('18 / Предварительная механика и тепловая модель','Расчёты открыты в tools/calculations.py; ни FEM/CFD, ни модель кожи не выполнялись')
b=calc['beam_screening'];y=table([['Оценка отдельной балки','Значение / смысл'],['Сечение, пролёт','Al 35×35×2 мм; L=0,82 м'],['Сила в середине одной из двух балок','120×9,81×1,5 / 2 = 882,9 Н'],['Максимальное напряжение',f'{b["stress_MPa"]:.1f} МПа'],['Расчётный прогиб',f'{b["deflection_mm"]:.2f} мм'],['Чего этот расчёт не доказывает','Прочность сварки, шарниров и замков; усталость; устойчивость; допустимую массу изделия']],M,H-140,[395,W-2*M-395])
p('<b>Тепловой баланс — сценарий, не температурный рейтинг.</b> Использованы предположенные тепловые сопротивления всего пакета одежды/воздуха/утеплителя и утечки. Они не получены из сетки CAD и не подтверждены толщиной компоновочной оболочки.',M,y,W-2*M,12)
data=[['Наружный воздух','Нужно электрического тепла по гипотезе','Установлено']]
for a in calc['heat_balance_scenarios']:data.append([f'{a["ambient_C"]} °C',f'{a["needed_electric_W"]:.1f} Вт',f'{a["available_W"]} Вт'])
y=table(data,M,y-88,[300,500,W-2*M-800])
p('Сценарий −10 °C требует больше тепла, чем дают панели. Даже сценарий 0 °C не подтверждает комфорт: ветер, щели и реальные материалы могут изменить результат. Рекламировать температурный предел по этому расчёту нельзя.',M,y,W-2*M,11)
head('19 / Раскладка прямых заготовок','Исходные ID совпадают с STEP и parts_work.csv. Хлыст 6000 мм; учтён пропил 3 мм после каждой заготовки.')
bins=json.loads((R/'cad/stock_nesting.json').read_text());yy=H-175
for bi,b in enumerate(bins):
 p(f'<b>Хлыст {b["bar"]}: {b["stock"]}</b>   занято {b["used_mm"]:.1f} мм; остаток {6000-b["used_mm"]:.1f} мм',M,yy,W-2*M,11)
 x0=M;scale=(W-2*M)/6000;barY=yy-53
 c.setFillColor(PALE);c.setStrokeColor(LINE);c.rect(x0,barY,6000*scale,25,fill=1,stroke=1)
 for j,a in enumerate(b['cuts']):
  x=x0+a['start_mm']*scale;ww=a['length_mm']*scale
  c.setFillColor(colors.HexColor('#D4E2E8') if j%2==0 else colors.HexColor('#EAD9C8'));c.rect(x,barY,ww,25,fill=1,stroke=1)
  c.saveState();c.setFillColor(INK);c.setFont('DejaVu',7 if ww<55 else 8)
  if ww>=25:c.drawCentredString(x+ww/2,barY+9,a['ID'])
  c.restoreState()
 yy-=91
p('Алгоритм first-fit decreasing, не доказанный глобальный оптимум. Малые профили не обязательно покупать шестиметровыми хлыстами. Торцовка, припуски, тип соединения и реальные длины проката требуют уточнения.',M,102,W-2*M,11)
head('20 / Реестр резки: 38 заготовок','Из CAD-реестра, без отдельно выдуманной спецификации. Все длины в миллиметрах.')
rows=list(csv.DictReader((R/'cad/stock_cutting.csv').open(encoding='utf-8-sig')))
for chunk,x in [(rows[:19],M),(rows[19:],625)]:
 data=[['ID','Профиль','Длина']]+[[r['ID'],r['stock'].replace('Al_',''),r['cut_length_mm']]for r in chunk]
 table(data,x,H-140,[145,250,125],10)
p('Телескопические опоры Txx, шарниры Hxx, держатели ламелей и крепёж сюда не включены: их окончательная деталировка не выпущена. Не считать эту таблицу полным производственным BOM.',M,90,W-2*M,11)
head('21 / Проверки и границы выпуска','Сохранены журналы, исходники тестов и воспроизводимые команды; результаты не заменяют испытания изделия')
y=table([['Проверка','Результат','Что проверялось'],['C++ управляющее ядро','50 PASS','Обрывы/перегрев всех датчиков, контакты, таймауты, предел сеанса, переполнение millis'],['Java протокол','12 PASS','Разбор телеметрии, диапазоны и повреждённые команды'],['Java → C++ native core','25 PASS','Реальный поток команд/телеметрии, стоп, аварии, потеря связи, повторное подключение'],['CAD BREP','100 / 92 валидных тела','Геометрическая корректность отдельных тел; не коллизии и не FEM'],['Геометрия двух PCB','0 нетрассированных пар; 0 нарушений зазора','Собственный Shapely-контроль меди ≥0,3 мм; не KiCad DRC'],['Реальная аппаратура / ESP binary / APK','НЕ ВЫПОЛНЕНО','Нет платы, датчиков, нагрузки, телефона и инструментов полной аппаратной сборки']],M,H-140,[300,300,W-2*M-600],11)
p('<b>До изготовления:</b> детали замков и крепежа → примерка мягкой части и ноутбука → выбор внешних модулей → штатные KiCad ERC/DRC → стенд на резисторах → независимая термометрия текстиля → механические и электрические испытания.',M,y,W-2*M,12)
p('Не закрыты также защита ADC при снятом питании, окончательный power-mux USB, точные корпуса компонентов и единственный владелец USB/BLE-сеанса. Подробно: docs/DESIGN_REVIEW.md.',M,y-83,W-2*M,12)
head('22 / Источники и навигация по комплекту','Первичные документы; проектные числа отдельно отделены от паспортных характеристик')
sources=[('1','Kanthal — Nikrothal 80, резистивный NiCr-сплав','https://www.kanthal.com/en/products/datasheets/material-datasheets/wire/resistance-heating-wire-and-resistance-wire/nikrothal-80/'),('2','IEC 60335-2-17:2022 — область гибких нагревательных изделий','https://webstore.iec.ch/en/publication/70369'),('3','Espressif — USB Serial/JTAG ESP32-S3','https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-guides/usb-serial-jtag-console.html'),('4','Microchip — TC4427, DS20001422G','https://ww1.microchip.com/downloads/en/DeviceDoc/20001422G.pdf'),('5','STMicroelectronics — STP55NF06L','https://www.st.com/resource/en/datasheet/stp55nf06l.pdf'),('6','Nexperia — 74HC/HCT123','https://assets.nexperia.com/documents/data-sheet/74HC_HCT123.pdf'),('7','Android Developers — разрешения BLE','https://developer.android.com/develop/connectivity/bluetooth/bt-permissions'),('8','jSerialComm — документация Java serial','https://fazecast.github.io/jSerialComm/')]
y=H-150
for n,t,u in sources:y=p(f'[{n}] <link href="{u}" color="#244E66">{html.escape(t)}</link>',M,y,W-2*M,13)-6
p('<b>Начало работы:</b> README_RU.md. <b>CAD:</b> cad/step и cad/source. <b>Электроника:</b> electronics/PINOUT.md и SAFETY_WIRING.md. <b>Запуск:</b> dist/lezhandr-desktop-demo.jar. <b>Оставшиеся доработки:</b> docs/DESIGN_REVIEW.md.',M,y-20,W-2*M,13)
p('Отдельный PDF A0 содержит геометрические развёртки оболочек и нагревательных кассет для примерочного макета. Печатать 100%, без Fit-to-page, проверить контрольный отрезок 100 мм. Это не утверждённый комплект швейных лекал.',M,y-125,W-2*M,12)
c.save()
# A0 patterns with exact 1:1 geometry from the 24-segment CAD profile.
MM=72/25.4;PW,PH=landscape(A0)
pc=canvas.Canvas(str(D/'Lezhandr_R01_patterns_A0.pdf'),pagesize=(PW,PH));pc.setTitle('ЛЕЖАНДР R01 — макетные развёртки A0 / 1:1')
pattern_rows=[]
def arc_points(w,h):return [(w/2*math.cos(i*math.pi/24),h*math.sin(i*math.pi/24))for i in range(25)]
def arc(w,h):q=arc_points(w,h);return sum(math.dist(a,b)for a,b in zip(q,q[1:]))
def pathead(title,note):
 pc.setFillColor(INK);pc.setFont('DejaVu-Bold',24);pc.drawString(22*MM,PH-20*MM,'СПИМ С ХАСКИ / ЛЕЖАНДР R01 — '+title)
 pc.setFont('DejaVu',13);pc.drawString(22*MM,PH-30*MM,note)
 pc.setFont('DejaVu',11);pc.drawString(22*MM,14*MM,'A0, масштаб 1:1. Без подгонки к листу. Только ненагреваемый примерочный макет; не производственное лекало.')
 pc.setLineWidth(.6);pc.line(PW-150*MM,18*MM,PW-50*MM,18*MM);pc.setFont('DejaVu',12);pc.drawString(PW-150*MM,23*MM,'Контроль: 100 мм')
for ID,L,w,h in [('C1',670,790,230),('C2',530,790,240),('C3',740,790,190),('D23',380,690,150)]:
 a=arc(w,h);pathead(ID+' / заготовка оболочки','Сплошная линия — шовная поверхность CAD; пунктир — 15 мм макетного припуска. Окна и соединения наносить при примерке.')
 x=(PW-a*MM)/2;y=45*MM
 assert y+(L+15)*MM<PH-35*MM
 pc.setStrokeColor(INK);pc.setLineWidth(.7);pc.rect(x,y,a*MM,L*MM)
 pc.setDash(7,4);pc.rect(x-15*MM,y-15*MM,(a+30)*MM,(L+30)*MM);pc.setDash()
 pc.setFont('DejaVu-Bold',20);pc.drawString(x+20*MM,y+L*MM/2,f'{ID}: {a:.1f} × {L} мм по поверхности')
 pc.setFont('DejaVu',14);pc.drawString(x+20*MM,y+L*MM/2-12*MM,'Вырезать из макетной ткани; не из рабочего нагревательного пакета.')
 # Facet construction marks, center line.
 qs=arc_points(w,h);run=0
 for j in range(1,24):
  run+=math.dist(qs[j-1],qs[j]);xx=x+run*MM;pc.line(xx,y-3*MM,xx,y+3*MM)
 pc.setDash(10,5);pc.line(x+a*MM/2,y,x+a*MM/2,y+L*MM);pc.setDash()
 pattern_rows.append([ID,a,L,15,'outer textile mockup; window layout pending']);pc.showPage()
pathead('C31 / торец ножной оболочки','Контур взят из полигональной дуги CAD. Припуск 15 мм наносится наружу вручную; не включён в сплошную линию.')
q=arc_points(790,190);x=PW/2;y=250*MM;path=pc.beginPath();path.moveTo(x+q[0][0]*MM,y+q[0][1]*MM)
for xx,yy in q[1:]:path.lineTo(x+xx*MM,y+yy*MM)
path.close();pc.drawPath(path);pc.setFont('DejaVu-Bold',20);pc.drawString(x-150*MM,y+70*MM,'C31: 790 × 190 мм');pc.showPage()
for ID,area,w,h in [('EH0',.4,758,214),('EH1',.45,758,174),('EH2',.18,758,174),('EH3',.18,666,138)]:
 a=arc(w,h);L=area*1e6/a;pathead(ID+' / поверхность кассеты','Без припуска. Это внешняя поверхность CAD-кассеты, не рисунок укладки голой проволоки. Конструкция — по ТУ изготовителя нагревателя.')
 x=(PW-a*MM)/2;y=180*MM;pc.setStrokeColor(INK);pc.rect(x,y,a*MM,L*MM)
 pc.setFont('DejaVu-Bold',22);pc.drawString(x+20*MM,y+L*MM/2,f'{ID}: {a:.2f} × {L:.2f} мм = {area:.2f} м²')
 pc.setFont('DejaVu',14);pc.drawString(x+20*MM,y+L*MM/2-15*MM,'Номинал мощности и сопротивления: project.json / heater_calculation.csv')
 pattern_rows.append([ID,a,L,0,'heater outer surface; not wire manufacturing pattern']);pc.showPage()
pc.save()
with (D/'patterns.csv').open('w',newline='',encoding='utf-8-sig')as f:
 ww=csv.writer(f);ww.writerow(['ID','developed_width_mm','length_mm','allowance_mm','note']);ww.writerows(pattern_rows)
print('Generated album',page,'A3 pages; patterns 9 A0 pages')
