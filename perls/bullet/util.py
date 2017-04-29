import json
import numpy as np

VEL_CTRL = 0
TORQ_CTRL = 1
POS_CTRL = 2

ARM = 3
GRIPPER = 4
CONSTRAINT = 5

_SHUTDOWN_HOOK = 6
_RESET_HOOK = 7
_START_HOOK = 8
_CTRL_HOOK = 9

class IllegalOperation(Exception):
	def __init__(self, link):
		self.link = link


class _WARNING_HOOK(object):
	def __init__(self, c):
		self.content = c

def get_distance(posA, posB):
	return np.sqrt(np.sum((np.array(posA) - np.array(posB)) ** 2))

def read_config(config):
	dic = {}
	with open(config, 'r') as f:
		config = json.load(f)
		for k, v in config.items():
			dic[str(k)] = v
	return dic

def parse_log(filename, verbose=True):

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

