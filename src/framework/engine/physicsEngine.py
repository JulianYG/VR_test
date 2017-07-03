#!/usr/bin/env/ python

import pybullet as p
import numpy as np
import os, time
import os.path as osp
from .base import FakeEngine
from ..utils import util
from ..utils.io_util import (FONT,
                             parse_log,
                             loginfo,
                             logerr)

__author__ = 'Julian Gao'
__email__ = 'julianyg@stanford.edu'
__license__ = 'private'
__version__ = '0.1'


class GazeboEngine(FakeEngine):
    pass


class MujocoEngine(FakeEngine):
    pass


class BulletPhysicsEngine(FakeEngine):
    """
    
    """
    STATUS = \
        ['running', 'pending', 'stopped',
         'killed', 'finished', 'error']

    JOINT_TYPES = {
        0: 'revolute', 1: 'prismatic', 2: 'spherical',
        3: 'planar', 4: 'fixed',
        5: 'point2point', 6: 'gear'}

    INV_JOINT_TYPES = \
        dict(revolute=0, prismatic=1, spherical=2,
             planar=3, fixed=4, point2point=5, gear=6)

    FRAME_TYPES = dict(off=0, gui=1, cmd=2, vr=3, udp=4, tcp=5)

    DISP_CONF = dict(gui_panel=1,
                     shadow=2,
                     wire_frame=3,
                     vr_teleporting=4,
                     vr_picking=5,
                     vr_render_controllers=6,
                     rendering=7,
                     # 8: Wait for pybullet
                     keyboard_shortcut=9,
                     mouse_picking=10)

    def __init__(self, e_id, max_run_time,
                 job='run', video=False,
                 async=False, step_size=0.001,
                 log_dir=''):
        """
        Initialize the physics engine.
        :param async: boolean: indicate if run 
        asynchronously with real world
        :param max_run_time: maximum running time.
        Should be integer of number of time steps if 
        async, and can be float of time lapse seconds 
        if synced.
        :param frame: the simulation frame, choose string 
        among 'vr, gui, cmd (non-gui), upd, or tcp'.
        :param step_size: time step size (float) for each 
        simulation step
        :param job: specify the run, choose string among
        'run, record, and replay'
        """
        self._version = 'perls version {}, bullet version {}'.\
            format(__version__, p.getAPIVersion())
        self._real_time = not async

        # physics server id, a.k.a. simulation id.
        # Indicates which bullet physics simulation server to
        # connect to. Default is 0
        self.engine_id = e_id
        self._physics_server_id = 0
        if async:
            self._step_size = step_size
            if not isinstance(max_run_time, int):
                logerr('Need to specify integer max time steps '
                      'for asynchronous simulation!', FONT.control)
                return
            self._max_run_time = int(max_run_time)
            self._step_count = 0
        else:
            self._step_size = None
            self._max_run_time = max_run_time
        self._job = job
        self._status = BulletPhysicsEngine.STATUS[1]

        self._error_message = list()
        self._record_video = video
        self._logging_id = list()

        self._record_name = 'perls_record'

        # Initialize logging paths
        log_dir = log_dir or \
            osp.abspath(osp.join(osp.dirname(__file__), '../../log'))
        self._log_path = dict(
            device=osp.join(log_dir, 'device'),
            trajectory=osp.join(log_dir, 'trajectory'),
            video=osp.join(log_dir, 'video')
        )
        # If not exist, create the paths
        for path in self._log_path.values():
            if not osp.exists(path):
                os.makedirs(path)

    @property
    def version(self):
        return p.getAPIVersion()

    @property
    def info(self):
        """
        Get the basic info description of the world.
        :return: A dictionary of information of this 
        world.
        {version/name, status, real time, id,
        step size (if async), running job, camera info,
        log info, record file name, max running time}
        """
        info_dic = dict(
            name='{}\t{}'.format(
                self.__class__,
                self.version),
            status=self.status,
            real_time=self._real_time,
            id=self.engine_id,
            job=self._job,
            record_name=self._record_name,
            log_info=self._log_path,
            camera_info=self.camera
            if self._status == 'running' else {},
            max_run_time=self._max_run_time)
        if not self._real_time:
            info_dic['step_size'] = self._step_size
        return info_dic

    @property
    def status(self):
        return self._status

    @property
    def camera(self):
        info = p.getDebugVisualizerCamera(self._physics_server_id)
        return dict(
            frame_width=info[0], frame_height=info[1],
            view_mat=np.array(info[2], dtype=np.float32).reshape((4, 4)),
            projection_mat=np.array(info[3], dtype=np.float32).reshape((4, 4)),
            up=np.where(info[4])[0][0],
            yaw=info[8], pitch=info[9], focal_len=info[11],
            focus=info[12],
        )

    @property
    def record_name(self):
        """
        Get the base name string of record file, either
        to save to or load from
        :return: String
        """
        return self._record_name

    @status.setter
    def status(self, stat):
        self._status = stat

    @camera.setter
    def camera(self, params):
        p.resetDebugVisualizerCamera(
            params['distance'],
            params['yaw'],
            params['pitch'],
            params['focus'],
            self._physics_server_id)

    @record_name.setter
    def record_name(self, name):

        # If name is empty string, use default name still
        self._record_name = name or self._record_name

    ###
    # General environment related methods
    def configure_environment(self, gravity, *_):
        p.setGravity(0., 0., - gravity * 9.8, self._physics_server_id)

    def load_asset(self, file_path,
        pos, orn, fixed):
        uid = -1
        try:
            if osp.basename(file_path).split('.')[1] == 'urdf':
                uid = p.loadURDF(file_path,
                                 basePosition=pos, baseOrientation=orn,
                                 useFixedBase=fixed, physicsClientId=self._physics_server_id)
            elif osp.basename(file_path).split('.')[1] == 'sdf':
                uid = p.loadSDF(file_path, physicsClientId=self._physics_server_id)[0]
                p.resetBasePositionAndOrientation(
                    uid, pos, orn, physicsClientId=self._physics_server_id)
                if fixed:
                    p.createConstraint(
                        uid, -1, -1, -1, p.JOINT_FIXED,
                        [0., 0., 0.], [0., 0., 0.], [0., 0., 0.],
                        physicsClientId=self._physics_server_id)
            # Leave other possible formats for now

            joints = list(range(p.getNumJoints(uid, physicsClientId=self._physics_server_id)))
            links = [-1] + joints
            return int(uid), links, joints
        except p.error:
            self.status = BulletPhysicsEngine.STATUS[-1]
            self._error_message.append(p.error.message)

    ###
    # Body related methods
    def get_body_scene_position(self, uid):
        return np.array(p.getBasePositionAndOrientation(
            uid, physicsClientId=self._physics_server_id)[0])

    def get_body_scene_orientation(self, uid, type):

        orn = p.getBasePositionAndOrientation(
            uid, physicsClientId=self._physics_server_id)[1]
        if type == 'quaternion':
            return np.array(orn)
        elif type == 'euler':
            return np.array(p.getEulerFromQuaternion(orn))
        else:
            loginfo('Unrecognized orientation form.', FONT.ignore)

    def get_body_camera_position(self):

        return None

    def get_body_camera_orientation(self, uid, type):

        return None

    def set_body_scene_pose(self, uid, pos, orn):
        status = 0
        try:
            p.resetBasePositionAndOrientation(
                uid, pos, orn, physicsClientId=self._physics_server_id)
        except p.error:
            status = -1
            logerr('BulletPhysicsEngine captured exception: ' + \
                  p.error.message, FONT.model)
            self.status = BulletPhysicsEngine.STATUS[-1]
            self._error_message.append(p.error.message)
        return status

    def get_body_name(self, uid):
        _, name_str = p.getBodyInfo(
            int(uid), physicsClientId=self._physics_server_id)
        if isinstance(name_str, bytes):
            name_str = name_str.decode('utf-8')
        return name_str

    def get_link_name(self, uid, lid):
        try:
            if lid == -1:
                link_str, _ = p.getBodyInfo(
                    uid, physicsClientId=self._physics_server_id)
            else:
                # Note link_0 is the base link
                link_str = p.getJointInfo(
                    uid, lid, physicsClientId=self._physics_server_id)[-1]
            if isinstance(link_str, bytes):
                link_str = link_str.decode('utf-8')
            return str(link_str)
        except p.error:
            self.status = BulletPhysicsEngine.STATUS[-1]
            self._error_message.append(p.error.message)

    def get_body_visual_shape(self, uid):
        return p.getVisualShapeData(
            uid, physicsClientId=self._physics_server_id)

    def set_body_visual_shape(
            self, uid, texture, qid, shape_id=p.GEOM_BOX,
            rgba_color=(1,1,1,1), spec_color=(1,1,1)):
        try:
            texture_id = p.loadTexture(texture, self._physics_server_id)
            p.changeVisualShape(
                uid, qid, shape_id, texture_id, rgba_color,
                spec_color, physicsClientId=self._physics_server_id)
            return texture_id
        except p.error:
            self.status = BulletPhysicsEngine.STATUS[-1]
            self._error_message.append(p.error.message)

    def change_loaded_texture(self, texture_id, pixels, w, h):
        p.changeTexture(texture_id, pixels, w, h, self._physics_server_id)

    def get_body_linear_velocity(self, uid):
        return np.array(p.getBaseVelocity(
            uid, physicsClientId=self._physics_server_id)[0])

    def set_body_linear_velocity(self, uid, vel):
        try:
            return p.resetBaseVelocity(
                uid, linearVelocity=vel, physicsClientId=self._physics_server_id)
        except p.error:
            self.status = BulletPhysicsEngine.STATUS[-1]
            self._error_message.append(p.error.message)

    def get_body_angular_velocity(self, uid):
        return np.array(p.getBaseVelocity(
            uid, physicsClientId=self._physics_server_id)[1])

    def set_body_angular_velocity(self, uid, vel):
        try:
            return p.resetBaseVelocity(
                uid, angularVelocity=vel, physicsClientId=self._physics_server_id)
        except p.error:
            self.status = BulletPhysicsEngine.STATUS[-1]
            self._error_message.append(p.error.message)

    def get_body_link_state(self, uid, lid):
        return tuple(
            [np.array(vec) for
             vec in p.getLinkState(
                uid, lid, 1, physicsClientId=self._physics_server_id)])

    def get_body_joint_info(self, uid, jid):
        info =list(p.getJointInfo(uid, jid, physicsClientId=self._physics_server_id))
        info[2] = BulletPhysicsEngine.JOINT_TYPES[info[2]]
        return tuple(info)

    def get_body_joint_state(self, uid, jid):
        p.enableJointForceTorqueSensor(uid, jid, 1, physicsClientId=self._physics_server_id)
        return p.getJointState(uid, jid, physicsClientId=self._physics_server_id)

    def set_body_joint_state(self, uid, jids, vals, ctype, kwargs):
        if isinstance(jids, int):
            jids = [jids]
        if isinstance(vals, int):
            vals = [vals]
        try:
            assert(len(jids) == len(vals)), \
                'In <set_body_joint_state>: Number of joints mismatches number of values'

            if not self._real_time:
                assert(ctype == 'position'), \
                'Reset joint states currently only supports position control'
                for jid, val in zip(jids, vals):
                    p.resetJointState(
                        uid, jid, targetValue=val, targetVelocity=0.,
                        physicsClientId=self._physics_server_id)
            else:
                if ctype == 'position':
                    p.setJointMotorControlArray(uid, jointIndices=jids,
                                                controlMode=p.POSITION_CONTROL,
                                                targetPositions=vals,
                                                targetVelocities=(0.,) * len(jids),
                                                physicsClientId=self._physics_server_id,
                                                **kwargs)
                elif ctype == 'velocity':
                    p.setJointMotorControlArray(uid, jointIndices=jids,
                                                controlMode=p.VELOCITY_CONTROL,
                                                targetVelocities=vals,
                                                physicsClientId=self._physics_server_id
                                                **kwargs)
                elif ctype == 'torque':
                    p.setJointMotorControlArray(uid, jointIndices=jids,
                                                controlMode=p.TORQUE_CONTROL,
                                                physicsClientId=self._physics_server_id,
                                                forces=vals, **kwargs)
        except AssertionError or p.error:
            self.status = BulletPhysicsEngine.STATUS[-1]
            if p.error:
                self._error_message.append(p.error.message)

    def get_body_dynamics(self, uid, lid):
        return p.getDynamicsInfo(uid, lid, physicsClientId=self._physics_server_id)

    def set_body_dynamics(self, uid, lid, info):
        """
        
        :param uid: 
        :param lid: 
        :param info: 
        :return: 0 if success, -1 for failure
        """
        status = 0
        try:
            if 'mass' in info:
                p.changeDynamics(uid, lid, mass=info['mass'],
                                 physicsClientId=self._physics_server_id)
            if 'lateral_friction' in info:
                p.changeDynamics(uid, lid,
                                 lateralFriction=info['lateral_friction'],
                                 physicsClientId=self._physics_server_id)
            if 'spinning_friction' in info:
                p.changeDynamics(uid, lid,
                                 spinningFriction=info['spinning_friction'],
                                 physicsClientId=self._physics_server_id)
            if 'rolling_friction' in info:
                p.changeDynamics(uid, lid,
                                 rollingFriction=info['rolling_friction'],
                                 physicsClientId=self._physics_server_id)
            if 'restitution' in info:
                p.changeDynamics(uid, lid,
                                 restitution=info['restitution'],
                                 physicsClientId=self._physics_server_id)
        except p.error:
            status = -1
            logerr('BulletPhysicsEngine captured exception: ' + \
                  p.error.message, FONT.model)
            self.status = BulletPhysicsEngine.STATUS[-1]
            self._error_message.append(p.error.message)
        return status

    def get_body_bounding_box(self, uid, lid):
        return p.getAABB(uid, linkIndex=lid, physicsClientId=self._physics_server_id)

    def get_body_contact_info(self, uid, lid):

        contacts = p.getContactPoints(bodyA=uid, linkIndexA=lid,
                                      physicsClientId=self._physics_server_id)
        contact_dic = []
        for contact in contacts:
            contact_dic.append(
                dict(uid=contact[2],
                     lid=contact[4],
                     posA=contact[5],   # Vec3
                     posB=contact[6],   # Vec3
                     normalB2A=contact[7],  # Vec3
                     distance=contact[8],   # Scalar
                     force=contact[9]) # Scalar
            )
        return contact_dic

    def get_body_surroundings(self, uidA, lidA, uidB, lidB, dist):

        neighbors = p.getClosestPoints(
            bodyA=uidA, bodyB=uidB,
            distance=dist,
            linkIndexA=lidA,
            linkIndexB=lidB,
            physicsClientId=self._physics_server_id
        )
        neighbor_dic = []
        for neighbor in neighbors:
            neighbor_dic.append(
                dict(uid=neighbor[2],
                     lid=neighbor[4],
                     posA=neighbor[5],  # Vec3
                     posB=neighbor[6],  # Vec3
                     distance=neighbor[8])  # Scalar
            )
        return neighbor_dic

    def add_body_text_marker(self, text, pos, font_size, color,
                             uid, lid, time):
        mid = p.addUserDebugText(
            text, pos, textColorRGB=tuple(color),
            textSize=float(font_size),
            lifeTime=time,
            # Not using textOrientation for now
            parentObjectUniqueId=uid,
            parentLinkIndex=lid,
            physicsClientId=self._physics_server_id)
        return mid

    def remove_body_text_marker(self, marker_id):
        p.removeUserDebugItem(marker_id,
                              physicsClientId=self._physics_server_id)

    def apply_force_to_body(self, uid, lid, force, pos, ref):
        try:
            if ref == 'abs':
                p.applyExternalForce(uid, lid, force, pos, p.WORLD_FRAME,
                                     physicsClientId=self._physics_server_id)
            elif ref == 'rel':
                p.applyExternalForce(uid, lid, force, pos, p.LINK_FRAME,
                                     physicsClientId=self._physics_server_id)
            else:
                loginfo('Unrecognized reference frame. Choose abs or rel',
                        FONT.ignore)
        except p.error:
            self.status = BulletPhysicsEngine.STATUS[-1]
            self._error_message.append(p.error.message)

    def apply_torque_to_body(self, uid, lid, torque, pos, ref):
        try:
            if ref == 'abs':
                p.applyExternalTorque(uid, lid, torque, pos, p.WORLD_FRAME,
                                      physicsClientId=self._physics_server_id)
            elif ref == 'rel':
                p.applyExternalTorque(uid, lid, torque, pos, p.LINK_FRAME,
                                      physicsClientId=self._physics_server_id)
            else:
                loginfo('Unrecognized reference frame. Choose abs or rel',
                        FONT.ignore)
        except p.error:
            self.status = BulletPhysicsEngine.STATUS[-1]
            self._error_message.append(p.error.message)

    def get_body_attachment(self, uid):

        attached = list()
        # cid starts from 1
        for cid in range(1, p.getNumConstraints(self._physics_server_id) + 1):
            info = p.getConstraintInfo(cid, physicsClientId=self._physics_server_id)

            if info[2] == uid:
                attached.append({
                    (info[0], cid):
                        dict(
                            parentJointIdx=info[1],
                            childLinkIndex=info[3],
                            type=info[4],
                            jointAxis=info[5],
                            parentJointPvt=info[6],
                            childJointPvt=info[7],
                            parentJointOrn=info[8],
                            childJointOrn=info[9],
                            maxForce=info[10])
                })
        return attached

    def set_body_attachment(self, parent_uid, parent_lid,
                            child_uid, child_lid,
                            jtype='fixed',
                            jaxis=(0., 0., 0.),
                            parent_pos=(0., 0., 0.),
                            child_pos=(0., 0., 0.),
                            **kwargs):
        parent_orn = kwargs.get('parentFrameOrientation', None)
        if parent_orn is None:
            parent_orn = (0., 0., 0., 1)

        child_orn = kwargs.get('childFrameOrientation', None)
        if child_orn is None:
            child_orn = (0., 0., 0., 1)
        try:
            return p.createConstraint(parent_uid, parent_lid,
                                      child_uid, child_lid,
                                      BulletPhysicsEngine.INV_JOINT_TYPES[jtype],
                                      jaxis, tuple(parent_pos), tuple(child_pos),
                                      parentFrameOrientation=tuple(parent_orn),
                                      childFrameOrientation=tuple(child_orn),
                                      physicsClientId=self._physics_server_id)
        except p.error:
            self.status = BulletPhysicsEngine.STATUS[-1]
            self._error_message.append(p.error.message)

    def remove_body_attachment(self, cid):
        p.removeConstraint(cid, physicsClientId=self._physics_server_id)

    def move_body(self, cid, pos, orn, force):
        # Pybullet needs tuple form
        try:
            p.changeConstraint(cid, jointChildPivot=tuple(pos),
                               jointChildFrameOrientation=tuple(orn),
                               maxForce=force,
                               physicsClientId=self._physics_server_id)
        except p.error:
            self.status = BulletPhysicsEngine.STATUS[-1]
            self._error_message.append(p.error.message)

    def delete_body(self, uid):
        p.removeBody(uid, physicsClientId=self._physics_server_id)

    ###
    # Arm related methods
    def solve_ik(self, uid, lid, pos, damping, orn=None):
        if orn is None:
            return p.calculateInverseKinematics(
                uid, lid, pos, jointDamping=damping,
                physicsClientId=self._physics_server_id)
        else:
            return p.calculateInverseKinematics(
                uid, lid, pos, orn, jointDamping=damping,
                physicsClientId=self._physics_server_id)

    def solve_ik_null_space(self, uid, lid, pos,
                            lower, upper, ranges,
                            rest, damping, orn=None):
        if orn is None:
            return p.calculateInverseKinematics(
                uid, lid, pos,
                lowerLimits=tuple(lower), upperLimits=tuple(upper),
                jointRanges=tuple(ranges), restPoses=rest,
                jointDamping=tuple(damping),
                physicsClientId=self._physics_server_id)   
        else:
            return p.calculateInverseKinematics(
                uid, lid, pos, orn,
                lowerLimits=tuple(lower), upperLimits=tuple(upper),
                jointRanges=tuple(ranges), restPoses=rest,
                jointDamping=tuple(damping),
                physicsClientId=self._physics_server_id)

    ###
    # General display related methods

    def _type_check(self, frame):
        """
        Check if frame and async match
        :return: 0 if success, -1 if failure
        """
        if self._real_time:
            if BulletPhysicsEngine.FRAME_TYPES[frame] == 2:
                self.status = BulletPhysicsEngine.STATUS[-1]
                self._error_message.append('CMD mode only supports async simulation.')
                return -1
        return 0

    def get_camera_position(self):
        view_matrix = self.camera['view_mat']
        return np.linalg.inv(view_matrix)[3, :3]

    def load_simulation(self, target_uids):
        if self.status == 'pending':

            # p.setRealTimeSimulation(int(self._real_time), physicsClientId=self._physics_server_id)
            if not self._real_time:
                p.setTimeStep(float(self._step_size), physicsClientId=self._physics_server_id)

            # Set status to running
            self.status = BulletPhysicsEngine.STATUS[0]
            loginfo('Starting simulation server {}, status: {}'.
                    format(self.engine_id, self.status), FONT.warning)

            if self._job == 'record':
                assert self._record_name, \
                    'Must provide record file name!'
                time_stamp = util.get_full_time_stamp()

                # Record only objects that are tracked
                self._logging_id.append(
                    p.startStateLogging(
                        p.STATE_LOGGING_GENERIC_ROBOT,
                        osp.join(self._log_path['trajectory'],
                                 '{}_{}.bin'.format(
                                     self._record_name, time_stamp)),
                        objectUniqueIds=target_uids,
                        physicsClientId=self._physics_server_id
                    )
                )

                # Record mp4 video if indicated
                if self._record_video:
                    self._logging_id.append(
                        p.startStateLogging(
                            p.STATE_LOGGING_VIDEO_MP4,
                            osp.join(self._log_path['video'],
                                     '{}_{}.mp4'.format(
                                         self._record_name, time_stamp)),
                            physicsClientId=self._physics_server_id
                        )
                    )

                # Record the egocentric camera pose
                self._logging_id.append(
                    p.startStateLogging(
                        p.STATE_LOGGING_VR_CONTROLLERS,
                        osp.join(self._log_path['device'],
                                 '{}_{}.bin'.format(
                                     self._record_name, time_stamp)),
                        deviceTypeFilter=p.VR_DEVICE_HMD,
                        physicsClientId = self._physics_server_id
                    )
                )

            elif self._job == 'replay':

                objects = osp.join(self._log_path['trajectory'],
                                      '{}.bin'.format(self._record_name))
                device = osp.join(self._log_path['device'],
                                      '{}.bin'.format(self._record_name))

                # Can change verbosity later
                obj_log = parse_log(self._record_name, verbose=False)

                for record in obj_log:
                    # time_stamp = float(record[1])
                    obj = record[2]
                    pos = record[3: 6]
                    orn = record[6: 10]
                    p.resetBasePositionAndOrientation(obj, pos, orn)
                    n_joints = p.getNumJoints(obj)
                    for i in range(n_joints):
                        jointInfo = p.getJointInfo(obj, i)
                        qid = jointInfo[3]
                        if qid > -1:
                            p.resetJointState(obj, i, record[qid - 7 + 17])

                    # TODO: think about changing delay
                    time.sleep(1e-5)

                # TODO: figure out using HMD log to revive FPS

        else:
            logerr('Cannot start physics engine %d '
                  'in error state.' % self.engine_id, FONT.disp)

    def configure_display(self, frame_args, config):

        if self._type_check(frame_args[0]) == 0:
            # Convert to bullet constant
            frame_args[0] = BulletPhysicsEngine.FRAME_TYPES[frame_args[0]]
            # The core step: connect to bullet physics server
            self._physics_server_id = p.connect(*frame_args)
            p.setInternalSimFlags(0, self._physics_server_id)
            p.resetSimulation(self._physics_server_id)

            for name, switch in config.items():
                p.configureDebugVisualizer(
                    BulletPhysicsEngine.DISP_CONF[name],
                    switch, physicsClientId=self._physics_server_id)

    def update(self, max_steps=1000):
        for _ in range(max_steps):
            p.stepSimulation(self._physics_server_id)

    def step(self, elapsed_time=0):
        if self.status == 'running':
            if not self._real_time:
                if self._step_count < self._max_run_time:
                    p.stepSimulation(self._physics_server_id)
                    self._step_count += 1
                    return False
            else:
                if elapsed_time < self._max_run_time:

                    # TODO: Figure out why this is not useful in <load_simulation>
                    p.setRealTimeSimulation(1, physicsClientId=self._physics_server_id)
                    return False
        return True

    def stop(self):

        # Stop state logging if any
        for lid in self._logging_id:
            p.stopStateLogging(lid, self._physics_server_id)

        # Shutdown simulation
        p.resetSimulation(self._physics_server_id)
        p.disconnect(self._physics_server_id)

        self.status = 'finished'
        loginfo('Physics engine stopped.', FONT.warning)
