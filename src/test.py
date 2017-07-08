import pybullet as p
import framework.entity.body as body
import framework.entity.rethinkGripper as rg
import framework.entity.sawyer as s
import framework.entity.kuka as k
import numpy as np
p.connect(p.GUI)


p.resetSimulation()

p.loadURDF('plane.urdf', useFixedBase=True)

# w = wsg.WSG50Gripper(async=True, pos=(-0.5, -0.7, 0.8))
# g.grasp(slide=1)
# w.grasp(slide=1)

# print(w.pos)
# print(w.tool_pos)

# r = k.Kuka(null_space=True, pos=[0,0,0],orn=[0,0,0,1])
# r = s.Sawyer()
# g = rg.RethinkGripper()
# r.grasp()
import math

r = p.loadURDF('sawyer_robot/sawyer_description/urdf/sawyer.urdf', [0,0,0.9],
	[0,0,0,1],useFixedBase=True)


# r = p.loadURDF('kuka_iiwa/model_vr_limits.urdf', [0,0,0.],
	# [0,0,0,-1],useFixedBase=True)

# p.setJointMotorControlArray(r, [0,1,2,3,4,5,6], 
# 		p.POSITION_CONTROL, targetPositions=[0,0,0,0.5*math.pi,0,-math.pi*0.5*0.66,0], 
# 		targetVelocities=[0] * 7,
# 		positionGains=[0.05] * 7, velocityGains=[1.] * 7)

# p.setJointMotorControlArray(r, [0,1,2,3,4,5,6], 
# 		p.POSITION_CONTROL, targetPositions=(0, -1.18, 0.00, 2.18, 0.00, 0.57, 3.3161), 
# 		targetVelocities=[0] * 7,
# 		positionGains=[0.05] * 7, velocityGains=[1.] * 7)

# pose = (0., 0., 0., 1.570793, 0., -1.04719755, 0.)
# for i in range(7):

# 	p.resetJointState(r, i, pose[i],0,0)

# p.setRealTimeSimulation(1)
# for _ in range(2000):
# 	p.stepSimulation()

ll=[-.967,-2	,-2.96,0.19,-2.96,-2.09,-3.05]
#upper limits for null space
ul=[.967,2	,2.96,2.29,2.96,2.09,3.05]
#joint ranges for null space
jr=[5.8,4,5.8,4,5.8,4,6]
#restposes for null space
rp=[0,0,0,0.5*math.pi,0,-math.pi*0.5*0.66,0]
#joint damping coefficents
jd=[0.1,0.1,0.1,0.1,0.1,0.1,0.1]

p.loadURDF('cube_small.urdf', [-0.6,0,0.2], useFixedBase=True)
p.setGravity(0,0,-9.8)
# r.mark('haha')
print (p.getLinkState(r, 4)[0])
# import ikpy
# chain = ikpy.chain.Chain.from_urdf_file(
# 	'../../bullet3/data/sawyer_robot/sawyer_description/urdf/sawyer_arm.urdf',
# 	base_elements=['right_arm_base_link'],
# 	active_links_mask=[False] + [True,] * 7)

# target_vector = [0.8, -0.12, 1.5]
# target_frame = np.eye(4)
# target_frame[:3, 3] = target_vector
# print(target_frame)
# sol = chain.inverse_kinematics(target_frame,
# 	initial_position=(0, 0, -1.18, 0.00, 2.18, 0.00, 0.57, 3.3161))
# [-0.465943   -0.89308893  2.286186    0.03158455 -2.25553708 -0.65736246
#   2.17224787]
sol = [-0.07833199, -0.29562288 ,-0.01593633,-0.31518591,  0.01860969 ,-0.96004085,
  1.81762848]
# print(sol)
# print(chain.forward_kinematics(sol))
# ik = p.calculateInverseKinematics(r, 6, (-0.8, 0, 0.2), 
# 		(0, 1, 0, 0),
# 		# lowerLimits=(-3.05, -3.82, -3.05, -3.05, -2.98, -2.98, -4.71), 
# 		# upperLimits=(3.05, 2.28, 3.05, 3.05, 2.98, 2.98, 4.71),
#   #       jointRanges=(6.1, 6.1, 6.1, 6.1, 5.96, 5.96, 9.4), 

#   #       restPoses=(0, -1.18, 0.00, 2.18, 0.00, 0.57, 3.3161),
#                 jointDamping=(.1,) * 7)
# print(ik)
print([(p.getJointInfo(r, o)[1], p.getLinkState(r, o)[0]) for o in range(p.getNumJoints(r))])

p.setJointMotorControlArray(r, [5,10,11,12,13,15,18], 
		p.POSITION_CONTROL, targetPositions=(0, -1.18, 0.00, 2.18, 0.00, 0.57, 3.3161), 
		targetVelocities=[0] * 7,
		positionGains=[0.05] * 7, velocityGains=[1.] * 7)

for _ in range(2000):
	p.stepSimulation()
ik = p.calculateInverseKinematics(r, 6, (0.8, 0.1, 0.8), 
		# (0, 1, 0, 0),
		lowerLimits=(-3.05, -3.82, -3.05, -3.05, -2.98, -2.98, -4.71), 
		upperLimits=(3.05, 2.28, 3.05, 3.05, 2.98, 2.98, 4.71),
        jointRanges=(6.1, 6.1, 6.1, 6.1, 5.96, 5.96, 9.4), 

        restPoses=(0, -1.18, 0.00, 2.18, 0.00, 0.57, 3.3161),
                jointDamping=(.1,) * 7)
print(ik)
# p.setJointMotorControlArray(r, [5,10,11,12,13,15,18], 
# 	p.POSITION_CONTROL, targetPositions=sol, 
# 	targetVelocities=[0] * 7,
# 	positionGains=[0.05] * 7, velocityGains=[1.] * 7)
# print(p.getNumJoints(r))
while 1:
	# print(p.getQuaternionFromEuler((0, 0, np.pi * 2)))
	
	p.setRealTimeSimulation(1)
	print(p.getLinkState(r, 18)[0])

	# print([(p.getLinkState(r, i)[0],p.getJointInfo(r, i)[-1])  for i in range(23)])
	# for e in p.getMouseEvents():
	# 	if e[0] == 2:
	# 		print(e[1], e[2])
	# r.reach((-.6, 0.0, .2), (0, 1, 0, 0))
	# for j in range(7):
	# 	p.setJointMotorControl2(r, j, 
	# 		p.POSITION_CONTROL, targetPosition=ik[j], targetVelocity=0.,
	# 		positionGain=0.05, velocityGain=1.)
	# r.tool_orn=((0,1,0,0))
	# (g.reach((0.8, -0.5,  1.), p.getQuaternionFromEuler((np.pi/2, -np.pi/2, 0))), 'delta')
	# print(r.tool_pos, r.tool_orn)
	# print(p.getLinkState(r.uid, 6)[0])
	# p.stepSimulation()



