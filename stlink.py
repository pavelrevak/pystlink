import sys
import lib.stlinkv2
import lib.stlinkex
import lib.stlinkstm32
import lib.dbg


# PARTNO = {
#     0xc20: {
#         'type': 'CortexM0',
#         'DBGMCU_IDCODE_addr': 0x40015800,
#     },
#     0xc60: {
#         'type': 'CortexM0+',
#         'DBGMCU_IDCODE_addr': 0x40015800,
#     },
#     0xc23: {
#         'type': 'CortexM3',
#         'DBGMCU_IDCODE_addr': 0xE0042000,
#     },
#     0xc24: {
#         'type': 'CortexM4',
#         'DBGMCU_IDCODE_addr': 0xE0042000,
#     },
#     0xc27: {
#         'type': 'CortexM4',
#         'DBGMCU_IDCODE_addr': 0xE0042000,
#     },
# }

# MCUS = [
#     {
#         'dev_id': 0x413,
#         'type': 'STM32F405/407/415/417',
#         'sram_start': 0x20000000,
#         'sram_size': 192 * 1024,
#         'flash_start': 0x08000000,
#         'flashsize_reg': 0x1fff7a22,
#         'flashpagesize': None,
#     }, {
#         'dev_id': 0x419,
#         'type': 'STM32F42x/43x',
#         'sram_start': 0x20000000,
#         'sram_size': 256 * 1024,
#         'flash_start': 0x08000000,
#         'flashsize_reg': 0x1fff7a22,
#         'flashpagesize': None,
#     }, {
#         'dev_id': 0x440,
#         'type': 'STM32F05x',
#         'sram_start': 0x20000000,
#         'sram_size': 8 * 1024,
#         'flash_start': 0x08000000,
#         'flashsize_reg': 0x1ffff7cc,
#         'flashpagesize': 1024,
#     }, {
#         # this MCU will be detected as STM32F05x
#         'dev_id': 0x440,
#         'type': 'STM32F030x8',
#         'sram_start': 0x20000000,
#         'sram_size': 8 * 1024,
#         'flash_start': 0x08000000,
#         'flashsize_reg': 0x1ffff7cc,
#         'flashpagesize': 1024,
#     }, {
#         'dev_id': 0x444,
#         'type': 'STM32F03x',
#         'sram_start': 0x20000000,
#         'sram_size': 4 * 1024,
#         'flash_start': 0x08000000,
#         'flashsize_reg': 0x1ffff7cc,
#         'flashpagesize': 1024,
#     }, {
#         'dev_id': 0x445,
#         'type': 'STM32F04x',
#         'sram_start': 0x20000000,
#         'sram_size': 6 * 1024,
#         'flash_start': 0x08000000,
#         'flashsize_reg': 0x1ffff7cc,
#         'flashpagesize': 1024,
#     }, {
#         'dev_id': 0x448,
#         'type': 'STM32F07x',
#         'sram_start': 0x20000000,
#         'sram_size': 16 * 1024,
#         'flash_start': 0x08000000,
#         'flashsize_reg': 0x1ffff7cc,
#         'flashpagesize': 2 * 1024,
#     },
# ]

class App():
    def __init__(self):
        self._dbg = lib.dbg.Dbg(verbose=1)
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
        # print("  write:reg:{data}:{addr} - write 32 bit register")
        # print()
        # print("  upload:mem:{file}:{addr}[:{size}] - upload file into memory")
        # print()
        print("example:")
        print("  %s verbose:1 cpu dump:registers dump:mem:0x08000000:256 dump:reg:0xe000ed00 download:flash:stmflash.bin" % sys.argv[0])

    def parse_cpu(self, params):
        cpu = None
        if params:
            cpu = params[0]
        self._stlink = lib.stlinkstm32.StlinkStm32(dbg=self._dbg)
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
            addr += bytes_per_line

    def parse_dump(self, params):
        if self._stlink is None or self._stlink._mcus is None:
            raise lib.stlinkex.StlinkException('CPU is not selected')
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
            mem = self._stlink.read_mem(int(params[0], 0), int(params[1], 0))
            self.print_mem(mem)
        elif (cmd == 'reg' or cmd == 'reg32') and params:
            addr = int(params[0], 0)
            reg = self._stlink.get_debugreg(addr)
            print('  %08x: %08x' % (addr, reg))
        elif cmd == 'reg16' and params:
            addr = int(params[0], 0)
            reg = self._stlink.get_debugreg16(addr)
            print('  %08x: %04x' % (addr, reg))
        elif cmd == 'reg8' and params:
            addr = int(params[0], 0)
            reg = self._stlink.get_debugreg8(addr)
            print('  %08x: %02x' % (addr, reg))
        else:
            raise lib.stlinkex.StlinkException('Bad param: "dump:%s"' % cmd)

    def store_file(self, mem, filename):
        addr, data = mem
        with open(filename, 'wb') as f:
            f.write(bytes(data))

    def parse_download(self, params):
        if self._stlink is None or self._stlink._mcu is None:
            raise lib.stlinkex.StlinkException('CPU is not selected')
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
            raise lib.stlinkex.StlinkException('Bad param: "read:%s"' % cmd)

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
        else:
            raise lib.stlinkex.StlinkException('Bad param: "%s"' % cmd)

    def start(self):
        argv = sys.argv[1:]
        if not argv:
            self.print_help()
            return
        try:
            for arg in sys.argv[1:]:
                self.parse_cmd(arg.split(':'))
            self._dbg.debug('DONE', 2)
        except lib.stlinkex.StlinkException as e:
            self._dbg.debug(e, level=0)
        except KeyboardInterrupt:
            self._dbg.debug('Keyboard interrupt', level=0)
        if self._stlink and self._stlink._mcu_devid:
            try:
                self._stlink.disconnect()
            except lib.stlinkex.StlinkException as e:
                self._dbg.debug(e, level=0)


if __name__ == "__main__":
    app = App()
    app.start()
