"""Minimal auditable DST/EXP codecs in 0.1 mm machine units.
No machine identity is assumed. Sew-out and machine/hoop checks remain mandatory.
"""
import math
from pathlib import Path

def normalize(commands,max_step=100):
 out=[];x=y=0
 for cmd,xx,yy,col in commands:
  X=int(round(xx*10));Y=int(round(yy*10))
  if cmd in ('S','J'):
   dx=X-x;dy=Y-y;n=max(1,math.ceil(max(abs(dx),abs(dy))/max_step))
   sx,sy=x,y
   for i in range(1,n+1):
    a=sx+round(dx*i/n);b=sy+round(dy*i/n);out.append((cmd,a,b,col))
   x,y=X,Y
  else:out.append((cmd,x,y,col))
 return out

def axis_bits(v,axis,bb):
 # balanced ternary coefficients for 1,3,9,27,81.
 if not -121<=v<=121:raise ValueError(v)
 coeff=[];q=v
 for w in [1,3,9,27,81]:
  r=q%3
  if r==2:r=-1
  coeff.append(r);q=(q-r)//3
 if q:raise ValueError(v)
 for w,s in zip([1,3,9,27,81],coeff):
  if s==0:continue
  if axis=='x':table={1:(0,0,1),3:(1,0,1),9:(0,2,3),27:(1,2,3),81:(2,2,3)}
  else:table={1:(0,7,6),3:(1,7,6),9:(0,5,4),27:(1,5,4),81:(2,5,4)}
  byte,plus,minus=table[w];bb[byte]|=1<<(plus if s>0 else minus)

def record(dx,dy,flag=0x03):
 bb=[0,0,flag];axis_bits(dx,'x',bb);axis_bits(dy,'y',bb);return bytes(bb)

def write_dst(commands,path,name='SPIM_HASKI'):
 a=normalize(commands);st=sum(c[0]=='S' for c in a);colors=sum(c[0]=='C' for c in a)
 coords=[(c[1],c[2]) for c in a];xp=max(x for x,y in coords);xm=min(x for x,y in coords);yp=max(y for x,y in coords);ym=min(y for x,y in coords)
 lines=[f'LA:{name[:16]:<16}',f'ST:{st:7d}',f'CO:{colors:3d}',f'+X:{max(0,xp):5d}',f'-X:{max(0,-xm):5d}',f'+Y:{max(0,yp):5d}',f'-Y:{max(0,-ym):5d}','AX:+    0','AY:+    0','MX:+    0','MY:+    0','PD:******']
 head=('\r'.join(lines)+'\r').encode('ascii')+b'\x1a';head=head.ljust(512,b' ')
 out=bytearray(head);x=y=0
 for cmd,X,Y,col in a:
  if cmd=='C':out+=bytes([0,0,0xc3])
  elif cmd=='T':
   # Conventional three short jumps; trims are interpreted by machine settings.
   for dx in [2,-4,2]:out+=record(dx,0,0x83)
  elif cmd=='E':out+=bytes([0,0,0xf3])
  else:out+=record(X-x,-(Y-y),0x03 if cmd=='S' else 0x83);x,y=X,Y
 if not a or a[-1][0]!='E':out+=bytes([0,0,0xf3])
 Path(path).write_bytes(out);return a

def read_dst(path):
 b=Path(path).read_bytes();x=y=0;col=0;out=[]
 for i in range(512,len(b)-2,3):
  p,q,r=b[i:i+3]
  if r==0xf3:out.append(('E',x,y,col));break
  if r==0xc3:col+=1;out.append(('C',x,y,col));continue
  dx=(bool(p&1)-bool(p&2))*1+(bool(q&1)-bool(q&2))*3+(bool(p&4)-bool(p&8))*9+(bool(q&4)-bool(q&8))*27+(bool(r&4)-bool(r&8))*81
  dy=(bool(p&128)-bool(p&64))*1+(bool(q&128)-bool(q&64))*3+(bool(p&32)-bool(p&16))*9+(bool(q&32)-bool(q&16))*27+(bool(r&32)-bool(r&16))*81
  x+=dx;y-=dy;out.append(('J' if r&128 else 'S',x,y,col))
 return out

def write_exp(commands,path):
 a=normalize(commands);out=bytearray();x=y=0
 for cmd,X,Y,col in a:
  if cmd=='C':out+=bytes([128,1,0,0])
  elif cmd=='T':out+=bytes([128,128,7,0])
  elif cmd=='E':pass
  else:
   if cmd=='J':out+=bytes([128,4])
   out+=bytes([(X-x)&255,(-(Y-y))&255]);x,y=X,Y
 Path(path).write_bytes(out);return a

def read_exp(path):
 b=Path(path).read_bytes();i=0;x=y=col=0;out=[]
 signed=lambda z:z if z<128 else z-256
 while i<len(b):
  if b[i]==128:
   code=b[i+1];u,v=b[i+2:i+4];i+=4
   if code==1:col+=1;out.append(('C',x,y,col))
   elif code==128:out.append(('T',x,y,col))
   elif code==4:x+=signed(u);y-=signed(v);out.append(('J',x,y,col))
   else:raise ValueError('EXP command')
  else:
   u,v=b[i:i+2];i+=2;x+=signed(u);y-=signed(v);out.append(('S',x,y,col))
 return out
