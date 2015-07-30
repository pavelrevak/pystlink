import lib.stm32
import lib.stlinkv2
import lib.stlinkex


class StlinkStm32(lib.stlinkv2.StlinkV2):

    REGISTERS = ['R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9', 'R10', 'R11', 'R12', 'SP', 'LR', 'PC']

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
        self._devid = None
        self._mcu_core = None
        self._mcu_devid = None
        self._mcus = None
        self._cputype = None
        self._flash_start = 0x08000000
        self._flash_size = None
        self._sram_start = 0x20000000
        self._sram_size = None
        self._eeprom_start = None
        self._eeprom_size = None

    def read_version(self):
        ver = self.get_version()
        self._ver_stlink = (ver >> 12) & 0xf
        self._ver_jtag = (ver >> 6) & 0x3f
        self._ver_swim = ver & 0x3f
        self._ver_api = 2 if self._ver_jtag > 11 else 1
        self._dbg.msg("STLINK: V%d.J%d.S%d (API:v%d)" % (self._ver_stlink, self._ver_jtag, self._ver_swim, self._ver_api), level=2)

    def read_target_voltage(self):
        self._voltage = self.get_target_voltage()
        self._dbg.msg("SUPPLY: %.2fV" % self._voltage)

    def read_coreid(self):
        self._coreid = self.get_coreid()
        self._dbg.msg("COREID: %08x" % self._coreid, 2)
        if self._coreid == 0:
            raise lib.stlinkex.StlinkException('Not connected to CPU')

    def read_cpuid(self):
        self._cpuid = self.get_debugreg(0xe000ed00)
        self._dbg.msg("CPUID: %08x" % self._cpuid, 2)

    def find_mcu_core(self):
        self.read_cpuid()
        self._partno = 0xfff & (self._cpuid >> 4)
        for mcu_core in lib.stm32.DEVICES:
            if mcu_core['part_no'] == self._partno:
                self._mcu_core = mcu_core
                break
        else:
            raise lib.stlinkex.StlinkException('PARTNO: 0x%03x is not supported' % self._partno)
        self._dbg.msg("CORE: %s" % self._mcu_core['core'])

    def read_idcode(self):
        self.find_mcu_core()
        self._idcode = self.get_debugreg(self._mcu_core['idcode_reg'])
        self._dbg.msg("IDCODE: %08x" % self._idcode, 2)

    def find_mcu_devid(self):
        self.read_idcode()
        self._devid = 0xfff & self._idcode
        for mcu_devid in self._mcu_core['devices']:
            if mcu_devid['dev_id'] == self._devid:
                self._mcu_devid = mcu_devid
                break
        else:
            raise lib.stlinkex.StlinkException('DEV_ID: 0x%03x is not supported' % self._devid)

    def read_flash_size(self):
        self.find_mcu_devid()
        self._flash_size = self.get_debugreg16(self._mcu_devid['flash_size_reg']) * 1024

    def find_mcu_info(self):
        self.read_flash_size()
        flash_size = self._flash_size // 1024
        mcus = []
        mcus_by_type = []
        for mcu in self._mcu_devid['devices']:
            if mcu['flash_size'] != flash_size:
                continue
            mcus.append(mcu)
            if self._cputype and not mcu['type'].startswith(self._cputype):
                continue
            mcus_by_type.append(mcu)
        if not mcus:
            raise lib.stlinkex.StlinkException('Connected CPU with dev_id: 0x%03x, FLASH size: %dKB is not supported' % (self._devid, flash_size))
        if self._cputype and not mcus_by_type:
            if len(mcus) > 1:
                raise lib.stlinkex.StlinkException('Connected CPU is not %s but one of: %s' % (self._cputype, ','.join([mcu['type'] for mcu in mcus])))
            elif mcus:
                raise lib.stlinkex.StlinkException('Connected CPU is not %s but: %s' % (self._cputype, mcus[0]['type']))
            raise lib.stlinkex.StlinkException('Connected CPU is not %s or has different dev_id or has different FLASH size or is not supported. Detected dev_id: 0x%03x, FLASH size: %dKB' % (self._cputype, self._devid, flash_size))
        self._mcus = mcus_by_type if mcus_by_type else mcus
        # if is found more CPUS, then SRAM and EEPROM size will be used the smallest of all
        sram_size = min([mcu['sram_size'] for mcu in self._mcus])
        eeprom_size = min([mcu['eeprom_size'] for mcu in self._mcus])
        self._dbg.msg("MCU: %s" % '/'.join([mcu['type'] for mcu in self._mcus]))
        self._dbg.msg("FLASH: %dKB" % flash_size)
        self._dbg.msg("SRAM: %dKB" % sram_size)
        self._dbg.msg("EEPROM: %dKB" % eeprom_size)
        self._sram_size = sram_size * 1024
        self._eeprom_size = eeprom_size * 1024
        diff = False
        if sram_size != max([mcu['sram_size'] for mcu in self._mcus]):
            diff = True
            self._dbg.msg(" * Detected CPUs have different SRAM sizes.")
        if eeprom_size != max([mcu['eeprom_size'] for mcu in self._mcus]):
            diff = True
            self._dbg.msg(" * Detected CPUs have different FLASH sizes.")
        if diff:
            self._dbg.msg(" * Is recommended to select certain CPU")

    def core_halt(self):
        self.set_debugreg(0xe000edf0, 0xa05f0003)

    def core_run(self):
        self.set_debugreg(0xe000edf0, 0xa05f0001)

    def core_nodebug(self):
        self.set_debugreg(0xe000edf0, 0xa05f0000)

    def detect(self, cputype=None):
        if cputype:
            cputype = cputype.upper()
            if not cputype.startswith('STM32'):
                raise lib.stlinkex.StlinkException('Selected CPU is not STM32')
            if len(cputype) > 9:
                cputype = list(cputype)
                cputype[9] = 'x'
                cputype = ''.join(cputype)
        self._cputype = cputype
        self.read_version()
        self.read_target_voltage()
        self.set_swd_freq(1800000)
        self.enter_debug_swd()
        self.read_coreid()
        self.find_mcu_info()

    def disconnect(self):
        self.core_nodebug()
        self.leave_state()

    def dump_registers(self):
        self.core_halt()
        for i in range(len(StlinkStm32.REGISTERS)):
            print("  %3s: %08x" % (StlinkStm32.REGISTERS[i], self.get_reg(i)))

    def read_mem(self, addr, size, block_size=1024):
        if size <= 0:
            return addr, []
        data = []
        blocks = size // block_size
        if size % block_size:
            blocks += 1
        self._dbg.bargraph_start('reading memory', value_max=blocks)
        iaddr = addr
        for i in range(blocks):
            self._dbg.bargraph_update(value=i)
            if (i + 1) * block_size > size:
                block_size = size - (block_size * i)
            block = self.get_mem32(iaddr, block_size)
            data.extend(block)
            iaddr += block_size
        self._dbg.bargraph_done()
        return (addr, data)

    def read_sram(self):
        return self.read_mem(self._sram_start, self._sram_size)

    def read_flash(self):
        return self.read_mem(self._flash_start, self._flash_size)


