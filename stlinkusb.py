import usb.core
import usb.util
import stlinkex


class StlinkUsb():
    STLINK_CMD_SIZE_V2 = 16

    def __init__(self, verbose=0):
        self._verbose = verbose
        self._dev = usb.core.find(idVendor=0x0483, idProduct=0x3748)
        if self._dev is None:
            raise stlinkex.StlinkException('ST-LINK v2 not connected')
        self._dev.set_configuration()
        self.debug("successfully connected to stlink", 1)

    def debug(self, msg, level=0):
        if self._verbose >= level:
            print(msg)
    def set_verbose(self, verbose):
        self._verbose = verbose

    def xfer(self, tx, rx_len=0):
        tx_len = len(tx)
        if tx_len > self.STLINK_CMD_SIZE_V2:
            raise stlinkex.StlinkException("Too many tx bytes: %d, maximum is %d" % (tx_len, self.STLINK_CMD_SIZE_V2))
        # pad to 16 bytes
        tx += [0] * (self.STLINK_CMD_SIZE_V2 - tx_len)
        self.debug("  USB > %s" % ' '.join(['%02x' % i for i in tx]), level=3)
        count = self._dev.write(0x02, tx, 0)
        if count != self.STLINK_CMD_SIZE_V2:
            raise stlinkex.StlinkException("Only %d bytes was transmitted to Stlink instead of %d" % (count, self.STLINK_CMD_SIZE_V2))
        if rx_len:
            rx = self._dev.read(0x81, rx_len, 0).tolist()
            self.debug("  USB < %s" % ' '.join(['%02x' % i for i in rx]), level=3)
            return rx
