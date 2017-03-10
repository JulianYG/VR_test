import math
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import time
import csv
import numpy as np
from model import *

class KukaSingleArmVR(KukaArmVR):
	"""
	An easier task without grasping
	"""
	def __init__(self, pybullet, task):

		super().__init__(pybullet, task)
		self.kuka = -2
		
	def record(self, file):
		load_status = 0
		while load_status == 0:
			self.p.connect(self.p.SHARED_MEMORY)
			load_status = self.setup(0)
		try:
			
			# Record everything
			bodyLog = self.p.startStateLogging(self.p.STATE_LOGGING_GENERIC_ROBOT,
				'../examples/pybullet/generic.' + file)

			# # May not needed anymore; benchmark all events during replay is also possible
			# ctrlLog = self.p.startStateLogging(self.p.STATE_LOGGING_VR_CONTROLLERS, 
			# 	file + '_ctrl')

			logIds = [bodyLog]
			cId = None
			while True:
				events = self.p.getVREvents()

				for e in (events):
					# If the user think one task is completed, 
					# he/she will push the menu button
					eef_pos = self.p.getLinkState(self.kuka, 6)[0]

					if not cId:		
						# If detected contact points
						touch = self.p.getContactPoints(self.kuka)
						
						# Only attach when sticked around the eef center
						for contact_point in touch:
							if self.euc_dist(eef_pos, contact_point[5]) < 0.01 and contact_point[2] not in range(3):
								cId = self.p.createConstraint(self.kuka, 6, contact_point[2], -1, self.p.JOINT_FIXED, [0, 0, 0], [0, 0, 0.05], [0, 0, 0])
								
					if e[self.BUTTONS][33] & self.p.VR_BUTTON_IS_DOWN:
						if cId:
							self.p.removeConstraint(cId)
						cId = None

					sq_len = self.euc_dist(eef_pos, e[1])

					# Allows robot arm control by VR controllers
					if sq_len < self.THRESHOLD * self.THRESHOLD:
						# eef_pos = self.p.getBasePositionAndOrientation()
						target_plane_pos = (e[1][0], e[1][1], 1.23)
						curr_pos = self.p.getLinkState(self.kuka, 6)[0]
						target_point_pos = (curr_pos[0], curr_pos[1], 0.525)  # e[1][2]
						eef_orn = (0, 1, 0, 0)
						
						if e[self.BUTTONS][32] & self.p.VR_BUTTON_IS_DOWN:
							self.ik_helper(self.kuka, target_point_pos, eef_orn)
						else: 
							self.ik_helper(self.kuka, target_plane_pos, eef_orn)
					else:
						self.disengage(self.kuka, e)
	
					# Add user interaction for task completion
					if (e[self.BUTTONS][1] & self.p.VR_BUTTON_WAS_TRIGGERED):
							# self.p.resetSimulation()
							# self.p.removeAllUserDebugItems()
						self.p.addUserDebugText('good job!', (1.7, 0, 1), (255, 0, 0), 12, 10)
						# Can add line for mark here
						# so that in saved csv file, we know when one task is complete		

		except KeyboardInterrupt:
			self.quit(logIds)

	def replay(self, file, saveVideo=0):
		
		load_status = 0
		while load_status == 0:
			load_status = self.setup(1)
		# Setup the camera 
		self.p.resetDebugVisualizerCamera(self.FOCAL_LENGTH, self.YAW, 
			self.PITCH, self.FOCAL_POINT)

		log = self.parse_log('generic.' + file, verbose=True)
		self.replay_log(log)
		# 		if saveVideo:
		# 			self.video_capture()
		self.quit([])

	def _setup_robot(self):
		# Only load a kuka arm, no need for gripper this time
		self.kuka = self.p.loadURDF("kuka_iiwa/model_vr_limits.urdf", 
			1.400000, -0.200000, 0.600000,
			0.000000, 0.000000, 0.000000, 1.000000)
		self.reset_kuka(self.kuka)


