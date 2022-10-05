import sys
import time
import logging
from logging import LogRecord
from typing import Callable, Optional
from tqdm import tqdm

logger = logging.getLogger('pystlink')
# logger.addHandler(logging.NullHandler())


class Formatter(logging.Formatter):
    def format(self, record: LogRecord) -> str:
        record.msg = record.msg.strip()
        return super(Formatter, self).format(record)


class Dbg:
    def __init__(self, verbose, bar_length=40, bargraph_on_update: Optional[Callable[[int, str], None]] = None):
        self._verbose = verbose
        self._bargraph_msg = None
        self._bargraph_min = None
        self._bargraph_max = None
        self._newline = True
        self._bar_length = bar_length
        self._prev_percent = None
        self._start_time = None
        self._bargraph_handler = self.print_bargraph if bargraph_on_update is None else bargraph_on_update

    def _msg(self, msg, level):
        if self._verbose >= level:
            if not self._newline:
                sys.stderr.write('\n')
                self._newline = True
            sys.stderr.write('%s\n' % msg)
            sys.stderr.flush()

    def debug(self, msg):
        logger.debug(f'{msg}\n')

    def verbose(self, msg):
        logger.debug(f'{msg}\n')

    def info(self, msg):
        logger.info(f'{msg}\n')

    def message(self, msg):
        logger.info(f'{msg}\n')

    def error(self, msg):
        logger.error(f'*** {msg} ***\n')

    def warning(self, msg):
        logger.warning(f' * {msg}\n')

    def print_bargraph(self, percent, msg):
        if percent == self._prev_percent:
            return
        if percent == -2:
            logger.info('\r%s: [%s] done in %.2fs\n' % (self._bargraph_msg, '=' * self._bar_length, time.time() - self._start_time))
            self._newline = True
            self._bargraph_msg = None
        elif percent == -1:
            if not self._newline:
                self._newline = False
                logger.info('%s' % msg)
            self._prev_percent = None
            self._newline = False
        else:
            bar = int(percent * self._bar_length) // 100
            logger.info('\r%s: [%s%s] %3d%%' % (self._bargraph_msg, '=' * bar, ' ' * (self._bar_length - bar), percent, ))
            self._prev_percent = percent
            self._newline = False

    def bargraph_start(self, msg, value_min=0, value_max=100, level=1):
        self._start_time = time.time()
        if self._verbose < level:
            return
        self._bargraph_msg = msg
        self._bargraph_min = value_min
        self._bargraph_max = value_max
        self._bargraph_handler(-1, msg)
        if not self._newline:
            logger.info('\n')
            self._newline = False
        logger.info('%s' % msg)
        self._prev_percent = None
        self._newline = False

    def bargraph_update(self, value=0, percent=None):
        if not self._bargraph_msg:
            return
        if percent is None:
            if (self._bargraph_max - self._bargraph_min) > 0:
                percent = 100 * (value - self._bargraph_min) // (self._bargraph_max - self._bargraph_min)
            else:
                percent = 0
        if percent > 100:
            percent = 100
        self._bargraph_handler(percent, self._bargraph_msg)

    def bargraph_done(self):
        if not self._bargraph_msg:
            return
        self._bargraph_handler(-2, self._bargraph_msg)

    def set_verbose(self, verbose):
        self._verbose = verbose
