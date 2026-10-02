#!/usr/bin/env python3
"""Small pre-sew coupon: .42mm tatami and .40mm pitch satin, not physical QA."""
import math,json
from pathlib import Path
import numpy as np
from shapely.geometry import Polygon,LineString
from shapely import affinity
from PIL import Image,ImageDraw
import machine_formats as mf
ROOT=Path(__file__).resolve().parents[1];commands=[];col=0;last=np.array([0.,0.])
def path(a):
 global last
 a=np.array(a,float); commands.append(('T',*last,col));commands.append(('J',*a[0],col))
 for p in a:commands.append(('S',*p,col))
 last=a[-1]
def grid(poly,angle,pitch):
 r=affinity.rotate(poly,-angle,origin=(0,0));xmin,ymin,xmax,ymax=r.bounds;result=[]
 th=math.radians(angle);R=np.array([[math.cos(th),math.sin(th)],[-math.sin(th),math.cos(th)]])
 for i,y in enumerate(np.arange(ymin+pitch/2,ymax,pitch)):
  line=r.intersection(LineString([(xmin-1,y),(xmax+1,y)]))
  if line.is_empty or line.geom_type!='LineString':continue
  p1,p2=line.coords[0],line.coords[-1];lo,hi=p1[0],p2[0]
  phase=(i%4)*.75;xx=np.arange(math.floor((lo-phase)/3)*3+phase,hi,3)
  xs=[lo]+[x for x in xx if lo+.3<x<hi-.3]+[hi]
  if i%2:xs=xs[::-1]
  arr=np.array([[x,y] for x in xs])@R
  # Coupon is convex: all connecting paths stay inside.
  if result:
   prev=result[-1];n=math.ceil(np.linalg.norm(arr[0]-prev)/3)
   result.extend(prev+(arr[0]-prev)*t/n for t in range(1,n+1))
  result.extend(arr)
 return result
P=Polygon([(5,5),(23,5),(23,28),(5,28)])
path(grid(P.buffer(-.65),135,1.8));path(grid(P,45,.42))
col=1;commands.append(('C',*last,col))
def satin(a,width):
 a=np.array(a);d=np.gradient(a,axis=0);n=np.stack([-d[:,1],d[:,0]],axis=1);n/=np.linalg.norm(n,axis=1)[:,None]
 ctr=a[::max(1,round(1.8/.2))];path(np.vstack([ctr,ctr[-2::-1]]))
 top=a+n*np.array([1 if i%2==0 else -1 for i in range(len(a))])[:,None]*(width/2+.12)
 path(top)
for x,w in [(32,1.6),(40,2.8)]:satin([(x,y) for y in np.arange(5,28.1,.2)],w)
# Open letter C-like curve from the actual lettering style; .4 peak-to-peak.
t=np.linspace(.7,5.58,125);satin(np.stack([59+8*np.cos(t),16.5+9*np.sin(t)],axis=1),1.65)
commands.append(('E',*last,col))
# Center this separate design at machine origin.
commands=[(c,x-36,y-17,col) for c,x,y,col in commands]
a=mf.write_dst(commands,ROOT/'machine/TEST_coupon_65x25.dst','R03_TEST');mf.write_exp(commands,ROOT/'machine/TEST_coupon_65x25.exp')
r=mf.read_dst(ROOT/'machine/TEST_coupon_65x25.dst')
assert [x for x in r if x[0]=='S']==[x for x in mf.read_exp(ROOT/'machine/TEST_coupon_65x25.exp') if x[0]=='S']
im=Image.new('RGB',(1080,525),'#f8f6ee');d=ImageDraw.Draw(im);prev=(0,0)
for c,x,y,col in r:
 p=((x/10+36)*15,(y/10+17)*15)
 if c=='S':d.line([prev,p],fill=['#7D8589','#244963'][col],width=4)
 if c in ('S','J'):prev=p
im.save(ROOT/'previews/test_coupon.png')
(ROOT/'machine/TEST_coupon_threads.txt').write_text('R03 TEST: first GRAY / second NAVY. Two colors, one color change. Coupon only; does not validate the complete logo.\n')
print('coupon needle_points',sum(c[0]=='S' for c in r))
