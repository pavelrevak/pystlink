import lib.stm32
import lib.stlinkex


class StlinkStm32():

    REGISTERS = ['R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9', 'R10', 'R11', 'R12', 'SP', 'LR', 'PC']
    CPUID_REG = 0xe000ed00

    def __init__(self, driver, dbg):
        self._driver = driver
        self._dbg = dbg
        self._ver_stlink = None
        self._ver_jtag = None
        self._ver_swim = None
        self._ver_api = None

        self._voltage = None
        self._coreid = None

        self._mcus_by_core = None
        self._mcus_by_devid = None
        self._mcus = None

        self._flash_start = 0x08000000
        self._flash_size = None
        self._sram_start = 0x20000000
        self._sram_size = None
        self._eeprom_start = None
        self._eeprom_size = None

    def read_version(self):
        ver = self._driver.get_version()
        self._ver_stlink = (ver >> 12) & 0xf
        self._ver_jtag = (ver >> 6) & 0x3f
        self._ver_swim = ver & 0x3f
        self._ver_api = 2 if self._ver_jtag > 11 else 1
        self._dbg.msg("STLINK: V%d.J%d.S%d (API:v%d)" % (self._ver_stlink, self._ver_jtag, self._ver_swim, self._ver_api), level=2)

    def read_target_voltage(self):
        self._voltage = self._driver.get_target_voltage()
        self._dbg.msg("SUPPLY: %.2fV" % self._voltage)

    def core_halt(self):
        self._driver.set_debugreg(0xe000edf0, 0xa05f0003)

    def core_run(self):
        self._driver.set_debugreg(0xe000edf0, 0xa05f0001)

    def core_nodebug(self):
        self._driver.set_debugreg(0xe000edf0, 0xa05f0000)

    def read_coreid(self):
        self._coreid = self._driver.get_coreid()
        self._dbg.msg("COREID: %08x" % self._coreid, 2)
        if self._coreid == 0:
            raise lib.stlinkex.StlinkException('Not connected to CPU')

    def find_mcus_by_core(self, cpuid):
        self._dbg.msg("CPUID: %08x" % cpuid, 2)
        partno = 0xfff & (cpuid >> 4)
        for mcu_core in lib.stm32.DEVICES:
            if mcu_core['part_no'] == partno:
                return mcu_core
        raise lib.stlinkex.StlinkException('PART_NO: 0x%03x is not supported' % partno)

    def find_mcus_by_devid(self, idcode):
        self._dbg.msg("IDCODE: %08x" % idcode, 2)
        devid = 0xfff & idcode
        for mcu_devid in self._mcus_by_core['devices']:
            if mcu_devid['dev_id'] == devid:
                return mcu_devid
        raise lib.stlinkex.StlinkException('DEV_ID: 0x%03x is not supported' % devid)

    def find_mcus_by_flash_size(self):
        mcus = []
        for mcu in self._mcus_by_devid['devices']:
            if mcu['flash_size'] == self._flash_size:
                mcus.append(mcu)
        if not mcus:
            raise lib.stlinkex.StlinkException('Connected CPU with DEV_ID: 0x%03x and FLASH size: %dKB is not supported' % (
                self._mcus_by_devid['dev_id'], self._flash_size
            ))
        return mcus

    def find_mcus_by_mcu_type(self, mcu_type):
        mcus = []
        for mcu in self._mcus:
            if mcu['type'].startswith(mcu_type):
                mcus.append(mcu)
        if not mcus:
            raise lib.stlinkex.StlinkException('Connected CPU is not %s but detected is %s %s' % (
                mcu_type,
                'one of' if len(self._mcus) > 1 else ''
                ','.join([mcu['type'] for mcu in self._mcus]),
            ))
        return mcus

    def clean_mcu_type(self, mcu_type=None):
        mcu_type = mcu_type.upper()
        if not mcu_type.startswith('STM32'):
            raise lib.stlinkex.StlinkException('Selected CPU is not STM32')
        # change character on 10 position to 'x' where is package size
        if len(mcu_type) > 9:
            mcu_type = list(mcu_type)
            mcu_type[9] = 'x'
            mcu_type = ''.join(mcu_type)
        return mcu_type

    def read_mcu_info(self, mcu_type):
        # find core by part_no from CPUID register
        cpuid = self._driver.get_debugreg(StlinkStm32.CPUID_REG)
        self._mcus_by_core = self.find_mcus_by_core(cpuid)
        # find MCUs group by dev_id from IDCODE register
        idcode = self._driver.get_debugreg(self._mcus_by_core['idcode_reg'])
        self._mcus_by_devid = self.find_mcus_by_devid(idcode)
        # find MCUs by flash size
        self._flash_size = self._driver.get_debugreg16(self._mcus_by_devid['flash_size_reg'])
        self._mcus = self.find_mcus_by_flash_size()
        if mcu_type:
            # filter found MCUs by selected MCU type
            mcu_type = self.clean_mcu_type(mcu_type)
            self._mcus = self.find_mcus_by_mcu_type(mcu_type)
        # if is found more CPUS, then SRAM and EEPROM size
        # will be used the smallest of all (worst case)
        self._sram_size = min([mcu['sram_size'] for mcu in self._mcus])
        self._eeprom_size = min([mcu['eeprom_size'] for mcu in self._mcus])

    def print_mcu_info(self):
        self._dbg.msg("CORE: %s" % self._mcus_by_core['core'])
        self._dbg.msg("MCU: %s" % '/'.join([mcu['type'] for mcu in self._mcus]))
        self._dbg.msg("FLASH: %dKB" % self._flash_size)
        self._dbg.msg("SRAM: %dKB" % self._sram_size)
        self._dbg.msg("EEPROM: %dKB" % self._eeprom_size)
        if len(self._mcus) > 1:
            diff = False
            if self._sram_size != max([mcu['sram_size'] for mcu in self._mcus]):
                diff = True
                self._dbg.msg(" * Detected CPUs have different SRAM sizes.")
            if self._eeprom_size != max([mcu['eeprom_size'] for mcu in self._mcus]):
                diff = True
                self._dbg.msg(" * Detected CPUs have different FLASH sizes.")
            if diff:
                self._dbg.msg(" * Is recommended to select certain CPU. Is used the smallest size.")

    def detect(self, mcu_type=None):
        self.read_version()
        self.read_target_voltage()
        self._driver.set_swd_freq(1800000)
        self._driver.enter_debug_swd()
        self.read_coreid()
        self.read_mcu_info(mcu_type)
        self.print_mcu_info()

    def disconnect(self):
        self.core_nodebug()
        self._driver.leave_state()

    def dump_registers(self):
        self.core_halt()
        for i in range(len(StlinkStm32.REGISTERS)):
            print("  %3s: %08x" % (StlinkStm32.REGISTERS[i], self._driver.get_reg(i)))

    def get_mem(self, addr, size, block_size=1024):
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
            block = self._driver.get_mem32(iaddr, block_size)
            data.extend(block)
            iaddr += block_size
        self._dbg.bargraph_done()
        return (addr, data)

    def read_sram(self):
        return self.get_mem(self._sram_start, self._sram_size)

    def read_flash(self):
        return self.get_mem(self._flash_start, self._flash_size)


