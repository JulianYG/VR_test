# !/usr/bin/env python

from .perls_env import PerlsEnv
from lib.utils import math_util


class PushCube(PerlsEnv):
    """
    Pushing cube across the table
    """

    metadata = {
        'render.modes': ['human', 'depth', 'segment'],
        'video.frames_per_second': 50
    }

    def __init__(self, conf_path):

        super(PushCube, self).__init__(conf_path)
        self._cube = self._world.body['cube_0']
        self._robot = self._world.tool['m0']

    def _reset(self):

        super(PushCube, self)._reset()

        for _ in range(200):
            # move robot to initial position
            self._robot.pinpoint(
                (.8, .0, .6),
                math_util.euler2quat(
                    [-math_util.pi, -math_util.pi / 2., 0.]),
                ftype='rel')
            self._world.update()
        print(self._get_relative_pose()[0][0])
        return self._get_relative_pose()

    def _get_relative_pose(self):

        cube_pose_rel = self._cube.get_pose(self._robot.uid, 0)
        eef_pose_rel = self._robot.tool_pose_rel

        return eef_pose_rel, cube_pose_rel

    def _step(self, action):

        # TODO: action should be delta Robot end effector 2D pose, so do bounds clipping and apply action

        # TODO: make sure to go through IK here, since it's not perfect

        # TODO: then read robot state, and get the stuff we care about again. 

        self._world.update()