class KukaDoubleArmVR(KukaArmVR):

	# This one try out the new loggingState method
	def __init__(self, pybullet, task):

		super().__init__(pybullet, task)
		self.kuka_arms = []
		self.kuka_grippers = []
		self.kuka_constraints = []

	def record(self, file, saveVideo=0):
		load_status = 0
		while load_status == 0:
			self.p.connect(self.p.SHARED_MEMORY)
			load_status = self.setup(0)

		try:
			gripperMap = dict(zip(self.controllers, self.kuka_grippers))
			kukaMap = dict(zip(self.controllers, self.kuka_arms))
			
			# Record everything
			bodyLog = self.p.startStateLogging(self.p.STATE_LOGGING_GENERIC_ROBOT,
				'../examples/pybullet/generic.' + file)

			# ctrlLog = self.p.startStateLogging(self.p.STATE_LOGGING_VR_CONTROLLERS, 
			# 	file + '_ctrl')
			logIds = [bodyLog]

			while True:

				events = self.p.getVREvents()
				for e in (events):
					# If the user think one task is completed, 
					# he/she will push the menu button
					# controller_pos, controller_orien = e
					kuka_gripper = gripperMap[e[0]]
					kuka = kukaMap[e[0]]			

					# Add sliders for gripper joints
					if e[self.BUTTONS][33] & self.p.VR_BUTTON_WAS_TRIGGERED:
						for i in range(self.p.getNumJoints(kuka_gripper)):
							self.p.setJointMotorControl2(kuka_gripper, i, self.p.VELOCITY_CONTROL, targetVelocity=5, force=50)

					if e[self.BUTTONS][33] & self.p.VR_BUTTON_WAS_RELEASED:	
						for i in range(self.p.getNumJoints(kuka_gripper)):
							self.p.setJointMotorControl2(kuka_gripper, i, self.p.VELOCITY_CONTROL, targetVelocity=-5, force=50)

					sq_len = self.euc_dist(self.p.getLinkState(kuka, 6)[0], e[1])
					print(sq_len)
					# Allows robot arm control by VR controllers
					if sq_len < self.THRESHOLD * self.THRESHOLD:
						self.engage(kuka, e, fixed=True)
					else:
						self.disengage(kuka, e)

					# Add user interaction for task completion
					if (e[self.BUTTONS][1] & self.p.VR_BUTTON_WAS_TRIGGERED):
							# self.p.resetSimulation()
							# self.p.removeAllUserDebugItems()
						self.p.addUserDebugText('good job!', (1.7, 0, 1), (255, 0, 0), 12, 10)
						# Can add line for mark here
						# so that in saved csv file, we know when one task is complete		

		except KeyboardInterrupt:
			self.quit(logIds)

	def replay(self, file, saveVideo=0):
		load_status = 0
		while load_status == 0:
			load_status = self.setup(1)
		# Setup the camera 
		self.p.resetDebugVisualizerCamera(self.FOCAL_LENGTH, self.YAW, 
			self.PITCH, self.FOCAL_POINT)

		log = self.parse_log('generic.' + file, verbose=True)
		self.replay_log(log, delay=0.00045)

		# 		if saveVideo:
		# 			self.video_capture()
		self.quit([])

	def _setup_robot(self):
		pos = [0.3, -0.5]		# Original y-coord for the robot arms
		# Gripper ID to kuka arm ID
		for i in range(2):
			self.kuka_arms.append(self.p.loadURDF('kuka_iiwa/model_vr_limits.urdf', 1.4, pos[i], 0.6, 0, 0, 0, 1))
			self.kuka_grippers.append(self.p.loadSDF('gripper/wsg50_one_motor_gripper_new_free_base.sdf')[0])
		
		# Setup initial conditions for both arms
		for kuka in self.kuka_arms:
			self.reset_kuka(kuka)

		# Setup initial conditions for both grippers
		for kuka_gripper in self.kuka_grippers:
			self.reset_kuka_gripper(kuka_gripper)
			
		# Setup constraints on kuka grippers
		for kuka, kuka_gripper in zip(self.kuka_arms, self.kuka_grippers):
			self.kuka_constraints.append(self.p.createConstraint(kuka,
				6, kuka_gripper, 0, self.p.JOINT_FIXED, [0,0,0], [0,0,0.05], [0,0,0], parentFrameOrientation=[0, 0, 0, 1]))
			

