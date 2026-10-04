#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'revisions/R03'
SOURCES={'artwork.py':'eb12b333d41eaac16836292c470122fc45965ba18ca5756c273a156dd5cf1dda','build_embroidery.py':'26338785ef9b3ff47aa92a7b887fe978ab8c1a551125efc4df614817a2688391','build_coupon.py':'27c9093598839e0805716add3604b8187de7d85b2db2440de9e2a2886dd1aeff','machine_formats.py':'751ea58ef9bd8d989b7296f9b62bb72cb289f24f1c41ab2c8ff5e080509c177c','validate.py':'43ebe32ff4e11064dbeac6254b49bf356449850b4757f31dc1d4086cbc10d2d9'}
ORIGINALS={'machine/Spim_s_haski_R03_140x156.dst':'87b06ec047d55e03d9141cea0d9cc3323407142a0da7f18701724d18658ab86d','machine/Spim_s_haski_R03_140x156.exp':'438f3a5f7f957bea8804472331bd1de953a416b5155518a04151643ff22916bd','Spim_s_haski_R03_editable.svg':'0b4fc7743414606d18ff7a7b01b4fe089d3fe1504b7310a6f35d129502ac4e1f'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 for p,h in SOURCES.items():
  if sha(R/'source'/p)!=h:raise RuntimeError('Original source hash mismatch '+p)
 for p in ['build_embroidery.py','build_coupon.py','validate.py']:subprocess.run([sys.executable,str(R/'source'/p)],check=True)
 result=json.loads((R/'tests/validation.json').read_text())
 comparisons=[{'path':p,'sha256':sha(R/p),'original_sha256':h,'byte_exact_original':sha(R/p)==h} for p,h in ORIGINALS.items()]
 from reportlab.pdfgen import canvas
 from reportlab.pdfbase import pdfmetrics
 from reportlab.pdfbase.ttfonts import TTFont
 from reportlab.lib.utils import ImageReader
 from PIL import Image
 for n,f in [('R','DejaVuSans.ttf'),('B','DejaVuSans-Bold.ttf')]:pdfmetrics.registerFont(TTFont(n,'/usr/share/fonts/truetype/dejavu/'+f))
 C=canvas.Canvas(str(R/'docs/Embroidery_R03_recovery.pdf'),pagesize=(842,595));C.setTitle('Спим с хаски R03 — повторная сборка машинной вышивки')
 C.setFont('B',21);C.drawString(32,555,'Спим с хаски / R03 — восстановленная вышивка')
 C.setFont('R',10);C.drawString(32,533,'Из прежних исходников. Вид ниже построен из декодированного DST, не фотография отшива.')
 im=Image.open(R/'previews/decoded_DST.png');C.drawImage(ImageReader(im),36,64,width=390,height=435,preserveAspectRatio=True,anchor='c')
 labels=[('Проколы',str(result['needle_points'])),('Размер, мм',' × '.join(map(str,result['dimensions_mm']))),('Цветов / смен','8 / 12'),('Сатиновых колонок',str(result['satin_columns'])),('Областей татами',str(result['tatami_objects'])),('DST и EXP','прочитаны заново, проколы совпали'),('Пробный отшив','не выполнен')]
 y=472
 for a,b in labels:
  C.setFont('B',11);C.drawString(462,y,a);C.setFont('R',10);C.drawString(462,y-19,b);y-=51
 C.setFont('R',9);C.drawString(32,28,'Новый контрольный PDF; исходный исторический PDF сохранён и отдельно выдан в беседе.');C.showPage()
 C.setFont('B',22);C.drawString(32,555,'Сравнение с сохранёнными оригиналами')
 y=510
 for row in comparisons:
  C.setFont('B',11);C.drawString(32,y,row['path']);C.setFont('R',10);C.drawString(32,y-22,'Байты совпали: '+('ДА' if row['byte_exact_original'] else 'НЕТ, файл пересобран'))
  C.setFont('R',8);C.drawString(32,y-42,'SHA-256: '+row['sha256']);y-=87
 C.drawImage(str(R/'previews/test_coupon.png'),40,42,width=450,height=219,preserveAspectRatio=True,anchor='c')
 C.setFont('R',10);C.drawString(513,210,'Тестовый купон сохранён');C.drawString(513,191,'отдельными DST / EXP.');C.drawString(513,155,'Не уменьшать рисунок');C.drawString(513,136,'без повторной оцифровки.');C.save()
 out={'status':'EMBROIDERY_REBUILT_AND_VERIFIED','workflow_run_id':os.getenv('GITHUB_RUN_ID'),'sources_sha256':SOURCES,'outputs_compared_to_originals':comparisons,'validation':result,'physical_sewout':False,'full_original_snapshot_uploaded':False}
 (ROOT/'provenance/EMBROIDERY_RECOVERY.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 print('EMBROIDERY_RECOVERY_OK',json.dumps(comparisons))
if __name__=='__main__':main()
