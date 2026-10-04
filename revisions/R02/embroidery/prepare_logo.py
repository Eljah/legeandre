from pathlib import Path
import json
import cv2,numpy as np
from scipy import ndimage as ndi
from PIL import Image
ROOT=Path(__file__).resolve().parent
# By default use the approved crop shipped with this project.  --sheet accepts
# the original 1448 x 1086 source sheet and applies the documented crop.
import argparse
parser=argparse.ArgumentParser()
parser.add_argument('--sheet', type=Path, help='Original approved sheet, 1448 x 1086 PNG')
args=parser.parse_args()
box=(80,130,678,743)
src=args.sheet or ROOT/'source/approved_logo_crop.png'
im=Image.open(src).convert('RGB')
if args.sheet: im=im.crop(box)
if im.size!=(598,613): raise ValueError('Approved crop must be 598 x 613 pixels')
a=np.array(im);h,w=a.shape[:2]
# Restrict to emblem bounds; discard software rulers/hoop/grid from the source sheet.
# This polygon is a generous segmentation ROI, not a new drawing of the emblem.
roi=np.zeros((h,w),np.uint8)
poly=np.array([(9,105),(41,19),(116,0),(204,10),(230,69),(284,86),(301,27),(409,5),(474,36),(525,76),(513,187),(542,218),(546,307),(544,450),(591,475),(591,561),(490,598),(282,610),(101,582),(0,510),(9,455),(1,339),(21,238)],np.int32)
roi[:]=1
# Suppress thin near-white CAD grid; retain dark outlines and every colored thread.
a=cv2.pyrMeanShiftFiltering(a,sp=9,sr=35,maxLevel=2);a=cv2.medianBlur(a,5)
hsv=cv2.cvtColor(a,cv2.COLOR_RGB2HSV);gray=cv2.cvtColor(a,cv2.COLOR_RGB2GRAY)
ink=((gray<174)|((hsv[:,:,1]>35)&(gray<231)))&roi.astype(bool)
ink=cv2.morphologyEx(ink.astype(np.uint8),cv2.MORPH_CLOSE,np.ones((4,4),np.uint8))
num,lab,stats,_=cv2.connectedComponentsWithStats(ink,8)
mask=np.zeros((h,w),np.uint8)
for i in range(1,num):
 if stats[i,cv2.CC_STAT_AREA]>=35:
  q=ndi.binary_fill_holes(lab==i);mask[q]=1
mask=ndi.binary_fill_holes(mask).astype(np.uint8)
# The emblem body is connected, whereas the wordmark and paws remain separate islands.
# Eight thread classes, sampled/assigned from the approved raster, not made-up catalog IDs.
palette=np.array([[241,236,222],[174,174,163],[94,95,92],[33,36,37],[27,71,102],[213,165,125],[146,102,64],[237,192,161]],np.uint8)
# Lab color distance with color-preserving smoothing; black outlines remain dark.
labim=cv2.cvtColor(a,cv2.COLOR_RGB2LAB).astype(float)
labpal=cv2.cvtColor(palette.reshape(1,-1,3),cv2.COLOR_RGB2LAB).reshape(-1,3).astype(float)
# Denoise original simulated stitch texture before tracing color areas.
labim=cv2.GaussianBlur(labim,(5,5),1.0)
d=((labim[:,:,None,:]-labpal[None,None,:,:])**2).sum(axis=3);labels=d.argmin(axis=2).astype(np.uint8)
labels=cv2.medianBlur(labels,5)
# Remove small isolated color flecks, which would otherwise require hundreds of trims.
for k in range(len(palette)):
 n,ll,st,_=cv2.connectedComponentsWithStats(((labels==k)&(mask>0)).astype(np.uint8),8)
 for i in range(1,n):
  if st[i,cv2.CC_STAT_AREA]<70:
   comp=ll==i;ring=cv2.dilate(comp.astype(np.uint8),np.ones((5,5),np.uint8)).astype(bool)&~comp&(mask>0)
   if ring.any():labels[comp]=np.bincount(labels[ring],minlength=len(palette)).argmax()
mask[535:] &= (~((gray[535:]>180)&(hsv[535:,:,1]<70))).astype(np.uint8)
labels[535:][mask[535:]>0]=4
result=palette[labels];result[mask==0]=255
Image.fromarray(result).save(ROOT/'logo_quantized.png');im.save(ROOT/'source/approved_logo_crop.png')
np.savez_compressed(ROOT/'source/logo_segments.npz',labels=labels,mask=mask,palette=palette)
(ROOT/'source/segmentation.json').write_text(json.dumps({'source_file':src.name,'crop_xyxy':box,'design_name':'Спим с хаски','method':'crop approved image -> background removal -> 8-color segmentation -> trace -> stitch generation','notes':'Not a new generated logo. Original text and face traced from approved raster; texture simplified.'},ensure_ascii=False,indent=2))
print('crop',im.size,'maskpixels',mask.sum())
