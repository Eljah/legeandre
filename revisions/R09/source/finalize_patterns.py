#!/usr/bin/env python3
"""R09 digital assembly-pattern set based on pinned R08 in Git, not chat images.
Runs locally and in Actions. Preserves every R08 byte. Does not approve manufacture.
"""
from pathlib import Path
from collections import defaultdict,Counter
import json,math,hashlib,csv,sys
import numpy as np
from scipy.spatial import ConvexHull
from shapely.geometry import Polygon,LineString
from pattern_geometry import flatten,recover_grid,perimeter_indices,segment_key,boundary

R=Path(__file__).resolve().parents[1];BASE=R.parent/'R08'
for d in ['patterns/dxf','patterns/svg','patterns/markers','tests','cad','docs','renders']:(R/d).mkdir(parents=True,exist_ok=True)

def js(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2,default=lambda a:a.item() if isinstance(a,np.generic) else a.tolist())+'\n',encoding='utf-8')
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
inputs=['patterns/panel_grids.json','patterns/patterns_registry.json','cad/model_R08.json','harness/zippers.json','harness/routes.json']
source_hashes={p:digest(BASE/p) for p in inputs}
lock=json.loads((R/'inputs.lock.json').read_text()) if (R/'inputs.lock.json').exists() else None
if lock is not None and source_hashes!=lock['input_sha256']:raise RuntimeError('R08 inputs differ from the pinned audit snapshot')
seeds={p['id']:p for p in json.loads((BASE/inputs[0]).read_text())}
old=json.loads((BASE/inputs[1]).read_text());bodies={x['id']:x for x in json.loads((BASE/inputs[2]).read_text())}
PIECES=[];ENVELOPES=[];OPERATIONS=[]

def put(id,group,material,xyz,uv,stats=None,grid=None,source='',edge_modes=None,allowance=12,qty=1):
    xyz=np.asarray(xyz);uv=np.asarray(uv);p=Polygon(uv)
    if not p.is_valid or p.area<.001:raise ValueError('Invalid outline '+id)
    # No font or other machine-local binaries are copied into the project.
    cut=p.buffer(allowance,join_style=2)
    if cut.geom_type!='Polygon' or not cut.is_valid:raise ValueError('Invalid cut contour '+id)
    rec={'id':id,'module':group,'material':material,'quantity':qty,'source':source,
        'seam_allowance_mm':allowance,'grain':'+X on pattern is roll length, no quarter-turn rotation',
        'xyz_border_mm':xyz.tolist(),'sew_outline_mm':uv.tolist(),'cut_outline_mm':np.array(cut.exterior.coords).tolist(),
        'stats':stats or {'max_strain_pct':0,'valid_polygon':True,'no_inverted_triangles':True,'planar_exact':True},
        'edge_modes':edge_modes,'notches':[],'attachment_marks':[],'release':'P1_COMPLETE_DIGITAL_SAMPLE_SET_NOT_PRODUCTION'}
    if grid is not None:rec['grid_mm']=np.asarray(grid).tolist();rec['uv_mm']=np.asarray(uv_grid_current).tolist()
    PIECES.append(rec)
    return rec

uv_grid_current=None

