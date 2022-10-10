import unittest

import pystlink
import lib.stm32
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

    def verbose(self, msg, level=1):
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


class TestStm32(unittest.TestCase):
    def setUp(self):
        self._pystlink = pystlink.PyStlink()
        self._pystlink._dbg = MockDbg()
        # self._driver = lib.stm32.Stm32(stlink=None, dbg=dbg)

    # def test_read_version(self):
    #     class MockStlink():
    #         def get_version(self):
    #             return 0x25c0
    #     self._driver._driver = MockStlink()
    #     self._driver.read_version()
    #     self.assertEqual(self._driver._ver_stlink, 2)
    #     self.assertEqual(self._driver._ver_jtag, 23)
    #     self.assertEqual(self._driver._ver_swim, 0)
    #     self.assertEqual(self._driver._ver_api, 2)

    # def test_read_target_voltage(self):
    #     class MockStlink():
    #         def get_target_voltage(self):
    #             return 3.3
    #     self._driver._driver = MockStlink()
    #     self._driver.read_target_voltage()
    #     self.assertEqual(self._driver._voltage, 3.3)

    def test_find_mcus_by_core_m0(self):
        self._pystlink._devices = [
            {'part_no': 0xc20, 'core': 'CortexM0'},
            {'part_no': 0xc24, 'core': 'CortexM4'},
        ]

        class MockStlink():
            def get_debugreg32(self, reg):
                assert reg == 0xe000ed00
                return 0x410cc200
        self._pystlink._stlink = MockStlink()
        self._pystlink.find_mcus_by_core()
        self.assertEqual(self._pystlink._mcus_by_core['core'], 'CortexM0')

    def test_find_mcus_by_core_m4(self):
        self._pystlink._devices = [
            {'part_no': 0xc20, 'core': 'CortexM0'},
            {'part_no': 0xc24, 'core': 'CortexM4'},
        ]

        class MockStlink():
            def get_debugreg32(self, reg):
                assert reg == 0xe000ed00
                return 0x410fc241
        self._pystlink._stlink = MockStlink()
        self._pystlink.find_mcus_by_core()
        self.assertEqual(self._pystlink._mcus_by_core['core'], 'CortexM4')

    def test_find_mcus_by_core_fail(self):
        self._pystlink._devices = [
            {'part_no': 0xc20, 'core': 'CortexM0'},
            {'part_no': 0xc24, 'core': 'CortexM4'},
        ]

        class MockStlink():
            def get_debugreg32(self, reg):
                assert reg == 0xe000ed00
                return 0x410fc251
        self._pystlink._stlink = MockStlink()
        with self.assertRaises(lib.stlinkex.StlinkException):
            self._pystlink.find_mcus_by_core()

    def test_find_mcus_by_devid_413(self):
        self._pystlink._mcus_by_core = {
            'idcode_reg': 0xE0042000,
            'devices': [
                {'dev_id': 0x413},
                {'dev_id': 0x415},
            ]
        }

        class MockStlink():
            def get_debugreg32(self, reg):
                assert reg == 0xE0042000
                return 0x10016413
        self._pystlink._stlink = MockStlink()
        self._pystlink.find_mcus_by_devid()
        assert self._pystlink._mcus_by_devid['dev_id'] == 0x413

    def test_find_mcus_by_devid_415(self):
        self._pystlink._mcus_by_core = {
            'idcode_reg': 0xE0042000,
            'devices': [
                {'dev_id': 0x413},
                {'dev_id': 0x415},
            ]
        }

        class MockStlink():
            def get_debugreg32(self, reg):
                assert reg == 0xE0042000
                return 0x10016415
        self._pystlink._stlink = MockStlink()
        self._pystlink.find_mcus_by_devid()
        assert self._pystlink._mcus_by_devid['dev_id'] == 0x415

    def test_find_mcus_by_devid_fail(self):
        self._pystlink._mcus_by_core = {
            'idcode_reg': 0xE0042000,
            'devices': [
                {'dev_id': 0x413},
                {'dev_id': 0x415},
            ]
        }

        class MockStlink():
            def get_debugreg32(self, reg):
                assert reg == 0xE0042000
                return 0x10016417
        self._pystlink._stlink = MockStlink()
        with self.assertRaises(lib.stlinkex.StlinkException):
            self._pystlink.find_mcus_by_devid()

    def test_find_mcus_by_flash_size_64(self):
        self._pystlink._mcus_by_devid = {
            'dev_id': 0x414,
            'flash_size_reg': 0x1fff7a22,
            'devices': [
                {'flash_size':   64},
                {'flash_size':  128},
                {'flash_size':   64},
                {'flash_size':  128},
                {'flash_size':  256},
            ]
        }

        class MockStlink():
            def get_debugreg16(self, reg):
                assert reg == 0x1fff7a22
                return 64
        self._pystlink._stlink = MockStlink()
        self._pystlink.find_mcus_by_flash_size()
        assert len(self._pystlink._mcus) == 2
        for mcu in self._pystlink._mcus:
            self.assertEqual(mcu['flash_size'], 64)

    def test_find_mcus_by_flash_size_256(self):
        self._pystlink._mcus_by_devid = {
            'dev_id': 0x414,
            'flash_size_reg': 0x1fff7a22,
            'devices': [
                {'flash_size':   64},
                {'flash_size':  128},
                {'flash_size':   64},
                {'flash_size':  128},
                {'flash_size':  256},
            ]
        }

        class MockStlink():
            def get_debugreg16(self, reg):
                assert reg == 0x1fff7a22
                return 256
        self._pystlink._stlink = MockStlink()
        self._pystlink.find_mcus_by_flash_size()
        assert len(self._pystlink._mcus) == 1
        for mcu in self._pystlink._mcus:
            self.assertEqual(mcu['flash_size'], 256)

    def test_find_mcus_by_flash_size_fail(self):
        self._pystlink._mcus_by_devid = {
            'dev_id': 0x414,
            'flash_size_reg': 0x1fff7a22,
            'devices': [
                {'flash_size':   64},
                {'flash_size':  128},
                {'flash_size':   64},
                {'flash_size':  128},
                {'flash_size':  256},
            ]
        }

        class MockStlink():
            def get_debugreg16(self, reg):
                assert reg == 0x1fff7a22
                return 512
        self._pystlink._stlink = MockStlink()
        with self.assertRaises(lib.stlinkex.StlinkException):
            self._pystlink.find_mcus_by_flash_size()

    def test_filter_detected_cpu_two(self):
        self._pystlink._mcus = [
            {'type': 'STM32F030x8'},
            {'type': 'STM32F031x8'},
            {'type': 'STM32F051x8'},
        ]
        self._pystlink.filter_detected_cpu(['STM32F03'])
        self.assertEqual(len(self._pystlink._mcus), 2)
        self.assertEqual(self._pystlink._mcus, [
            {'type': 'STM32F030x8'},
            {'type': 'STM32F031x8'},
        ])

    def test_filter_detected_cpu_one(self):
        self._pystlink._mcus = [
            {'type': 'STM32F030x8'},
            {'type': 'STM32F031x8'},
            {'type': 'STM32F051x8'},
        ]
        self._pystlink.filter_detected_cpu(['STM32F051R8'])
        self.assertEqual(len(self._pystlink._mcus), 1)
        self.assertEqual(self._pystlink._mcus, [
            {'type': 'STM32F051x8'},
        ])

    def test_filter_detected_cpu_fail(self):
        self._pystlink._mcus = [
            {'type': 'STM32F030x8'},
            {'type': 'STM32F031x8'},
            {'type': 'STM32F051x8'},
        ]
        with self.assertRaises(lib.stlinkex.StlinkException):
            self._pystlink.filter_detected_cpu(['STM32F103'])


