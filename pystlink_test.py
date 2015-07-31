import unittest

import lib.stlinkstm32
import lib.stlinkex


class MockDbg():
    def __init__(self):
        pass

    def debug(self, msg, level=2):
        pass
        # print(msg)

    def msg(self, msg, level=1):
        pass
        # print(msg)

    def bargraph_start(self, msg, value_min=0, value_max=100, level=1):
        pass

    def bargraph_update(self, value=0, percent=None):
        pass

    def bargraph_done(self):
        pass

    def set_verbose(self, verbose):
        pass


class TestStlinkStm32(unittest.TestCase):
    def setUp(self):
        self._stlink = lib.stlinkstm32.StlinkStm32(None, None, MockDbg())

    def test_read_version(self):
        class MockDriver():
            def get_version(self):
                return 0x25c0
        self._stlink._driver = MockDriver()
        self._stlink.read_version()
        self.assertEqual(self._stlink._ver_stlink, 2)
        self.assertEqual(self._stlink._ver_jtag, 23)
        self.assertEqual(self._stlink._ver_swim, 0)
        self.assertEqual(self._stlink._ver_api, 2)

    def test_read_target_voltage(self):
        class MockDriver():
            def get_target_voltage(self):
                return 3.3
        self._stlink._driver = MockDriver()
        self._stlink.read_target_voltage()
        self.assertEqual(self._stlink._voltage, 3.3)

    def test_find_mcus_by_core_m0(self):
        self._stlink._devices = [
            {'part_no': 0xc20, 'core': 'CortexM0'},
            {'part_no': 0xc24, 'core': 'CortexM4'},
        ]
        mcu_core = self._stlink.find_mcus_by_core(0x410cc200)
        self.assertEqual(mcu_core['core'], 'CortexM0')

    def test_find_mcus_by_core_m4(self):
        self._stlink._devices = [
            {'part_no': 0xc20, 'core': 'CortexM0'},
            {'part_no': 0xc24, 'core': 'CortexM4'},
        ]
        mcu_core = self._stlink.find_mcus_by_core(0x410fc241)
        self.assertEqual(mcu_core['core'], 'CortexM4')

    def test_find_mcus_by_core_fail(self):
        self._stlink._devices = [
            {'part_no': 0xc20, 'core': 'CortexM0'},
            {'part_no': 0xc24, 'core': 'CortexM4'},
        ]
        with self.assertRaises(lib.stlinkex.StlinkException):
            self._stlink.find_mcus_by_core(0x410fc251)

    def test_find_mcus_by_devid_413(self):
        self._stlink._mcus_by_core = {'devices': [
            {'dev_id': 0x413},
            {'dev_id': 0x414},
        ]}
        mcu_devid = self._stlink.find_mcus_by_devid(0x10016413)
        self.assertEqual(mcu_devid['dev_id'], 0x413)

    def test_find_mcus_by_devid_414(self):
        self._stlink._mcus_by_core = {'devices': [
            {'dev_id': 0x413},
            {'dev_id': 0x414},
        ]}
        mcu_devid = self._stlink.find_mcus_by_devid(0x10026414)
        self.assertEqual(mcu_devid['dev_id'], 0x414)

    def test_find_mcus_by_devid_fail(self):
        self._stlink._mcus_by_core = {'devices': [
            {'dev_id': 0x413},
            {'dev_id': 0x414},
        ]}
        with self.assertRaises(lib.stlinkex.StlinkException):
            self._stlink.find_mcus_by_devid(0x10026415)

    def test_find_mcus_by_flash_size_64(self):
        self._stlink._flash_size = 64
        self._stlink._mcus_by_devid = {
            'dev_id': 0x414,
            'devices': [
                {'flash_size':   64},
                {'flash_size':  128},
                {'flash_size':   64},
                {'flash_size':  128},
                {'flash_size':  256},
            ]
        }
        mcus = self._stlink.find_mcus_by_flash_size()
        self.assertEqual(len(mcus), 2)
        for mcu in mcus:
            self.assertEqual(mcu['flash_size'], 64)

    def test_find_mcus_by_flash_size_256(self):
        self._stlink._flash_size = 256
        self._stlink._mcus_by_devid = {
            'dev_id': 0x414,
            'devices': [
                {'flash_size':   64},
                {'flash_size':  128},
                {'flash_size':   64},
                {'flash_size':  128},
                {'flash_size':  256},
            ]
        }
        mcus = self._stlink.find_mcus_by_flash_size()
        self.assertEqual(len(mcus), 1)
        for mcu in mcus:
            self.assertEqual(mcu['flash_size'], 256)

    def test_find_mcus_by_flash_size_fail(self):
        self._stlink._flash_size = 512
        self._stlink._mcus_by_devid = {
            'dev_id': 0x414,
            'devices': [
                {'flash_size':   64},
                {'flash_size':  128},
                {'flash_size':   64},
                {'flash_size':  128},
                {'flash_size':  256},
            ]
        }
        with self.assertRaises(lib.stlinkex.StlinkException):
            self._stlink.find_mcus_by_flash_size()

    def test_find_mcus_by_mcu_type_two(self):
        self._stlink._mcus = [
            {'type': 'STM32F030x8'},
            {'type': 'STM32F031x8'},
            {'type': 'STM32F051x8'},
        ]
        mcus = self._stlink.find_mcus_by_mcu_type('STM32F03')
        self.assertEqual(len(mcus), 2)
        self.assertEqual(mcus, [
            {'type': 'STM32F030x8'},
            {'type': 'STM32F031x8'},
        ])

    def test_find_mcus_by_mcu_type_one(self):
        self._stlink._mcus = [
            {'type': 'STM32F030x8'},
            {'type': 'STM32F031x8'},
            {'type': 'STM32F051x8'},
        ]
        mcus = self._stlink.find_mcus_by_mcu_type('STM32F051')
        self.assertEqual(len(mcus), 1)
        self.assertEqual(mcus, [
            {'type': 'STM32F051x8'},
        ])

    def test_find_mcus_by_mcu_type_fail(self):
        self._stlink._mcus = [
            {'type': 'STM32F030x8'},
            {'type': 'STM32F031x8'},
            {'type': 'STM32F051x8'},
        ]
        with self.assertRaises(lib.stlinkex.StlinkException):
            self._stlink.find_mcus_by_mcu_type('STM32F103')

    def test_clean_mcu_type_short(self):
        mcu_type = self._stlink.clean_mcu_type('STM32F051')
        self.assertEqual(mcu_type, 'STM32F051')

    def test_clean_mcu_type_replace_package_code(self):
        mcu_type = self._stlink.clean_mcu_type('STM32F051R8')
        self.assertEqual(mcu_type, 'STM32F051x8')

    def test_clean_mcu_type_fail(self):
        with self.assertRaises(lib.stlinkex.StlinkException):
            self._stlink.clean_mcu_type('MSP430')


if __name__ == '__main__':
    unittest.main()
