#!/usr/bin/env python3
"""E01: explicit exit sequence derived from preserved R08 tessellated CAD.
R09 changes cutting, not external CAD. Original inputs are never modified.
Cloth is prescribed kinematics, not a cloth/foam/contact simulation.
The two end releases on the dropping side panel are NEW design requirements.
"""
from pathlib import Path
import os, json, math, hashlib
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.spatial.transform import Rotation
import vtk
from vtk.util.numpy_support import numpy_to_vtk, vtk_to_numpy
HERE=Path(__file__).resolve().parents[1]
BASE=Path(os.getenv('LEZHANDR_INPUT', str(HERE/'input/revisions/R08')))
ROWS=json.loads((BASE/'cad/model_R08.json').read_text())
BYID={r['id']:r for r in ROWS}
PAL=json.loads((BASE/'cad/palette.json').read_text())
H0=np.array([1050.,0,230.]);U0=np.array([-math.cos(math.radians(55)),0,math.sin(math.radians(55))]);N0=np.array([U0[2],0,-U0[0]])
S0=H0+600*U0;E0=S0+[165,0,-330*math.sin(math.radians(60))]
WR0=E0+[math.sqrt(285**2-90**2)*math.cos(math.radians(16)),0,math.sqrt(285**2-90**2)*math.sin(math.radians(16))]
K0=H0+[490*math.cos(math.radians(5)),0,490*math.sin(math.radians(5))]
A0=K0+[490*math.cos(math.radians(8)),0,-490*math.sin(math.radians(8))]
W=PchipInterpolator([55,150,300,450,650,820,950,1050,1300,1600,1900,2140,2290,2345], [65,250,400,490,532,410,545,545,527,496,444,350,205,65])
CROWN=PchipInterpolator([620,700,810,950,1080,1330],[904,897,820,712,622,640])
EDGE=PchipInterpolator([620,700,810,820,950,1080,1330],[785,800,805,805,560,490,420])
SEQUENCES=[
 {'id':'00','title':'Работа: человек внутри кокона','flap':0,'park':0,'zip':0,'shoulder':0,'quilt':0,'side':0,'pose':'rest'},
 {'id':'01','title':'Освободить кисти','flap':1,'park':0,'zip':0,'shoulder':0,'quilt':0,'side':0,'pose':'rest'},
 {'id':'02','title':'Выключить нагрев и припарковать столик','flap':1,'park':1,'zip':0,'shoulder':0,'quilt':0,'side':0,'pose':'hands_in'},
 {'id':'03','title':'Расстегнуть правый пользовательский вход','flap':1,'park':1,'zip':1,'shoulder':0,'quilt':0,'side':0,'pose':'hands_in'},
 {'id':'04','title':'Снять укрытие с плеч и сложить влево','flap':1,'park':1,'zip':1,'shoulder':1,'quilt':0,'side':0,'pose':'hands_in'},
 {'id':'05','title':'Собрать покрывало к ножному торцу','flap':1,'park':1,'zip':1,'shoulder':1,'quilt':1,'side':0,'pose':'hands_in'},
 {'id':'06','title':'Опустить правый борт наружу','flap':1,'park':1,'zip':1,'shoulder':1,'quilt':1,'side':1,'pose':'hands_in'},
 {'id':'07','title':'Повернуть таз и вывести правую ногу','flap':1,'park':1,'zip':1,'shoulder':1,'quilt':1,'side':1,'pose':'turn'},
 {'id':'08','title':'Вывести вторую ногу; сесть снаружи','flap':1,'park':1,'zip':1,'shoulder':1,'quilt':1,'side':1,'pose':'edge'},
 {'id':'09','title':'Перейти в полувыпад с опорой на пол','flap':1,'park':1,'zip':1,'shoulder':1,'quilt':1,'side':1,'pose':'kneel'},
 {'id':'10','title':'Встать вне кокона','flap':1,'park':1,'zip':1,'shoulder':1,'quilt':1,'side':1,'pose':'stand'},
]
def poly(v,f):
 p=vtk.vtkPoints();p.SetData(numpy_to_vtk(np.asarray(v,dtype=np.float64),deep=True));d=vtk.vtkPolyData();d.SetPoints(p)
 ca=vtk.vtkCellArray();arr=np.asarray(f,dtype=np.int64)
 if len(arr):ca.SetCells(len(arr),numpy_to_vtk(np.c_[np.full(len(arr),3),arr].ravel(),deep=True,array_type=vtk.VTK_ID_TYPE))
 d.SetPolys(ca);return d

