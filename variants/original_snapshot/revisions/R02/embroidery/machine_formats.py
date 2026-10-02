"""Small DST/EXP binary codec. Coordinates in signed 0.1 mm, image Y down.
Format bit assignments cross-checked against the open-source pyembroidery
DST/EXP readers/writers (see docs/SOURCES.md). No renamed raster files.
No proprietary PES writer claimed. Standard DST has no RGB thread palette:
always supply the accompanying threadlist. DST automatic trims are machine-dependent.
"""
from pathlib import Path
import math

def normalized(commands):
 out=[];x=y=0
 for cmd,xx,yy,col in commands:
  tx,ty=round(xx*10),round(yy*10)
  if cmd in ('S','J'):
   dx,dy=tx-x,ty-y;n=max(1,math.ceil(max(abs(dx),abs(dy))/100))
   if cmd=='S':n=max(n,math.ceil(math.hypot(dx,dy)/35))
   ox,oy=x,y
   for i in range(1,n+1):out.append((cmd,round(ox+dx*i/n),round(oy+dy*i/n),col))
   x,y=tx,ty
  else:out.append((cmd,x,y,col))
 return out

# Independent writer representation: each coordinate is a balanced ternary number.
X_BITS={1:(0,0,1),3:(1,0,1),9:(0,2,3),27:(1,2,3),81:(2,2,3)}
Y_BITS={1:(0,7,6),3:(1,7,6),9:(0,5,4),27:(1,5,4),81:(2,5,4)}
def encode_dst(dx,dy,jump=False):
 if abs(dx)>121 or abs(dy)>121:raise ValueError('DST delta out of range')
 b=[0,0,0x83 if jump else 0x03]
 for value,table in [(dx,X_BITS),(-dy,Y_BITS)]:
  for weight in [81,27,9,3,1]:
   bound=(weight-1)//2
   byte,pos,neg=table[weight]
   if value>bound:b[byte]|=1<<pos;value-=weight
   elif value<-bound:b[byte]|=1<<neg;value+=weight
  assert value==0
 return bytes(b)

def write_dst(commands,path,name='SPIM_HASKI_160'):
 cmds=normalized(commands);records=[];x=y=0
 for cmd,xx,yy,col in cmds:
  if cmd in ('S','J'):records.append(encode_dst(xx-x,yy-y,cmd=='J'));x,y=xx,yy
  elif cmd=='T':records.extend([encode_dst(2,2,True),encode_dst(-4,-4,True),encode_dst(2,2,True)])
  elif cmd=='C':records.append(b'\x00\x00\xc3')
  elif cmd=='E':records.append(b'\x00\x00\xf3')
 xs=[c[1] for c in cmds];ys=[c[2] for c in cmds]
 header=(f'LA:{name[:16]:<16}\rST:{len(records)-1:7d}\rCO:{sum(c[0]=="C" for c in cmds):3d}\r'
         f'+X:{max(0,max(xs)):5d}\r-X:{max(0,-min(xs)):5d}\r+Y:{max(0,-min(ys)):5d}\r-Y:{max(0,max(ys)):5d}\r'
         f'AX:{x:+6d}\rAY:{-y:+6d}\rMX:+    0\rMY:+    0\rPD:******\r').encode('ascii')+b'\x1a'
 if len(header)>512:raise ValueError('DST header too long')
 Path(path).write_bytes(header.ljust(512,b' ')+b''.join(records));return cmds

def write_exp(commands,path):
 cmds=normalized(commands);out=bytearray();x=y=0
 for cmd,xx,yy,col in cmds:
  if cmd in ('S','J'):
   dx,dy=xx-x,-(yy-y)
   assert -127<=dx<=127 and -127<=dy<=127
   if cmd=='J':out.extend(b'\x80\x04')
   out.extend(bytes((dx&255,dy&255)));x,y=xx,yy
  elif cmd=='T':out.extend(b'\x80\x80\x07\x00')
  elif cmd=='C':out.extend(b'\x80\x01\x00\x00')
 Path(path).write_bytes(out);return cmds

# Reader uses direct signed bit sums, not the writer's balanced-ternary algorithm.
def read_dst(path):
 data=Path(path).read_bytes();assert data[:3]==b'LA:' and len(data)>=515
 x=y=0;col=0;out=[];ended=False
 for i in range(512,len(data)-2,3):
  b0,b1,b2=data[i:i+3]
  bit=lambda b,n:(b>>n)&1
  dx=(bit(b0,0)-bit(b0,1))+3*(bit(b1,0)-bit(b1,1))+9*(bit(b0,2)-bit(b0,3))+27*(bit(b1,2)-bit(b1,3))+81*(bit(b2,2)-bit(b2,3))
  dy=-((bit(b0,7)-bit(b0,6))+3*(bit(b1,7)-bit(b1,6))+9*(bit(b0,5)-bit(b0,4))+27*(bit(b1,5)-bit(b1,4))+81*(bit(b2,5)-bit(b2,4)))
  if b2&0xf3==0xf3:out.append(('E',x,y,col));ended=True;break
  x+=dx;y+=dy
  if b2&0xc3==0xc3:col+=1;out.append(('C',x,y,col))
  elif b2&0x83==0x83:out.append(('J',x,y,col))
  else:
   if b2&3!=3:raise ValueError('Invalid DST record')
   out.append(('S',x,y,col))
 if not ended:raise ValueError('Missing DST END')
 return out

def read_exp(path):
 data=Path(path).read_bytes();out=[];x=y=0;col=0;i=0
 signed=lambda a:a if a<128 else a-256
 while i<len(data):
  a,b=data[i:i+2];i+=2
  if a==128:
   c,d=data[i:i+2];i+=2
   if b==0x80:out.append(('T',x,y,col));continue
   if b==1:col+=1;out.append(('C',x,y,col));continue
   if b!=4:raise ValueError('Unsupported EXP command')
   x+=signed(c);y-=signed(d);out.append(('J',x,y,col))
  else:x+=signed(a);y-=signed(b);out.append(('S',x,y,col))
 out.append(('E',x,y,col));return out