class TestStm32_get_mem(unittest.TestCase):
    def setUp(self):
        class MockStlink():
            STLINK_MAXIMUM_TRANSFER_SIZE = 1024

            def __init__(self, test):
                self._test = test
                self._pointer = None
                self._index = 0

            def get_mem32(self, addr, size):
                self._test.assertNotEqual(size, 0)
                self._test.assertEqual(addr % 4, 0)
                self._test.assertEqual(size % 4, 0)
                if self._pointer is None:
                    self._pointer = addr
                assert size <= 1024
                self._test.assertEqual(addr, self._pointer)
                self._pointer += size
                old_index = self._index
                self._index += size
                return [i & 0xff for i in range(old_index, self._index)]

            def get_mem8(self, addr, size):
                self._test.assertNotEqual(size, 0)
                if self._pointer is None:
                    self._pointer = addr
                assert size <= 64
                self._test.assertEqual(addr, self._pointer)
                self._pointer += size
                old_index = self._index
                self._index += size
                return [i & 0xff for i in range(old_index, self._index)]

        self._driver = lib.stm32.Stm32(stlink=MockStlink(self), dbg=MockDbg())

    def _test_get_mem(self, addr, size):
        data = self._driver.get_mem(addr, size)
        expected_data = [i & 0xff for i in range(0, size)]
        self.assertEqual(data, expected_data)

    def test_addr_0_size_0(self):
        self._test_get_mem(0, 0)

    def test_addr_0_size_1(self):
        self._test_get_mem(0, 1)

    def test_addr_0_size_2(self):
        self._test_get_mem(0, 2)

    def test_addr_0_size_3(self):
        self._test_get_mem(0, 3)

    def test_addr_0_size_4(self):
        self._test_get_mem(0, 4)

    def test_addr_1_size_0(self):
        self._test_get_mem(1, 0)

    def test_addr_1_size_1(self):
        self._test_get_mem(1, 1)

    def test_addr_1_size_3(self):
        self._test_get_mem(1, 3)

    def test_addr_1_size_4(self):
        self._test_get_mem(1, 4)

    def test_addr_2_size_1(self):
        self._test_get_mem(2, 1)

    def test_addr_2_size_2(self):
        self._test_get_mem(2, 2)

    def test_addr_2_size_4(self):
        self._test_get_mem(2, 4)

    def test_addr_3_size_1(self):
        self._test_get_mem(3, 1)

    def test_addr_3_size_2(self):
        self._test_get_mem(3, 2)

    def test_addr_3_size_4(self):
        self._test_get_mem(3, 4)

    def test_addr_4_size_1(self):
        self._test_get_mem(4, 1)

    def test_addr_4_size_4(self):
        self._test_get_mem(4, 4)

    def test_addr_4_size_12(self):
        self._test_get_mem(4, 12)

    def test_addr_4_size_13(self):
        self._test_get_mem(4, 13)

    def test_addr_5_size_11(self):
        self._test_get_mem(5, 11)

    def test_addr_5_size_12(self):
        self._test_get_mem(5, 12)

    def test_addr_0_size_1024(self):
        self._test_get_mem(0, 1024)

    def test_addr_0_size_1025(self):
        self._test_get_mem(0, 1025)

    def test_addr_0_size_1028(self):
        self._test_get_mem(0, 1028)

    def test_addr_0_size_2048(self):
        self._test_get_mem(0, 2048)

    def test_addr_0_size_8192(self):
        self._test_get_mem(0, 8192)

    def test_addr_1_size_8192(self):
        self._test_get_mem(1, 8192)

    def test_addr_4095_size_8192(self):
        self._test_get_mem(4095, 8192)

    def test_addr_4096_size_8192(self):
        self._test_get_mem(4096, 8192)

    def test_addr_1_size_1100(self):
        self._test_get_mem(1, 1100)

    def test_addr_4_size_1100(self):
        self._test_get_mem(2, 1100)


