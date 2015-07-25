import stlinkusb
import stlinkv2


PARTNO = {
    0xc20: {
        'type': 'CortexM0',
        'DBGMCU_IDCODE_addr': 0x40015800,
    },
    0xc24: {
        'type': 'CortexM4',
        'DBGMCU_IDCODE_addr': 0xE0042000,
    },
}

DEV_ID = {
    0x413: {
        'type': 'STM32F405/407/415/417',
        'sram': 192 * 1024,
        'flashsize_reg': 0x1fff7a22,
    },
    0x419: {
        'type': 'STM32F42x/43x',
        'sram': 256 * 1024,
        'flashsize_reg': 0x1fff7a22,
    },
    0x440: {
        'type': 'STM32F030x8',
        'sram': 8 * 1024,
        'flashsize_reg': 0x1ffff7cc,
    },
    0x444: {
        'type': 'STM32F03x',
        'sram': 4 * 1024,
        'flashsize_reg': 0x1ffff7cc,
        'flashpagesize': 1024,
    },
    0x445: {
        'type': 'STM32F04x',
        'sram': 6 * 1024,
        'flashsize_reg': 0x1ffff7cc,
        'flashpagesize': 1024,
    },
    0x440: {
        'type': 'STM32F05x',
        'sram': 8 * 1024,
        'flashsize_reg': 0x1ffff7cc,
        'flashpagesize': 1024,
    },
    0x448: {
        'type': 'STM32F07x',
        'sram': 16 * 1024,
        'flashsize_reg': 0x1ffff7cc,
        'flashpagesize': 2 * 1024,
    },
}


class Stlink(stlinkv2.StlinkV2):
    def __init__(self, **kwds):
        super().__init__(**kwds)
        self._ver_stlink = None
        self._ver_jtag = None
        self._ver_swim = None
        self._ver_api = None
        self._voltage = None
        self._coreid = None
        self._cpuid = None
        self._idcode = None
        self._partno = None
        self._dev_id = None

    def read_version(self):
        ver = self.get_version()
        self._ver_stlink = (ver >> 12) & 0xf
        self._ver_jtag = (ver >> 6) & 0x3f
        self._ver_swim = ver & 0x3f
        self._ver_api = 2 if self._ver_jtag > 11 else 1
        self.debug("STLINK: V%d.J%d.S%d (API:v%d)" % (self._ver_stlink, self._ver_jtag, self._ver_swim, self._ver_api), level=1)

    def read_target_voltage(self):
        self._voltage = self.get_target_voltage()
        self.debug("SUPPLY: %.2fV" % self._voltage)

    def read_coreid(self):
        self._coreid = self.get_coreid()
        self.debug("COREID: %08x" % self._coreid, 1)
        if self._coreid == 0:
            raise stlinkex.StlinkException('Not connected to CPU')

    def read_cpuid(self):
        self._cpuid = self.get_debugreg(0xe000ed00)
        self._partno = 0xfff & (self._cpuid >> 4)
        self.debug("CPUID: %08x" % self._cpuid, 1)
        if self._partno not in PARTNO:
            raise stlinkex.StlinkException('CORE id:0x%03x is not supported' % self._partno)
        self.debug("CORE: %s" % PARTNO[self._partno]['type'])

    def read_idcode(self):
        self._idcode = self.get_debugreg(PARTNO[self._partno]['DBGMCU_IDCODE_addr'])
        self._dev_id = 0xfff & self._idcode
        self.debug("IDCODE: %08x" % self._idcode, 1)
        if self._dev_id not in DEV_ID:
            raise stlinkex.StlinkException('CPU is not supported')
        self.debug("CPU: %s" % DEV_ID[self._dev_id]['type'])
        self.debug("SRAM: %dKB" % (DEV_ID[self._dev_id]['sram'] / 1024))

    def read_flashsize(self):
        self._flashsize = self.get_debugreg16(DEV_ID[self._dev_id]['flashsize_reg'])
        self.debug("FLASH: %dKB" % self._flashsize)

    def core_halt(self):
        self.set_debugreg(0xe000edf0, 0xa05f0003)

    def core_run(self):
        self.set_debugreg(0xe000edf0, 0xa05f0001)

    def core_nodebug(self):
        self.set_debugreg(0xe000edf0, 0xa05f0000)

    def init_mcu(self):
        self.read_version()
        self.read_target_voltage()
        self.set_swd_freq(1800000)
        self.enter_debug_swd()
        self.read_coreid()
        self.read_cpuid()
        self.read_idcode()
        self.read_flashsize()
        self.core_halt()
        for i in range(16):
            self.debug("%2d: %08x" % (i, self.get_reg(i)))
        i = 15
        self.core_nodebug()
        self.leave_state()


if __name__ == "__main__":
    try:
        stlink = Stlink(verbose=0)
        stlink.init_mcu()
        stlink.debug('DONE')
    except stlinkex.StlinkException as e:
        print(e)
