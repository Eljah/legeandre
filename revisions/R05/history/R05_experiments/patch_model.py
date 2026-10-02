from pathlib import Path
p=Path(__file__).with_name('build_r05.py');s=p.read_text()
s=s.replace("tube('F_BACK_PROP_'+str(sy),(a[0],a[1],bz),a)","tube('F_BACK_PROP_'+str(sy),(a[0],a[1],bz),a)\n    tube('F_BACK_BASE_LINK_'+str(sy),(a[0],a[1],bz),(bx0,sy*by,bz),35,20,2)\n    tube('F_BACK_LOWER_LINK_'+str(sy),b,(1110,sy*315,bz),35,20,2)")
s=s.replace("r=42\n    sh=cylinder(a,bb,r)","r=56\n    sh=cylinder(a,bb,r)\n    if '_UPPER' in b['id']:\n        lim=tz(a[0])-12\n        sh=sh.intersect(cq.Workplane('XY').box(5000,5000,2000).translate((1000,0,lim-1000)).val())")
s=s.replace('Nominal removable 30 mm class tube padding; compression not solved.','Nominal 30 mm minimum corner padding (trimmed below tray contact); compression not solved.')
a=s.index('# Shoulder yoke is NOT sealed around neck.')
b=s.index('# Forward flap continues',a)
s=s[:a]+'''# Three-part shoulder roof with a real U-shaped neck opening, 310 x 145 mm.
# No material covers the face/throat. Wings start behind the shoulder joint.
c0=np.array([[650,0,855],[720,0,850],[795,0,785],[870,0,710],[955,0,626],[1035,0,577],[1100,0,545]],float)
cx=np.r_[np.linspace(650,795,30,endpoint=False),np.linspace(795,1100,61)];cz=PchipInterpolator(c0[:,0],c0[:,2])(cx);c=np.c_[cx,np.zeros(len(cx)),cz]
qc=[]
qc.append(develop_panel('Q01_CENTRE',c[cx>=795],[0,1,0],-155,155,'cape',('closed','rolled'),'Central chest cover. Front edge of open neck cutout, no neck seal.'))
for sy in [-1,1]:
    lo,hi=(-310,-155) if sy<0 else (155,310)
    qc.append(develop_panel('Q01_WING_'+('L' if sy<0 else 'R'),c,[0,1,0],lo,hi,'cape',('closed','rolled'),'Shoulder wing continuing from behind shoulder to wrist.'))
    cside=c+np.array([0,sy*310,0]);develop_panel('Q02_SIDE_'+('L' if sy<0 else 'R'),cside,[0,sy*110,-280],0,math.hypot(110,280),'cape',('closed','rolled'),'Arm-side wrap, right edge detachable from inside.')
qtop=qc[0]
''' +s[b:]
s=s.replace('[[1450,0,365],[1580,0,362],[1900,0,267],[2200,0,212]]','[[1450,0,380],[1580,0,380],[1900,0,290],[2240,0,270]]').replace('xf=np.linspace(1450,2200,65)','xf=np.linspace(1450,2240,65)')
# Make variable-width boundaries on the same developable generalized-cylinder surface.
s=s.replace('vv=np.linspace(vmin,vmax,11);g=c[:,None,:]+vv[None,:,None]*d',"v0=np.broadcast_to(np.asarray(vmin,float),(len(c),));v1=np.broadcast_to(np.asarray(vmax,float),(len(c),));vv=v0[:,None]+np.linspace(0,1,11)[None,:]*(v1-v0)[:,None];g=c[:,None,:]+vv[:,:,None]*d")
s=s.replace('np.c_[uu,eta+vmin],np.c_[uu[::-1],eta[::-1]+vmax]','np.c_[uu,eta+v0],np.c_[uu[::-1],(eta+v1)[::-1]]')
s=s.replace("uv=np.stack(np.meshgrid(uu,vv,indexing='ij'),axis=-1);uv[:,:,1]+=eta[:,None]","uv=np.stack([np.broadcast_to(uu[:,None],vv.shape),eta[:,None]+vv],axis=-1)")
s=s.replace('len(vv)-dj','vv.shape[1]-dj').replace("'extrusion_width_mm':vmax-vmin","'extrusion_width_mm':float(max(v1-v0))")
s=s.replace("[0,1,0],-340,340,'cape',('closed','rolled')","[0,1,0],-np.linspace(320,150,len(xf)),np.linspace(320,150,len(xf)),'cape',('closed','rolled')")
s=s.replace("[qtop,qflap]+sidegs","qc+[qflap]+sidegs").replace("[qtop,rg]+sidegs","qc+[rg]+sidegs")
# Snapshot data is dumped before optional CAD distance screening. Normal entry route is only screened, not simulated dynamically.
insert='''
# Clearance screen using actual OpenCASCADE solid distance at discrete lateral poses.
# Tucked arms are used; blanket and right bolster must be opened separately.
rigid_ids=[o['id'] for o in ITEMS if o['group'] in ['frame','joints','desk','laptop'] and not o['id'].startswith('RUBBER')]
rigid=cq.Compound.makeCompound([SHAPES[i] for i in rigid_ids])
body_ids=[o['id'] for o in ITEMS if o['id'].startswith('EXIT_')]
body=cq.Compound.makeCompound([SHAPES[i] for i in body_ids])
clear=[]
for shift in np.linspace(0,800,21):
    moved=body.translate((0,float(shift)-800,0))
    dist=moved.distance(rigid)
    clear.append({'lateral_shift_mm':float(shift),'surface_distance_mm':float(dist)})
dump(ROOT/'calculations/exit_clearance.json',{'poses':clear,'minimum_distance_mm':min(x['surface_distance_mm'] for x in clear),'method':'BRepExtrema between true mannequin solids and true rigid solids; 21 static poses','limitations':'Straight lateral swept-clearance screen, NOT a biomechanically solved getting-up trajectory; zero distance can mean touch or overlap. Does not validate unsupported body, folded bolster, or every possible movement. Padding clearances are separate.'})
'''
s=s.replace("print('ERGO',ergo,flush=True)",insert+"\nprint('ERGO',ergo,flush=True)")
p.write_text(s)
