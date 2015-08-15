import usb.core
import usb.util
import lib.stlinkex


class StlinkUsbConnector():
    STLINK_CMD_SIZE_V2 = 16

    def __init__(self, dbg=None):
        self._dbg = dbg
        self._dev = usb.core.find(idVendor=0x0483, idProduct=0x3748)
        if self._dev is None:
            raise lib.stlinkex.StlinkException('ST-LINK v2 not connected')
        self._dev.set_configuration()
        self._dbg.debug("successfully connected to stlink", level=3)

    def _write(self, data):
        self._dbg.debug("  USB > %s" % ' '.join(['%02x' % i for i in data]), level=3)
        count = self._dev.write(0x02, data, 0)
        if count != len(data):
            raise lib.stlinkex.StlinkException("Only %d bytes was transmitted to ST-LINK instead of %d" % (count, len(data)))

    def _read(self, size):
        data = self._dev.read(0x81, size, 0).tolist()
        self._dbg.debug("  USB < %s" % ' '.join(['%02x' % i for i in data]), level=3)
        return data

    def xfer(self, cmd, data=None, rx_len=None):
        cmd_len = len(cmd)
        if cmd_len > self.STLINK_CMD_SIZE_V2:
            raise lib.stlinkex.StlinkException("Too many tx bytes: %d, maximum is %d" % (cmd_len, self.STLINK_CMD_SIZE_V2))
        # pad to 16 bytes
        cmd += [0] * (self.STLINK_CMD_SIZE_V2 - cmd_len)
        self._write(cmd)
        if data:
            self._write(data)
        if rx_len:
            return self._read(rx_len)
        return None
