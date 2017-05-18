#!/usr/bin/env python
from __future__ import print_function

import pickle
import sys, os
import rospy
import rosparam
import cv2
import intera_interface
from std_msgs.msg import String, Header

#TODO: 
from sensor_msgs.msg import CameraInfo
from geometry_msgs.msg import (
    PoseStamped,
    Pose,
    Point,
    Quaternion,
    Vector3Stamped,
    Vector3
)

import tf
from cv_bridge import CvBridge, CvBridgeError

from os.path import join as pjoin
sys.path.append(pjoin(os.getcwd(), 'ros_'))
from robot import Robot
import time
import numpy as np

rospy.init_node('grasp', anonymous=True)

limb = intera_interface.Limb('right')
gripper = intera_interface.Gripper('right')
arm = Robot(limb, gripper)

# USB Camera matrix 
_UK = np.array([
    [600.153387, 0, 315.459915], 
    [0, 598.015225, 222.933946], 
    [0,          0,          1]
    ], np.float32)

# USB Camera Distortion
_UD = np.array([0.147084, -0.257330, 
    0.003032, -0.006975, 0.000000], np.float32)

class GraspSawyer(object):

    def __init__(self, robot, usbCameraMatrix=None, 
        usbDistortionVector=None, boardSize=(9, 6), 
        checkerSize=0.026, numCalibPoints=10,
        usbCameraIndex=0, stereo=True, gripper_init_pos=None):

        if not stereo and (not gripper_init_pos \
            or usbCameraMatrix is None or usbDistortionVector is None):
            raise Exception('Need to specify gripper position for single camera')

        self._robot = robot
        self.stereo = stereo
        self._calibration_iter = numCalibPoints

        self._usb_intrinsic = usbCameraMatrix
        self._usb_distortion = usbDistortionVector
        self._usb_index = usbCameraIndex

        head_camera_param = rosparam.get_param('/robot_config/'
            'jcb_joint_config/head_pan/head_camera')['intrinsics']

        wrist_camera_param = rosparam.get_param('/robot_config/'
            'jcb_joint_config/right_j5/right_hand_camera')['intrinsics']

        self._head_camera_intrinsic = np.array([
            [head_camera_param[2], 0, head_camera_param[5]], 
            [0, head_camera_param[3], head_camera_param[6]], 
            [0,                    0,                   1]], dtype=np.float32)

        self._wrist_camera_intrinsic = np.array([
            [wrist_camera_param[2], 0, wrist_camera_param[5]], 
            [0, wrist_camera_param[3], wrist_camera_param[6]], 
            [0,                    0,                   1]], dtype=np.float32)

        self._head_camera_distortion = np.array(head_camera_param[-8:], dtype=np.float32)
        self._wrist_camera_distortion = np.array(wrist_camera_param[-8:], dtype=np.float32)

        self._board_size = boardSize
        self._checker_size = checkerSize
        self._numCornerPoints = self._board_size[0] * self._board_size[1]

        self._init_pose = {'right_j6': 3.3161, 'right_j5': 0.57, 'right_j4': 0, 
            'right_j3': 2.18, 'right_j2': -0, 'right_j1': -1.18, 'right_j0': 0.}

        self._usb_camera = cv2.VideoCapture(usbCameraIndex)
        self._robot_camera = intera_interface.Cameras()
        self.tl = tf.TransformListener()

        self.head_camera_corner_points = []
        self.wrist_camera_corner_points = []
        self.usb_camera_corner_points = []

 
        if self.stereo:
            self._usb_intrinsic, self._usb_distortion, \
                self._head_camera_intrinsic, self._head_camera_distortion, \
                self._fundamental = self.calibrate_stereo(self.stereo)
        else:
            self.usb_pxl_translation, self.usb_pxl_invRotation = \
                self._calibrate_external_camera(gripper_init_pos)

        self._inverse_robot_intrinsic = np.linalg.inv(self._head_camera_intrinsic)
        self._inverse_usb_intrinsic = np.linalg.inv(self._usb_intrinsic)

        self._robot.limb.set_joint_position_speed(0.1)
        self._robot.slide_grasp(1)
        # self._robot.limb.move_to_neutral()

    def _calibrate_external_camera(self, gripper_init_pos):

        if not os.path.exists('ros_/calib_data/extern_invR.p') or \
            not os.path.exists('ros_/calib_data/extern_T.p'):
            found = False
            while not found:
                found, usbCamCornerPoints, _ = self._get_external_points()

            gripper_pos = np.zeros((self._board_size[1], self._board_size[0], 3), 
                dtype=np.float32)
            for i in range(self._board_size[1]):
                for j in range(self._board_size[0]):
                    # Use 0.09 for z as approximate height of cubes
                    gripper_pos[i, j] = [gripper_init_pos[0] + i * self._checker_size, 
                        gripper_init_pos[1] + j * self._checker_size, 0.09]

            gripper_pos = np.reshape(gripper_pos, (self._numCornerPoints, 3)).astype(np.float32)

            retval, rvec, tvec = cv2.solvePnP(
                gripper_pos, usbCamCornerPoints, 
                self._usb_intrinsic, self._usb_distortion)

            rotMatrix = cv2.Rodrigues(rvec)[0]
            invRotation = np.linalg.inv(rotMatrix)

            with open('ros_/calib_data/extern_invR.p', 'wb') as ir:
                pickle.dump(invRotation, ir)

            with open('ros_/calib_data/extern_T.p', 'wb') as t:
                pickle.dump(tvec, t)
            
        else:
            with open('ros_/calib_data/extern_invR.p', 'rb') as r:
                invRotation = pickle.load(r)

            with open('ros_/calib_data/extern_T.p', 'rb') as f:
                tvec = pickle.load(f)

        return tvec, invRotation

    def _calibrate_head_camera(self, ):
        pass

    def _calibrate_wrist_camera(self):

        self._get_wrist_camera_points()

        raw_points = np.zeros((self._board_size[1], self._board_size[0], 3), 
                dtype=np.float32)
        for i in range(self._board_size[1]):
            for j in range(self._board_size[0]):
                # Use 0 for z as for lying on the plane
                raw_points[i, j] = [i * self._checker_size, j * self._checker_size, 0.]

        object_points = np.reshape(raw_points, (self._numCornerPoints, 3)).astype(np.float32)

        retval, K, d, rvec, tvec = cv2.calibrateCamera(
            [object_points] * len(self.wrist_camera_corner_points),
            self.wrist_camera_corner_points, (752, 480))

        print(rvec, tvec, K, d)
        return K, d, rvec, tvec

    def _get_wrist_camera_points(self):

        if not self._robot_camera.verify_camera_exists('right_hand_camera'):
            rospy.logerr("Invalid right_hand_camera name, exiting the example.")
        
        self._robot_camera.start_streaming('right_hand_camera')
        self._robot_camera.set_callback('right_hand_camera', self.robot_camera_callback,
            rectify_image=True, callback_args='right_hand_camera')
        try:
            rospy.spin()
        except KeyboardInterrupt:
            rospy.loginfo('Shutting down robot camera corner detection')
            self._robot_camera.stop_streaming('right_hand_camera')


    def calibrate_stereo(self, camera):

        if not os.path.exists('ros_/calib_data/fundamental.p') or \
            (not os.path.exists('ros_/calib_data/sawyer_head_camera.p') or not \
                os.path.exists('ros_/calib_data/usb_camera.p')):
            # Fill in points
            self._get_stereo_points(camera)

            raw_points = np.zeros((self._board_size[1], self._board_size[0], 3), 
                dtype=np.float32)
            for i in range(self._board_size[1]):
                for j in range(self._board_size[0]):
                    # Use 0 for z as for lying on the plane
                    raw_points[i, j] = [i * self._checker_size, j * self._checker_size, 0.]

            object_points = np.reshape(raw_points, (self._numCornerPoints, 3)).astype(np.float32)

            if camera == 'head_camera':
                robot_points = self.head_camera_corner_points
                robot_matrix = self._head_camera_intrinsic
                robot_distortion = self._head_camera_distortion
            elif camera == 'right_hand_camera':
                robot_points = self.wrist_camera_corner_points
                robot_matrix = self._wrist_camera_intrinsic
                robot_distortion = self._wrist_camera_distortion
            else:
                raise NotImplementedError('Invalid camera')

            print((self.usb_camera_corner_points))
            print(robot_points)

            print(len(self.usb_camera_corner_points))
            print(len(robot_points))

            #TODO: Use cornerSubPix
            retVal, k1, d1, k2, d2, R, T, E, F = cv2.stereoCalibrate(
                [object_points] * len(self.usb_camera_corner_points), 
                self.usb_camera_corner_points, 
                robot_points, (640, 480),

                cameraMatrix1=self._usb_intrinsic, 
                distCoeffs1=self._usb_distortion,
                cameraMatrix2=robot_matrix, 
                distCoeffs2=robot_distortion,

                flags=cv2.CALIB_FIX_INTRINSIC + cv2.CALIB_FIX_ASPECT_RATIO +
                                 cv2.CALIB_ZERO_TANGENT_DIST +
                                 cv2.CALIB_SAME_FOCAL_LENGTH +
                                 cv2.CALIB_RATIONAL_MODEL +
                                 cv2.CALIB_FIX_K3 + cv2.CALIB_FIX_K4 + cv2.CALIB_FIX_K5,
            )

            with open('ros_/calib_data/usb_camera.p', 'wb') as fu:
                pickle.dump(k1, fu)
                pickle.dump(d1, fu)

            with open('ros_/calib_data/sawyer_head_camera.p', 'wb') as fs:
                pickle.dump(k2, fs)
                pickle.dump(d2, fs)

            with open('ros_/calib_data/fundamental.p', 'wb') as ff:
                pickle.dump(F, ff)

            with open('ros_/calib_data/rotation.p', 'wb') as ff:
                pickle.dump(R, ff)

            with open('ros_/calib_data/translation.p', 'wb') as ff:
                pickle.dump(T, ff)

        else:
            with open('ros_/calib_data/usb_camera.p', 'rb') as f:
                k1 = pickle.load(f)
                d1 = pickle.load(f)

            with open('ros_/calib_data/sawyer_head_camera.p', 'rb') as r:
                k2 = pickle.load(r)
                d2 = pickle.load(r)

            with open('ros_/calib_data/fundamental.p', 'rb') as f:
                F = pickle.load(f)

            with open('ros_/calib_data/rotation.p', 'rb') as ff:
                R = pickle.load(ff)

            with open('ros_/calib_data/translation.p', 'rb') as ff:
                T = pickle.load(ff)


        print(F, R, T,  k1, d1, k2, d2)
        print(np.array([227, 143,1]).dot(F))
        return k1, d1, k2, d2, F

    def _get_stereo_points(self, camera):

        if not self._robot_camera.verify_camera_exists(camera):
            rospy.logerr("Invalid self._robot_camera name, exiting the example.")
        
        self._robot_camera.start_streaming(camera)
        self._robot_camera.set_callback(camera, self.robot_camera_callback,
            rectify_image=True, callback_args=camera)
        try:
            rospy.spin()
        except KeyboardInterrupt:
            rospy.loginfo('Shutting down robot camera corner detection')
            self._robot_camera.stop_streaming(camera)

    def _get_external_points(self):

        # self._usb_camera.open(self._usb_index)
        s = False
        # Loop until read image
        print('Reading from usb camera...')
        while not s:
            s, img = self._usb_camera.read()

        # Loop until found checkerboard pattern
        print('USB camera finding checkerboard pattern...')
        
        foundPattern, usbCamCornerPoints = cv2.findChessboardCorners(
            img, self._board_size, None, 
            cv2.CALIB_CB_ADAPTIVE_THRESH
        )
        if not foundPattern:
            print('USB camera did not find pattern...')
            return False, None, img

        # self._usb_camera.release()
        return True, usbCamCornerPoints.reshape((self._numCornerPoints, 2)), img

    def robot_camera_callback(self, img_data, camera):
        
        bridge = CvBridge()
        try:
            time_stamp = rospy.Time.now()
            cv_image = bridge.imgmsg_to_cv2(img_data, "bgr8")
            print('Both cameras looking for checkerboard pattern...')
            robotFoundPattern, robot_points = cv2.findChessboardCorners(
                cv_image, self._board_size, None
            )
            #TODO: unsubscribe by itself
            usb_found, usb_points, usb_img = self._get_external_points()

            if not robotFoundPattern or not usb_found:
                raw_input('One camera did not find pattern...'
                    ' Please re-adjust checkerboard position and press Enter.')
                cv2.imwrite('ros_/calib_data/failures/{}.jpg'.format(time_stamp), cv_image)
                return
            elif len(self.head_camera_corner_points) < self._calibration_iter:
                time.sleep(1)
                print('Saving to usb corner points..')
                self.usb_camera_corner_points.append(usb_points)
                print('Saving to sawyer corner points..')
                if camera == 'head_camera':
                    self.head_camera_corner_points.append(np.reshape(robot_points, (self._numCornerPoints, 2)))
                elif camera == 'right_hand_camera':
                    self.wrist_camera_corner_points.append(np.reshape(robot_points, (self._numCornerPoints, 2)))
                cv2.imwrite('ros_/calib_data/camera/{}.jpg'.format(time_stamp), usb_img)
                cv2.imwrite('ros_/calib_data/{}/{}.jpg'.format(camera, time_stamp), cv_image)
                raw_input('Successfully read one point.'
                    ' Re-adjust the checkerboard and press Enter to Continue...')
                return
        except CvBridgeError, err:
            rospy.logerr(err)
            return

    def _usb_cam_to_gripper(self, u, v):

        p = np.array([u, v, 1], dtype=np.float32)

        if self.stereo:
            pixel_location = self._fundamental.dot(p.T)

            # TODO: figure out how to do the image to camera reference frame in sawyer
            if self.tl.frameExists('head_camera') and self.tl.frameExists('right_hand'):
                
                hdr = Header(stamp=self.tl.getLatestCommonTime('head_camera',
                    'right_hand'), frame_id='head_camera')

                # pixel_location = np.array([pixel_location[0], pixel_location[1], 1], 
                #     dtype=np.float32)
                # print(pixel_location, 'pix')

                pixel_location = np.array([689, 582, 1], 
                    dtype=np.float32)

                camera_frame_position = self._inverse_robot_intrinsic.dot(pixel_location)

                print(camera_frame_position, 'camera (world) frame')

                v3s = Vector3Stamped(header=hdr,
                        vector=Vector3(*camera_frame_position))
                gripper_vector = self.tl.transformVector3('right_hand', v3s).vector
                
                return np.array([gripper_vector.x, gripper_vector.y, gripper_vector.z])

        else:
            tempMat = self.usb_pxl_invRotation * self._usb_intrinsic
            tempMat2 = tempMat.dot(p)
            tempMat3 = self.usb_pxl_invRotation.dot(
                np.reshape(self.usb_pxl_translation, 3))

            # approx height of each block + 
            # (inv Rotation matrix * inv Camera matrix * point)
            # inv Rotation matrix * tvec
            s = (.09 + tempMat3[2]) / tempMat2[2]

            # s * [u,v,1] = M(R * [X,Y,Z] - t)  
            # ->   R^-1 * (M^-1 * s * [u,v,1] - t) = [X,Y,Z] 
            temp = self._inverse_usb_intrinsic.dot(s * p)
            temp2 = temp - np.reshape(self.usb_pxl_translation, 3)
            gripper_coords = self.usb_pxl_invRotation.dot(temp2)

            return gripper_coords

    def move_to(self, u, v, z):
        offset_x = 0.007
        offset_y = -0.01
        gripper_coords = self._usb_cam_to_gripper(u, v)
        print(gripper_coords, 'gripper coords')
        self._robot.reach_absolute({'position': (gripper_coords[0]+offset_x, 
            gripper_coords[1]+offset_y, z), 'orientation': (0.707, 0.707, 0, 0)})

    def move_to_with_grasp(self, u, v, hover, dive):        
        self.move_to(u, v, hover)
        time.sleep(0.7)
        self.move_to(u, v, dive + 0.06)
        self._robot.limb.set_joint_position_speed(0.06)
        self.move_to(u, v, dive)
        time.sleep(0.8)
        arm.slide_grasp(0)

    def move_to_with_lift(self, u, v, 
        hover=0.32, dive=0.09, drop=None):

        self.move_to_with_grasp(u, v, hover, dive)
        time.sleep(.75)

        self.move_to(u, v, 0.13)
        time.sleep(0.2)
        self._robot.limb.set_joint_position_speed(0.1)
        if drop:
            self.move_to(u, v, 0.35)
            time.sleep(.75)
            self.move_to(drop[0], drop[1], hover)
        else:
            self.move_to(u, v, 0.35)
            time.sleep(.75)
            # Hardcoded bin
            self._robot.reach_absolute({'position': (0.5713327811387512, 
                0.24199145859810134, 0.35), 
                'orientation': (0.707, 0.707, 0, 0)}) #move_to_neutral()

        time.sleep(.8)
        self._robot.reach_absolute({'position': (0.5713327811387512, 
            0.24199145859810134, 0.23),
            'orientation': (0.707, 0.707, 0, 0)}) #move_to_neutral()
        time.sleep(.8)
        arm.slide_grasp(1)
        time.sleep(0.5)
        self._robot.reach_absolute({'position': (0.5713327811387512, 
            0.24199145859810134, 0.35),
            'orientation': (0.707, 0.707, 0, 0)}) #move_to_neutral()

    def grasp_by_click(self):
        
        def mouse_callback(event, x, y, flags, params):
            if event == 1:
                self.move_to_with_lift(x, y)
        while True:
            try:
                s, img = self._usb_camera.read()
                cv2.namedWindow('grasp-by-click', cv2.CV_WINDOW_AUTOSIZE)
                cv2.setMouseCallback('grasp-by-click', mouse_callback)
                cv2.imshow('grasp-by-click', img)
                cv2.waitKey(1)
            except KeyboardInterrupt:
                cv2.destroyAllWindows()

    def grasp_by_color(self, color='blue'):

        im = self._usb_camera.read()[1]
        im = cv2.bilateralFilter(im,9,75,75)
        im = cv2.fastNlMeansDenoisingColored(im,None,10,10,7,21)
        hsv_img = cv2.cvtColor(im, cv2.COLOR_BGR2HSV) 

        if color == 'blue':
            COLOR_MIN = np.array([110, 50, 50], dtype=np.uint8)
            COLOR_MAX = np.array([130, 255, 255], dtype=np.uint8)

            # Thresholding image
            frame_threshed = cv2.inRange(hsv_img, COLOR_MIN, COLOR_MAX)    

        elif color == 'red':
            COLOR_MIN = np.array([0,50,50], np.uint8)
            COLOR_MAX = np.array([10,255,255], np.uint8)
            mask0 = cv2.inRange(hsv_img, COLOR_MIN, COLOR_MAX)
            
            COLOR_MIN = np.array([170,50,50], np.uint8)
            COLOR_MAX = np.array([180,255,255], np.uint8)
            mask1 = cv2.inRange(hsv_img, COLOR_MIN, COLOR_MAX)
            
            frame_threshed = mask0 + mask1

        elif color == 'yellow':
            # HSV color code lower and upper bounds
            COLOR_MIN = np.array([20, 100, 100], np.uint8)       
            COLOR_MAX = np.array([30, 255, 255], np.uint8)
            
            frame_threshed = cv2.inRange(hsv_img, COLOR_MIN, COLOR_MAX)

        else:
            raise NotImplementedError('Unrecognized color')

        ret, thresh = cv2.threshold(frame_threshed, 127, 255, 0)
        contours, hierarchy = cv2.findContours(thresh, 
            cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        cubePoints = []

        for k, cnt in enumerate(contours):
            x, y, w, h = cv2.boundingRect(cnt)
            # cv2.rectangle(color_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cubePoints.append((x + w / 2., y + h / 2.))

        for cp in cubePoints:
            #TODO: maybe change to grasp
            self.move_to_with_lift(cp[0], cp[1])
            time.sleep(1)

sawyer = GraspSawyer(arm, 
    usbCameraMatrix=_UK, 
    usbDistortionVector=_UD, 
    usbCameraIndex=0,
    boardSize=(9, 6), 
    checkerSize=0.026,
    numCalibPoints=10,
    stereo='', 
    gripper_init_pos=(0.41988895080044875, -0.40558702344362024)
    )
# sawyer.grasp_by_color('red')

sawyer.grasp_by_click()
# sawyer._calibrate_wrist_camera()

# sawyer.move_to(38, 35, 0.2)
# sawyer.calibrate_stereo()


