import unittest
import subprocess


class Stlink(unittest.TestCase):
    def _pystlink(self, arg=None, excepted_err=''):
        args = ['python', 'pystlink.py']
        if arg:
            args += arg.split(' ')
        p = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        ret = p.wait()
        out, err = p.communicate()
        out = out.decode(encoding='UTF-8').strip()
        err = err.decode(encoding='UTF-8').strip()
        errors = []
        warnings = []
        debug = []
        params = {}
        for err_line in err.splitlines():
            e = err_line.strip()
            if e.startswith('***') and e.endswith('***'):
                errors.append(e.strip('***').strip())
            elif e.startswith('*'):
                errors.append(e.strip('*').strip())
            else:
                if e:
                    debug.append(e)
            if ':' in e:
                k, v = e.split(':', 1)
                params[k.strip()] = v.strip()
        output = []
        values = {}
        for out_line in out.splitlines():
            o = out_line.strip()
            if o:
                output.append(o)
            if ':' in o:
                k, v = o.split(':', 1)
                values[k.strip()] = v.strip()
        return {
            'ret': ret,
            # 'stdout': out,
            # 'stderr': err,
            'errors': errors,
            'warnings': warnings,
            'debug': debug,
            'output': output,
            'params': params,
            'values': values,
        }


class TestNotStlink(Stlink):
    def testNotConnectedStlink(self):
        ret = self._pystlink()
        self.assertEqual(ret['errors'], ['ST-Link/V2 is not connected'])
        self.assertEqual(ret['warnings'], [])
        self.assertEqual(ret['output'], [])


class TestNotCpu(Stlink):
    def testNotConnectedCpu(self):
        ret = self._pystlink()
        self.assertEqual(ret['errors'], ['Not connected to CPU'])
        self.assertEqual(ret['warnings'], [])
        assert 'STLINK' in ret['params']
        assert 'SUPPLY' in ret['params']
        self.assertEqual(ret['output'], [])


