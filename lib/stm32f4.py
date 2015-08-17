import time
import lib.stm32
import lib.stlinkex

class Stm32F4(lib.stm32.Stm32):
    FLASH_REG_BASE = 0x40023c00
    FLASH_KEYR_REG = FLASH_REG_BASE + 0x04
    FLASH_SR_REG = FLASH_REG_BASE + 0x0c
    FLASH_CR_REG = FLASH_REG_BASE + 0x10

    FLASH_CR_LOCK_BIT = 0x80000000
    FLASH_CR_PG_BIT = 0x00000001
    FLASH_CR_SER_BIT = 0x00000002
    FLASH_CR_MER_BIT = 0x00000004
    FLASH_CR_STRT_BIT = 0x00010000
    FLASH_CR_PSIZE_X8 = 0x00000000
    FLASH_CR_PSIZE_X16 = 0x00000100
    FLASH_CR_PSIZE_X32 = 0x00000200
    FLASH_CR_PSIZE_X64 = 0x00000300
    FLASH_CR_SNB_BITINDEX = 3

    FLASH_SR_BUSY_BIT = 0x00010000

    FLASH_WRITER_OFFSET = lib.stm32.Stm32.SRAM_START
    FLASH_DATA_OFFSET = lib.stm32.Stm32.SRAM_START + 0x100

    FLASH_WRITER_F4_CODE_X8 = [
        # PARAMS
        # R0: SRC data
        # R1: DST data
        # R2: size
        # R4: STM32_FLASH_SR
        # R5: FLASH_SR_BUSY_BIT
                    # write:
        0x03, 0x78, # 0x7803    # ldrh r3, [r0]
        0x0b, 0x70, # 0x700b    # strh r3, [r1]
                    # test_busy:
        0x23, 0x68, # 0x6823    # ldr r3, [r4]
        0x2b, 0x42, # 0x422b    # tst r3, r5
        0xfc, 0xd1, # 0xd1fc    # bne <test_busy>
        0x00, 0x2b, # 0x2b00    # cmp r3, #0
        0x04, 0xd1, # 0xd104    # bne <exit>
        0x01, 0x30, # 0x3001    # adds r0, #1
        0x01, 0x31, # 0x3101    # adds r1, #1
        0x01, 0x3a, # 0x3a01    # subs r2, #1
        0x00, 0x2a, # 0x2a00    # cmp r2, #0
        0xf3, 0xd1, # 0xd1f3    # bne <write>
                    # exit:
        0x00, 0xbe, # 0xbe00    # bkpt 0x00
    ]

    FLASH_WRITER_F4_CODE_X16 = [
        # PARAMS
        # R0: SRC data
        # R1: DST data
        # R2: size
        # R4: STM32_FLASH_SR
        # R5: FLASH_SR_BUSY_BIT
                    # write:
        0x03, 0x88, # 0x8803    # ldrh r3, [r0]
        0x0b, 0x80, # 0x800b    # strh r3, [r1]
                    # test_busy:
        0x23, 0x68, # 0x6823    # ldr r3, [r4]
        0x2b, 0x42, # 0x422b    # tst r3, r5
        0xfc, 0xd1, # 0xd1fc    # bne <test_busy>
        0x00, 0x2b, # 0x2b00    # cmp r3, #0
        0x04, 0xd1, # 0xd104    # bne <exit>
        0x02, 0x30, # 0x3002    # adds r0, #2
        0x02, 0x31, # 0x3102    # adds r1, #2
        0x02, 0x3a, # 0x3a02    # subs r2, #2
        0x00, 0x2a, # 0x2a00    # cmp r2, #0
        0xf3, 0xd1, # 0xd1f3    # bne <write>
                    # exit:
        0x00, 0xbe, # 0xbe00    # bkpt 0x00
    ]

    FLASH_WRITER_F4_CODE_X32 = [
        # PARAMS
        # R0: SRC data
        # R1: DST data
        # R2: size
        # R4: STM32_FLASH_SR
        # R5: FLASH_SR_BUSY_BIT
                    # write:
        0x03, 0x68, # 0x6803    # ldr r3, [r0]
        0x0b, 0x60, # 0x600b    # str r3, [r1]
                    # test_busy:
        0x23, 0x68, # 0x6823    # ldr r3, [r4]
        0x2b, 0x42, # 0x422b    # tst r3, r5
        0xfc, 0xd1, # 0xd1fc    # bne <test_busy>
        0x00, 0x2b, # 0x2b00    # cmp r3, #0
        0x04, 0xd1, # 0xd104    # bne <exit>
        0x04, 0x30, # 0x3004    # adds r0, #4
        0x04, 0x31, # 0x3104    # adds r1, #4
        0x04, 0x3a, # 0x3a04    # subs r2, #4
        0x00, 0x2a, # 0x2a00    # cmp r2, #0
        0xf3, 0xd1, # 0xd1f3    # bne <write>
                    # exit:
        0x00, 0xbe, # 0xbe00    # bkpt 0x00
    ]

    SECTORS_TABLE = {
        0: 16,
        1: 16,
        2: 16,
        3: 16,
        4: 64,
        5: 128,
        6: 128,
        7: 128,
        8: 128,
        9: 128,
        10: 128,
        11: 128,
    }

    def address_to_sector(self, addr):
        actual_addr = self.FLASH_START
        sector = 0
        if addr < actual_addr:
            raise lib.stlinkex.StlinkException('Address is out of FLASH memory')
        while True:
            for sector, size in Stm32F4.SECTORS_TABLE.items():
                actual_addr += size * 1024
                if addr < actual_addr:
                    return sector

    def flash_unlock(self):
        self.core_reset_halt()
        # programing locked
        if self._stlink.get_debugreg32(Stm32F4.FLASH_CR_REG) & Stm32F4.FLASH_CR_LOCK_BIT:
            # unlock keys
            self._stlink.set_debugreg32(Stm32F4.FLASH_KEYR_REG, 0x45670123)
            self._stlink.set_debugreg32(Stm32F4.FLASH_KEYR_REG, 0xcdef89ab)
        # programing locked
        if self._stlink.get_debugreg32(Stm32F4.FLASH_CR_REG) & Stm32F4.FLASH_CR_LOCK_BIT:
            raise lib.stlinkex.StlinkException('Error unlocking FLASH')

    def get_voltage_dependend_params(self):
        self._stlink.read_target_voltage()
        if self._stlink.target_voltage > 2.7:
            return {
                'PSIZE': Stm32F4.FLASH_CR_PSIZE_X32,
                'max_erase_time': 16000,
                'FLASH_WRITER_CODE': Stm32F4.FLASH_WRITER_F4_CODE_X32,
            }
        if self._stlink.target_voltage > 2.1:
            return {
                'PSIZE': Stm32F4.FLASH_CR_PSIZE_X16,
                'max_erase_time': 22000,
                'FLASH_WRITER_CODE': Stm32F4.FLASH_WRITER_F4_CODE_X16,
            }
        if self._stlink.target_voltage > 1.8:
            return {
                'PSIZE': Stm32F4.FLASH_CR_PSIZE_X8,
                'max_erase_time': 32000,
                'FLASH_WRITER_CODE': Stm32F4.FLASH_WRITER_F4_CODE_X8,
            }
        raise lib.stlinkex.StlinkException('Supply voltage is %.2fV, but minimum for FLASH program or erase is 1.8V' % self._stlink.target_voltage)

    def flash_erase(self, page_addr=None, sector=None, nodbg=False):
        params = self.get_voltage_dependend_params()
        if not nodbg:
            self._dbg.bargraph_start('Erasing FLASH', value_max=params['max_erase_time'])
        self.flash_unlock()
        if page_addr is not None:
            raise lib.stlinkex.StlinkException('Erasing pages is not supported in this MCU')
        if sector is not None:
            # sector erase
            self._stlink.set_debugreg32(Stm32F4.FLASH_CR_REG, Stm32F4.FLASH_CR_SER_BIT | params['PSIZE'] | (sector << Stm32F4.FLASH_CR_SNB_BITINDEX))
            # sector erase start
            self._stlink.set_debugreg32(Stm32F4.FLASH_CR_REG, Stm32F4.FLASH_CR_SER_BIT | Stm32F4.FLASH_CR_STRT_BIT)
        else:
            # mass erase
            self._stlink.set_debugreg32(Stm32F4.FLASH_CR_REG, Stm32F4.FLASH_CR_MER_BIT | params['PSIZE'])
            # mass erase start
            self._stlink.set_debugreg32(Stm32F4.FLASH_CR_REG, Stm32F4.FLASH_CR_MER_BIT | Stm32F4.FLASH_CR_STRT_BIT)
        # wait while busy
        limit = 0
        status = 0
        # max_erase_time is from data sheet, but we are more pessimistic
        while limit < params['max_erase_time'] * 2:
            if not nodbg:
                self._dbg.bargraph_update(value=limit)
            limit += 100
            # status
            status = self._stlink.get_debugreg32(Stm32F4.FLASH_SR_REG)
            # BUSY in status
            if not status & Stm32F4.FLASH_SR_BUSY_BIT:
                break
            time.sleep(.1)
        # end of operation in status
        if status:
            raise lib.stlinkex.StlinkException('Error erasing FLASH with status (FLASH_SR) %08x' % status)
        # disable erase and lock FLASH
        self._stlink.set_debugreg32(Stm32F4.FLASH_CR_REG, Stm32F4.FLASH_CR_LOCK_BIT)
        if not nodbg:
            self._dbg.bargraph_done()

    def flash_erase_sectors(self, addr, size):
        sector = self.address_to_sector(addr)
        last_sector = self.address_to_sector(addr + size - 1)
        self._dbg.bargraph_start('Erasing FLASH', value_min=sector, value_max=last_sector + 1)
        while sector <= last_sector:
            self._dbg.bargraph_update(value=sector)
            self.flash_erase(sector=sector, nodbg=True)
            sector += 1
        self._dbg.bargraph_done()

    def flash_write(self, addr, data, block_size=1024, erase=False, verify=False):
        params = self.get_voltage_dependend_params()
        if addr is None:
            addr = self.FLASH_START
        if addr % 4:
            raise lib.stlinkex.StlinkException('Address is not alligned')
        while len(data) % 2:
            data.append(0xff)
        if erase:
            self.flash_erase_sectors(addr, len(data))
        self._dbg.bargraph_start('Writing FLASH', value_min=addr, value_max=addr + len(data))
        self.flash_unlock()
        self._stlink.set_mem8(Stm32F4.FLASH_WRITER_OFFSET, params['FLASH_WRITER_CODE'])
        # set constants to flash writer
        self.set_reg('R4', Stm32F4.FLASH_SR_REG)
        self.set_reg('R5', Stm32F4.FLASH_SR_BUSY_BIT)
        # enable PG
        self._stlink.set_debugreg32(Stm32F4.FLASH_CR_REG, Stm32F4.FLASH_CR_PG_BIT | params['PSIZE'])
        while(data):
            self._dbg.bargraph_update(value=addr)
            block = data[:block_size]
            data = data[block_size:]
            if min(block) != 0xff:
                # align block
                if len(block) % 4:
                    block.extend([0xff] * (4 - len(block) % 4))
                # upload data for flashing
                self._stlink.set_mem32(Stm32F4.FLASH_DATA_OFFSET, block)
                self.set_reg('PC', Stm32F4.FLASH_WRITER_OFFSET)
                self.set_reg('R0', Stm32F4.FLASH_DATA_OFFSET)
                self.set_reg('R1', addr)
                self.set_reg('R2', len(block))
                # run flash writer
                self.core_run()
                # wait for breakpoint
                limit = 100
                while limit > 0 and not self._stlink.get_debugreg32(Stm32F4.DHCSR_REG) & Stm32F4.DHCSR_STATUS_HALT_BIT:
                    limit -= 1
                    time.sleep(0.01)
                # status
                status = self._stlink.get_debugreg32(Stm32F4.FLASH_SR_REG)
                # end of operation in status
                if status:
                    raise lib.stlinkex.StlinkException('Error writing FLASH with status (FLASH_SR) %08x' % status)
            if verify and block != self._stlink.get_mem32(addr, len(block)):
                raise lib.stlinkex.StlinkException('Verify error at block address: 0x%08x' % addr)
            addr += block_size
        self.core_reset()
        # disable PG and lock FLASH
        self._stlink.set_debugreg32(Stm32F4.FLASH_CR_REG, Stm32F4.FLASH_CR_LOCK_BIT)
        self._dbg.bargraph_done()
