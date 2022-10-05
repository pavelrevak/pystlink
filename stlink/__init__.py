import logging

from stlink.pystlink import PyStlink
from typing import Optional, List, Union, Callable
from argparse import Namespace
# from .pystlink import PyStlink

__all__ = [
    'PyStlink',
    'StlinkWrapper'
]


class StlinkWrapper:
    def __init__(self):
        self._link = PyStlink()
        self._commands: List[List] = []

    def _dispatch(self, actions: Optional[List[List]], verbosity: int = 1, serial: str = None, hard: bool = False,
                  index: int = 0, cpu: List[str] = (), no_unmount=True, no_run=True,
                  bar_on_update: Callable[[int, str], None] = None):
        args = {
            'action': [':'.join(filter(None, [] if action is None else action)) for action in actions],
            'serial': serial, 'index': index, 'hard': hard, 'verbosity': verbosity, 'cpu': cpu,
            'no_run': no_run, 'no_unmount': no_unmount
        }
        args = Namespace(**args)
        self._link.start(args, bargraph_on_update=bar_on_update)
        self._commands.clear()

    def dispatch(self, verbosity: int = 1, serial: str = None, hard: bool = False,
                  index: int = 0, cpu: List[str] = (), no_unmount=True, no_run=True,
                 bar_on_update: Callable[[int, str], None] = None):
        self._dispatch(self._commands, verbosity, serial, hard, index, cpu, no_unmount, no_run, bar_on_update)

    def _add_command(self, commands: List):
        self._commands.append(commands)

    def reset(self, halt: bool = False):
        self._add_command(['reset', 'halt'] if halt else ['reset'])
        return self

    def run(self):
        self._add_command(['run'])
        return self

    def sleep(self, duration: float):
        self._add_command(['sleep', f'{duration}'])
        return self

    def step(self):
        self._add_command(['step'])
        return self

    def halt(self):
        self._add_command(['halt'])
        return self

    """
    Verify flash {at address} against binary file ( or against .srec file)
    """
    def flash_check(self, file: Optional[str] = None, addr: Optional[int] = None):
        self._add_command(['flash', 'check', f'{file}', f'{addr}'])
        return self

    def flash_erase(self, erase: bool, verify: bool, file: str, addr: Optional[str] = None):
        self._add_command(['flash', 'erase' if erase else None, 'verify' if verify else None, addr if addr is not None else None,
                  file])
        return self

    """
    Write binary file into memory of sram
    :arg addr  Use sram to write value to sram
    """
    def write(self, file: str, addr: Union[str, int]):
        self._add_command(['fill', f'{addr}', file])
        return self

    """
    Fill memory or sram with pattern 
    """
    def fill(self, addr: Union[str, int], size: int, pattern: str):
        self._add_command(['fill', f'{addr}', None if size is None else size, f'{pattern}'])
        return self

    """
    Read memory/SRAM/flash into file
    """
    def read(self, addr: Union[str, int], size: int, file: str):
        self._add_command(['read', addr, f'{size}', file])
        return self

    """
    Set register or 32 bit memory
    """
    def set(self, reg: str, data: str):
        self._add_command(['set', reg, data])
        return self

    """
    Print all address value to the console
    :args addr Possible values: "core", "sram", "flash", or integer value representing the address of the core register
    """
    def dump(self, addr: Union[str, int], size: Optional[int]):
        self._add_command(['dump', f'{addr}', size])
        return self

    def dump16(self, addr: int):
        self._add_command(['dump16', addr])
        return self

    def dump8(self, addr: int):
        self._add_command(['dump8', addr])
        return self


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logging.StreamHandler.terminator = ''   # Ugly trick to suppress '\n', they are manually managed by the DBG class
    stlink = StlinkWrapper()
    stlink\
        .reset()\
        .flash_erase(erase=True, verify=True, file='../SW.bin', addr='0x8000000') \
        .dispatch(verbosity=2)
#        .dispatch(verbosity=2, bar_on_update=lambda x, y: print(x, y))

# if __name__ == '__main__':
#    pass
    # stlink = StlinkWrapper()
    # stlink.reset().dispatch()
    # stlink.flash_erase(True, True, '../flash_tool.bin').dispatch(verbosity=3)
