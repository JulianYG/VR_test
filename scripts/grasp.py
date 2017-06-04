#!/usr/bin/env python

__package__ = 'ros_'

import time, os
import sys
import numpy as np

from os.path import join as pjoin
path = os.path.split(os.path.abspath(os.getcwd()))
rpath = '/'.join(path[: path.index('perls') + 1])
sys.path.append(pjoin(rpath, 'src'))

import ros_

from .controller import Controller
from .robot import Robot

import rospy
import intera_interface

rospy.init_node('track')

limb = intera_interface.Limb('right')
gripper = intera_interface.Gripper('right')
limb.set_joint_position_speed(0.2)
robot = Robot(limb, gripper)

ctrlr = Controller(robot, 
	pjoin(os.path.dirname(__file__), '../tools/calib_data/Tracker_inverseRotation.p'),
	pjoin(os.path.dirname(__file__), '../tools/calib_data/Tracker_translation.p'),
	pjoin(os.path.dirname(__file__), '../tools/calib_data/Tracker_intrinsics.p'))

ctrlr.grasp_by_click()
# ctrlr.grasp_by_color('blue red yellow')
# ctrlr.stack()

