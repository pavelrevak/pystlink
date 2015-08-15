import lib.stm32devices
import lib.stlinkex
import time


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
        reg = reg.upper()
        if reg in Stm32.REGISTERS:
            index = Stm32.REGISTERS.index(reg)
            return self._stlink.get_reg(index)
        raise lib.stlinkex.StlinkException('Wrong register name')

    def set_reg(self, reg, value):
        reg = reg.upper()
        if reg in Stm32.REGISTERS:
            index = Stm32.REGISTERS.index(reg)
            return self._stlink.set_reg(index, value)
        raise lib.stlinkex.StlinkException('Wrong register name')

    def get_mem(self, addr, size, block_size=1024):
        if size == 0:
            return addr, []
        self._dbg.bargraph_start('Reading memory', value_max=size)
        data = []
        if addr % 4:
            read_size = min(4 - (addr % 4), size)
            data = self._stlink.get_mem8(addr, read_size)
        while True:
            self._dbg.bargraph_update(value=len(data))
            read_size = min((size - len(data) & 0xfffffffc), block_size)
            if read_size == 0:
                break
            data.extend(self._stlink.get_mem32(addr + len(data), read_size))
        if len(data) < size:
            read_size = size - len(data)
            data.extend(self._stlink.get_mem8(addr + len(data), read_size))
        self._dbg.bargraph_done()
        return (addr, data)

    def set_mem(self, addr, data, block_size=1024):
        if len(data) == 0:
            return addr, []
        self._dbg.bargraph_start('Writing memory', value_max=len(data))
        size = 0
        if addr % 4:
            write_size = min(4 - (addr % 4), len(data))
            self._stlink.set_mem8(addr, data[:write_size])
            size = write_size
        while True:
            self._dbg.bargraph_update(value=size)
            write_size = min((len(data) - size) & 0xfffffffc, block_size)
            if write_size == 0:
                break
            self._stlink.set_mem32(addr + size, data[size:size + write_size])
            size += write_size
        if size < len(data):
            self._stlink.set_mem8(addr + size, data[size:])
        self._dbg.bargraph_done()
        return (addr, data)

    # def read_sram(self, size=None):
    #     if size is None:
    #         size = self._sram_size * 1024
    #     return self.get_mem(Stm32.SRAM_START, size)

    # def read_flash(self, size=None):
    #     if size is None:
    #         size = self._flash_size * 1024
    #     return self.get_mem(Stm32.FLASH_START, size)

    def core_reset(self):
        self._stlink.set_debugreg32(Stm32.DEMCR_REG, Stm32.DEMCR_RUN_AFTER_RESET)
        self._stlink.set_debugreg32(Stm32.AIRCR_REG, Stm32.AIRCR_SYSRESETREQ)
        self._stlink.get_debugreg32(Stm32.AIRCR_REG)

    def core_reset_halt(self):
        self._stlink.set_debugreg32(Stm32.DHCSR_REG, Stm32.DHCSR_HALT)
        self._stlink.set_debugreg32(Stm32.DEMCR_REG, Stm32.DEMCR_HALT_AFTER_RESET)
        self._stlink.set_debugreg32(Stm32.AIRCR_REG, Stm32.AIRCR_SYSRESETREQ)
        self._stlink.get_debugreg32(Stm32.AIRCR_REG)

    def core_halt(self):
        self._stlink.set_debugreg32(Stm32.DHCSR_REG, Stm32.DHCSR_HALT)

    def core_step(self):
        self._stlink.set_debugreg32(Stm32.DHCSR_REG, Stm32.DHCSR_STEP)

    def core_run(self):
        self._stlink.set_debugreg32(Stm32.DHCSR_REG, Stm32.DHCSR_DEBUGEN)

    def core_nodebug(self):
        self._stlink.set_debugreg32(Stm32.DHCSR_REG, Stm32.DHCSR_DEBUGDIS)

    def flash_erase(self, addr):
        raise lib.stlinkex.StlinkException('Erasing FLASH is not implemented for this MCU')

    def flash_write(self, addr, data, block_size=1024):
        raise lib.stlinkex.StlinkException('Programing FLASH is not implemented for this MCU')


