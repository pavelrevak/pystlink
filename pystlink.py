import sys
import lib.stlinkusb
import lib.stlinkv2
import lib.stm32
import lib.stm32devices
import lib.stlinkex
import lib.dbg


class PyStlink():
    def __init__(self, dbg):
        self._dbg = dbg
        self._connector = None
        self._stlink = None
        self._driver = None
        self._stay_in_debug = False

    def print_version(self):
        print("  ST-LinkV2 for python v0.0.0")
        print("(c)2015 by pavel.revak@gmail.com")
        print("https://github.com/pavelrevak/pystlink")
        print()

    def print_help(self):
        self.print_version()
        print("usage:")
        print("  %s [options|verbose] [commands|verbose ...]" % sys.argv[0])
        print()
        print("options:")
        print("  --help -h          show this help")
        print("  --version -V       show version")
        print("  --cpu -c {cputype} set expected cputype, eg: STM32F051R8 or STM32L4")
        print()
        print("verbose:")
        print("  all verbose modes can also use between any commands (to configure verbosity of any commands)")
        print("  -q                 set quiet")
        print("  -i                 set info (default)")
        print("  -v                 set verbose")
        print("  -d                 set debug")
        print()
        print("commands:")
        print("  dump:reg:all - print all registers (halt core)")
        print("  dump:reg:{reg_name} - print register (halt core)")
        print("  dump:reg:{addr} - print content of 32 bit memory register")
        print("  dump:reg16:{addr} - print content of 16 bit memory register")
        print("  dump:reg8:{addr} - print content of 8 bit memory register")
        print("  dump:mem:{addr}:{size} - print content of memory")
        print("  dump:flash[:{size}] - print content of FLASH memory")
        print("  dump:sram[:{size}] - print content of SRAM memory")
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
        print("  %s --help" % sys.argv[0])
        print("  %s -V --cpu STM32F051R8" % sys.argv[0])
        print("  %s -q --cpu STM32F03 dump:flash dump:sram" % sys.argv[0])
        print("  %s dump:mem:0x08000000:256" % sys.argv[0])
        print("  %s write:reg:0x48000018:0x00000100 dump:reg:0x48000014" % sys.argv[0])
        print("  %s download:sram:aaa.bin download:flash:bbb.bin" % sys.argv[0])
        print("  %s norun core:reset:halt dump:reg:pc core:step dump:reg:all" % sys.argv[0])
        print()

    def find_mcus_by_core(self):
        CPUID_REG = 0xe000ed00
        cpuid = self._stlink.get_debugreg32(CPUID_REG)
        self._dbg.msg("CPUID:  %08x" % cpuid, 2)
        partno = 0xfff & (cpuid >> 4)
        for mcu_core in lib.stm32devices.DEVICES:
            if mcu_core['part_no'] == partno:
                self._mcus_by_core = mcu_core
                return
        raise lib.stlinkex.StlinkException('PART_NO: 0x%03x is not supported' % partno)

    def find_mcus_by_devid(self):
        idcode = self._stlink.get_debugreg32(self._mcus_by_core['idcode_reg'])
        self._dbg.msg("IDCODE: %08x" % idcode, 2)
        devid = 0xfff & idcode
        for mcu_devid in self._mcus_by_core['devices']:
            if mcu_devid['dev_id'] == devid:
                self._mcus_by_devid = mcu_devid
                return
        raise lib.stlinkex.StlinkException('DEV_ID: 0x%03x is not supported' % devid)

    def find_mcus_by_flash_size(self):
        self._flash_size = self._stlink.get_debugreg16(self._mcus_by_devid['flash_size_reg'])
        self._mcus = []
        for mcu in self._mcus_by_devid['devices']:
            if mcu['flash_size'] == self._flash_size:
                self._mcus.append(mcu)
        if not self._mcus:
            raise lib.stlinkex.StlinkException('Connected CPU with DEV_ID: 0x%03x and FLASH size: %dKB is not supported' % (
                self._mcus_by_devid['dev_id'], self._flash_size
            ))

    def find_mcus_by_mcu_type(self, mcu_type):
        mcu_type = mcu_type.upper()
        if not mcu_type.startswith('STM32'):
            raise lib.stlinkex.StlinkException('Selected CPU is not STM32 family')
        # change character on 10 position to 'x' where is package size code
        if len(mcu_type) > 9:
            mcu_type = list(mcu_type)
            mcu_type[9] = 'x'
            mcu_type = ''.join(mcu_type)
        mcus = []
        for mcu in self._mcus:
            if mcu['type'].startswith(mcu_type):
                mcus.append(mcu)
        if not mcus:
            raise lib.stlinkex.StlinkException('Connected CPU is not %s but detected is %s %s' % (
                mcu_type,
                'one of' if len(self._mcus) > 1 else '',
                ','.join([mcu['type'] for mcu in self._mcus]),
            ))
        return mcus

    def find_sram_eeprom_size(self):
        # if is found more MCUS, then SRAM and EEPROM size
        # will be used the smallest of all (worst case)
        self._sram_size = min([mcu['sram_size'] for mcu in self._mcus])
        self._eeprom_size = min([mcu['eeprom_size'] for mcu in self._mcus])
        self._dbg.msg("SRAM:   %dKB" % self._sram_size)
        if self._eeprom_size:
            self._dbg.msg("EEPROM: %dKB" % self._eeprom_size)
        if len(self._mcus) > 1:
            diff = False
            if self._sram_size != max([mcu['sram_size'] for mcu in self._mcus]):
                diff = True
                self._dbg.msg(" * Detected CPUs have different SRAM sizes.")
            if self._eeprom_size != max([mcu['eeprom_size'] for mcu in self._mcus]):
                diff = True
                self._dbg.msg(" * Detected CPUs have different EEPROM sizes.")
            if diff:
                self._dbg.msg(" * Is recommended to select certain CPU with --cpu {cputype}. Now is used the smallest memory size.")

    def load_driver(self):
        if self._mcus[0]['type'].startswith('STM32F0'):
            self._driver = lib.stm32.Stm32F0(self._stlink, dbg=self._dbg)
        else:
            self._driver = lib.stm32.Stm32(self._stlink, dbg=self._dbg)

    def is_mcu_selected(self):
        return bool(self._driver)

    def detect_cpu(self, cpu_type=None):
        self._connector = lib.stlinkusb.StlinkUsbConnector(dbg=self._dbg)
        self._stlink = lib.stlinkv2.Stlink(self._connector, dbg=self._dbg)
        self._dbg.msg("STLINK: %s" % self._stlink.ver_str, level=1)
        self._dbg.msg("SUPPLY: %.2fV" % self._stlink.target_voltage, level=1)
        self._dbg.msg("COREID: %08x" % self._stlink.coreid, level=2)
        if self._stlink.coreid == 0:
            raise lib.stlinkex.StlinkException('Not connected to CPU')
        self.find_mcus_by_core()
        self._dbg.msg("CORE:   %s" % self._mcus_by_core['core'])
        self.find_mcus_by_devid()
        self.find_mcus_by_flash_size()
        if cpu_type:
            # filter found MCUs by selected MCU type
            self._mcus = self.find_mcus_by_mcu_type(cpu_type)
        self._dbg.msg("MCU:    %s" % '/'.join([mcu['type'] for mcu in self._mcus]))
        self._dbg.msg("FLASH:  %dKB" % self._flash_size)
        self.find_sram_eeprom_size()
        self.load_driver()

    def print_buffer(self, mem, bytes_per_line=16):
        addr, data = mem
        prev_chunk = []
        same_chunk = False
        for i in range(0, len(data), bytes_per_line):
            chunk = data[i:i + bytes_per_line]
            if prev_chunk != chunk:
                print('%08x  %s%s  %s' % (
                    addr,
                    ' '.join(['%02x' % d for d in chunk]),
                    '   ' * (16 - len(chunk)),
                    ''.join([chr(d) if d >= 32 and d < 127 else '\u00B7' for d in chunk]),
                ))
                prev_chunk = chunk
                same_chunk = False
            elif not same_chunk:
                print('*')
                same_chunk = True
            addr += len(chunk)
        print('%08x' % addr)

    def store_file(self, mem, filename):
        addr, data = mem
        with open(filename, 'wb') as f:
            f.write(bytes(data))

    def read_file(self, filename, size=None):
        with open(filename, 'rb') as f:
            return list(f.read())

    def cmd_dump(self, params):
        if self._driver is None or not self.is_mcu_selected():
            raise lib.stlinkex.StlinkExceptionCpuNotSelected()
        cmd = params[0]
        params = params[1:]
        if (cmd == 'reg') and params:
            if self._driver.is_reg(params[0]):
                self._driver.core_halt()
                reg = params[0].upper()
                print("  %3s: %08x" % (reg, self._driver.get_reg(reg)))
            elif params[0] == 'all':
                self._driver.core_halt()
                for reg, val in self._driver.get_reg_all():
                    print("  %3s: %08x" % (reg, val))
            else:
                addr = int(params[0], 0)
                reg = self._stlink.get_debugreg32(addr)
                print('  %08x: %08x' % (addr, reg))
        elif cmd == 'reg16' and params:
            addr = int(params[0], 0)
            reg = self._stlink.get_debugreg16(addr)
            print('  %08x: %04x' % (addr, reg))
        elif cmd == 'reg8' and params:
            addr = int(params[0], 0)
            reg = self._stlink.get_debugreg8(addr)
            print('  %08x: %02x' % (addr, reg))
        elif cmd == 'mem' and len(params) > 1:
            mem = self._driver.get_mem(int(params[0], 0), int(params[1], 0))
            self.print_buffer(mem)
        elif cmd == 'flash':
            size = int(params[0], 0) if params else self._flash_size * 1024
            addr = self._driver.FLASH_START
            mem = self._driver.get_mem(addr, size)
            self.print_buffer(mem)
        elif cmd == 'sram':
            size = int(params[0], 0) if params else self._sram_size * 1024
            addr = self._driver.SRAM_START
            mem = self._driver.get_mem(addr, size)
            self.print_buffer(mem)
        else:
            raise lib.stlinkex.StlinkExceptionBadParam()

    def cmd_download(self, params):
        if self._driver is None or not self.is_mcu_selected():
            raise lib.stlinkex.StlinkExceptionCpuNotSelected()
        cmd = params[0]
        params = params[1:]
        if cmd == 'mem' and len(params) > 2:
            mem = self._driver.get_mem(int(params[0], 0), int(params[1], 0))
            self.store_file(mem, params[2])
        elif cmd == 'flash' and params:
            size = int(params[0], 0) if len(params) == 2 else self._flash_size * 1024
            addr = self._driver.FLASH_START
            mem = self._driver.get_mem(addr, size)
            self.store_file(mem, params[-1])
        elif cmd == 'sram' and params:
            size = int(params[0], 0) if len(params) == 2 else self._sram_size * 1024
            addr = self._driver.SRAM_START
            mem = self._driver.get_mem(addr, size)
            self.store_file(mem, params[-1])
        else:
            raise lib.stlinkex.StlinkExceptionBadParam()

    def cmd_write(self, params):
        if self._driver is None or not self.is_mcu_selected():
            raise lib.stlinkex.StlinkExceptionCpuNotSelected()
        cmd = params[0]
        params = params[1:]
        if (cmd == 'reg') and len(params) > 1:
            data = int(params[1], 0)
            if self._driver.is_reg(params[0]):
                self._driver.core_halt()
                reg = params[0].upper()
                self._driver.set_reg(reg, data)
            else:
                addr = int(params[0], 0)
                self._stlink.set_debugreg32(addr, data)
        else:
            raise lib.stlinkex.StlinkExceptionBadParam()

    def cmd_upload(self, params):
        if self._driver is None or not self.is_mcu_selected():
            raise lib.stlinkex.StlinkExceptionCpuNotSelected()
        cmd = params[0]
        params = params[1:]
        if cmd == 'mem' and len(params) > 1:
            data = self.read_file(params[1])
            self._driver.set_mem(int(params[0], 0), data)
        else:
            raise lib.stlinkex.StlinkExceptionBadParam()

    def cmd_flash(self, params):
        if self._driver is None or not self.is_mcu_selected():
            raise lib.stlinkex.StlinkExceptionCpuNotSelected()
        cmd = params[0]
        params = params[1:]
        if cmd == 'erase':
            block_addr = int(params[0], 0) if params else None
            self._driver.flash_erase(block_addr)
        elif cmd == 'write' and params:
            data = self.read_file(params[0])
            start_addr = int(params[1], 0) if len(params) > 1 else None
            self._driver.flash_write(start_addr, data)
        else:
            raise lib.stlinkex.StlinkExceptionBadParam()

    def cmd_core(self, params):
        if self._driver is None or not self.is_mcu_selected():
            raise lib.stlinkex.StlinkExceptionCpuNotSelected()
        cmd = params[0]
        params = params[1:]
        # if cmd == 'resetsys':
        #     self._stlink.debug_resetsys()
        if cmd == 'reset':
            if params:
                if params[0] == 'halt':
                    self._driver.core_reset_halt()
                else:
                    raise lib.stlinkex.StlinkExceptionBadParam()
            else:
                self._driver.core_reset()
        elif cmd == 'halt':
            self._driver.core_halt()
        elif cmd == 'step':
            self._driver.core_step()
        elif cmd == 'run':
            self._driver.core_run()
        else:
            raise lib.stlinkex.StlinkExceptionBadParam()

    def cmd(self, params):
        cmd = params[0]
        params = params[1:]
        if cmd == 'dump' and params:
            self.cmd_dump(params)
        elif cmd == 'download' and params:
            self.cmd_download(params)
        elif cmd == 'write' and params:
            self.cmd_write(params)
        elif cmd == 'upload' and params:
            self.cmd_upload(params)
        elif cmd == 'flash' and params:
            self.cmd_flash(params)
        elif cmd == 'core' and params:
            self.cmd_core(params)
        elif cmd == 'norun':
            self._stay_in_debug = True
        else:
            raise lib.stlinkex.StlinkExceptionBadParam()

    def start(self):
        VERBOSE_CMDS = {'-q': 0, '-i': 1, '-v': 2, '-d': 3}
        argv = sys.argv[1:]
        if argv:
            if argv[0] in ['--help', '-h']:
                self.print_help()
                return
            if argv[0] in ['--version']:
                self.print_version()
                return
            if argv[0] in VERBOSE_CMDS:
                self._dbg.set_verbose(VERBOSE_CMDS[argv[0]])
                argv = argv[1:]
        else:
            self.print_help()
        try:
            if argv and (argv[0] in ['--cpu', '-c']):
                argv = argv[1:]
                if not argv:
                    raise lib.stlinkex.StlinkException('CPU type is not set')
                self.detect_cpu(argv[0])
                argv = argv[1:]
            else:
                self.detect_cpu(None)
            while argv:
                if argv[0] in VERBOSE_CMDS:
                    self._dbg.set_verbose(VERBOSE_CMDS[argv[0]])
                else:
                    self._dbg.debug('CMD: %s' % argv[0], 2)
                    try:
                        self.cmd(argv[0].split(':'))
                    except lib.stlinkex.StlinkExceptionBadParam as e:
                        raise e.set_cmd(argv[0])
                argv = argv[1:]
        except lib.stlinkex.StlinkException as e:
            self._dbg.debug(e, level=0)
        except KeyboardInterrupt:
            self._dbg.debug('Keyboard interrupt', level=0)
        if self._driver and self.is_mcu_selected():
            try:
                if self.is_mcu_selected() and not self._stay_in_debug:
                    self._driver.core_nodebug()
                self._stlink.leave_state()
            except lib.stlinkex.StlinkException as e:
                self._dbg.debug(e, level=0)
        self._dbg.debug('DONE', 2)


if __name__ == "__main__":
    dbg = lib.dbg.Dbg(verbose=1)
    pystlink = PyStlink(dbg=dbg)
    pystlink.start()
