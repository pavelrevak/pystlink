import usb.core
import usb.util
import lib.stlinkex


class StlinkUsbConnector():
    STLINK_CMD_SIZE_V2 = 16

    def __init__(self, dbg=None, idVendor=0x0483, idProduct=0x3748):
        self._dbg = dbg
        self._dbg.debug("Connecting to ST-Link/V2 %04x:%04x" % (idVendor, idProduct))
        self._dev = usb.core.find(idVendor=idVendor, idProduct=idProduct)
        if self._dev is None:
            raise lib.stlinkex.StlinkException('ST-Link/V2 is not connected')
        self._dev.set_configuration()
        self._dbg.verbose("Successfully connected to ST-Link/V2")

    def _write(self, data):
        self._dbg.debug("  USB > %s" % ' '.join(['%02x' % i for i in data]))
        count = self._dev.write(0x02, data, 0)
        if count != len(data):
            raise lib.stlinkex.StlinkException("Error, only %d Bytes was transmitted to ST-Link instead of expected %d" % (count, len(data)))

    def _read(self, size):
        data = self._dev.read(0x81, size, 0).tolist()
        self._dbg.debug("  USB < %s" % ' '.join(['%02x' % i for i in data]))
        return data

    def xfer(self, cmd, data=None, rx_len=None):
        if len(cmd) > self.STLINK_CMD_SIZE_V2:
            raise lib.stlinkex.StlinkException("Error too many Bytes in command: %d, maximum is %d" % (len(cmd), self.STLINK_CMD_SIZE_V2))
        # pad to 16 bytes
        cmd += [0] * (self.STLINK_CMD_SIZE_V2 - len(cmd))
        self._write(cmd)
        if data:
            self._write(data)
        if rx_len:
            return self._read(rx_len)
        return None
