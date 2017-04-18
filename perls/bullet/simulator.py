import pybullet as p
import numpy as np
import os, struct, time
from datetime import datetime
from time import strftime
from matplotlib import pyplot as plt
from os.path import join as pjoin

class BulletSimulator(object):

	def __init__(self, model, interface):
		# Default settings for camera
		self.FOCAL_POINT = (0., 0., 0.)
		self.YAW = 35.
		self.PITCH = 50.
		self.ROLL = 0.
		self.FOCAL_LENGTH = 5.
		self.UP_AX_IDX = 2
		self.viewMatrix = None
		self.projectionMatrix = None

		self.logIds = []
		self._interface = interface
		self.model = model
		self.VIDEO_DIR = pjoin(os.getcwd(), 'data', 'video')
		self.TRAJECTORY_LOG_DIR = pjoin(os.getcwd(), 'data', 'record', 'trajectory')
		self.CONTROL_LOG_DIR = pjoin(os.getcwd(), 'data', 'record', 'control')
		self.CONTACT_LOG_DIR = pjoin(os.getcwd(), 'data', 'record', 'contact')

	def setup(self, task, flag, vr):
		if not self.model.reset(flag, vr):
			if vr:
				raise Exception('Cannot detect running VR application. Please try again.')
			else:
				raise Exception('Cannot create pybullet GUI instance. Please try again.')
		self.model.setup_scene(task)

	def run(self, file='', record=False, video=False):
		try:
			if record:
				file += '_' + datetime.now().strftime('%m-%d-%H-%M-%S')
				if video:
					# Does logging only need to be called once with SharedMemory? 
					self.logIds.append(p.startStateLogging(p.STATE_LOGGING_VIDEO_MP4, 
						pjoin(self.VIDEO_DIR, file + '.mp4')))
				else:
					# Record everything
					self.logIds.append(p.startStateLogging(p.STATE_LOGGING_GENERIC_ROBOT,
						pjoin(self.TRAJECTORY_LOG_DIR, 'traj.' + file)))
					self.logIds.append(p.startStateLogging(p.STATE_LOGGING_VR_CONTROLLERS, 
						pjoin(self.CONTROL_LOG_DIR, 'ctrl.' + file)))
					self.logIds.append(p.startStateLogging(p.STATE_LOGGING_CONTACT_POINTS,
						pjoin(self.CONTACT_LOG_DIR, 'cont.' + file)))

			self._interface.communicate(self.model)

		except KeyboardInterrupt:
			self.quit()		

	def playback(self, file, delay=0.0001):
		p.resetDebugVisualizerCamera(cameraDistance=self.FOCAL_LENGTH, 
			cameraYaw=self.YAW, cameraPitch=self.PITCH, 
			cameraTargetPosition=self.FOCAL_POINT)
		log = self.parse_log(pjoin(self.TRAJECTORY_LOG_DIR, 'traj.' + file), verbose=True)
		self.replay_log(log, delay=delay)
		self.quit()

	def set_camera_view(self, targetPosX, targetPosY, targetPosZ, roll, 
		pitch, yaw, dist, width=600, height=540):
		"""
		Set the view of camera; typically egocentric, or oblique
		"""
		self.FOCAL_POINT = (targetPosX, targetPosY,  targetPosZ)
		self.PITCH = pitch
		self.ROLL = roll
		self.YAW = yaw
		self.FOCAL_LENGTH = dist
		self.image_width = width
		self.image_height = height
		self.viewMatrix = p.computeViewMatrixFromYawPitchRoll((targetPosX, targetPosY, targetPosZ), 
			dist, yaw, pitch, roll, self.UP_AX_IDX)
		self.projectionMatrix = p.computeProjectionMatrixFOV(60, float(width) / height, .01, 1000.)

	def snapshot(self, show=False):
		img_arr = p.getCameraImage(self.image_width, self.image_height, 
			self.viewMatrix, self.projectionMatrix)
		np_img = np.reshape(img_arr[2], (img_arr[1], img_arr[0], 4)) / 255.
		if show:
			plt.imshow(np_img)
		return np_img

	def parse_log(self, filename, verbose=True):

	  	f = open(filename, 'rb')
	  	print('Opened'),
	  	print(filename)

	  	keys = f.readline().decode('utf8').rstrip('\n').split(',')
	  	fmt = f.readline().decode('utf8').rstrip('\n')

	  	# The byte number of one record
	  	sz = struct.calcsize(fmt)
	  	# The type number of one record
	  	ncols = len(fmt)

	  	if verbose:
	  		print('Keys:'), 
	  		print(keys)
	  		print('Format:'),
	  		print(fmt)
	  		print('Size:'),
	  		print(sz)
	  		print('Columns:'),
	  		print(ncols)

	  	# Read data
	  	wholeFile = f.read()
	  	# split by alignment word
	  	chunks = wholeFile.split(b'\xaa\xbb')
	  	log = list()
	  	for chunk in chunks:
		    if len(chunk) == sz:
		      	values = struct.unpack(fmt, chunk)
		      	record = list()
		      	for i in range(ncols):
		        	record.append(values[i])
		      	log.append(record)

	  	return log

	def replay_log(self, log, delay=0.0005):

		for record in log:
			time_stamp = float(record[1])
			obj = record[2]
			pos = record[3: 6]
			orn = record[6: 10]
			p.resetBasePositionAndOrientation(obj, pos, orn)
			numJoints = p.getNumJoints(obj)
			for i in range(numJoints):
				jointInfo = p.getJointInfo(obj, i)
				qIndex = jointInfo[3]
				if qIndex > -1:
					p.resetJointState(obj, i, record[qIndex - 7 + 17])
			time.sleep(delay)

	def quit(self):
		"""
		Perform clean up before exit
		"""
		if self.logIds:
			for Id in self.logIds:
				p.stopStateLogging(Id)
		if self._interface:
			self._interface.close_socket()
		p.resetSimulation()
		p.disconnect()
