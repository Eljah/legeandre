#!/usr/bin/env python3
"""Actual OCCT solid half-section, Y>=0. Not a separately illustrated cutaway."""
from build_cad import build,box,export_render
parts=build('work');out=[]
keep=box(5000,2500,3000,(250,1250,1200))
for part in parts:
 try:
  cut=part['shape'].intersect(keep)
  if cut.Volume()>0.1:
   p=part.copy();p['shape']=cut;out.append(p)
 except Exception:
  raise RuntimeError('Failed boolean section '+part['id'])
export_render(out,'work_section','iso')
print('Section rendered from',len(out),'intersected solids')