class TestStm32_set_mem(unittest.TestCase):
    def setUp(self):
        class MockStlink():
            STLINK_MAXIMUM_TRANSFER_SIZE = 1024

            def __init__(self, test):
                self._test = test
                self._pointer = None
                self._index = 0

            def set_mem32(self, addr, data):
                self._test.assertNotEqual(len(data), 0)
                self._test.assertEqual(addr % 4, 0)
                self._test.assertEqual(len(data) % 4, 0)
                if self._pointer is None:
                    self._pointer = addr
                assert len(data) <= 1024
                self._test.assertEqual(addr, self._pointer)
                self._pointer += len(data)
                self._index += len(data)

            def set_mem8(self, addr, data):
                self._test.assertNotEqual(len(data), 0)
                if self._pointer is None:
                    self._pointer = addr
                assert len(data) <= 64
                self._test.assertEqual(addr, self._pointer)
                self._pointer += len(data)
                self._index += len(data)

        self._driver = lib.stm32.Stm32(stlink=MockStlink(self), dbg=MockDbg())

    def _test_set_mem(self, addr, size):
        self._driver.set_mem(addr, [i & 0xff for i in range(0, size)])

    def test_addr_0_size_0(self):
        self._test_set_mem(0, 0)

    def test_addr_0_size_1(self):
        self._test_set_mem(0, 1)

    def test_addr_0_size_2(self):
        self._test_set_mem(0, 2)

    def test_addr_0_size_3(self):
        self._test_set_mem(0, 3)

    def test_addr_0_size_4(self):
        self._test_set_mem(0, 4)

    def test_addr_1_size_0(self):
        self._test_set_mem(1, 0)

    def test_addr_1_size_1(self):
        self._test_set_mem(1, 1)

    def test_addr_1_size_3(self):
        self._test_set_mem(1, 3)

    def test_addr_1_size_4(self):
        self._test_set_mem(1, 4)

    def test_addr_2_size_1(self):
        self._test_set_mem(2, 1)

    def test_addr_2_size_2(self):
        self._test_set_mem(2, 2)

    def test_addr_2_size_4(self):
        self._test_set_mem(2, 4)

    def test_addr_3_size_1(self):
        self._test_set_mem(3, 1)

    def test_addr_3_size_2(self):
        self._test_set_mem(3, 2)

    def test_addr_3_size_4(self):
        self._test_set_mem(3, 4)

    def test_addr_4_size_1(self):
        self._test_set_mem(4, 1)

    def test_addr_4_size_4(self):
        self._test_set_mem(4, 4)

    def test_addr_4_size_12(self):
        self._test_set_mem(4, 12)

    def test_addr_4_size_13(self):
        self._test_set_mem(4, 13)

    def test_addr_5_size_11(self):
        self._test_set_mem(5, 11)

    def test_addr_5_size_12(self):
        self._test_set_mem(5, 12)

    def test_addr_0_size_1024(self):
        self._test_set_mem(0, 1024)

    def test_addr_0_size_1025(self):
        self._test_set_mem(0, 1025)

    def test_addr_0_size_1028(self):
        self._test_set_mem(0, 1028)

    def test_addr_0_size_2048(self):
        self._test_set_mem(0, 2048)

    def test_addr_0_size_8192(self):
        self._test_set_mem(0, 8192)

    def test_addr_1_size_8192(self):
        self._test_set_mem(1, 8192)

    def test_addr_4095_size_8192(self):
        self._test_set_mem(4095, 8192)

    def test_addr_4096_size_8192(self):
        self._test_set_mem(4096, 8192)

    def test_addr_1_size_1100(self):
        self._test_set_mem(1, 1100)

    def test_addr_4_size_1100(self):
        self._test_set_mem(2, 1100)


