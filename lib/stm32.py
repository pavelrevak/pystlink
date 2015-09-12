import lib.stm32devices
import lib.stlinkex


class Stm32():
    REGISTERS = ['R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9', 'R10', 'R11', 'R12', 'SP', 'LR', 'PC', 'PSR', 'MSP', 'PSP']

    SRAM_START = 0x20000000
    FLASH_START = 0x08000000

    AIRCR_REG = 0xe000ed0c
    DHCSR_REG = 0xe000edf0
    DEMCR_REG = 0xe000edfc

    AIRCR_KEY = 0x05fa0000
    AIRCR_SYSRESETREQ_BIT = 0x00000004
    AIRCR_SYSRESETREQ = AIRCR_KEY | AIRCR_SYSRESETREQ_BIT

    DHCSR_KEY = 0xa05f0000
    DHCSR_DEBUGEN_BIT = 0x00000001
    DHCSR_HALT_BIT = 0x00000002
    DHCSR_STEP_BIT = 0x00000004
    DHCSR_STATUS_HALT_BIT = 0x00020000
    DHCSR_DEBUGDIS = DHCSR_KEY
    DHCSR_DEBUGEN = DHCSR_KEY | DHCSR_DEBUGEN_BIT
    DHCSR_HALT = DHCSR_KEY | DHCSR_DEBUGEN_BIT | DHCSR_HALT_BIT
    DHCSR_STEP = DHCSR_KEY | DHCSR_DEBUGEN_BIT | DHCSR_STEP_BIT

    DEMCR_RUN_AFTER_RESET = 0x00000000
    DEMCR_HALT_AFTER_RESET = 0x00000001

    def __init__(self, stlink, dbg):
        self._stlink = stlink
        self._dbg = dbg

    def is_reg(self, reg):
        return reg.upper() in Stm32.REGISTERS

    def get_reg_all(self):
        return [(reg, self.get_reg(reg)) for reg in Stm32.REGISTERS]

    def get_reg(self, reg):
        self._dbg.debug('Stm32.get_reg(%s)' % reg)
        reg = reg.upper()
        if reg in Stm32.REGISTERS:
            index = Stm32.REGISTERS.index(reg)
            return self._stlink.get_reg(index)
        raise lib.stlinkex.StlinkException('Wrong register name')

    def set_reg(self, reg, value):
        self._dbg.debug('Stm32.set_reg(%s, 0x%08x)' % (reg, value))
        reg = reg.upper()
        if reg in Stm32.REGISTERS:
            index = Stm32.REGISTERS.index(reg)
            return self._stlink.set_reg(index, value)
        raise lib.stlinkex.StlinkException('Wrong register name')

    def get_mem(self, addr, size):
        self._dbg.debug('Stm32.get_mem(0x%08x, %d)' % (addr, size))
        if size == 0:
            return addr, []
        if size >= 16384:
            self._dbg.bargraph_start('Reading memory', value_max=size)
        data = []
        if addr % 4:
            read_size = min(4 - (addr % 4), size)
            data = self._stlink.get_mem8(addr, read_size)
        while True:
            self._dbg.bargraph_update(value=len(data))
            read_size = min((size - len(data) & 0xfffffffc), self._stlink.STLINK_MAXIMUM_TRANSFER_SIZE)
            if read_size == 0:
                break
            data.extend(self._stlink.get_mem32(addr + len(data), read_size))
        if len(data) < size:
            read_size = size - len(data)
            data.extend(self._stlink.get_mem8(addr + len(data), read_size))
        self._dbg.bargraph_done()
        return (addr, data)

    def set_mem(self, addr, data):
        self._dbg.debug('Stm32.set_mem(0x%08x, [data:%dBytes])' % (addr, len(data)))
        if len(data) == 0:
            return
        if len(data) >= 16384:
            self._dbg.bargraph_start('Writing memory', value_max=len(data))
        size = 0
        if addr % 4:
            write_size = min(4 - (addr % 4), len(data))
            self._stlink.set_mem8(addr, data[:write_size])
            size = write_size
        while True:
            self._dbg.bargraph_update(value=size)
            write_size = min((len(data) - size) & 0xfffffffc, self._stlink.STLINK_MAXIMUM_TRANSFER_SIZE)
            if write_size == 0:
                break
            self._stlink.set_mem32(addr + size, data[size:size + write_size])
            size += write_size
        if size < len(data):
            self._stlink.set_mem8(addr + size, data[size:])
        self._dbg.bargraph_done()
        return

    def fill_mem(self, addr, size, pattern):
        if pattern >= 256:
            raise lib.stlinkex.StlinkException('Fill pattern can by 8 bit number')
        self._dbg.debug('Stm32.fill_mem(0x%08x, 0x%02d)' % (addr, pattern))
        if size == 0:
            return
        if size >= 16384:
            self._dbg.bargraph_start('Writing memory', value_max=size)
        written_size = 0
        if addr % 4:
            write_size = min(4 - (addr % 4), size)
            self._stlink.set_mem8(addr, [pattern] * write_size)
            written_size = write_size
        while True:
            self._dbg.bargraph_update(value=written_size)
            write_size = min((size - written_size) & 0xfffffffc, self._stlink.STLINK_MAXIMUM_TRANSFER_SIZE)
            if write_size == 0:
                break
            self._stlink.set_mem32(addr + written_size, [pattern] * write_size)
            written_size += write_size
        if written_size < size:
            self._stlink.set_mem8(addr + written_size, [pattern] * (size - written_size))
        self._dbg.bargraph_done()
        return

    def core_reset(self):
        self._dbg.debug('Stm32.core_reset()')
        self._stlink.set_debugreg32(Stm32.DEMCR_REG, Stm32.DEMCR_RUN_AFTER_RESET)
        self._stlink.set_debugreg32(Stm32.AIRCR_REG, Stm32.AIRCR_SYSRESETREQ)
        self._stlink.get_debugreg32(Stm32.AIRCR_REG)

    def core_reset_halt(self):
        self._dbg.debug('Stm32.core_reset_halt()')
        self._stlink.set_debugreg32(Stm32.DHCSR_REG, Stm32.DHCSR_HALT)
        self._stlink.set_debugreg32(Stm32.DEMCR_REG, Stm32.DEMCR_HALT_AFTER_RESET)
        self._stlink.set_debugreg32(Stm32.AIRCR_REG, Stm32.AIRCR_SYSRESETREQ)
        self._stlink.get_debugreg32(Stm32.AIRCR_REG)

    def core_halt(self):
        self._dbg.debug('Stm32.core_halt()')
        self._stlink.set_debugreg32(Stm32.DHCSR_REG, Stm32.DHCSR_HALT)

    def core_step(self):
        self._dbg.debug('Stm32.core_step()')
        self._stlink.set_debugreg32(Stm32.DHCSR_REG, Stm32.DHCSR_STEP)

    def core_run(self):
        self._dbg.debug('Stm32.core_run()')
        self._stlink.set_debugreg32(Stm32.DHCSR_REG, Stm32.DHCSR_DEBUGEN)

    def core_nodebug(self):
        self._dbg.debug('Stm32.core_nodebug()')
        self._stlink.set_debugreg32(Stm32.DHCSR_REG, Stm32.DHCSR_DEBUGDIS)

    def flash_erase_all(self):
        self._dbg.debug('Stm32.flash_mass_erase()')
        raise lib.stlinkex.StlinkException('Erasing FLASH is not implemented for this MCU')

    def flash_write(self, addr, data, erase=False, verify=False, erase_sizes=None):
        self._dbg.debug('Stm32.flash_write(%s, [data:%dBytes], erase=%s, verify=%s, erase_sizes=%s)' % (('0x%08x' % addr) if addr is not None else 'None', len(data), erase, verify, erase_sizes))
        raise lib.stlinkex.StlinkException('Programing FLASH is not implemented for this MCU')