def poly_arrays(d):
 tri=vtk.vtkTriangleFilter();tri.SetInputData(d);tri.Update();out=tri.GetOutput()
 if not out.GetNumberOfPoints():return np.empty((0,3)),np.empty((0,3),int)
 v=vtk_to_numpy(out.GetPoints().GetData()).copy();f=vtk_to_numpy(out.GetPolys().GetData()).reshape(-1,4)[:,1:].copy();return v,f

def clip_part(d,origin,normal):
 p=vtk.vtkPlane();p.SetOrigin(*origin);p.SetNormal(*normal)
 c=vtk.vtkClipPolyData();c.SetInputData(d);c.SetClipFunction(p);c.GenerateClippedOutputOn();c.Update()
 a=vtk.vtkPolyData();a.DeepCopy(c.GetOutput());b=vtk.vtkPolyData();b.DeepCopy(c.GetClippedOutput());return a,b

def split_side():
 r=BYID['O08_SMOOTH_LOWER'];d=poly(r['vertices_mm'],r['faces']);outside=[]
 for p,n in [((845,0,0),(1,0,0)),((2140,0,0),(-1,0,0)),((0,0,0),(0,1,0)),((0,0,140),(0,0,1))]:
  d,b=clip_part(d,p,n);outside.append(b)
 app=vtk.vtkAppendPolyData()
 for o in outside:app.AddInputData(o)
 app.Update();sv,sf=poly_arrays(app.GetOutput());mv,mf=poly_arrays(d)
 def row(name,v,f):return {**r,'id':name,'vertices_mm':v.tolist(),'faces':f.tolist()}
 return row('O08_STATIONARY_SHELL',sv,sf),row('E01_RIGHT_DROPPING_PANEL',mv,mf)
SHELL,PANEL=split_side()

def rotx_vertices(v,angle,y,z):
 a=math.radians(angle);v=np.asarray(v).copy();dy=v[:,1]-y;dz=v[:,2]-z
 v[:,1]=y+dy*math.cos(a)-dz*math.sin(a);v[:,2]=z+dy*math.sin(a)+dz*math.cos(a);return v

def move_shoulder(v,t):
 v=np.array(v).copy();x=v[:,0];z=CROWN(np.clip(x,620,1330))
 # Fold free right wing on top of the left, then fold the two layers outwards.
 m=v[:,1]>0
 v[m]=rotx_vertices(v[m],170*min(t*2,1),0,z[m])
 a=max(0,(t-.35)/.65)*140
 return rotx_vertices(v,a,-510,EDGE(np.clip(x,620,1330)))

def move_quilt(v,t):
 v=np.asarray(v).copy();s=(v[:,0]-965)/1355
 # Prescribed 3-fold concertina: all material stays visible on foot end.
 px=[1820,2260,1860,2320];pz=[490,490,560,340]
 lens=np.sqrt(np.diff(px)**2+np.diff(pz)**2);cs=np.r_[0,np.cumsum(lens)];ss=s*cs[-1]
 xx=np.interp(ss,cs,px);zz=np.interp(ss,cs,pz)
 oldz=PchipInterpolator([965,1100,1290,1450,1650,1870,2110,2320],[407,424,461,478,468,436,414,340])(np.clip(v[:,0],965,2320))
 final=v.copy();final[:,0]=xx;final[:,2]=zz+(v[:,2]-oldz)*.85
 return v*(1-t)+final*t

def move_side(v,t):
 v=np.asarray(v).copy();x=v[:,0];hy=W(np.clip(x,845,2140))-90
 return rotx_vertices(v,-90*t,hy,140)

def align_vectors(a,b):
 a=np.asarray(a,float);a/=np.linalg.norm(a);b=np.asarray(b,float);b/=np.linalg.norm(b);cross=np.cross(a,b);l=np.linalg.norm(cross)
 if l<1e-9:return np.eye(3) if np.dot(a,b)>0 else Rotation.from_rotvec(np.array([0,1,0])*math.pi).as_matrix()
 return Rotation.from_rotvec(cross/l*math.atan2(l,np.dot(a,b))).as_matrix()

def rigid(v,old0,old1,new0,new1):
 r=align_vectors(np.array(old1)-old0,np.array(new1)-new0);return (np.asarray(v)-old0)@r.T+new0

