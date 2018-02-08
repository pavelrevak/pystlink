import time
import lib.stm32
import lib.stlinkex


class Flash():
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

    # PARAMS
    # R0: SRC data
    # R1: DST data
    # R2: size
    # R4: STM32_FLASH_SR
    # R5: FLASH_SR_BUSY_BIT
    FLASH_WRITER_F4_CODE_X8 = [
        # write:
        0x03, 0x78,  # 0x7803    # ldrh r3, [r0]
        0x0b, 0x70,  # 0x700b    # strh r3, [r1]
        # test_busy:
        0x23, 0x68,  # 0x6823    # ldr r3, [r4]
        0x2b, 0x42,  # 0x422b    # tst r3, r5
        0xfc, 0xd1,  # 0xd1fc    # bne <test_busy>
        0x00, 0x2b,  # 0x2b00    # cmp r3, #0
        0x04, 0xd1,  # 0xd104    # bne <exit>
        0x01, 0x30,  # 0x3001    # adds r0, #1
        0x01, 0x31,  # 0x3101    # adds r1, #1
        0x01, 0x3a,  # 0x3a01    # subs r2, #1
        0x00, 0x2a,  # 0x2a00    # cmp r2, #0
        0xf3, 0xd1,  # 0xd1f3    # bne <write>
        # exit:
        0x00, 0xbe,  # 0xbe00    # bkpt 0x00
    ]
    FLASH_WRITER_F4_CODE_X16 = [
        # write:
        0x03, 0x88,  # 0x8803    # ldrh r3, [r0]
        0x0b, 0x80,  # 0x800b    # strh r3, [r1]
        # test_busy:
        0x23, 0x68,  # 0x6823    # ldr r3, [r4]
        0x2b, 0x42,  # 0x422b    # tst r3, r5
        0xfc, 0xd1,  # 0xd1fc    # bne <test_busy>
        0x00, 0x2b,  # 0x2b00    # cmp r3, #0
        0x04, 0xd1,  # 0xd104    # bne <exit>
        0x02, 0x30,  # 0x3002    # adds r0, #2
        0x02, 0x31,  # 0x3102    # adds r1, #2
        0x02, 0x3a,  # 0x3a02    # subs r2, #2
        0x00, 0x2a,  # 0x2a00    # cmp r2, #0
        0xf3, 0xd1,  # 0xd1f3    # bne <write>
        # exit:
        0x00, 0xbe,  # 0xbe00    # bkpt 0x00
    ]
    FLASH_WRITER_F4_CODE_X32 = [
        # write:
        0x03, 0x68,  # 0x6803    # ldr r3, [r0]
        0x0b, 0x60,  # 0x600b    # str r3, [r1]
        # test_busy:
        0x23, 0x68,  # 0x6823    # ldr r3, [r4]
        0x2b, 0x42,  # 0x422b    # tst r3, r5
        0xfc, 0xd1,  # 0xd1fc    # bne <test_busy>
        0x00, 0x2b,  # 0x2b00    # cmp r3, #0
        0x04, 0xd1,  # 0xd104    # bne <exit>
        0x04, 0x30,  # 0x3004    # adds r0, #4
        0x04, 0x31,  # 0x3104    # adds r1, #4
        0x04, 0x3a,  # 0x3a04    # subs r2, #4
        0x00, 0x2a,  # 0x2a00    # cmp r2, #0
        0xf3, 0xd1,  # 0xd1f3    # bne <write>
        # exit:
        0x00, 0xbe,  # 0xbe00    # bkpt 0x00
    ]

    VOLTAGE_DEPENDEND_PARAMS = [
        {
            'min_voltage': 2.7,
            'max_mass_erase_time': 16,
            'max_erase_time': {16: .5, 32: 1.1, 64: 1.1, 128: 2, 256: 2},
            'FLASH_CR_PSIZE': FLASH_CR_PSIZE_X32,
            'FLASH_WRITER_CODE': FLASH_WRITER_F4_CODE_X32,
        }, {
            'min_voltage': 2.1,
            'max_mass_erase_time': 22,
            'max_erase_time': {16: .6, 32: 1.4, 64: 1.4, 128: 2.6, 256: 2.6},
            'FLASH_CR_PSIZE': FLASH_CR_PSIZE_X16,
            'FLASH_WRITER_CODE': FLASH_WRITER_F4_CODE_X16,
        }, {
            'min_voltage': 1.8,
            'max_mass_erase_time': 32,
            'max_erase_time': {16: .8, 32: 2.4, 64: 2.4, 128: 4, 256: 4},
            'FLASH_CR_PSIZE': FLASH_CR_PSIZE_X8,
            'FLASH_WRITER_CODE': FLASH_WRITER_F4_CODE_X8,
        }
    ]

    def __init__(self, driver, stlink, dbg):
        self._driver = driver
        self._stlink = stlink
        self._dbg = dbg
        self._params = self.get_voltage_dependend_params()
        self.unlock()

    def get_voltage_dependend_params(self):
        self._stlink.read_target_voltage()
        for params in Flash.VOLTAGE_DEPENDEND_PARAMS:
            if self._stlink.target_voltage > params['min_voltage']:
                return params
        raise lib.stlinkex.StlinkException('Supply voltage is %.2fV, but minimum for FLASH program or erase is 1.8V' % self._stlink.target_voltage)

    def unlock(self):
        self._driver.core_reset_halt()
        # do dummy read of FLASH_CR_REG
        self._stlink.get_debugreg32(Flash.FLASH_CR_REG)
        self._stlink.get_debugreg32(Flash.FLASH_CR_REG)
        # programing locked
        if self._stlink.get_debugreg32(Flash.FLASH_CR_REG) & Flash.FLASH_CR_LOCK_BIT:
            # unlock keys
            self._stlink.set_debugreg32(Flash.FLASH_KEYR_REG, 0x45670123)
            self._stlink.set_debugreg32(Flash.FLASH_KEYR_REG, 0xcdef89ab)
            # check if programing was unlocked
        if self._stlink.get_debugreg32(Flash.FLASH_CR_REG) & Flash.FLASH_CR_LOCK_BIT:
            raise lib.stlinkex.StlinkException('Error unlocking FLASH')

    def lock(self):
        self._stlink.set_debugreg32(Flash.FLASH_CR_REG, Flash.FLASH_CR_LOCK_BIT)
        self._driver.core_reset_halt()

    def erase_all(self):
        self._stlink.set_debugreg32(Flash.FLASH_CR_REG, Flash.FLASH_CR_MER_BIT)
        self._stlink.set_debugreg32(Flash.FLASH_CR_REG, Flash.FLASH_CR_MER_BIT | Flash.FLASH_CR_STRT_BIT)
        self.wait_busy(self._params['max_mass_erase_time'], 'Erasing FLASH')

    def erase_sector(self, sector, erase_size):
        flash_cr_value = Flash.FLASH_CR_SER_BIT
        flash_cr_value |= self._params['FLASH_CR_PSIZE'] | (sector << Flash.FLASH_CR_SNB_BITINDEX)
        self._stlink.set_debugreg32(Flash.FLASH_CR_REG, flash_cr_value)
        self._stlink.set_debugreg32(Flash.FLASH_CR_REG, flash_cr_value | Flash.FLASH_CR_STRT_BIT)
        self.wait_busy(self._params['max_erase_time'][erase_size / 1024])

    def erase_sectors(self, flash_start, erase_sizes, addr, size):
        erase_addr = flash_start
        self._dbg.bargraph_start('Erasing FLASH', value_min=flash_start, value_max=flash_start + size)
        sector = 0
        while True:
            for erase_size in erase_sizes:
                if addr < erase_addr + erase_size:
                    self._dbg.bargraph_update(value=erase_addr)
                    self.erase_sector(sector, erase_size)
                erase_addr += erase_size
                if addr + size < erase_addr:
                    self._dbg.bargraph_done()
                    return
                sector += 1

    def init_write(self, sram_offset):
        self._flash_writer_offset = sram_offset
        self._flash_data_offset = sram_offset + 0x100
        self._stlink.set_mem8(self._flash_writer_offset, self._params['FLASH_WRITER_CODE'])
        # set configuration for flash writer
        self._driver.set_reg('R4', Flash.FLASH_SR_REG)
        self._driver.set_reg('R5', Flash.FLASH_SR_BUSY_BIT)
        # enable PG
        self._stlink.set_debugreg32(Flash.FLASH_CR_REG, Flash.FLASH_CR_PG_BIT | self._params['FLASH_CR_PSIZE'])

    def write(self, addr, block):
        # if all data are 0xff then will be not written
        if min(block) == 0xff:
            return
        self._stlink.set_mem32(self._flash_data_offset, block)
        self._driver.set_reg('PC', self._flash_writer_offset)
        self._driver.set_reg('R0', self._flash_data_offset)
        self._driver.set_reg('R1', addr)
        self._driver.set_reg('R2', len(block))
        self._driver.core_run()
        self.wait_for_breakpoint(0.2)

    def wait_busy(self, wait_time, bargraph_msg=None):
        end_time = time.time() + wait_time * 1.5
        if bargraph_msg:
            self._dbg.bargraph_start(bargraph_msg, value_min=time.time(), value_max=time.time() + wait_time)
        while time.time() < end_time:
            if bargraph_msg:
                self._dbg.bargraph_update(value=time.time())
            status = self._stlink.get_debugreg32(Flash.FLASH_SR_REG)
            if not status & Flash.FLASH_SR_BUSY_BIT:
                self.end_of_operation(status)
                if bargraph_msg:
                    self._dbg.bargraph_done()
                return
            time.sleep(wait_time / 20)
        raise lib.stlinkex.StlinkException('Operation timeout')

    def wait_for_breakpoint(self, wait_time):
        end_time = time.time() + wait_time
        while time.time() < end_time and not self._stlink.get_debugreg32(lib.stm32.Stm32.DHCSR_REG) & lib.stm32.Stm32.DHCSR_STATUS_HALT_BIT:
            time.sleep(wait_time / 20)
        self.end_of_operation(self._stlink.get_debugreg32(Flash.FLASH_SR_REG))

    def end_of_operation(self, status):
        if status:
            raise lib.stlinkex.StlinkException('Error writing FLASH with status (FLASH_SR) %08x' % status)


