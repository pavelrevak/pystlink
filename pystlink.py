import sys
import lib.stlinkusb
import lib.stlinkv2
import lib.stlinkstm32
import lib.stm32
import lib.stlinkex
import lib.dbg


class App():
    REGISTERS = ['R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9', 'R10', 'R11', 'R12', 'SP', 'LR', 'PC', 'PSR', 'MSP', 'PSP']

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
        print("  v:{level} - set verbose level from 0 - minimal to 3 - maximal (can also use between commands)")
        print("  cpu[:{cputype}] - connect and detect CPU, set expected cputype, eg: STM32F051R8 or STM32L4")
        print()
        print("  dump:reg:all - print all registers (halt core)")
        print("  dump:reg:{reg_name} - print register (halt core)")
        print("  dump:reg:{addr} - print content of 32 bit memory register")
        print("  dump:reg16:{addr} - print content of 16 bit memory register")
        print("  dump:reg8:{addr} - print content of 8 bit memory register")
        print("  dump:mem:{addr}:{size} - print content of memory")
        print("  dump:flash - print content of FLASH memory")
        print("  dump:sram - print content of SRAM memory")
        print()
        print("  download:mem:{addr}:{size}:{file} - download memory into file")
        print("  download:sram:{file} - download SRAM into file")
        print("  download:flash:{file} - download FLASH into file")
        print()
        print("  write:reg:{reg_name}:{data} - write register (halt core)")
        print("  write:reg:{addr}:{data} - write 32 bit memory register")
        print()
        print("  upload:mem:{addr}:{file} - upload file into memory (not for writing FLASH, only SRAM or registers)")
        print()
        print("  core:reset - reset core")
        print("  core:reset:halt - reset and halt core")
        print("  core:halt - halt core")
        print("  core:step - step core")
        print("  core:run - run core")
        print()
        print("  norun - don't run core when disconnecting from ST-Link (when program end)")
        print()
        print("examples:")
        print("  %s help" % sys.argv[0])
        print("  %s cpu dump:mem:0x08000000:256" % sys.argv[0])
        print("  %s v:2 cpu:STM32F051R8" % sys.argv[0])
        print("  %s v:0 cpu:STM32F03 dump:flash dump:sram" % sys.argv[0])
        print("  %s cpu write:reg:0x48000018:0x00000100 dump:reg:0x48000014" % sys.argv[0])
        print("  %s cpu download:sram:aaa.bin download:flash:bbb.bin" % sys.argv[0])
        print("  %s cpu norun core:reset:halt dump:reg:pc core:step dump:reg:all" % sys.argv[0])

    def cmd_cpu(self, params):
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

    def cmd_dump(self, params):
        if self._stlink is None or self._stlink._mcus is None:
            raise lib.stlinkex.StlinkExceptionCpuNotSelected()
        cmd = params[0]
        params = params[1:]
        if (cmd == 'reg') and params:
            if params[0].upper() in App.REGISTERS:
                # register
                self._stlink.core_halt()
                reg = params[0].upper()
                if reg not in App.REGISTERS:
                    raise lib.stlinkex.StlinkException('Wrong register name')
                print("  %3s: %08x" % (reg, self._driver.get_reg(App.REGISTERS.index(reg))))
            elif params[0] == 'all':
                self._stlink.core_halt()
                for i in range(len(App.REGISTERS)):
                    print("  %3s: %08x" % (App.REGISTERS[i], self._driver.get_reg(i)))
            else:
                # memory register
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
        elif cmd == 'mem' and len(params) > 1:
            mem = self._stlink.get_mem(int(params[0], 0), int(params[1], 0))
            self.print_mem(mem)
        elif cmd == 'flash':
            if params:
                mem = self._stlink.read_flash(int(params[0], 0))
            else:
                mem = self._stlink.read_flash()
            self.print_mem(mem)
        elif cmd == 'sram':
            if params:
                mem = self._stlink.read_sram(int(params[0], 0))
            else:
                mem = self._stlink.read_sram()
            self.print_mem(mem)
        else:
            raise lib.stlinkex.StlinkExceptionBadParam()

    def store_file(self, mem, filename):
        addr, data = mem
        with open(filename, 'wb') as f:
            f.write(bytes(data))

    def read_file(self, filename, size=None):
        with open(filename, 'rb') as f:
            return list(f.read())

    def cmd_download(self, params):
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

    def cmd_write(self, params):
        if self._stlink is None or self._stlink._mcus is None:
            raise lib.stlinkex.StlinkExceptionCpuNotSelected()
        cmd = params[0]
        params = params[1:]
        if (cmd == 'reg') and len(params) > 1:
            data = int(params[1], 0)
            if params[0].upper() in App.REGISTERS:
                # register
                self._stlink.core_halt()
                reg = params[0].upper()
                if reg not in App.REGISTERS:
                    raise lib.stlinkex.StlinkException('Wrong register name')
                self._driver.set_reg(App.REGISTERS.index(reg), data)
            else:
                # memory register
                addr = int(params[0], 0)
                self._driver.set_debugreg32(addr, data)
        else:
            raise lib.stlinkex.StlinkExceptionBadParam()

    def cmd_upload(self, params):
        if self._stlink is None or self._stlink._mcus is None:
            raise lib.stlinkex.StlinkExceptionCpuNotSelected()
        cmd = params[0]
        params = params[1:]
        if cmd == 'mem' and len(params) > 1:
            data = self.read_file(params[1])
            self._stlink.set_mem(int(params[0], 0), data)
        else:
            raise lib.stlinkex.StlinkExceptionBadParam()

    def cmd_core(self, params):
        if self._stlink is None or self._stlink._mcus is None:
            raise lib.stlinkex.StlinkExceptionCpuNotSelected()
        cmd = params[0]
        params = params[1:]
        if cmd == 'resetsys':
            self._driver.debug_resetsys()
        elif cmd == 'reset':
            if params:
                if params[0] == 'halt':
                    self._stlink.core_reset_halt()
                else:
                    raise lib.stlinkex.StlinkExceptionBadParam()
            else:
                self._stlink.core_reset()
        elif cmd == 'halt':
            self._stlink.core_halt()
        elif cmd == 'step':
            self._stlink.core_step()
        elif cmd == 'run':
            self._stlink.core_run()
        else:
            raise lib.stlinkex.StlinkExceptionBadParam()

    def cmd(self, params):
        cmd = params[0]
        params = params[1:]
        if cmd == 'help':
            self.print_help()
        elif cmd == 'version':
            self.print_version()
        elif cmd == 'v' and params:
            self._dbg.set_verbose(int(params[0]))
        elif cmd == 'cpu':
            self.cmd_cpu(params)
        elif cmd == 'dump' and params:
            self.cmd_dump(params)
        elif cmd == 'download' and params:
            self.cmd_download(params)
        elif cmd == 'write' and params:
            self.cmd_write(params)
        elif cmd == 'upload' and params:
            self.cmd_upload(params)
        elif cmd == 'core' and params:
            self.cmd_core(params)
        elif cmd == 'norun':
            self._stlink.set_norun()
        else:
            raise lib.stlinkex.StlinkExceptionBadParam()

    def start(self):
        argv = sys.argv[1:]
        if not argv:
            self.print_help()
            return
        try:
            for arg in sys.argv[1:]:
                self._dbg.debug('CMD: %s' % arg, 3)
                try:
                    self.cmd(arg.split(':'))
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
