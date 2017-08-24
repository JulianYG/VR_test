import time
from multiprocessing import Process, Event


class TimedRecorder(Process):

    def __init__(self, interval, func, *args):

        super(TimedRecorder, self).__init__()
        self._interval = interval
        self._func = func
        self.args = args
        self._done = Event()

    def cancel(self):
        """Stop the timer if it hasn't finished yet"""
        self._done.set()

    def run(self):
        if not self._done.is_set():
            while 1:
                old_time = time.time()
                self._func(*self.args)
                interval = time.time() - old_time
                if self._interval > interval:
                    time.sleep(self._interval - interval)


def pause(t):
    time.sleep(t)


def get_abs_time():

    return time.time()


def get_time_stamp():
    return time.strftime('%H:%M:%s', time.localtime())


def get_full_time_stamp():

    return time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())


def get_elapsed_time(start=None):

    if start > 0:
        # Pack into some human readable form
        return time.time() - start
    else:
        return 0.