def grid_piece(id,g,group,material,initial=None,source='',depth=0,allowance=12):
    global uv_grid_current
    g=np.asarray(g,float)
    import pickle
    cache=R/'_work/metric_cache';cache.mkdir(parents=True,exist_ok=True)
    key=hashlib.sha256(g.tobytes()+(np.array(initial).tobytes() if initial is not None else b'')+b'triangle-metric-v3').hexdigest()
    cp=cache/(key+'.pickle')
    if cp.exists(): uv,stats=pickle.loads(cp.read_bytes())
    else:
        uv,stats=flatten(g,initial);cp.write_bytes(pickle.dumps((uv,stats)))
    # Refine explicit panel seams rather than silently stretch the mesh or repair outlines.
    if (stats['max_strain_pct']>2 or not stats['valid_polygon'] or not stats['no_inverted_triangles']) and depth<9:
        nr,nc=g.shape[:2];along=np.linalg.norm(np.diff(g[:,nc//2],axis=0),axis=1).sum();across=np.linalg.norm(np.diff(g[nr//2],axis=0),axis=1).sum()
        ax=0 if nr>2 and (along>=across or nc<=2) else 1
        if g.shape[ax]<=2:raise ValueError('Further dart required '+id)
        mid=(g.shape[ax]-1)//2
        for suffix,part in [('a',g[:mid+1] if ax==0 else g[:,:mid+1]),('b',g[mid:] if ax==0 else g[:,mid:])]:grid_piece(id+suffix,part,group,material,source=source,depth=depth+1,allowance=allowance)
        return
    if stats['max_strain_pct']>2.001 or not stats['valid_polygon'] or not stats['no_inverted_triangles']:raise ValueError('Metric release gate '+id)
    xyz,poly=boundary(g,uv);uv_grid_current=uv
    put(id,group,material,xyz,poly,stats,g,source,allowance=allowance)
    print('PANEL',id,round(stats['max_strain_pct'],3),flush=True)

def planar(id,xyz,group,material='lining',source='',modes=None,allowance=12,qty=1):
    xyz=np.asarray(xyz,float);center=xyz.mean(0);_,_,basis=np.linalg.svd(xyz-center,full_matrices=False)
    if np.max(abs((xyz-center)@basis[-1]))>.05:raise ValueError('Not planar '+id)
    uv=(xyz-center)@basis[:2].T
    return put(id,group,material,xyz,uv,source=source,edge_modes=modes,allowance=allowance,qty=qty)

# All original skins are retained, including the original explicit seam subdivisions.
# Strip accessories are replaced below: their synthetic XY coordinates must not create false 3D matches.
for rec in old:
    if rec['parent'].startswith(('Z0','W0')):continue
    g=recover_grid(rec,seeds)
    grid_piece(rec['id'],g,rec['parent'],rec['material'],np.array(rec['uv_mm']),source='R08 accepted mesh '+rec['id'],allowance=rec['seam_allowance_mm'])

# Close formerly uncovered boundaries of the floor, rear end and keyboard flap.
def close_pair(name,a,b,group,which):
    for label,aa,bb in [('START',a[0],b[0]),('END',a[-1],b[-1]),('LEFT',a[:,0],b[:,0]),('RIGHT',a[:,-1],b[:,-1])]:
        if label in which:grid_piece(name+'_'+label,np.stack([aa,bb],axis=1),group,'lining',source='Boundary connector between actual R08 skins')
close_pair('F09_END',np.array(seeds['F08_TOP']['grid_mm']),np.array(seeds['F08_BOTTOM']['grid_mm']),'F08_FLEXIBLE_SOLE',{'START','END'})
close_pair('G09_REAR_EDGE',np.array(seeds['G08_REAR_O']['grid_mm']),np.array(seeds['G08_REAR_I']['grid_mm']),'G08_REAR_END',{'START','END','LEFT','RIGHT'})
close_pair('K09_FLAP_EDGE',np.array(seeds['K08_FLAP_OUTER']['grid_mm']),np.array(seeds['K08_FLAP_LINING']['grid_mm']),'K07_PASSIVE_FLAP_CLOSED',{'START','END','LEFT','RIGHT'})

# Form-fitting removable inner liners: sample real CAD tessellation cross sections.
# The sewing envelope is piecewise ruled, explicitly exported separately from unchanged R08.
def section_envelope(body,nsections=17,nring=16):
    v=np.asarray(body['vertices_mm']);f=np.asarray(body['faces'],int);center=(v.max(0)+v.min(0))/2
    # Largest principal dimension gives the least number of hidden gores.
    vals,basis=np.linalg.eigh(np.cov(v.T));axis=basis[:,-1]
    if np.dot(axis,[1,.05,.2])<0:axis=-axis
    reference=np.array([0.,1.,0.])
    if abs(reference@axis)>.9:reference=np.array([0.,0.,1.])
    e1=reference-axis*(reference@axis);e1/=np.linalg.norm(e1);e2=np.cross(axis,e1);M=np.stack([axis,e1,e2],axis=1)
    loc=(v-center)@M;tri=loc[f];amin,amax=loc[:,0].min(),loc[:,0].max();length=amax-amin
    # At most 5 mm end setback avoids unsewable pole caps; recorded in the envelope metadata.
    eps=min(5.0,length*.01);aa=amin+eps;bb=amax-eps;ts=aa+(bb-aa)*(1-np.cos(np.linspace(0,np.pi,nsections)))/2
    rings=[]
    for t in ts:
        hits=[]
        for i,j in [(0,1),(1,2),(2,0)]:
            A=tri[:,i];B=tri[:,j];d=B[:,0]-A[:,0];valid=((A[:,0]-t)*(B[:,0]-t)<=0)&(abs(d)>1e-10)
            A=A[valid];B=B[valid];q=(t-A[:,0])/(B[:,0]-A[:,0]);hits.extend((A+q[:,None]*(B-A))[:,1:].tolist())
        hits=np.unique(np.round(hits,8),axis=0)
        if len(hits)<3:raise ValueError('Section absent '+body['id'])
        hull=hits[ConvexHull(hits).vertices];poly=Polygon(hull);c=np.array(poly.centroid.coords[0]);ring=[]
        for theta in np.linspace(0,2*np.pi,nring,endpoint=False):
            ray=np.array([math.cos(theta),math.sin(theta)]);h=poly.intersection(LineString([c,c+ray*10000]))
            if h.geom_type!='LineString':raise ValueError('Section ray '+body['id'])
            q=np.array(h.coords[-1]);ring.append(center+M@np.r_[t,q])
        rings.append(ring)
    rings=np.array(rings)
    return rings,{'method':'convex cross-sections of original BREP tessellation; separate ruled sewing envelope',
                  'end_offset_mm':eps,'axis':axis.tolist(),'section_count':nsections,'points_per_section':nring,
                  'inner_concavities':'not copied; the removable bag encloses the sampled outer profile',
                  'physics_validated':False}

bag_groups={'forming_fill','contact_fill','pelvis','leg_support','footstop','arm_support','pillow','frame_padding'}
for body in bodies.values():
    if body['group'] not in bag_groups and body['id']!='O08_TOE_CAP':continue
    bid='B09_'+body['id'];rings,meta=section_envelope(body)
    env={'id':bid,'source_cad_part':body['id'],'source_group':body['group'],'rings_mm':rings.tolist(),'metadata':meta}
    ENVELOPES.append(env)
    # Sixteen developable longitudinal gores; no impractical tiny transverse patchwork.
    for i in range(16):
        ids=[i,(i+1)%16];grid_piece(bid+'_G'+str(i+1),rings[:,ids],bid,'inner_bag',source='R08 tessellation '+body['id'])
    planar(bid+'_CAP_A',rings[0],bid,'inner_bag',source='Sampled start plane of '+body['id'])
    planar(bid+'_CAP_B',rings[-1][::-1],bid,'inner_bag',source='Sampled end plane of '+body['id'])

js(R/'cad/inner_sewing_envelopes.json',ENVELOPES)

# Accessories: physical cut lengths, complete edge operations and matching sewn ports.
zips=json.loads((BASE/'harness/zippers.json').read_text());routes=json.loads((BASE/'harness/routes.json').read_text())

def rectangle(id,L,W,group,material,modes=None,qty=1,allowance=12):
    # X=roll length. Synthetic coordinates are never paired by spatial coincidence.
    uv=np.array([[0.,0],[L,0],[L,W],[0,W]])
    return put(id,group,material,np.c_[uv,np.zeros(4)],uv,source='dimensioned accessory',edge_modes=modes or ['hem']*4,qty=qty,allowance=allowance)

for z in zips:
    key=z['id'];pts=np.array(z.get('path_mm',z.get('polyline_mm',z.get('points_mm',[]))))
    L=float(z.get('length_mm',z.get('chain_mm',z.get('finished_chain_mm',0))))
    if L<=0:
        # R08 metadata may name the supplier order length separately.
        for k,v in z.items():
            if isinstance(v,(int,float)) and 'length' in k:L=float(v);break
    if L<=0:raise ValueError('Zipper length absent '+str(z))
    for side in ['A','B']:
        rectangle(key+'_FACING_'+side,L,40,key,'technical',['attachment','hem','zipper_half','hem'])
    rectangle(key+'_STORM_LAP',L+40,110,key,'outer',['attachment','hem','fold','hem'])
    for side in ['START','STOP']:rectangle(key+'_END_'+side,65,65,key,'technical',['attachment']*4)
    OPERATIONS.append({'id':key,'type':'zipper','finished_chain_mm':L,'halves':2,'end_allowance_mm':20,'source':z,
                       'construction':'40 mm facings each side, 12 mm seams; lap folds to 43 mm finished cover; attachment stations from R08 3D route',
                       'release':'sample sewing and slider/chain supplier confirmation required'})

for r in routes:
    name=r['id'];L=float(r.get('cut_length_mm',r.get('cut_mm',r.get('length_mm',0))))
    if L<=0:
        for k,v in r.items():
            if isinstance(v,(int,float)) and ('length' in k or 'cut' in k):L=float(v);break
    if L<=0:raise ValueError('Route length absent '+str(r))
    rectangle(name+'_SLEEVE',L,70,name,'technical',['folded_longitudinal_seam','hem','folded_longitudinal_seam','hem'])
    for side in ['A','B']:rectangle(name+'_STRAIN_RELIEF_'+side,100,25,name,'webbing',['attachment']*4,allowance=0)
    OPERATIONS.append({'id':name,'type':'cable_channel','raw_length_mm':L,'finished_width_mm':23,'source':r,
                       'construction':'70 mm strip: seam 12 mm each side, flattened tube width 23 mm; open ends hemmed; no right-exit cable',
                       'mating':'attach along original R08 centreline, not inside loose filler; commercial preterminated USB/PD unchanged'})

# Independent removable mat sleeves, three edges sewn, fourth zipper/hem; no sewn hole through heaters.
for name,source in [('EH09_BACK','EH08_BACK_CASSETTE'),('EH09_SEAT','EH08_SEAT_CASSETTE')]:
    body=bodies[source];v=np.asarray(body['vertices_mm']);_,basis=np.linalg.eigh(np.cov(v.T));a=v@basis
    dims=np.sort(np.ptp(a,axis=0));L,W=dims[-1]+20,dims[-2]+20
    for s in ['A','B']:rectangle(name+'_'+s,L,W,name,'lining',['accessory_seam','accessory_seam','accessory_zipper','accessory_seam'])
    OPERATIONS.append({'id':name,'type':'heater_sleeve','source_part':source,'finished_mm':[L,W],
                       'allowance_mm':12,'paired_edges':[0,1,3],'zipper_edge':2,'stitching_through_mat':False})
# External service pockets and closed cover of the junction box, not a loose cable under the sitter.
for s in ['A','B']:rectangle('J09_SERVICE_POCKET_'+s,210,150,'J09_SERVICE_POCKET','outer',['accessory_seam','accessory_seam','accessory_zipper','accessory_seam'])
rectangle('J09_BULKHEAD_REINFORCEMENT',150,125,'J09_BULKHEAD','technical',['attachment']*4,qty=2)
for i in range(6):rectangle('PULL09_'+str(i+1),90,25,'PULL09','webbing',['hem','fold','hem','attachment'],allowance=0)
# Inner liner ties and stopper anchors have separate webbing cut items.
for b in bodies.values():
    if b['group'] not in {'straps','foot_straps','foot_anchors'} or b['kind']=='hardware':continue
    v=np.asarray(b['vertices_mm']);dims=np.sort(np.ptp(v,axis=0));L=float(np.linalg.norm(np.ptp(v,axis=0)))+100;W=40 if b['group']!='foot_anchors' else 48
    rectangle('WEB09_'+b['id'],L,W,'WEB09_'+b['id'],'webbing',['hem','attachment','hem','attachment'],allowance=0)
    OPERATIONS.append({'id':'WEB09_'+b['id'],'type':'webbing','CAD_reference':b['id'],'cut_length_mm':L,
                       'allowance_for_attachment_mm':100,'load_testing_completed':False})

# Seam topology: scope by manufacturing module, not raw coordinates shared by unrelated components.
incidence=defaultdict(list)
for rec in PIECES:
    xyz=np.array(rec['xyz_border_mm']);uv=np.array(rec['sew_outline_mm']);N=len(xyz)
    if rec['material']=='insulation' or rec['edge_modes'] is not None:continue
    for i in range(N):
        j=(i+1)%N;key=(rec['module'],segment_key(xyz[i],xyz[j]))
        incidence[key].append({'panel':rec['id'],'index':i,'cad_mm':float(np.linalg.norm(xyz[j]-xyz[i])),
                               'flat_mm':float(np.linalg.norm(uv[j]-uv[i]))})
unpaired=[(key,v) for key,v in incidence.items() if len(v)!=2]
if unpaired:
    js(R/'tests/unresolved_edges.json',[{'module':k[0],'points':k[1],'members':v} for k,v in unpaired]);raise ValueError(f'{len(unpaired)} unresolved physical seam segments')
lookup={p['id']:p for p in PIECES};seams=[]
for num,((module,xyz),members) in enumerate(sorted(incidence.items(),key=lambda kv:str(kv[0])),1):
    mismatch=abs(members[0]['flat_mm']-members[1]['flat_mm'])
    seams.append({'id':f'S{num:05d}','module':module,'members':members,'source_segment_mm':xyz,'mismatch_mm':mismatch,'operation':'lockstitch, allowance 12 mm'})
# Group contiguous segments by their mating panel pair for real seam lengths and notch stations.
grouped=defaultdict(list)
for s in seams:grouped[(s['module'],tuple(sorted(m['panel'] for m in s['members'])))].append(s)
chains=[]
for count,(key,ss) in enumerate(sorted(grouped.items()),1):
    # Separate disconnected chains even when the same two panels touch on more than one side.
    rem=set(range(len(ss)))
    while rem:
        k=rem.pop();block={k};verts=set(map(tuple,ss[k]['source_segment_mm']));changed=True
        while changed:
            changed=False
            for j in list(rem):
                vv=set(map(tuple,ss[j]['source_segment_mm']))
                if verts&vv:rem.remove(j);block.add(j);verts|=vv;changed=True
        q=[ss[j] for j in sorted(block)];names=key[1];lengths={n:sum(next(m['flat_mm'] for m in s['members'] if m['panel']==n) for s in q) for n in names}
        # Project matching notch locations from the same 3D vertices onto both flat patterns.
        cid=f'J{len(chains)+1:04d}';ids={s['id'] for s in q};station=0.0
        for s in q:
            if station==0 or station>=75:
                for m in s['members']:
                    rec=lookup[m['panel']];ii=m['index'];uv=np.array(rec['sew_outline_mm']);xy=(uv[ii]+uv[(ii+1)%len(uv)])/2
                    rec['notches'].append({'seam':cid,'segment':s['id'],'uv_mm':xy.tolist(),'mark':'2 mm circle, chalk mark; do not cut past seam'})
                station=0.0
            station+=s['members'][0]['cad_mm']
        difference=max(lengths.values())-min(lengths.values())
        chains.append({'id':cid,'module':key[0],'panels':list(names),'length_mm':lengths,'mismatch_mm':difference,
                       'segments':sorted(ids),'operation':'sew','intentional_ease_mm':difference})

# One dismountable service seam per inner bag; not all physically closed seams are permanently sewn.
for env in ENVELOPES:
    options=[s for s in chains if s['module']==env['id'] and min(s['length_mm'].values())>=140]
    if not options:raise ValueError('No accessible bag fill seam '+env['id'])
    use=max(options,key=lambda s:min(s['length_mm'].values()));L=min(use['length_mm'].values())
    use['operation']='zipper_service';use['chain_nominal_mm']=max(80,math.floor((L-30)/10)*10)
    rectangle(env['id']+'_INNER_FILL_GUARD',use['chain_nominal_mm']+40,85,env['id']+'_SERVICE','lining',['attachment','hem','fold','hem'])
    OPERATIONS.append({'id':env['id']+'_ZIP','type':'inner_bag_zipper','mating_seam':use['id'],'nominal_chain_mm':use['chain_nominal_mm'],
                       'double_containment':'zipper plus folded internal guard; service only without occupant; no free granular access'})

# Every manufactured edge has an operation; insulation edges are intentionally free-cut inserts.
edges=[]
for p in PIECES:
    N=len(p['sew_outline_mm'])
    if p['edge_modes'] is None and p['material']!='insulation':continue
    for i in range(N):edges.append({'panel':p['id'],'edge':i,'operation':'insert_free_cut' if p['material']=='insulation' else p['edge_modes'][i],
                                   'module':p['module'],'length_mm':float(np.linalg.norm(np.array(p['sew_outline_mm'][(i+1)%N])-p['sew_outline_mm'][i]))})
# Remove redundant R08 record metadata; serialization remains fully traceable.
js(R/'patterns/pieces.json',PIECES);js(R/'patterns/seam_segments.json',seams);js(R/'patterns/seam_chains.json',chains)
js(R/'patterns/edge_operations.json',edges);js(R/'patterns/hardware_operations.json',OPERATIONS)
js(R/'tests/input_hashes.json',source_hashes)
summary={'source_revision':'R08 at a40b3730fcb924dd086d1c2088c60cb4972a96c2','digital_set':'P1 - complete assembly definitions, sample sewing required',
         'pattern_types':len(PIECES),'cut_pieces':sum(p['quantity'] for p in PIECES),'internal_envelopes':len(ENVELOPES),
         'seam_segments':len(seams),'seam_chains':len(chains),'unclassified_physical_edges':0,
         'intentionally_finished_accessory_or_insert_edges':len(edges),
         'max_metric_strain_pct':max(p['stats']['max_strain_pct'] for p in PIECES),
         'max_seam_segment_mismatch_mm':max(s['mismatch_mm'] for s in seams),
         'max_seam_chain_mismatch_mm':max(s['mismatch_mm'] for s in chains),
         'fabric_calibrated':False,'physical_fit_tested':False,'production_approved':False,
         'scope':'complete digital cut set and operation registry; not a production release or tested ergonomic/thermal product'}
js(R/'tests/summary.json',summary);print('PATTERN_SET_COMPLETE',json.dumps(summary),flush=True)