class PR2GripperVR(BulletPhysicsVR):

	def __init__(self, pybullet, task):

		super().__init__(pybullet, task)
		self.pr2_gripper = 0
		self.pr2_cid = 0

	def create_scene(self):
		"""
		Basic scene needed for running tasks
		"""
		self.p.resetSimulation()
		self.p.setGravity(0, 0, -9.81)
		self.load_default_env()

	def record(self, file):

		load_status = 0
		while load_status == 0:
			self.p.connect(self.p.SHARED_MEMORY)
			load_status = self.setup(0)
		try:
			# Record everything
			bodyLog = self.p.startStateLogging(self.p.STATE_LOGGING_GENERIC_ROBOT,
				'../examples/pybullet/generic.' + file)

			# ctrlLog = self.p.startStateLogging(self.p.STATE_LOGGING_VR_CONTROLLERS, 
			# 	file + '_ctrl')
			logIds = [bodyLog]

			while True:

				events = self.p.getVREvents()
				for e in (events):

					# PR2 gripper follows VR controller				
					self.p.changeConstraint(self.pr2_cid, e[1], e[self.ORIENTATION], maxForce=1000)	

					if e[self.BUTTONS][33] & self.p.VR_BUTTON_WAS_TRIGGERED:
						for i in range(self.p.getNumJoints(self.pr2_gripper)):
							self.p.setJointMotorControl2(self.pr2_gripper, i, self.p.POSITION_CONTROL, targetPosition=0, force=50)

					if e[self.BUTTONS][33] & self.p.VR_BUTTON_WAS_RELEASED:	
						for i in range(self.p.getNumJoints(self.pr2_gripper)):
							self.p.setJointMotorControl2(self.pr2_gripper, i, self.p.POSITION_CONTROL, targetPosition=1, force=50)

					if (e[self.BUTTONS][1] & self.p.VR_BUTTON_WAS_TRIGGERED):
						self.p.addUserDebugText('One Item Inserted', (1.7, 0, 1), (255, 0, 0), 12, 10)

		except KeyboardInterrupt:
			self.quit(logIds)

	def replay(self, file, saveVideo=0):

		load_status = 0
		while load_status == 0:
			load_status = self.setup(1)
		# Setup the camera 
		self.p.resetDebugVisualizerCamera(self.FOCAL_LENGTH, self.YAW, 
			self.PITCH, self.FOCAL_POINT)

		log = self.parse_log('generic.' + file, verbose=True)
		self.replay_log(log, delay=1e-9)

		# 		if saveVideo:
		# 			self.video_capture()
		self.quit([])


