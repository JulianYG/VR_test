from bullet.control.interface import CtrlInterface
import pybullet as p
import time
import redis
from bullet.util import ARM, GRIPPER
from bullet.util import _RESET_HOOK, _SHUTDOWN_HOOK, _START_HOOK, _CTRL_HOOK

class IVR(CtrlInterface):

	def __init__(self, host, remote):
		# Default settings for camera
		super(IVR, self).__init__(host, remote)

	def client_communicate(self, agent):

		self.socket.connect_with_server()
		control_map, obj_map = agent.create_control_mappings()

		# Let the socket know controller IDs
		self.socket.broadcast_to_server((_CTRL_HOOK, agent.controllers))
		while True:
			# Send to server
			events = p.getVREvents()
			for e in (events):
				self.socket.broadcast_to_server(e)

			# Receive and render from server
			signal = self.socket.listen_to_server()
			for s in signal:
				if s is _SHUTDOWN_HOOK:
					raise KeyboardInterrupt('Server invokes shutdown')
					continue
				if s is _START_HOOK:
					print('Server is online')
					continue
				self._render_from_signal(agent, control_map, obj_map, s)
			time.sleep(0.001)

	def server_communicate(self, agent, scene, task, gui=True):

		self.socket.connect_with_client()

		# First get the controller IDs
		while not agent.controllers:
			events = self.socket.listen_to_client()
			for e in events:
				if isinstance(e, tuple):
					if e[0] is _CTRL_HOOK:
						agent.set_virtual_controller(e[1])
						control_map, obj_map = agent.create_control_mappings()

		skip_flag = agent.redundant_control()

		while True:
			events = self.socket.listen_to_client()
			for e in events:
				# Hook handlers
				if e is _RESET_HOOK:
					print('VR Client connected. Initializing reset...')
					p.setInternalSimFlags(0)
					p.resetSimulation()
					agent.solo = len(agent.arms) == 1 or len(agent.grippers) == 1
					agent.setup_scene(scene, task, gui)
					continue
				if e is _SHUTDOWN_HOOK:
					print('VR Client quit')
					continue
				if isinstance(e, tuple):
					if e[0] is _CTRL_HOOK:
						agent.set_virtual_controller(e[1])
						print('Received VR controller IDs: {}'.format(agent.controllers))
						continue
				if skip_flag:
					if e[0] == agent.controllers[1]:
						break
				agent.control(e, control_map)
			if not gui:
				p.stepSimulation()

			self.socket.broadcast_to_client(self._msg_wrapper(agent, obj_map))

	def local_communicate(self, agent, gui=True):
		control_map, _ = agent.create_control_mappings()
		while True:
			events = p.getVREvents()
			skip_flag = agent.redundant_control()
			for e in (events):
				if skip_flag:
					if e[0] == agent.controllers[1]:
						break
					agent.control(e, control_map)
				else:
					agent.control(e, control_map)
			if not gui:
				p.stepSimulation()

	


