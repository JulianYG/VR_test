import numpy as np

def get_distance(posA, posB):
	return np.sqrt(np.sum((np.array(posA) - np.array(posB)) ** 2))

class Constant():

	WARNING_HOOK = -1
	VEL_CTRL = 0
	TORQ_CTRL = 1
	POS_CTRL = 2

	ARM = 3
	GRIPPER = 4
	CONSTRAINT = 5

	SHUTDOWN_HOOK = 6
	RESET_HOOK = 7
	START_HOOK = 8
	CTRL_HOOK = 9
	

	HOT_KEYS = [49, 50, 99, 111, 114, 120, 121, 122, 65295, 65296, 65297, 65298]
