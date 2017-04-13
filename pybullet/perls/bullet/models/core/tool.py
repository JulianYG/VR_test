import pybullet as p
import numpy as np
from bullet.models.core.scene import Scene

class Tool(Scene):

	ARM = 0
	GRIPPER = 1
	CONSTRAINT = 2

	def __init__(self, pos, enableForceSensor):

		super(Tool, self).__init__(enableForceSensor, pos)
		self.THRESHOLD = 1.3
		self.pos = pos

	def add_marker(self, event, tool_id, color=[255,0,0]):
		#TODO
		pass

	def set_force_sensor(self):
		self.has_force_sensor = True

	def set_virtual_controller(self, controllers):
		self.controllers = controllers

	def get_tool_control_deviation(self, tool_id, pos):
		eef_id = p.getNumJoints(tool_id) - 1
		return self._get_distance(p.getLinkState(tool_id, eef_id)[0], pos)

	def redundant_control(self):
		return len(self.controllers) > max(len(self.grippers), 
			len(self.arms), len(self.constraints))

	def create_control_mappings(self):
		control_map = {}
		if self.grippers:
			control_map[self.GRIPPER] = dict(zip(self.controllers, self.grippers))
		if self.arms:
			control_map[self.ARM] = dict(zip(self.controllers, self.arms))
		if self.constraints:
			control_map[self.CONSTRAINT] = dict(zip(self.controllers, 
				self.constraints))
		return control_map

	def set_tool_states(self, tool_ids, vals, ctrl_type='pos'):

		if ctrl_type == 'pos':
			for tool_id, val in zip(tool_ids, vals):
				for jointIndex in range(p.getNumJoints(tool_id)):
					p.setJointMotorControl2(tool_id, jointIndex, p.POSITION_CONTROL,
						targetPosition=pos[jointIndex], targetVelocity=0, positionGain=0.05, 
						velocityGain=1.0, force=self.MAX_FORCE)
		elif ctrl_type == 'vel':
			for tool_id, val in zip(tool_ids, vals):
				for jointIndex in range(p.getNumJoints(tool_id)):
					p.setJointMotorControl2(tool_id, jointIndex, p.VELOCITY_CONTROL,
						targetVelocity=val[jointIndex], force=self.MAX_FORCE)
		else:
			raise NotImplementedError('Cannot recognize current control type: ' + ctrl_type)

	def get_tool_joint_state(self, tool_joint_idx):
		"""
		Given (tool, joint) index tuple, return given joint 
		state of given tool.
		"""
		joint_state = p.getJointState(tool_joint_idx[0], tool_joint_idx[1])
		if self.has_force_sensor:
			return np.array([joint_state[0], joint_state[1], joint_state[2]])
		return np.array([joint_state[0], joint_state[1]])

	def get_tool_joint_states(self, tool_idx):
		"""
		Given tool index, return all joint states of that tool
		"""	
		if isinstance(tool_idx, list):
			joint_states = [[self.get_tool_joint_state((t, 
				i)) for i in range(p.getNumJoints(t))] for t in tool_idx]
		else:
			link_states = [self.get_tool_joint_state((tool_idx, 
				i)) for i in range(p.getNumJoints(tool_idx))]
		return np.array(joint_states)

	def get_tool_link_state(self, tool_link_idx):
		"""
		Returns pos, orn, link_velocity
		Given (tool, joint) index tuple, return given link 
		state of given tool. -1 indicates end effector
		"""
		if tool_link_idx[1] == -1:
			tool_link_idx = (tool_link_idx[0], 
				p.getNumJoints(tool_link_idx[0]) - 1)
		link_state = p.getLinkState(tool_link_idx[0], tool_link_idx[1], 1)
		return np.array([link_state[0], link_state[1], link_state[-2]])

	def get_tool_link_states(self, tool_idx):
		"""
		Returns pos, orn, link_velocity
		Given tool index, return all link states of given tool
		-1 indicates end effector
		"""
		if isinstance(tool_idx, list):
			link_states = [[self.get_tool_link_state((t, 
				i)) for i in range(p.getNumJoints(t))] for t in tool_idx]
		else:
			print(tool_idx)
			link_states = [self.get_tool_link_state((tool_idx, 
				i)) for i in range(p.getNumJoints(tool_idx))]
		return np.array(link_states)

	def get_tool_poses(self, tool_ids, velocity=0):
		return np.array([self.get_tool_pose(t, velocity) for t in tool_ids])

	def _get_distance(self, posA, posB):
		dist = 0.
		for i in range(len(posA)):
			dist += (posA[i] - posB[i]) ** 2
		return dist

	def setup_scene(self, task):
		raise NotImplementedError('Each tool model must re-implement this method.')

	def control(self, event, ctrl_map):
		raise NotImplementedError("Each tool model must re-implement this method.")

	def reach(self, tool_id, eef_pos, eef_orien, fixed):
		raise NotImplementedError('Each tool model must re-implement this method.')

	def grasp(self, gripper, controller_event):
		raise NotImplementedError('Each tool model must re-implement this method.')

	def get_tool_ids(self):
		raise NotImplementedError('Each tool model must re-implement this method.')

	def get_tool_pose(self, tool_id, velocity=0):
		raise NotImplementedError('Each tool model must re-implement this method.')

	def _load_tools(self, pos):
		raise NotImplementedError('Each tool model must re-implement this method.')


	