class TestStm32_fill_mem(unittest.TestCase):
    def setUp(self):
        class MockStlink():
            STLINK_MAXIMUM_TRANSFER_SIZE = 1024

            def __init__(self, test):
                self._test = test
                self._pointer = None
                self._index = 0

            def set_mem32(self, addr, data):
                self._test.assertNotEqual(len(data), 0)
                self._test.assertEqual(addr % 4, 0)
                self._test.assertEqual(len(data) % 4, 0)
                if self._pointer is None:
                    self._pointer = addr
                assert len(data) <= 1024
                self._test.assertEqual(addr, self._pointer)
                self._pointer += len(data)
                self._index += len(data)

            def set_mem8(self, addr, data):
                self._test.assertNotEqual(len(data), 0)
                if self._pointer is None:
                    self._pointer = addr
                assert len(data) <= 64
                self._test.assertEqual(addr, self._pointer)
                self._pointer += len(data)
                self._index += len(data)

        self._driver = lib.stm32.Stm32(stlink=MockStlink(self), dbg=MockDbg())

    def _test_fill_mem(self, addr, size):
        self._driver.fill_mem(addr, size, 0x55)

    def test_addr_0_size_0(self):
        self._test_fill_mem(0, 0)

    def test_addr_0_size_1(self):
        self._test_fill_mem(0, 1)

    def test_addr_0_size_2(self):
        self._test_fill_mem(0, 2)

    def test_addr_0_size_3(self):
        self._test_fill_mem(0, 3)

    def test_addr_0_size_4(self):
        self._test_fill_mem(0, 4)

    def test_addr_1_size_0(self):
        self._test_fill_mem(1, 0)

    def test_addr_1_size_1(self):
        self._test_fill_mem(1, 1)

    def test_addr_1_size_3(self):
        self._test_fill_mem(1, 3)

    def test_addr_1_size_4(self):
        self._test_fill_mem(1, 4)

    def test_addr_2_size_1(self):
        self._test_fill_mem(2, 1)

    def test_addr_2_size_2(self):
        self._test_fill_mem(2, 2)

    def test_addr_2_size_4(self):
        self._test_fill_mem(2, 4)

    def test_addr_3_size_1(self):
        self._test_fill_mem(3, 1)

    def test_addr_3_size_2(self):
        self._test_fill_mem(3, 2)

    def test_addr_3_size_4(self):
        self._test_fill_mem(3, 4)

    def test_addr_4_size_1(self):
        self._test_fill_mem(4, 1)

    def test_addr_4_size_4(self):
        self._test_fill_mem(4, 4)

    def test_addr_4_size_12(self):
        self._test_fill_mem(4, 12)

    def test_addr_4_size_13(self):
        self._test_fill_mem(4, 13)

    def test_addr_5_size_11(self):
        self._test_fill_mem(5, 11)

    def test_addr_5_size_12(self):
        self._test_fill_mem(5, 12)

    def test_addr_0_size_1024(self):
        self._test_fill_mem(0, 1024)

    def test_addr_0_size_1025(self):
        self._test_fill_mem(0, 1025)

    def test_addr_0_size_1028(self):
        self._test_fill_mem(0, 1028)

    def test_addr_0_size_2048(self):
        self._test_fill_mem(0, 2048)

    def test_addr_0_size_8192(self):
        self._test_fill_mem(0, 8192)

    def test_addr_1_size_8192(self):
        self._test_fill_mem(1, 8192)

    def test_addr_4095_size_8192(self):
        self._test_fill_mem(4095, 8192)

    def test_addr_4096_size_8192(self):
        self._test_fill_mem(4096, 8192)

    def test_addr_1_size_1100(self):
        self._test_fill_mem(1, 1100)

    def test_addr_4_size_1100(self):
        self._test_fill_mem(2, 1100)


if __name__ == '__main__':
    unittest.main()
