import sys


class Dbg():
    def __init__(self, verbose):
        self._verbose = verbose
        self._bargraph_msg = None
        self._bargraph_min = None
        self._bargraph_max = None
        self._newline = True

    def debug(self, msg, level=2):
        if self._verbose >= level:
            if not self._newline:
                sys.stderr.write('\n')
                self._newline = True
            sys.stderr.write('%s\n' % msg)
            sys.stderr.flush()

    def msg(self, msg, level=1):
        if self._verbose >= level:
            if not self._newline:
                sys.stderr.write('\n')
                self._newline = True
            sys.stderr.write('%s\n' % msg)
            sys.stderr.flush()

    def bargraph_start(self, msg, value_min=0, value_max=100, level=1):
        if self._verbose >= level:
            self._bargraph_msg = msg
            self._bargraph_min = value_min
            self._bargraph_max = value_max
            if not self._newline:
                sys.stderr.write('\n')
                self._newline = False
            sys.stderr.write('%s: %3d%%' % (self._bargraph_msg, 1))
            sys.stderr.flush()
            self._newline = False
        elif self._bargraph_msg:
            self.bargraph_done()

    def bargraph_update(self, value=0, percent=None):
        if self._bargraph_msg:
            if percent is None:
                percent = 100 * (value - self._bargraph_min) / (self._bargraph_max - self._bargraph_min)
            sys.stderr.write('\r%s: %3d%%' % (self._bargraph_msg, percent))
            self._newline = False
            sys.stderr.flush()

    def bargraph_done(self):
        if self._bargraph_msg:
            sys.stderr.write('\r%s: done\n' % self._bargraph_msg)
            sys.stderr.flush()
            self._newline = True
            self._bargraph_msg = None

    def set_verbose(self, verbose):
        self._verbose = verbose
