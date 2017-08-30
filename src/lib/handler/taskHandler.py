# !/usr/bin/env python

from ..utils import math_util
from ..utils.io_util import loginfo, FONT

__author__ = 'Julian Gao'
__email__ = 'julianyg@stanford.edu'
__license__ = 'private'
__version__ = '0.1'


class Checker(object):
    """
    Check if given task is finished
    """
    def __init__(self, env_name):
        self._name = env_name

        self._states = dict()

    @property
    def name(self):
        return 'TaskCompletionChecker'

    def initialize(self, world):

        """
        Customize world for some fine tunings that
        cannot be specified in env xml file
        :param world: the world object to be setup
        :return: None
        """
        if self._name == 'push_sawyer' or self._name == 'push_kuka':

            table = world.body['table_0']
            # table.mark = {}

            cube_pos = world.body['cube_0'].pos
            robot = world.body['titan_0']

            # Initializes the gripper next to the cube
            initial_gripper_pos = \
                (cube_pos[0] - 0.05, cube_pos[1], cube_pos[2] + 0.025)
            robot.grasp(1)
            robot.tool_pos = (initial_gripper_pos, 300)

            loginfo('Initialize finished.', FONT.model)
            loginfo('Initial joint positions: {}'.
                    format(robot.joint_positions),
                    FONT.model)
            loginfo('Initial gripper finger position: {}'.
                    format(robot.tool_pos),
                    FONT.model)

    def score(self, world):
        """
        Score the current performance of the agent. Generates
        the reward
        :param world: current environment status object
        :return: User defined format of reward
        """
        # TODO
        if self._name == 'push_sawyer' or 'push_kuka':

            return 0

    def check(self, world):

        body_dict = world.body

        if self._name == 'push_sawyer' or 'push_kuka':

            cube = body_dict['cube_0']
            table = body_dict['table_0']

            # If cost too high, mark fail and done
            if -self.score(world) > 200:
                return True, False

            if cube.pos[2] >= 0.69 or cube.pos[2] <= 0.6:
                # If the cube bumps or falls
                return True, False

            # Check if cube is within the boundary
            if 0:

                return True, True

        return False, False

    def stop(self):
        return
