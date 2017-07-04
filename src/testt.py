import pybullet as p
from framework.utils import math_util
p.connect(p.GUI)

p.setRealTimeSimulation(1)
	
import numpy as np

width, height, vmat, projmat, _, _, _, _, yaw, pitch, dist, target = p.getDebugVisualizerCamera()

vmat = np.array(vmat).reshape((4,4))
projmat = np.array(projmat).reshape((4,4))
vp = projmat.dot(vmat)

# print(proj[:3,:3].dot(x[:3,:3]).dot(np.array([512,378,1])))
# point3d = vp.dot(np.array([0,0,0,1]))

# print(width, height)
# print((point3d[0] + 1) / 2. * width /2 , (1 - point3d[1]) / 2. * height/2)
p.loadURDF('cube_small.urdf',(1,0,0))
print(vmat, np.linalg.inv(vmat), 'fuck')
_AXES2TUPLE = {
    'sxyz': (0, 0, 0, 0), 'sxyx': (0, 0, 1, 0), 'sxzy': (0, 1, 0, 0),
    'sxzx': (0, 1, 1, 0), 'syzx': (1, 0, 0, 0), 'syzy': (1, 0, 1, 0),
    'syxz': (1, 1, 0, 0), 'syxy': (1, 1, 1, 0), 'szxy': (2, 0, 0, 0),
    'szxz': (2, 0, 1, 0), 'szyx': (2, 1, 0, 0), 'szyz': (2, 1, 1, 0),
    'rzyx': (0, 0, 0, 1), 'rxyx': (0, 0, 1, 1), 'ryzx': (0, 1, 0, 1),
    'rxzx': (0, 1, 1, 1), 'rxzy': (1, 0, 0, 1), 'ryzy': (1, 0, 1, 1),
    'rzxy': (1, 1, 0, 1), 'ryxy': (1, 1, 1, 1), 'ryxz': (2, 0, 0, 1),
    'rzxz': (2, 0, 1, 1), 'rxyz': (2, 1, 0, 1), 'rzyz': (2, 1, 1, 1)}

for x in _AXES2TUPLE.keys():
	vvv = np.array(math_util.mat2quat(np.linalg.inv(vmat[:3,:3])))
	print(vvv * 180 / np.pi, x)
while 1:

	for e in p.getMouseEvents():
		if e[0] == 2:
			# print(e[1], e[2], 0)
			x = 2. * e[1] * 2. / width- 1
			y = -2. * e[2] * 2. / height + 1
			# print(np.linalg.inv(vp)[:3,:3].dot(np.array([x,y,0])))