# support all STM32F MCUs with sector access access to FLASH
# (STM32F2xx, STM32F4xx)
class Stm32FS(lib.stm32.Stm32):
    def flash_erase_all(self):
        self._dbg.debug('Stm32FS.flash_erase_all()')
        flash = Flash(self, self._stlink, self._dbg)
        flash.erase_all()
        flash.lock()

    def flash_write(self, addr, data, erase=False, verify=False, erase_sizes=None):
        self._dbg.debug('Stm32FS.flash_write(%s, [data:%dBytes], erase=%s, verify=%s, erase_sizes=%s)' % (('0x%08x' % addr) if addr is not None else 'None', len(data), erase, verify, erase_sizes))
        if addr is None:
            addr = self.FLASH_START
        if addr % 4:
            raise lib.stlinkex.StlinkException('Start address is not aligned to word')
        # align data
        if len(data) % 4:
            data.extend([0xff] * (4 - len(data) % 4))
        flash = Flash(self, self._stlink, self._dbg)
        if erase:
            if erase_sizes:
                flash.erase_sectors(self.FLASH_START, erase_sizes, addr, len(data))
            else:
                flash.erase_all()
        self._dbg.bargraph_start('Writing FLASH', value_min=addr, value_max=addr + len(data))
        flash.init_write(Stm32FS.SRAM_START)
        while(data):
            self._dbg.bargraph_update(value=addr)
            block = data[:self._stlink.STLINK_MAXIMUM_TRANSFER_SIZE]
            data = data[self._stlink.STLINK_MAXIMUM_TRANSFER_SIZE:]
            flash.write(addr, block)
            if verify and block != self._stlink.get_mem32(addr, len(block)):
                raise lib.stlinkex.StlinkException('Verify error at block address: 0x%08x' % addr)
            addr += len(block)
        flash.lock()
        self._dbg.bargraph_done()
