import usb.core
import usb.util
import lib.stlinkex


class StlinkUsbConnector():
    STLINK_CMD_SIZE_V2 = 16

    DEV_TYPES = [
        {
            'version': 'V2',
            'idVendor': 0x0483,
            'idProduct': 0x3748,
            'outPipe': 0x02,
            'inPipe': 0x81,
        }, {
            'version': 'V2-1',
            'idVendor': 0x0483,
            'idProduct': 0x374b,
            'outPipe': 0x01,
            'inPipe': 0x81,
        }
    ]

    def __init__(self, dbg=None):
        self._dbg = dbg
        self._dev_type = None
        self._xfer_counter = 0
        devices = usb.core.find(find_all=True)
        for dev in devices:
            for dev_type in StlinkUsbConnector.DEV_TYPES:
                if dev.idVendor == dev_type['idVendor'] and dev.idProduct == dev_type['idProduct']:
                    self._dev = dev
                    self._dev_type = dev_type
                    self._dbg.verbose("Successfully connected to ST-Link/%s" % dev_type['version'])
                    return
        raise lib.stlinkex.StlinkException('ST-Link/V2 is not connected')

    @property
    def version(self):
        return self._dev_type['version']

    @property
    def xfer_counter(self):
        return self._xfer_counter

    def _write(self, data):
        self._dbg.debug("  USB > %s" % ' '.join(['%02x' % i for i in data]))
        self._xfer_counter += 1
        count = self._dev.write(self._dev_type['outPipe'], data, 1000)
        if count != len(data):
            raise lib.stlinkex.StlinkException("Error, only %d Bytes was transmitted to ST-Link instead of expected %d" % (count, len(data)))

    def _read(self, size):
        read_size = size
        if read_size < 64:
            read_size = 64
        elif read_size % 4:
            read_size += 3
            read_size &= 0xffc
        data = self._dev.read(self._dev_type['inPipe'], read_size, 1000).tolist()
        self._dbg.debug("  USB < %s" % ' '.join(['%02x' % i for i in data]))
        return data[:size]

    def xfer(self, cmd, data=None, rx_len=None):
        try:
            if len(cmd) > self.STLINK_CMD_SIZE_V2:
                raise lib.stlinkex.StlinkException("Error too many Bytes in command: %d, maximum is %d" % (len(cmd), self.STLINK_CMD_SIZE_V2))
            # pad to 16 bytes
            cmd += [0] * (self.STLINK_CMD_SIZE_V2 - len(cmd))
            self._write(cmd)
            if data:
                self._write(data)
            if rx_len:
                return self._read(rx_len)
        except usb.core.USBError as e:
            raise lib.stlinkex.StlinkException("USB Error: %s" % e)
        return None
