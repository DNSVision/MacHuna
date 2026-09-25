import sys; sys.path.insert(0,'/Users/davidsteer/Developer/MacHuna')
import numpy as np, machuna as m

P='/Users/davidsteer/Desktop/TEST WIPES/50i/EIF/0003.eif'
h=m.EIFHeader(P)
U=m._EIF_UNIT_BYTES
def frame(f,i):
    f.seek(h.video_start+i*3*U)
    return np.asarray(m._decode_eif_frame_rgba(f.read(U),f.read(U),f.read(U)),dtype=np.float32)

print(f"{h.clip_name}  {h.frame_count} frames @ {h.fps}fps\n")
print(" fr   adjacent  alternate   ratio   motion vs next   verdict")
with open(P,'rb') as f:
    prev=None
    for i in range(0,min(10,h.frame_count)):
        a=frame(f,i)
        y=a[...,0]*0.299+a[...,1]*0.587+a[...,2]*0.114
        adj=np.abs(y[:-1]-y[1:]).mean()        # neighbouring lines = OPPOSITE fields
        alt=np.abs(y[:-2]-y[2:]).mean()        # two apart = SAME field
        mot=np.abs(y-prev).mean() if prev is not None else float('nan')
        prev=y
        r=adj/alt if alt else float('nan')
        v="INTERLACED" if r>1.0 else ("progressive" if r<0.8 else "unclear")
        print(f"{i:3d}   {adj:7.2f}   {alt:7.2f}   {r:6.2f}   {mot:10.2f}       {v}")
