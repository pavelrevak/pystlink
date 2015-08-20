import time
import lib.stm32
import lib.stlinkex


class Flash():
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

    # PARAMS
    # R0: SRC data
    # R1: DST data
    # R2: size
    # R4: STM32_FLASH_SR
    # R5: FLASH_SR_BUSY_BIT
    # R6: FLASH_SR_EOP_BIT
    FLASH_WRITER_F0_CODE = [
                    # write:
        0x03, 0x88, # 0x8803    # ldrh r3, [r0]
        0x0b, 0x80, # 0x800b    # strh r3, [r1]
                    # test_busy:
        0x23, 0x68, # 0x6823    # ldr r3, [r4]
        0x2b, 0x42, # 0x422b    # tst r3, r5
        0xfc, 0xd1, # 0xd1fc    # bne <test_busy>
        0x33, 0x42, # 0x4233    # tst r3, r6
        0x04, 0xd0, # 0xd104    # beq <exit>
        0x02, 0x30, # 0x3002    # adds r0, #2
        0x02, 0x31, # 0x3102    # adds r1, #2
        0x02, 0x3a, # 0x3a02    # subs r2, #2
        0x00, 0x2a, # 0x2a00    # cmp r2, #0
        0xf3, 0xd1, # 0xd1f3    # bne <write>
                    # exit:
        0x00, 0xbe, # 0xbe00    # bkpt 0x00
    ]

    def __init__(self, driver, stlink, dbg):
        self._driver = driver
        self._stlink = stlink
        self._dbg = dbg
        self._stlink.read_target_voltage()
        if self._stlink.target_voltage < 2.0:
            raise lib.stlinkex.StlinkException('Supply voltage is %.2fV, but minimum for FLASH program or erase is 2.0V' % self._stlink.target_voltage)
        self.unlock()

    def unlock(self):
        self._driver.core_reset_halt()
        # programing locked
        if self._stlink.get_debugreg32(Flash.FLASH_CR_REG) & Flash.FLASH_CR_LOCK_BIT:
            # unlock keys
            self._stlink.set_debugreg32(Flash.FLASH_KEYR_REG, 0x45670123)
            self._stlink.set_debugreg32(Flash.FLASH_KEYR_REG, 0xcdef89ab)
        # programing locked
        if self._stlink.get_debugreg32(Flash.FLASH_CR_REG) & Flash.FLASH_CR_LOCK_BIT:
            raise lib.stlinkex.StlinkException('Error unlocking FLASH')

    def lock(self):
        self._stlink.set_debugreg32(Flash.FLASH_CR_REG, Flash.FLASH_CR_LOCK_BIT)
        self._driver.core_reset_halt()

    def erase_all(self):
        self._stlink.set_debugreg32(Flash.FLASH_CR_REG, Flash.FLASH_CR_MER_BIT)
        self._stlink.set_debugreg32(Flash.FLASH_CR_REG, Flash.FLASH_CR_MER_BIT | Flash.FLASH_CR_STRT_BIT)
        self.wait_busy(2, 'Erasing FLASH')

    def erase_page(self, page_addr):
        self._stlink.set_debugreg32(Flash.FLASH_CR_REG, Flash.FLASH_CR_PER_BIT)
        self._stlink.set_debugreg32(Flash.FLASH_AR_REG, page_addr)
        self._stlink.set_debugreg32(Flash.FLASH_CR_REG, Flash.FLASH_CR_PER_BIT | Flash.FLASH_CR_STRT_BIT)
        self.wait_busy(0.2)

    def erase_pages(self, flash_start, erase_sizes, addr, size):
        page_addr = flash_start
        self._dbg.bargraph_start('Erasing FLASH', value_min=addr, value_max=addr + size)
        while True:
            for page_size in erase_sizes:
                if addr < page_addr + page_size * 1024:
                    self._dbg.bargraph_update(value=page_addr)
                    self.erase_page(page_addr)
                page_addr += page_size * 1024
                if addr + size < page_addr:
                    self._dbg.bargraph_done()
                    return

    def init_write(self, sram_offset):
        self._flash_writer_offset = sram_offset
        self._flash_data_offset = sram_offset + 0x100
        self._stlink.set_mem8(self._flash_writer_offset, Flash.FLASH_WRITER_F0_CODE)
        # set configuration for flash writer
        self._driver.set_reg('R4', Flash.FLASH_SR_REG)
        self._driver.set_reg('R5', Flash.FLASH_SR_BUSY_BIT)
        self._driver.set_reg('R6', Flash.FLASH_SR_EOP_BIT)
        # enable PG
        self._stlink.set_debugreg32(Flash.FLASH_CR_REG, Flash.FLASH_CR_PG_BIT)

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
        end_time = time.time()
        if bargraph_msg:
            self._dbg.bargraph_start(bargraph_msg, value_min=time.time(), value_max=end_time + wait_time)
        # all times are from data sheet, will be more safe to wait 2 time longer
        end_time += wait_time * 2
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
        if status != Flash.FLASH_SR_EOP_BIT:
            raise lib.stlinkex.StlinkException('Error writing FLASH with status (FLASH_SR) %08x' % status)
        self._stlink.set_debugreg32(Flash.FLASH_SR_REG, status)


# support STM32F0xx, STM32F1xx and also STM32F2xx
class Stm32F0(lib.stm32.Stm32):
    def flash_erase_all(self):
        self._dbg.debug('Stm32F0.flash_erase_all()')
        flash = Flash(self, self._stlink, self._dbg)
        flash.erase_all()
        flash.lock()

    def flash_write(self, addr, data, erase=False, verify=False, erase_sizes=None):
        self._dbg.debug('Stm32.flash_write(%s, [data:%dBytes], erase=%s, verify=%s, erase_sizes=%s)' % (('0x%08x' % addr) if addr is not None else 'None', len(data), erase, verify, erase_sizes))
        if addr is None:
            addr = self.FLASH_START
        if addr % 2:
            raise lib.stlinkex.StlinkException('Address is not alligned')
        # align data
        if len(data) % 4:
            data.extend([0xff] * (4 - len(data) % 4))
        flash = Flash(self, self._stlink, self._dbg)
        if erase:
            if erase_sizes:
                flash.erase_pages(self.FLASH_START, erase_sizes, addr, len(data))
            else:
                flash.erase_all()
        self._dbg.bargraph_start('Writing FLASH', value_min=addr, value_max=addr + len(data))
        flash.init_write(Stm32F0.SRAM_START)
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
