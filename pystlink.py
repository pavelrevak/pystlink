import sys
import lib.stlinkusb
import lib.stlinkv2
import lib.stlinkstm32
import lib.stm32
import lib.stlinkex
import lib.dbg


class App():
    def __init__(self):
        self._dbg = lib.dbg.Dbg(verbose=1)
        self._connector = None
        self._driver = None
        self._stlink = None

    def print_version(self):
        print("  ST-LinkV2 for python v0.0.0")
        print("(c)2015 by pavel.revak@gmail.com")
        print("https://github.com/pavelrevak/pystlink")

    def print_help(self):
        self.print_version()
        print()
        print("usage:")
        print("  %s [commands ...]" % sys.argv[0])
        print()
        print("commands:")
        print("  help - show help")
        print("  version - show version")
        print("  verbose:{level} - set verbose level from 0 - minimal to 3 - maximal")
        print("  cpu[:{cputype}] - connect and detect CPU, set expected cputype, eg: STM32F051R8 or STM32L4")
        print()
        print("  dump:registers - print all registers")
        print("  dump:flash - print content of FLASH memory")
        print("  dump:sram - print content of SRAM memory")
        print("  dump:mem:{addr}:{size} - print content of memory")
        print("  dump:reg:{addr} - print content of 32 bit register")
        print("  dump:reg16:{addr} - print content of 16 bit register")
        print("  dump:reg8:{addr} - print content of 8 bit register")
        print()
        print("  download:mem:{addr}:{size}:{file} - download memory into file")
        print("  download:sram:{file} - download SRAM into file")
        print("  download:flash:{file} - download FLASH into file")
        print()
        print("  write:reg:{addr}:{data} - write 32 bit register")
        print()
        print("  upload:mem:{addr}:{file} - upload file into memory (not for writing FLASH, only SRAM or registers")
        print()
        print("examples:")
        print("  %s help" % sys.argv[0])
        print("  %s cpu dump:mem:0x08000000:256" % sys.argv[0])
        print("  %s verbose:2 cpu:STM32F051R8" % sys.argv[0])
        print("  %s verbose:0 cpu:STM32F03 dump:flash dump:sram" % sys.argv[0])
        print("  %s cpu dump:registers download:sram:aaa.bin download:flash:bbb.bin" % sys.argv[0])

    def parse_cpu(self, params):
        cpu = None
        if params:
            cpu = params[0]
        self._connector = lib.stlinkusb.StlinkUsbConnector(dbg=self._dbg)
        self._driver = lib.stlinkv2.StlinkDriver(self._connector, dbg=self._dbg)
        self._stlink = lib.stlinkstm32.StlinkStm32(self._driver, lib.stm32.DEVICES, dbg=self._dbg)
        self._stlink.detect(cpu)

    def print_mem(self, mem, bytes_per_line=16):
        addr, data = mem
        prev_chunk = []
        same_chunk = False
        for i in range(0, len(data), bytes_per_line):
            chunk = data[i:i + bytes_per_line]
            if prev_chunk != chunk:
                print('  %08x  %s%s  %s' % (
                    addr,
                    ' '.join(['%02x' % d for d in chunk]),
                    '   ' * (16 - len(chunk)),
                    ''.join([chr(d) if d >= 32 and d < 127 else '\u00B7' for d in chunk]),
                ))
                prev_chunk = chunk
                same_chunk = False
            elif not same_chunk:
                print('  *')
                same_chunk = True
            addr += len(chunk)
        print('  %08x' % addr)

    def parse_dump(self, params):
        if self._stlink is None or self._stlink._mcus is None:
            raise lib.stlinkex.StlinkExceptionCpuNotSelected()
        cmd = params[0]
        params = params[1:]
        if cmd == 'registers':
            self._stlink.dump_registers()
        elif cmd == 'flash':
            mem = self._stlink.read_flash()
            self.print_mem(mem)
        elif cmd == 'sram':
            mem = self._stlink.read_sram()
            self.print_mem(mem)
        elif cmd == 'mem' and len(params) > 1:
            mem = self._stlink.get_mem(int(params[0], 0), int(params[1], 0))
            self.print_mem(mem)
        elif (cmd == 'reg' or cmd == 'reg32') and params:
            addr = int(params[0], 0)
            reg = self._driver.get_debugreg32(addr)
            print('  %08x: %08x' % (addr, reg))
        elif cmd == 'reg16' and params:
            addr = int(params[0], 0)
            reg = self._driver.get_debugreg16(addr)
            print('  %08x: %04x' % (addr, reg))
        elif cmd == 'reg8' and params:
            addr = int(params[0], 0)
            reg = self._driver.get_debugreg8(addr)
            print('  %08x: %02x' % (addr, reg))
        else:
            raise lib.stlinkex.StlinkExceptionBadParam()

    def store_file(self, mem, filename):
        addr, data = mem
        with open(filename, 'wb') as f:
            f.write(bytes(data))

    def read_file(self, filename, size=None):
        with open(filename, 'rb') as f:
            return list(f.read())

    def parse_download(self, params):
        if self._stlink is None or self._stlink._mcus is None:
            raise lib.stlinkex.StlinkExceptionCpuNotSelected()
        cmd = params[0]
        params = params[1:]
        if cmd == 'mem' and len(params) > 2:
            mem = self._stlink.read_mem(int(params[0], 0), int(params[1], 0))
            self.store_file(mem, params[2])
        elif cmd == 'flash' and params:
            mem = self._stlink.read_flash()
            self.store_file(mem, params[0])
        elif cmd == 'sram' and params:
            mem = self._stlink.read_sram()
            self.store_file(mem, params[0])
        else:
            raise lib.stlinkex.StlinkExceptionBadParam()

    def parse_write(self, params):
        if self._stlink is None or self._stlink._mcus is None:
            raise lib.stlinkex.StlinkExceptionCpuNotSelected()
        cmd = params[0]
        params = params[1:]
        if (cmd == 'reg') and params and len(params) > 1:
            addr = int(params[0], 0)
            data = int(params[1], 0)
            self._driver.set_debugreg32(addr, data)
        else:
            raise lib.stlinkex.StlinkExceptionBadParam()

    def parse_upload(self, params):
        if self._stlink is None or self._stlink._mcus is None:
            raise lib.stlinkex.StlinkExceptionCpuNotSelected()
        cmd = params[0]
        params = params[1:]
        if cmd == 'mem' and len(params) > 1:
            data = self.read_file(params[1])
            self._stlink.set_mem(int(params[0], 0), data)
        else:
            raise lib.stlinkex.StlinkExceptionBadParam()

    def parse_cmd(self, params):
        cmd = params[0]
        params = params[1:]
        if cmd == 'help':
            self.print_help()
        elif cmd == 'version':
            self.print_version()
        elif cmd == 'verbose' and params:
            self._dbg.set_verbose(int(params[0]))
        elif cmd == 'cpu':
            self.parse_cpu(params)
        elif cmd == 'dump' and params:
            self.parse_dump(params)
        elif cmd == 'download' and params:
            self.parse_download(params)
        elif cmd == 'write' and params:
            self.parse_write(params)
        elif cmd == 'upload' and params:
            self.parse_upload(params)
        else:
            raise lib.stlinkex.StlinkExceptionBadParam()

    def start(self):
        argv = sys.argv[1:]
        if not argv:
            self.print_help()
            return
        try:
            for arg in sys.argv[1:]:
                try:
                    self.parse_cmd(arg.split(':'))
                except lib.stlinkex.StlinkExceptionBadParam as e:
                    raise e.set_cmd(arg)
            self._dbg.debug('DONE', 2)
        except lib.stlinkex.StlinkException as e:
            self._dbg.debug(e, level=0)
        except KeyboardInterrupt:
            self._dbg.debug('Keyboard interrupt', level=0)
        if self._stlink and self._stlink._mcus:
            try:
                self._stlink.disconnect()
            except lib.stlinkex.StlinkException as e:
                self._dbg.debug(e, level=0)


if __name__ == "__main__":
    app = App()
    app.start()
