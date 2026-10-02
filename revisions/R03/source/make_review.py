from pathlib import Path
import json,csv,math
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4,landscape
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph,Table,TableStyle
from reportlab.lib.styles import ParagraphStyle
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
pdfmetrics.registerFont(TTFont('DV','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('DVB','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
SZ=landscape(A4);PW,PH=SZ
C=canvas.Canvas(str(ROOT/'docs/Spim_s_haski_R03_sew_sheet.pdf'),pagesize=SZ)
C.setTitle('Спим с хаски — R03. Объектная оцифровка шеврона')
C.setAuthor('Проект Лежандр')
navy=HexColor('#244963');muted=HexColor('#52626D');cream=HexColor('#F8F6EE')
style=ParagraphStyle('body',fontName='DV',fontSize=9,leading=13,textColor=navy)
small=ParagraphStyle('small',parent=style,fontSize=7.2,leading=10)
def text(s,x,top,w,size=9,bold=False):
 st=ParagraphStyle('t',parent=style,fontName='DVB' if bold else 'DV',fontSize=size,leading=size*1.4)
 p=Paragraph(s,st);ww,hh=p.wrap(w*mm,200*mm);p.drawOn(C,x*mm,PH-top*mm-hh);return hh/mm

def page(title,sub,no):
 C.setFillColor(cream);C.rect(0,0,PW,PH,fill=1,stroke=0)
 C.setFillColor(navy);C.setFont('DVB',20);C.drawString(14*mm,PH-16*mm,title)
 text(sub,14,20,268,8)
 C.setStrokeColor(HexColor('#CCD5D8'));C.line(14*mm,PH-30*mm,PW-14*mm,PH-30*mm)
 C.setFont('DV',7);C.setFillColor(muted)
 C.drawString(14*mm,8*mm,'СПИМ С ХАСКИ / ЛЕЖАНДР   ·   R03   ·   01.10.2026   ·   ПРОБНЫЙ ОТШИВ НЕ ВЫПОЛНЕН')
 C.drawRightString(PW-14*mm,8*mm,str(no))
def pic(file,x,top,w,h):
 im=Image.open(ROOT/file);ar=im.width/im.height;ww=w;hh=w/ar
 if hh>h:hh=h;ww=hh*ar
 C.drawImage(str(ROOT/file),x*mm,PH-(top+hh)*mm,width=ww*mm,height=hh*mm,mask='auto')
 return hh

def box(s,x,top,w,h):
 C.setFillColor(HexColor('#E8EEF0'));C.roundRect(x*mm,PH-(top+h)*mm,w*mm,h*mm,2*mm,fill=1,stroke=0)
 text(s,x+3,top+3,w-6,8)
report=json.loads((ROOT/'tests/validation.json').read_text())
page('Спим с хаски / шеврон R03','Лицо, пять завитых хвостов и надпись. Изображение ниже построено из повторно прочитанного DST.',1)
pic('previews/decoded_DST.png',14,34,144,159)
text('Поле вышивки: 140 × 155 мм',170,37,111,13,True)
text('50 691 прокол · 8 цветов<br/>13 блоков / 12 смен цвета<br/>347 запросов обрезки',170,51,111,10)
text('61 область татами<br/>108 сатиновых колонок',170,76,111,11,True)
text('Буквы и кайма — поперечный сатин. Крупные цветовые поля — татами. Под каждым типом предусмотрена своя подложка.',170,96,108,9)
box('Это визуализация траекторий с условной шириной нити 0,36 мм. Она не предсказывает укрывистость, блеск, стягивание ткани или результат реального отшива.',170,126,112,28)
text('DST + EXP + редактируемый SVG<br/>Проверить полезное поле пялец, команды обрезки и порядок нитей перед загрузкой. Файл не масштабировать без повторной оцифровки.',170,165,110,8)
C.showPage()
page('Рисунок → швейные объекты','Ручная перерисовка смысловых границ. Волокна на исходной картинке не превращаются в сотни случайных пятен.',2)
text('ОДОБРЕННАЯ КОМПОЗИЦИЯ R02',16,34,125,9,True)
text('ОБЪЕКТНЫЙ ЭСКИЗ R03',160,34,125,9,True)
pic('source/approved_logo_crop.png',16,43,121,129)
pic('previews/logo_vector.png',165,43,116,129)
box('Сохранён сюжет, но детали упрощены для вышивания. Шерсть разделена на крупные поля; глаза, улыбка, контуры, лапки и буквы заданы отдельно. Это не обещание точного пиксельного совпадения с исходным изображением.',15,178,268,19)
C.showPage()
page('Сатин и татами — разные траектории','Фрагменты ниже вырезаны из тонколинейной визуализации настоящего DST. Увеличение предназначено для проверки стежков.',3)
text('САТИНОВЫЕ БУКВЫ',15,35,126,10,True)
pic('previews/detail_satin_letters.png',15,44,126,55)
text('Один поперечный стежок идёт от рельса к рельсу. Шаг по одноимённой стороне — 0,40 мм. Номинальная ширина букв — 1,65 мм; компенсация +0,12 мм на сторону.',15,102,125,9)
text('ТАТАМИ / ЛИЦО И ПОДЛОЖКА',157,35,126,10,True)
pic('previews/detail_face_fill.png',157,44,126,84)
text('Междурядье 0,42 мм, длина в ряду до 3 мм. Соседние ряды смещены. Подложка разреженная; на этой диагностической картинке видна намеренно.',157,130,124,8)
pic('previews/test_coupon.png',15,145,125,47)
text('ТЕСТОВЫЙ КУПОН<br/>Татами + колонки 1,6 / 2,8 мм + буква.<br/>Сначала проверить нить и натяжение на нём, затем отшить полный логотип.',157,163,124,8)
C.showPage()
page('Порядок нитей и контроль отшива','Восемь физических цветов возвращаются в нескольких блоках. RGB — цветовые цели, не номера каталога ниток.',4)
rows=list(csv.DictReader((ROOT/'machine/thread_sequence.csv').open(encoding='utf-8-sig')))
data=[['Блок','Цвет','Проколы']]+[[r['block'],r['name'],r['needle_points']] for r in rows]
t=Table(data,colWidths=[18*mm,76*mm,27*mm],rowHeights=9.1*mm)
t.setStyle(TableStyle([('FONTNAME',(0,0),(-1,-1),'DV'),('FONTSIZE',(0,0),(-1,-1),9),('BACKGROUND',(0,0),(-1,0),navy),('TEXTCOLOR',(0,0),(-1,0),HexColor('#FFFFFF')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LINEBELOW',(0,0),(-1,-1),.3,HexColor('#CFD6D8')),('ALIGN',(2,0),(2,-1),'RIGHT')]))
t.wrapOn(C,150*mm,200*mm);t.drawOn(C,15*mm,PH-38*mm-t._height)
text('ДО ЗАПУСКА',153,36,130,10,True)
text('Проверить полезное поле не менее 150 × 165 мм; исходно подойдут пяльцы 200 × 200 мм только при совместимости с машиной. Основа — отдельный стабильный твил; нить и стабилизатор выбираются по ткани.',153,45,129,9)
text('ПОСЛЕ ПОЛНОГО ПРОБНОГО ОТШИВА',153,80,130,10,True)
text('Проверить просветы у контуров, стягивание, буквы, уплотнение в углах и работу обрезок. 347 обрезок ещё требуют производственной оптимизации. Сатиновая рамка — не оверлочный Merrow.',153,89,129,9)
text('ЧТО ДЕЙСТВИТЕЛЬНО ПРОВЕРЕНО',153,122,130,10,True)
text('DST и EXP повторно прочитаны; координаты проколов совпали. SVG разобран и отрендерен Inkscape 1.4. Последовательных одинаковых проколов нет. Движки Ink/Stitch и Wilcom здесь не исполнялись; программа получена собственным оцифровщиком.',153,131,129,9)
box('Не вышивать через собранный кокон, нагреватели и проводку. Сначала изготовить отдельную нашивку. Вырезание и обметывание её края не входят в DST/EXP.',153,170,130,24)
text('Источники техники: Wilcom «Mastering Satin Stitch and Tatami Stitch»; документация Ink/Stitch Satin Column / Tatami. Ссылки в docs/SOURCES.md.',15,180,121,7)
C.showPage();C.save()
print(ROOT/'docs/Spim_s_haski_R03_sew_sheet.pdf')