def ik(a,c,L1,L2,pole):
 a=np.array(a,float);c=np.array(c,float);d=c-a;length=np.linalg.norm(d)
 if length>=L1+L2-.01:
  d=d/length*(L1+L2-.01);c=a+d;length=np.linalg.norm(d)
 e=d/length;pole=np.array(pole,float);p=pole-e*np.dot(pole,e)
 if np.linalg.norm(p)<1e-9:p=np.cross(e,[1,0,0])
 p/=np.linalg.norm(p);along=(L1*L1-L2*L2+length*length)/(2*length);height=math.sqrt(max(0,L1*L1-along*along))
 return a+e*along+p*height,c

def skeleton(mode):
 configs={
  'rest':(H0,0,55),'hands_in':(H0,0,55),
  'turn':([1030,270,235],32,60),
  'edge':([960,625,275],83,84),
  'kneel':([1010,1450,550],90,110),
  'stand':([1010,1370,995],90,90),
 }
 H,yaw,back=configs[mode];H=np.array(H,float);a=math.radians(yaw);F=np.array([math.cos(a),math.sin(a),0]);L=np.array([-math.sin(a),math.cos(a),0]);Z=np.array([0.,0,1]);U=-math.cos(math.radians(back))*F+math.sin(math.radians(back))*Z;N=math.sin(math.radians(back))*F+math.cos(math.radians(back))*Z;S=H+600*U
 q={'hip':H,'shoulder':S,'yaw':yaw,'back':back,'F':F,'L':L,'U':U,'N':N}
 for sy in [-1,1]:
  hip=H+L*115*sy
  if mode in ['rest','hands_in']:
   knee=K0+[0,sy*115,0];ankle=A0+[0,sy*115,0]
  elif mode=='turn':
   ankle=hip+F*(865 if sy==1 else 930);ankle[2]=60 if sy==1 else 145
   knee,ankle=ik(hip,ankle,490,490,Z+F*.1)
  elif mode=='edge':
   ankle=hip+F*825;ankle[2]=60
   knee,ankle=ik(hip,ankle,490,490,Z+F*.3)
  elif mode=='kneel':
   if sy==-1:
    # Back knee on the floor; ankle behind it, clear of the rigid base.
    dz=H[2]-83;dx=math.sqrt(max(0,490**2-dz**2))
    knee=hip-F*dx;knee[2]=83
    ankle=knee-F*math.sqrt(490**2-23**2);ankle[2]=60
   else:
    ankle=hip+F*395;ankle[2]=60
    knee,ankle=ik(hip,ankle,490,490,F+Z*.5)
  else:
   ankle=hip+F*95;ankle[2]=60;knee,ankle=ik(hip,ankle,490,490,F)
  sho=S+L*225*sy
  if mode=='rest':
   wr=WR0+[-30,sy*155,55];el,wr=ik(sho,wr,float(np.linalg.norm((E0+[0,sy*245,0])-(S0+[0,sy*225,0]))),285,-F-Z);handdir=np.array([1.,0,-.12]);handdir/=np.linalg.norm(handdir)
  else:
   if mode=='hands_in':wr=H-F*100+L*sy*145+Z*230
   elif mode=='turn':wr=H+F*175+L*sy*200+Z*90
   elif mode=='edge':wr=knee-F*120+Z*70
   elif mode=='kneel':wr=q.get('knee1',knee)+Z*75 if sy==1 else H-L*280+F*180-Z*80
   else:wr=sho-Z*560+F*40
   el,wr=ik(sho,wr,float(np.linalg.norm((E0+[0,sy*245,0])-(S0+[0,sy*225,0]))),285, -F+L*sy*.2-Z*.1)
   handdir=(F*.6+Z*.8) if mode=='hands_in' else (wr-el)/np.linalg.norm(wr-el)
  q.update({f'hip{sy}':hip,f'knee{sy}':knee,f'ankle{sy}':ankle,f'sho{sy}':sho,f'elbow{sy}':el,f'wrist{sy}':wr,f'handdir{sy}':handdir})
 return q