class Stm32F0(Stm32):
    FLASH_REG_BASE = 0x40022000
    FLASH_KEYR_REG = FLASH_REG_BASE + 0x04
    FLASH_SR_REG = FLASH_REG_BASE + 0x0c
    FLASH_CR_REG = FLASH_REG_BASE + 0x10
    FLASH_AR_REG = FLASH_REG_BASE + 0x14

    FLASH_CR_LOCK_BIT = 0x00000080
    FLASH_CR_PG_BIT = 0x00000001
    FLASH_CR_PER_BIT = 0x00000002
    FLASH_CR_MER_BIT = 0x00000004
    FLASH_CR_STRT_BIT = 0x00000040
    FLASH_SR_BUSY_BIT = 0x00000001
    FLASH_SR_EOP_BIT = 0x00000020

    def flash_unlock(self):
        self.core_reset_halt()
        # programing locked
        if self._stlink.get_debugreg32(Stm32F0.FLASH_CR_REG) & Stm32F0.FLASH_CR_LOCK_BIT:
            # unlock keys
            self._stlink.set_debugreg32(Stm32F0.FLASH_KEYR_REG, 0x45670123)
            self._stlink.set_debugreg32(Stm32F0.FLASH_KEYR_REG, 0xcdef89ab)
        # programing locked
        if self._stlink.get_debugreg32(Stm32F0.FLASH_CR_REG) & Stm32F0.FLASH_CR_LOCK_BIT:
            raise lib.stlinkex.StlinkException('Error unlocking FLASH')

    def flash_erase(self, addr):
        self._dbg.bargraph_start('Erasing FLASH')
        self.flash_unlock()
        if addr is None:
            # mass erase
            self._stlink.set_debugreg32(Stm32F0.FLASH_CR_REG, Stm32F0.FLASH_CR_MER_BIT)
            # mass erase start
            self._stlink.set_debugreg32(Stm32F0.FLASH_CR_REG, Stm32F0.FLASH_CR_MER_BIT | Stm32F0.FLASH_CR_STRT_BIT)
        else:
            # page erase
            self._stlink.set_debugreg32(Stm32F0.FLASH_CR_REG, Stm32F0.FLASH_CR_PER_BIT)
            # address
            self._stlink.set_debugreg32(Stm32F0.FLASH_AR_REG, addr)
            # page erase start
            self._stlink.set_debugreg32(Stm32F0.FLASH_CR_REG, Stm32F0.FLASH_CR_PER_BIT | Stm32F0.FLASH_CR_STRT_BIT)
        # wait while busy
        limit = 100
        status = 0
        while limit > 0:
            limit -= 1
            # status
            status = self._stlink.get_debugreg32(Stm32F0.FLASH_SR_REG)
            # BUSY in status
            if not status & Stm32F0.FLASH_SR_BUSY_BIT:
                break
            time.sleep(0.01)
        # end of operation in status
        if not status & Stm32F0.FLASH_SR_EOP_BIT:
            raise lib.stlinkex.StlinkException('Error erasing FLASH with status %08x' % status)
        # disable erase and lock FLASH
        self._stlink.set_debugreg32(Stm32F0.FLASH_CR_REG, Stm32F0.FLASH_CR_LOCK_BIT)
        self._dbg.bargraph_done()

    FLASH_WRITER_F0_CODE = [
        # PARAMS
        # R0: SRC data
        # R1: DST data
        # R2: size
        # R4: STM32_FLASH_BASE
                    # write:
        0x03, 0x88, # 0x8803    # ldrh    r3, [r0, #0]
        0x0b, 0x80, # 0x800b    # strh    r3, [r1, #0]
                    # test_busy:
        0xe3, 0x68, # 0x68e3    # ldr r3, [r4, #12]
        0x2b, 0x42, # 0x422b    # tst r3, r5
        0xfc, 0xd1, # 0xd1fc    # bne <test_busy>
        0x33, 0x42, # 0x4233    # tst r3, r6
        0x04, 0xd0, # 0xd104    # beq <exit>
        0x02, 0x30, # 0x3002    # adds    r0, #2
        0x02, 0x31, # 0x3102    # adds    r1, #2
        0x02, 0x3a, # 0x3a02    # subs    r2, #2
        0x00, 0x2a, # 0x2a00    # cmp r2, #0
        0xf3, 0xd1, # 0xd1f3    # bne <write>
                    # exit:
        0x00, 0xbe, # 0xbe00    # bkpt    0x00
    ]

    def flash_write(self, addr, data, block_size=1024):
        FLASH_WRITER_OFFSET = self.SRAM_START
        FLASH_DATA_OFFSET = self.SRAM_START + 0x100
        if addr is None:
            addr = self.FLASH_START
        if addr % 2:
            raise lib.stlinkex.StlinkException('Address is not alligned')
        if len(data) % 2:
            data.append(0xff)
        if len(data) % 2:
            raise lib.stlinkex.StlinkException('Data length is not alligned')
        self._dbg.bargraph_start('Writing FLASH', value_min=addr, value_max=addr + len(data))
        self.flash_unlock()
        self._stlink.set_mem8(FLASH_WRITER_OFFSET, Stm32F0.FLASH_WRITER_F0_CODE)
        # set constants to flash writer
        self._stlink.set_reg(Stm32.REGISTERS.index('R4'), Stm32F0.FLASH_REG_BASE)
        self._stlink.set_reg(Stm32.REGISTERS.index('R5'), Stm32F0.FLASH_SR_BUSY_BIT)
        self._stlink.set_reg(Stm32.REGISTERS.index('R6'), Stm32F0.FLASH_SR_EOP_BIT)
        # enable PG
        self._stlink.set_debugreg32(Stm32F0.FLASH_CR_REG, Stm32F0.FLASH_CR_PG_BIT)
        while(data):
            self._dbg.bargraph_update(value=addr)
            block = data[:block_size]
            data = data[block_size:]
            if min(block) == 0xff:
                addr += block_size
                continue
            # align block
            if len(block) % 4:
                block.extend([0xff] * (4 - len(block) % 4))
            # upload data for flashing
            self._stlink.set_mem32(FLASH_DATA_OFFSET, block)
            self._stlink.set_reg(Stm32.REGISTERS.index('PC'), FLASH_WRITER_OFFSET)
            self._stlink.set_reg(Stm32.REGISTERS.index('R0'), FLASH_DATA_OFFSET)
            self._stlink.set_reg(Stm32.REGISTERS.index('R1'), addr)
            self._stlink.set_reg(Stm32.REGISTERS.index('R2'), len(block))
            # run flash writer
            self.core_run()
            # wait for breakpoint
            limit = 100
            while limit > 0 and not self._stlink.get_debugreg32(Stm32.DHCSR_REG) & Stm32.DHCSR_STATUS_HALT_BIT:
                limit -= 1
                time.sleep(0.01)
            # status
            status = self._stlink.get_debugreg32(Stm32F0.FLASH_SR_REG)
            # end of operation in status
            if not status & Stm32F0.FLASH_SR_EOP_BIT:
                raise lib.stlinkex.StlinkException('Error writing FLASH with status (FLASH_SR) %08x' % status)
            addr += block_size
        self.core_reset()
        # disable PG and lock FLASH
        self._stlink.set_debugreg32(Stm32F0.FLASH_CR_REG, Stm32F0.FLASH_CR_LOCK_BIT)
        self._dbg.bargraph_done()