class DemoVR(BulletPhysicsVR):

	# Still use current logging by myself to record grasp events
	def __init__(self, pybullet, task):

		super().__init__(pybullet, task)
		self.pr2_gripper = 2
		self.completed_task = {}
		self.obj_cnt = 0
		self.container = 19

	def create_scene(self, flag):
		"""
		Basic scene needed for running tasks
		"""
		load_status = -1
		while load_status < 0:
			if flag:
				load_status = self.p.connect(self.p.SHARED_MEMORY)
			else:
				load_status = self.p.connect(self.p.GUI)
		# self.p.resetSimulation()       # Comment out the reset simulation to provide entire control and access to obj info...
		self.p.setGravity(0, 0, -9.81)
		self.obj_cnt = self.p.getNumBodies()
		if flag:
			for obj in self.task:
				self.p.loadURDF(*obj)

	def record(self, file):

		self.create_scene(1)
		try:
			# Record everything
			bodyLog = self.p.startStateLogging(self.p.STATE_LOGGING_GENERIC_ROBOT,
				'../examples/pybullet/generic.' + file)

			# ctrlLog = self.p.startStateLogging(self.p.STATE_LOGGING_VR_CONTROLLERS, 
			# 	file + '_ctrl')
			logIds = [bodyLog]

			while True:

				self._check_task()

				events = self.p.getVREvents()
				for e in (events):
					if (e[self.BUTTONS][1] & self.p.VR_BUTTON_WAS_TRIGGERED):
						self.p.addUserDebugText('One Task Completed', (1.7, 0, 1), (255, 0, 0), 12, 10)



		except KeyboardInterrupt:
			self.quit(logIds)

	def replay(self, file, saveVideo=0):
		self.create_scene(0)
		self.p.setRealTimeSimulation(0)

		# Sorry, but must follow the same order of initialization as in compiled executable demo
		objects = [self.p.loadURDF("plane.urdf", 0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,1.000000)]
		objects = [self.p.loadURDF("samurai.urdf", 0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,1.000000)]
		objects = [self.p.loadURDF("pr2_gripper.urdf", 0.500000,0.300006,0.700000,-0.000000,-0.000000,-0.000031,1.000000)]
		pr2_gripper = objects[0]

		jointPositions = [ 0.550569, 0.000000, 0.549657, 0.000000 ]
		for jointIndex in range (self.p.getNumJoints(pr2_gripper)):
			self.p.resetJointState(pr2_gripper,jointIndex,jointPositions[jointIndex])

		objects = [self.p.loadURDF("kuka_iiwa/model_vr_limits.urdf", 1.400000,-0.200000,0.600000,0.000000,0.000000,0.000000,1.000000)]
		kuka = objects[0]
		jointPositions = [ -0.000000, -0.000000, 0.000000, 1.570793, 0.000000, -1.036725, 0.000001 ]
		for jointIndex in range (self.p.getNumJoints(kuka)):
			self.p.resetJointState(kuka,jointIndex,jointPositions[jointIndex])
			self.p.setJointMotorControl2(kuka,jointIndex,self.p.POSITION_CONTROL,jointPositions[jointIndex],0)

		objects = [self.p.loadURDF("lego/lego.urdf", 1.000000,-0.200000,0.700000,0.000000,0.000000,0.000000,1.000000)]
		objects = [self.p.loadURDF("lego/lego.urdf", 1.000000,-0.200000,0.800000,0.000000,0.000000,0.000000,1.000000)]
		objects = [self.p.loadURDF("lego/lego.urdf", 1.000000,-0.200000,0.900000,0.000000,0.000000,0.000000,1.000000)]

		objects = self.p.loadSDF("gripper/wsg50_one_motor_gripper_new_free_base.sdf")
		kuka_gripper = objects[0]
		self.p.resetBasePositionAndOrientation(kuka_gripper,[0.923103,-0.200000,1.250036],[-0.000000,0.964531,-0.000002,-0.263970])
		jointPositions = [ 0.000000, -0.011130, -0.206421, 0.205143, -0.009999, 0.000000, -0.010055, 0.000000 ]
		for jointIndex in range (self.p.getNumJoints(kuka_gripper)):
			self.p.resetJointState(kuka_gripper,jointIndex,jointPositions[jointIndex])
			self.p.setJointMotorControl2(kuka_gripper,jointIndex,self.p.POSITION_CONTROL,jointPositions[jointIndex],0)
		kuka_cid = self.p.createConstraint(kuka, 6, kuka_gripper, 0, self.p.JOINT_FIXED, [0,0,0], [0,0,0.05], [0,0,0], childFrameOrientation=[0, 0, 0, 1])

		objects = [self.p.loadURDF("jenga/jenga.urdf", 1.300000,-0.700000,0.750000,0.000000,0.707107,0.000000,0.707107)]
		objects = [self.p.loadURDF("jenga/jenga.urdf", 1.200000,-0.700000,0.750000,0.000000,0.707107,0.000000,0.707107)]
		objects = [self.p.loadURDF("jenga/jenga.urdf", 1.100000,-0.700000,0.750000,0.000000,0.707107,0.000000,0.707107)]
		objects = [self.p.loadURDF("jenga/jenga.urdf", 1.000000,-0.700000,0.750000,0.000000,0.707107,0.000000,0.707107)]
		objects = [self.p.loadURDF("jenga/jenga.urdf", 0.900000,-0.700000,0.750000,0.000000,0.707107,0.000000,0.707107)]
		objects = [self.p.loadURDF("jenga/jenga.urdf", 0.800000,-0.700000,0.750000,0.000000,0.707107,0.000000,0.707107)]
		objects = [self.p.loadURDF("table/table.urdf", 1.000000,-0.200000,0.000000,0.000000,0.000000,0.707107,0.707107)]
		objects = [self.p.loadURDF("teddy_vhacd.urdf", 1.050000,-0.500000,0.700000,0.000000,0.000000,0.707107,0.707107)]
		objects = [self.p.loadURDF("cube_small.urdf", 0.950000,-0.100000,0.700000,0.000000,0.000000,0.707107,0.707107)]
		objects = [self.p.loadURDF("sphere_small.urdf", 0.850000,-0.400000,0.700000,0.000000,0.000000,0.707107,0.707107)]
		objects = [self.p.loadURDF("duck_vhacd.urdf", 0.850000,-0.400000,0.900000,0.000000,0.000000,0.707107,0.707107)]
		objects = self.p.loadSDF("kiva_shelf/model.sdf")
		self.container = objects[0]
		self.p.resetBasePositionAndOrientation(ob,[0.000000,1.000000,1.204500],[0.000000,0.000000,0.000000,1.000000])
		objects = [self.p.loadURDF("teddy_vhacd.urdf", -0.100000,0.600000,0.850000,0.000000,0.000000,0.000000,1.000000)]
		objects = [self.p.loadURDF("sphere_small.urdf", -0.100000,0.955006,1.169706,0.633232,-0.000000,-0.000000,0.773962)]
		objects = [self.p.loadURDF("cube_small.urdf", 0.300000,0.600000,0.850000,0.000000,0.000000,0.000000,1.000000)]
		objects = [self.p.loadURDF("table_square/table_square.urdf", -1.000000,0.000000,0.000000,0.000000,0.000000,0.000000,1.000000)]
		ob = objects[0]
		jointPositions = [ 0.000000 ]
		for jointIndex in range (self.p.getNumJoints(ob)):
			self.p.resetJointState(ob,jointIndex,jointPositions[jointIndex])

		objects = [self.p.loadURDF("husky/husky.urdf", 2.000000,-5.000000,1.000000,0.000000,0.000000,0.000000,1.000000)]
		ob = objects[0]
		jointPositions = [ 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000 ]
		for jointIndex in range (self.p.getNumJoints(ob)):
			self.p.resetJointState(ob,jointIndex,jointPositions[jointIndex])

		for obj in self.task:
			self.p.loadURDF(*obj)

		# Setup the camera 
		self.p.resetDebugVisualizerCamera(self.FOCAL_LENGTH, self.YAW, 
			self.PITCH, self.FOCAL_POINT)

		log = self.parse_log('generic.' + file, verbose=False)
		self.replay_log(log, delay=0)
			
				# if saveVideo:
				# 	self.video_capture()
		self.quit([])

	def _check_task(self):
		# Only check boundaries for objects in task
		for obj in range(self.obj_cnt, self.p.getNumBodies()):
			if obj not in self.completed_task:

				base = self.p.getBasePositionAndOrientation(self.container)[0]
				obj_pos = self.p.getBasePositionAndOrientation(obj)[0]
				shape_dim = self.p.getVisualShapeData(self.container)[0][3]
				bound = (base, shape_dim)
				print(bound)
				if self._fit_boundary(obj_pos, bound):
					self.completed_task[obj] = True
					self.p.addUserDebugText('Finished', obj_pos, [255, 0, 0], lifeTime=5.)

	def _fit_boundary(self, position, boundary):

		return all([(boundary[0][i] - boundary[1][i] / 2) <= position[i]\
			<= (boundary[0][i] + boundary[1][i] / 2)  for i in range(3)])

			