def pose_rows(mode):
 q=skeleton(mode);H=q['hip'];L=q['L'];F=q['F'];S=q['shoulder'];U=q['U'];N=q['N'];Ry=Rotation.from_euler('z',q['yaw'],degrees=True).as_matrix();Rt=np.stack([N,L,U],1)@np.stack([N0,[0,1,0],U0],1).T
 ans=[]
 for r in ROWS:
  if r['group']!='human':continue
  n=r['id'];v=np.array(r['vertices_mm']);old=v.copy()
  if n=='M_TORSO':v=(v-H0)@Rt.T+H
  elif n=='M_PELVIS':v=(v-H0)@Ry.T+H
  elif n in ['M_HEAD','M_NECK']:v=(v-S0)@Ry.T+S
  else:
   sy=-1 if n.endswith('-1') else 1
   if n.startswith('M_ARM'):p0=S0+[0,sy*225,0];p1=E0+[0,sy*245,0];a=q[f'sho{sy}'];b=q[f'elbow{sy}']
   elif n.startswith('M_FOREARM'):p0=E0+[0,sy*245,0];p1=WR0+[0,sy*155,0];a=q[f'elbow{sy}'];b=q[f'wrist{sy}']
   elif n.startswith('M_HAND'):p0=WR0+[0,sy*155,0];p1=p0+90*np.array([math.cos(math.radians(16)),0,math.sin(math.radians(16))]);a=q[f'wrist{sy}'];b=a+90*q[f'handdir{sy}']
   elif n.startswith('M_THIGH'):p0=H0+[0,sy*115,0];p1=K0+[0,sy*115,0];a=q[f'hip{sy}'];b=q[f'knee{sy}']
   elif n.startswith('M_SHIN'):p0=K0+[0,sy*115,0];p1=A0+[0,sy*115,0];a=q[f'knee{sy}'];b=q[f'ankle{sy}']
   else:
    p0=A0+[0,sy*115,0];p1=p0+[100,0,0];a=q[f'ankle{sy}'];b=a+100*F
    if mode=='kneel' and sy==-1:b=a-100*F
   v=rigid(v,p0,p1,a,b)
  ans.append({**r,'vertices_mm':v.tolist()})
 return ans,q

def frame_rows(s):
 ans=[]
 for r in ROWS:
  g=r['group'];n=r['id'];v=np.array(r['vertices_mm']).reshape(-1,3)
  if g=='human' or n=='O08_SMOOTH_LOWER':continue
  if g=='flap':
   if s['flap']==0 and 'closed' not in r['states']:continue
   if s['flap']>0 and 'open' not in r['states']:continue
  elif 'open' not in r['states']:continue
  if g in ['zipper','harness']:continue
  if g in ['desk','laptop']:v=v+[80*s['park'],0,0]
  if g=='shoulder' or (g=='flap' and s['shoulder']):v=move_shoulder(v,s['shoulder'])
  if g=='leg_quilt':v=move_quilt(v,s['quilt'])
  if g=='release_tabs' and s['side']>0:continue
  ans.append({**r,'vertices_mm':v.tolist()})
 ans.append(SHELL)
 v=move_side(PANEL['vertices_mm'],s['side']);ans.append({**PANEL,'vertices_mm':v.tolist()})
 human,q=pose_rows(s['pose']);ans+=human
 return ans,q

def export_state_vtm(rows,path):
 multi=vtk.vtkMultiBlockDataSet();multi.SetNumberOfBlocks(len(rows));count=0
 for i,r in enumerate(rows):
  if not r['faces']:continue
  d=poly(r['vertices_mm'],r['faces']);multi.SetBlock(count,d);multi.GetMetaData(count).Set(vtk.vtkCompositeDataSet.NAME(),r['id']);count+=1
 multi.SetNumberOfBlocks(count);writer=vtk.vtkXMLMultiBlockDataWriter();writer.SetFileName(str(path));writer.SetInputData(multi);writer.SetDataModeToBinary();writer.Write()

if __name__=='__main__':
 from collections import Counter
 print('parts',len(ROWS),'split',len(SHELL['vertices_mm']),len(PANEL['vertices_mm']))
 for s in SEQUENCES:
  rr,q=frame_rows(s);mins={}
  for group in ['human','shoulder','leg_quilt','lower_shell']:
   vv=np.concatenate([np.array(r['vertices_mm']) for r in rr if r['group']==group]);mins[group]=[vv.min(0).round(1).tolist(),vv.max(0).round(1).tolist()]
  print(s['id'],s['pose'],mins)
 (HERE/'checks/input_provenance.json').write_text(json.dumps({'source':'R08 as preserved by R09 at a2445cda6d919bb7a8f7e56662d9ae37c164d5fe','sha256_model':hashlib.sha256((BASE/'cad/model_R08.json').read_bytes()).hexdigest(),'unmodified_input':True,'new_definition':'E01 adds two end releases to articulate the sidewall; quilt folds and human poses are prescribed, not validated dynamics'},indent=2))
