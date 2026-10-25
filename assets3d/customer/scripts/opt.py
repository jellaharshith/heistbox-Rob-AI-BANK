import bpy, math, random, numpy as np
from mathutils import Euler, Matrix, Vector, Quaternion
O=bpy.data.objects; rig=O["CHAR_Customer"]; phone=O["PROP_Phone"]
for o in list(O):
    pass
ad=rig.animation_data
for t in ad.nla_tracks: t.mute=True
bn={b.name.split(":")[1]:b for b in rig.data.bones}
Rr={k:b.matrix_local.to_3x3() for k,b in bn.items()}
Rdir={k:(b.tail_local-b.head_local).normalized() for k,b in bn.items()}
def basis(bone,spec):
    rx,ry,rz=spec[:3]; roll=spec[3] if len(spec)>3 else 0
    e=Euler((math.radians(rx),math.radians(ry),math.radians(rz)),'XYZ').to_matrix()
    if roll: e=e@Matrix.Rotation(math.radians(roll),3,Rdir[bone])
    return (Rr[bone].inverted()@e@Rr[bone]).to_quaternion()
def setp(P):
    for pb in rig.pose.bones:
        pb.rotation_mode='QUATERNION'; pb.rotation_quaternion=Quaternion((1,0,0,0))
    for k,v in P.items():
        rig.pose.bones["mixamorig:"+k].rotation_quaternion=basis(k,v)
    bpy.context.view_layer.update()
tgt=Vector((0.0,-0.32,1.66))
def score(p):
    setp(dict(RightArm=p[0:3],RightForeArm=(p[3],0,p[4]),RightHand=(p[5],p[6],0,p[7]),Spine=(2,0,0),Neck=(0,0,0)))
    m=phone.matrix_world; c=m.translation; n=(m.to_3x3()@Vector((0,-1,0))).normalized(); up=(m.to_3x3()@Vector((0,0,1))).normalized()
    return (c-tgt).length + 0.12*(1-n.dot(Vector((0,1,0.1)).normalized())) + 0.05*(1-up.z)
lo=np.array([-110,-30,-70,-140,-60,-60,-40,-120.]); hi=np.array([-40,30,40,-60,40,40,40,120.])
best=None
random.seed(1)
for i in range(1500):
    p=lo+np.random.rand(8)*(hi-lo); s=score(p)
    if best is None or s<best[0]: best=(s,p)
s0,p0=best
step=(hi-lo)*0.1
for i in range(1500):
    p=np.clip(p0+np.random.randn(8)*step,lo,hi); s=score(p)
    if s<s0: s0,p0=s,p
    if i%500==499: step*=0.5
print("OPT",s0,[round(float(x),1) for x in p0])
setp(dict(RightArm=p0[0:3],RightForeArm=(p0[3],0,p0[4]),RightHand=(p0[5],p0[6],0,p0[7])))
print("PH", phone.matrix_world.translation, (phone.matrix_world.to_3x3()@Vector((0,-1,0))))
