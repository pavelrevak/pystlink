import sys
import time
import lib.stlinkusb
import lib.stlinkv2
import lib.stm32
import lib.stm32fp
import lib.stm32fs
import lib.stm32devices
import lib.stlinkex
import lib.dbg
import lib.srec


class PyStlink():
    CPUID_REG = 0xe000ed00

    VERBOSE_CMDS = {
        '-q': 0, '--quiet': 0,
        '-i': 1, '--info': 1,
        '-v': 2, '--verbose': 2,
        '-d': 3, '--debug': 3
    }

    def __init__(self, dbg):
        self._start_time = time.time()
        self._dbg = dbg
        self._connector = None
        self._stlink = None
        self._driver = None
        self._stay_in_debug = False
        self._expected_cpu = None

    def print_version(self):
        print("  ST-LinkV2 for python v0.0.0")
        print("(c)2015 by pavel.revak@gmail.com")
        print("https://github.com/pavelrevak/pystlink")
        print()

    def print_help(self):
        self.print_version()
        print("usage:")
        print("  %s [options] [commands ...]" % sys.argv[0])
        print()
        print("options:")
        print("  -h --help          show this help")
        print("  -V --version       show version")
        print("  -n --norun         don't run core when disconnecting from ST-Link (when program end)")
        print("  -c --cpu {cputype} set expected cputype, eg: STM32F051R8 or STM32L4")
        print()
        print("verbose:")
        print("  all verbose modes can also use between any commands (to set verbosity of any commands)")
        print("  -q --quiet         set quiet")
        print("  -i --info          set info (default)")
        print("  -v --verbose       set verbose")
        print("  -d --debug         set debug")
        print()
        print("commands:")
        print("  (address and size can be in different numeric formats, like: 123, 0x1ac, 0o137, 0b1011)")
        print("  dump:core              print all core registers (halt core)")
        print("  dump:{reg}             print core register (halt core)")
        print("  dump:{addr}:{size}     print content of memory")
        print("  dump:sram[:{size}]     print content of SRAM memory")
        print("  dump:flash[:{size}]    print content of FLASH memory")
        print("  dump:{addr}            print content of 32 bit memory register")
        print("  dump16:{addr}          print content of 16 bit memory register")
        print("  dump8:{addr}           print content of 8 bit memory register")
        print()
        print("  write:{reg}:{data}     write register (halt core)")
        print("  write:{addr}:{data}    write 32 bit memory register")
        print()
        print("  download:{addr}:{size}:{file}      download memory with size into file")
        print("  download:sram[:{size}]:{file}      download SRAM into file")
        print("  download:flash[:{size}]:{file}     download FLASH into file")
        print()
        print("  fill:{addr}:{size}:{pattern}   fill memory with a pattern")
        print("  fill:sram[:{size}]:{pattern}   fill SRAM memory with a pattern")
        print()
        print("  upload:{file.srec}     upload SREC file into memory")
        print("  upload:{addr}:{file}   upload binary file into memory")
        print("  upload:sram:{file}     upload binary file into SRAM memory")
        print()
        print("  flash:erase            complete erase FLASH memory aka mass erase")
        print("  flash[:erase][:verify]:{file.srec}     erase + flash SREC file + verify")
        print("  flash[:erase][:verify][:{addr}]:{file} erase + flash binary file + verify")
        print()
        print("  reset                  reset core")
        print("  reset:halt             reset and halt core")
        print("  halt                   halt core")
        print("  step                   step core")
        print("  run                    run core")
        print()
        print("  sleep:{seconds}        sleep (float) - insert delay between commands")
        print()
        print("examples:")
        program_name = sys.argv[0]
        print("  %s --help" % program_name)
        print("  %s -v --cpu STM32F051R8" % program_name)
        print("  %s -q --cpu STM32F03 dump:flash dump:sram" % program_name)
        print("  %s dump:0x08000000:256" % program_name)
        print("  %s write:0x48000018:0x00000100 dump:0x48000014" % program_name)
        print("  %s download:sram:256:aaa.bin download:flash:bbb.bin" % program_name)
        print("  %s -n reset:halt write:pc:0x20000010 dump:pc core:step dump:all" % program_name)
        print("  %s flash:erase:verify:app.bin" % program_name)
        print("  %s flash:erase flash:verify:0x08010000:boot.bin" % program_name)
        print()

    def find_mcus_by_core(self):
        cpuid = self._stlink.get_debugreg32(PyStlink.CPUID_REG)
        self._dbg.verbose("CPUID:  %08x" % cpuid)
        partno = 0xfff & (cpuid >> 4)
        for mcu_core in lib.stm32devices.DEVICES:
            if mcu_core['part_no'] == partno:
                self._mcus_by_core = mcu_core
                return
        raise lib.stlinkex.StlinkException('PART_NO: 0x%03x is not supported' % partno)

    def find_mcus_by_devid(self):
        idcode = self._stlink.get_debugreg32(self._mcus_by_core['idcode_reg'])
        self._dbg.verbose("IDCODE: %08x" % idcode)
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
        self._dbg.info("SRAM:   %dKB" % self._sram_size)
        if self._eeprom_size:
            self._dbg.info("EEPROM: %dKB" % self._eeprom_size)
        if len(self._mcus) > 1:
            diff = False
            if self._sram_size != max([mcu['sram_size'] for mcu in self._mcus]):
                diff = True
                self._dbg.warning("Detected CPUs have different SRAM sizes.")
            if self._eeprom_size != max([mcu['eeprom_size'] for mcu in self._mcus]):
                diff = True
                self._dbg.warning("Detected CPUs have different EEPROM sizes.")
            if diff:
                self._dbg.warning("Is recommended to select certain CPU with --cpu {cputype}. Now is used the smallest memory size.")

    def load_driver(self):
        flash_driver = self._mcus_by_devid['flash_driver']
        if flash_driver == 'STM32FP':
            self._driver = lib.stm32fp.Stm32FP(self._stlink, dbg=self._dbg)
        elif flash_driver == 'STM32FPXL':
            self._driver = lib.stm32fp.Stm32FPXL(self._stlink, dbg=self._dbg)
        elif flash_driver == 'STM32FS':
            self._driver = lib.stm32fs.Stm32FS(self._stlink, dbg=self._dbg)
        else:
            self._driver = lib.stm32.Stm32(self._stlink, dbg=self._dbg)

    def is_mcu_selected(self):
        return bool(self._driver)

    def detect_cpu(self):
        self._connector = lib.stlinkusb.StlinkUsbConnector(dbg=self._dbg)
        self._stlink = lib.stlinkv2.Stlink(self._connector, dbg=self._dbg)
        self._dbg.info("DEVICE: ST-Link/%s" % self._stlink.ver_str)
        self._dbg.info("SUPPLY: %.2fV" % self._stlink.target_voltage)
        self._dbg.verbose("COREID: %08x" % self._stlink.coreid)
        if self._stlink.coreid == 0:
            raise lib.stlinkex.StlinkException('Not connected to CPU')
        self.find_mcus_by_core()
        self._dbg.info("CORE:   %s" % self._mcus_by_core['core'])
        self.find_mcus_by_devid()
        self.find_mcus_by_flash_size()
        if self._expected_cpu:
            # filter found MCUs by selected MCU type
            self._mcus = self.find_mcus_by_mcu_type(self._expected_cpu)
        self._dbg.info("MCU:    %s" % '/'.join([mcu['type'] for mcu in self._mcus]))
        self._dbg.info("FLASH:  %dKB" % self._flash_size)
        self.find_sram_eeprom_size()
        self.load_driver()

    def print_buffer(self, addr, data, bytes_per_line=16):
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

    def store_file(self, addr, data, filename):
        with open(filename, 'wb') as f:
            f.write(bytes(data))
            self._dbg.info("Saved %d Bytes into %s file" % (len(data), filename))

    def read_file(self, filename):
        if filename.endswith('.srec'):
            srec = lib.srec.Srec()
            srec.encode_file(filename)
            return srec.buffers
        with open(filename, 'rb') as f:
            data = list(f.read())
            self._dbg.info("Loaded %d Bytes from %s file" % (len(data), filename))
            return [(None, data)]
        raise lib.stlinkex.StlinkException("Error reading file")

    def dump_mem(self, addr, size):
        data = self._driver.get_mem(addr, size)
        self.print_buffer(addr, data)

    def cmd_dump(self, params):
        cmd = params[0]
        params = params[1:]
        if cmd == 'core':
            # dump all core registers
            self._driver.core_halt()
            for reg, val in self._driver.get_reg_all():
                print("  %3s: %08x" % (reg, val))
        elif self._driver.is_reg(cmd):
            # dump core register
            self._driver.core_halt()
            reg = cmd.upper()
            val = self._driver.get_reg(reg)
            print("  %3s: %08x" % (reg, val))
        elif cmd == 'flash':
            size = int(params[0], 0) if params else self._flash_size * 1024
            data = self._driver.get_mem(self._driver.FLASH_START, size)
            self.print_buffer(self._driver.FLASH_START, data)
        elif cmd == 'sram':
            size = int(params[0], 0) if params else self._sram_size * 1024
            data = self._driver.get_mem(self._driver.SRAM_START, size)
            self.print_buffer(self._driver.SRAM_START, data)
        elif params:
            # dump memory from address with size
            addr = int(cmd, 0)
            data = self._driver.get_mem(addr, int(params[0], 0))
            self.print_buffer(addr, data)
        else:
            # dump 32 bit register at address
            addr = int(cmd, 0)
            val = self._stlink.get_debugreg32(addr)
            print('  %08x: %08x' % (addr, val))

    def cmd_download(self, params):
        cmd = params[0]
        file_name = params[-1]
        params = params[1:-1]
        if cmd == 'flash':
            addr = self._driver.FLASH_START
            size = int(params[0], 0) if params else self._flash_size * 1024
        elif cmd == 'sram':
            addr = self._driver.SRAM_START
            size = int(params[0], 0) if params else self._sram_size * 1024
        elif params:
            addr = int(cmd, 0)
            size = int(params[0], 0)
        else:
            raise lib.stlinkex.StlinkExceptionBadParam()
        data = self._driver.get_mem(addr, size)
        self.store_file(addr, data, file_name)

    def cmd_write(self, params):
        cmd = params[0]
        params = params[1:]
        if not params:
            raise lib.stlinkex.StlinkExceptionBadParam('Missing argument')
        data = int(params[0], 0)
        if self._driver.is_reg(cmd):
            self._driver.core_halt()
            reg = cmd.upper()
            self._driver.set_reg(reg, data)
        else:
            addr = int(cmd, 0)
            self._stlink.set_debugreg32(addr, data)

    def cmd_fill(self, params):
        cmd = params[0]
        value = int(params[-1], 0)
        params = params[1:-1]
        if cmd == 'sram':
            size = int(params[0], 0) if params else self._sram_size * 1024
            self._driver.fill_mem(self._driver.SRAM_START, size, value)
        elif params:
            self._driver.fill_mem(int(cmd, 0), int(params[0], 0), value)
        else:
            raise lib.stlinkex.StlinkExceptionBadParam()

    def cmd_upload(self, params):
        mem = self.read_file(params[-1])
        params = params[:-1]
        if len(mem) == 1 and mem[0][0] is None:
            data = mem[0][1]
            if len(params) != 1:
                raise lib.stlinkex.StlinkExceptionBadParam('Address is not set')
            if params[0] == 'sram':
                addr = self._driver.SRAM_START
                if len(data) > self._sram_size * 1024:
                    raise lib.stlinkex.StlinkExceptionBadParam('Data are bigger than SRAM')
            else:
                addr = int(params[0], 0)
            self._driver.set_mem(addr, data)
            return
        if params:
            raise lib.stlinkex.StlinkException('Address for upload is set by file')
        for addr, data in mem:
            self._driver.set_mem(addr, data)

    def cmd_flash_write(self, params, erase=False):
        mem = self.read_file(params[-1])
        params = params[:-1]
        verify = False
        if params and params[0] == 'verify':
            verify = True
            params = params[1:]
        start_addr = lib.stm32.Stm32.FLASH_START
        if len(mem) == 1 and mem[0][0] is None:
            if params:
                start_addr = int(params[0], 0)
                params = params[1:]
        if params:
            raise lib.stlinkex.StlinkExceptionBadParam('Address for upload is set by file')
        for addr, data in mem:
            if addr is None:
                addr = start_addr
            self._driver.flash_write(addr, data, erase=erase, verify=verify, erase_sizes=self._mcus_by_devid['erase_sizes'])

    def cmd_flash(self, params):
        erase = False
        if params[0] == 'erase':
            params = params[1:]
            if not params:
                self._driver.flash_erase_all()
                return
            erase = True
        self.cmd_flash_write(params, erase=erase)

    def cmd(self, params):
        cmd = params[0]
        params = params[1:]
        if cmd == 'dump' and params:
            self.cmd_dump(params)
        elif cmd == 'dump16' and params:
            addr = int(params[0], 0)
            reg = self._stlink.get_debugreg16(addr)
            print('  %08x: %04x' % (addr, reg))
        elif cmd == 'dump8' and params:
            addr = int(params[0], 0)
            reg = self._stlink.get_debugreg8(addr)
            print('  %08x: %02x' % (addr, reg))
        elif cmd == 'download' and params:
            self.cmd_download(params)
        elif cmd == 'write' and params:
            self.cmd_write(params)
        elif cmd == 'upload' and params:
            self.cmd_upload(params)
        elif cmd == 'fill' and params:
            self.cmd_fill(params)
        elif cmd == 'flash' and params:
            self.cmd_flash(params)
        elif cmd == 'reset':
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
        elif cmd == 'sleep' and len(params) == 1:
            time.sleep(float(params[0]))
        else:
            raise lib.stlinkex.StlinkExceptionBadParam()

    def parse_option_cmd(self, argv):
        if argv[0] in PyStlink.VERBOSE_CMDS:
            self._dbg.set_verbose(PyStlink.VERBOSE_CMDS[argv[0]])
        elif argv[0] in ['--norun', '-n']:
            self._stay_in_debug = True
        else:
            return 0
        return 1

    def parse_option(self, argv):
        if argv[0] in ['--help', '-h']:
            self.print_help()
            sys.exit(0)
        if argv[0] in ['--version', '-V']:
            self.print_version()
            sys.exit(0)
        if argv[0] in ['--cpu', '-c']:
            if self._expected_cpu is not None:
                raise lib.stlinkex.StlinkExceptionBadParam('CPU type is already set')
            if len(argv) < 2:
                raise lib.stlinkex.StlinkExceptionBadParam('CPU type is not entered')
            self._expected_cpu = argv[1]
            if not self._expected_cpu.upper().startswith('STM32'):
                raise lib.stlinkex.StlinkExceptionBadParam('%s CPU is not STM32 family' % self._expected_cpu)
            return 2
        else:
            return self.parse_option_cmd(argv)
        return 1

    def start(self):
        argv = sys.argv[1:]
        runtime_status = 0
        try:
            while argv and argv[0].startswith('-'):
                args = self.parse_option(argv)
                if args:
                    argv = argv[args:]
                    continue
                raise lib.stlinkex.StlinkExceptionBadParam()
            self.detect_cpu()
            if argv and (self._driver is None or not self.is_mcu_selected()):
                raise lib.stlinkex.StlinkExceptionCpuNotSelected()
            while argv:
                if argv[0].startswith('-'):
                    args = self.parse_option_cmd(argv)
                    if args:
                        argv = argv[args:]
                        continue
                    raise lib.stlinkex.StlinkExceptionBadParam()
                self._dbg.verbose('CMD: %s' % argv[0])
                self.cmd(argv[0].split(':'))
                argv = argv[1:]
        except ValueError:
            self._dbg.error('Bad numeric velue in param: %s' % argv[0])
            runtime_status = 1
        except OverflowError:
            self._dbg.error('Too big number in param: %s' % argv[0])
            runtime_status = 1
        except lib.stlinkex.StlinkExceptionBadParam as e:
            e.set_cmd(argv[0])
            self._dbg.error(e)
            runtime_status = 1
        except lib.stlinkex.StlinkException as e:
            self._dbg.error(e)
            runtime_status = 1
        except KeyboardInterrupt:
            self._dbg.error('Keyboard interrupt')
            runtime_status = 1
        if self._driver and self.is_mcu_selected():
            # disconnect from MCU
            try:
                if self._stay_in_debug:
                    self._dbg.warning('CPU remain in debug mode', level=1)
                else:
                    self._driver.core_nodebug()
                self._stlink.leave_state()
            except lib.stlinkex.StlinkException as e:
                self._dbg.error(e)
                runtime_status = 1
            self._dbg.verbose('DONE in %0.2fs' % (time.time() - self._start_time))
        if runtime_status:
            sys.exit(runtime_status)


if __name__ == "__main__":
    dbg = lib.dbg.Dbg(verbose=1)
    pystlink = PyStlink(dbg)
    pystlink.start()
