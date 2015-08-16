import time
import lib.stm32
import lib.stlinkex

class Stm32F0(lib.stm32.Stm32):
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
        self.set_reg('R4', Stm32F0.FLASH_REG_BASE)
        self.set_reg('R5', Stm32F0.FLASH_SR_BUSY_BIT)
        self.set_reg('R6', Stm32F0.FLASH_SR_EOP_BIT)
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
            self.set_reg('PC', FLASH_WRITER_OFFSET)
            self.set_reg('R0', FLASH_DATA_OFFSET)
            self.set_reg('R1', addr)
            self.set_reg('R2', len(block))
            # run flash writer
            self.core_run()
            # wait for breakpoint
            limit = 100
            while limit > 0 and not self._stlink.get_debugreg32(Stm32F0.DHCSR_REG) & Stm32F0.DHCSR_STATUS_HALT_BIT:
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
