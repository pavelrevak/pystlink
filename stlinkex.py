class StlinkException(Exception):
    def __init__(self, msg):
        self._msg = msg

    def __str__(self):
        return "*** %s ***" % self._msg
