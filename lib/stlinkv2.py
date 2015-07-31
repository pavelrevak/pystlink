import lib.stlinkex


class StlinkDriver():
    STLINK_GET_VERSION                  = 0xf1
    STLINK_DEBUG_COMMAND                = 0xf2
    STLINK_DFU_COMMAND                  = 0xf3
    STLINK_SWIM_COMMAND                 = 0xf4
    STLINK_GET_CURRENT_MODE             = 0xf5
    STLINK_GET_TARGET_VOLTAGE           = 0xf7

    STLINK_MODE_DFU                     = 0x00
    STLINK_MODE_MASS                    = 0x01
    STLINK_MODE_DEBUG                   = 0x02
    STLINK_MODE_SWIM                    = 0x03
    STLINK_MODE_BOOTLOADER              = 0x04

    STLINK_DFU_EXIT                     = 0x07

    STLINK_SWIM_ENTER                   = 0x00
    STLINK_SWIM_EXIT                    = 0x01

    STLINK_DEBUG_ENTER_JTAG             = 0x00
    STLINK_DEBUG_STATUS                 = 0x01
    STLINK_DEBUG_FORCEDEBUG             = 0x02
    STLINK_DEBUG_APIV1_RESETSYS         = 0x03
    STLINK_DEBUG_APIV1_READALLREGS      = 0x04
    STLINK_DEBUG_APIV1_READREG          = 0x05
    STLINK_DEBUG_APIV1_WRITEREG         = 0x06
    STLINK_DEBUG_READMEM_32BIT          = 0x07
    STLINK_DEBUG_WRITEMEM_32BIT         = 0x08
    STLINK_DEBUG_RUNCORE                = 0x09
    STLINK_DEBUG_STEPCORE               = 0x0a
    STLINK_DEBUG_APIV1_SETFP            = 0x0b
    STLINK_DEBUG_READMEM_8BIT           = 0x0c
    STLINK_DEBUG_WRITEMEM_8BIT          = 0x0d
    STLINK_DEBUG_APIV1_CLEARFP          = 0x0e
    STLINK_DEBUG_APIV1_WRITEDEBUGREG    = 0x0f
    STLINK_DEBUG_APIV1_SETWATCHPOINT    = 0x10
    STLINK_DEBUG_APIV1_ENTER            = 0x20
    STLINK_DEBUG_EXIT                   = 0x21
    STLINK_DEBUG_READCOREID             = 0x22
    STLINK_DEBUG_APIV2_ENTER            = 0x30
    STLINK_DEBUG_APIV2_READ_IDCODES     = 0x31
    STLINK_DEBUG_APIV2_RESETSYS         = 0x32
    STLINK_DEBUG_APIV2_READREG          = 0x33
    STLINK_DEBUG_APIV2_WRITEREG         = 0x34
    STLINK_DEBUG_APIV2_WRITEDEBUGREG    = 0x35
    STLINK_DEBUG_APIV2_READDEBUGREG     = 0x36
    STLINK_DEBUG_APIV2_READALLREGS      = 0x3a
    STLINK_DEBUG_APIV2_GETLASTRWSTATUS  = 0x3b
    STLINK_DEBUG_APIV2_DRIVE_NRST       = 0x3c
    STLINK_DEBUG_UNKNOWN_MAYBE_SYNC     = 0x3e
    STLINK_DEBUG_APIV2_START_TRACE_RX   = 0x40
    STLINK_DEBUG_APIV2_STOP_TRACE_RX    = 0x41
    STLINK_DEBUG_APIV2_GET_TRACE_NB     = 0x42
    STLINK_DEBUG_APIV2_SWD_SET_FREQ     = 0x43
    STLINK_DEBUG_ENTER_SWD              = 0xa3

    STLINK_DEBUG_APIV2_DRIVE_NRST_LOW   = 0x00
    STLINK_DEBUG_APIV2_DRIVE_NRST_HIGH  = 0x01
    STLINK_DEBUG_APIV2_DRIVE_NRST_PULSE = 0x02

    STLINK_DEBUG_APIV2_SWD_SET_FREQ_MAP = {
        4000000: 0,
        1800000: 1,  # default
        1200000: 2,
        950000:  3,
        480000:  7,
        240000: 15,
        125000: 31,
        100000: 40,
        50000:  79,
        25000: 158,
        # 15000: 265,
        # 5000:  798
    }

    def __init__(self, connector, dbg):
        self._connector = connector
        self._dbg = dbg

    def get_version(self):
        rx = self._connector.xfer([StlinkDriver.STLINK_GET_VERSION, 0x80], 6)
        return int.from_bytes(rx[:2], byteorder='big')

    def leave_state(self):
        rx = self._connector.xfer([StlinkDriver.STLINK_GET_CURRENT_MODE], 2)
        if rx[0] == StlinkDriver.STLINK_MODE_DFU:
            self._connector.xfer([StlinkDriver.STLINK_DFU_COMMAND, StlinkDriver.STLINK_DFU_EXIT])
        if rx[0] == StlinkDriver.STLINK_MODE_DEBUG:
            self._connector.xfer([StlinkDriver.STLINK_DEBUG_COMMAND, StlinkDriver.STLINK_DEBUG_EXIT])
        if rx[0] == StlinkDriver.STLINK_MODE_SWIM:
            self._connector.xfer([StlinkDriver.STLINK_SWIM_COMMAND, StlinkDriver.STLINK_SWIM_EXIT])

    def get_target_voltage(self):
        self.leave_state()
        rx = self._connector.xfer([StlinkDriver.STLINK_GET_TARGET_VOLTAGE], 8)  # GET_TARGET_VOLTAGE
        a0 = int.from_bytes(rx[:4], byteorder='little')
        a1 = int.from_bytes(rx[4:8], byteorder='little')
        if a0 != 0:
            return 2 * a1 * 1.2 / a0

    def set_swd_freq(self, freq=1800000):
        for f, d in StlinkDriver.STLINK_DEBUG_APIV2_SWD_SET_FREQ_MAP.items():
            if freq >= f:
                rx = self._connector.xfer([StlinkDriver.STLINK_DEBUG_COMMAND, StlinkDriver.STLINK_DEBUG_APIV2_SWD_SET_FREQ, d], 2)  # ???
                if rx[0] != 0x80:
                    raise lib.stlinkex.StlinkException("Error switching SWD frequency")
                return
        raise lib.stlinkex.StlinkException("Selected SWD frequency is too low")

    def enter_debug_swd(self):
        rx = self._connector.xfer([StlinkDriver.STLINK_DEBUG_COMMAND, StlinkDriver.STLINK_DEBUG_APIV2_ENTER, StlinkDriver.STLINK_DEBUG_ENTER_SWD], 2)

    def get_coreid(self):
        rx = self._connector.xfer([StlinkDriver.STLINK_DEBUG_COMMAND, StlinkDriver.STLINK_DEBUG_READCOREID], 4)
        return int.from_bytes(rx[:4], byteorder='little')

    def set_debugreg(self, addr, data):
        if addr % 4:
            raise lib.stlinkex.StlinkException('get_mem_short address is not in multiples of 4')
        cmd = [StlinkDriver.STLINK_DEBUG_COMMAND, StlinkDriver.STLINK_DEBUG_APIV2_WRITEDEBUGREG]
        cmd.extend(list(addr.to_bytes(4, byteorder='little')))
        cmd.extend(list(data.to_bytes(4, byteorder='little')))
        return self._connector.xfer(cmd, 2)

    def get_debugreg(self, addr):
        if addr % 4:
            raise lib.stlinkex.StlinkException('get_mem_short address is not in multiples of 4')
        cmd = [StlinkDriver.STLINK_DEBUG_COMMAND, StlinkDriver.STLINK_DEBUG_APIV2_READDEBUGREG]
        cmd.extend(list(addr.to_bytes(4, byteorder='little')))
        rx = self._connector.xfer(cmd, 8)
        return int.from_bytes(rx[4:8], byteorder='little')

    def get_debugreg16(self, addr):
        if addr % 2:
            raise lib.stlinkex.StlinkException('get_mem_short address is not in even')
        val = self.get_debugreg(addr & 0xfffffffc)
        if addr % 4:
            val >>= 16
        return val & 0xffff

    def get_debugreg8(self, addr):
        val = self.get_debugreg(addr & 0xfffffffc)
        val >>= (addr % 4) << 3
        return val & 0xff

    def get_reg(self, reg):
        cmd = [StlinkDriver.STLINK_DEBUG_COMMAND, StlinkDriver.STLINK_DEBUG_APIV2_READREG, reg]
        rx = self._connector.xfer(cmd, 8)
        return int.from_bytes(rx[4:8], byteorder='little')

    def get_mem32(self, addr, size):
        if addr % 4:
            raise lib.stlinkex.StlinkException('get_mem: Address must be in multiples of 4')
        cmd = [StlinkDriver.STLINK_DEBUG_COMMAND, StlinkDriver.STLINK_DEBUG_READMEM_32BIT]
        cmd.extend(list(addr.to_bytes(4, byteorder='little')))
        cmd.extend(list(size.to_bytes(4, byteorder='little')))
        return self._connector.xfer(cmd, size)