class TestStm32(Stlink):
    REGISTERS = ['R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9', 'R10', 'R11', 'R12', 'SP', 'LR', 'PC', 'PSR', 'MSP', 'PSP']
    SRAM_START = 0x20000000
    FLASH_START = 0x08000000

    def testConnect(self):
        ret = self._pystlink()
        self.assertEqual(ret['errors'], [])
        self.assertEqual(ret['warnings'], [])
        assert 'STLINK' in ret['params']
        assert 'SUPPLY' in ret['params']
        assert 'CORE' in ret['params']
        assert 'MCU' in ret['params']
        assert 'FLASH' in ret['params']
        assert 'SRAM' in ret['params']
        self.assertEqual(ret['output'], [])

    def testCoreReset(self):
        ret = self._pystlink('core:reset')
        self.assertEqual(ret['errors'], [])
        self.assertEqual(ret['warnings'], [])
        self.assertEqual(ret['output'], [])

    def testCoreResetHalt(self):
        ret = self._pystlink('core:reset:halt')
        self.assertEqual(ret['errors'], [])
        self.assertEqual(ret['warnings'], [])
        self.assertEqual(ret['output'], [])

    def testCoreHalt(self):
        ret = self._pystlink('core:halt')
        self.assertEqual(ret['errors'], [])
        self.assertEqual(ret['warnings'], [])
        self.assertEqual(ret['output'], [])

    def testCoreRun(self):
        ret = self._pystlink('core:run')
        self.assertEqual(ret['errors'], [])
        self.assertEqual(ret['warnings'], [])
        self.assertEqual(ret['output'], [])

    def testCoreStep(self):
        ret = self._pystlink('core:step')
        self.assertEqual(ret['errors'], [])
        self.assertEqual(ret['warnings'], [])
        self.assertEqual(ret['output'], [])

    def testNorun(self):
        ret = self._pystlink('norun')
        self.assertEqual(ret['errors'], [])
        self.assertEqual(ret['warnings'], [])
        self.assertEqual(ret['output'], [])

    def testDumpRegAll(self):
        ret = self._pystlink('dump:reg:all')
        self.assertEqual(ret['errors'], [])
        self.assertEqual(ret['warnings'], [])
        for reg in self.REGISTERS:
            assert reg in ret['values']

    def testDumpRegR0(self):
        ret = self._pystlink('dump:reg:R0')
        self.assertEqual(ret['errors'], [])
        self.assertEqual(ret['warnings'], [])
        assert 'R0' in ret['values']

    def testDumpRegPC(self):
        ret = self._pystlink('dump:reg:PC')
        self.assertEqual(ret['errors'], [])
        self.assertEqual(ret['warnings'], [])
        assert 'PC' in ret['values']

    def testDumpRegAddr(self):
        ret = self._pystlink('dump:reg:0x08000000')
        self.assertEqual(ret['errors'], [])
        self.assertEqual(ret['warnings'], [])
        assert '08000000' in ret['values']

    def testDumpReg(self):
        ret = self._pystlink('dump:reg:0x08000000')
        self.assertEqual(ret['errors'], [])
        self.assertEqual(ret['warnings'], [])
        assert '08000000' in ret['values']
        assert len(ret['values']['08000000']) == 8

    def testDumpReg16(self):
        ret = self._pystlink('dump:reg16:0x08000000')
        self.assertEqual(ret['errors'], [])
        self.assertEqual(ret['warnings'], [])
        assert '08000000' in ret['values']
        assert len(ret['values']['08000000']) == 4

    def testDumpReg8(self):
        ret = self._pystlink('dump:reg8:0x08000000')
        self.assertEqual(ret['errors'], [])
        self.assertEqual(ret['warnings'], [])
        assert '08000000' in ret['values']
        assert len(ret['values']['08000000']) == 2

    def testDumpMem1(self):
        ret = self._pystlink('dump:mem:0x08000000:1')
        self.assertEqual(ret['errors'], [])
        self.assertEqual(ret['warnings'], [])
        self.assertEqual(len(ret['output']), 2)
        self.assertEqual(ret['output'][-1], '08000001')

    def testDumpMem16(self):
        ret = self._pystlink('dump:mem:0x08000000:16')
        self.assertEqual(ret['errors'], [])
        self.assertEqual(ret['warnings'], [])
        self.assertEqual(len(ret['output']), 2)
        self.assertEqual(ret['output'][-1], '08000010')

    def testDumpMem18(self):
        ret = self._pystlink('dump:mem:0x08000000:18')
        self.assertEqual(ret['errors'], [])
        self.assertEqual(ret['warnings'], [])
        assert len(ret['output']) <= 3
        self.assertEqual(ret['output'][-1], '08000012')

    def testDumpMem1024(self):
        ret = self._pystlink('dump:mem:0x08000000:1024')
        self.assertEqual(ret['errors'], [])
        self.assertEqual(ret['warnings'], [])
        assert len(ret['output']) <= 64
        self.assertEqual(ret['output'][-1], '08000400')

    def testDumpMem4008(self):
        ret = self._pystlink('dump:mem:0x08000000:4008')
        self.assertEqual(ret['errors'], [])
        self.assertEqual(ret['warnings'], [])
        assert len(ret['output']) <= 251
        self.assertEqual(ret['output'][-1], '08000fa8')

    def testDumpSram(self):
        ret = self._pystlink('dump:sram')
        self.assertEqual(ret['errors'], [])
        self.assertEqual(ret['warnings'], [])
        sram_size = int(ret['params']['SRAM'].strip('KB')) * 1024
        assert len(ret['output']) <= sram_size // 16
        self.assertEqual(int(ret['output'][0].split()[0], 16), self.SRAM_START)
        self.assertEqual(int(ret['output'][-1], 16), self.SRAM_START + sram_size)

    def testDumpFlash(self):
        ret = self._pystlink('dump:flash')
        self.assertEqual(ret['errors'], [])
        self.assertEqual(ret['warnings'], [])
        flash_size = int(ret['params']['FLASH'].strip('KB')) * 1024
        assert len(ret['output']) <= flash_size // 16
        self.assertEqual(int(ret['output'][0].split()[0], 16), self.FLASH_START)
        self.assertEqual(int(ret['output'][-1], 16), self.FLASH_START + flash_size)


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('Select right test case class depending on connected HW (as command line parameter):')
        import inspect
        for name, obj in inspect.getmembers(sys.modules[__name__]):
            if inspect.isclass(obj) and name.startswith('Test'):
                print('  ' + name)
        exit(0)
    unittest.main()
