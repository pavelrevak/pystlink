# PYSTLINK

This is successful attempt to communicate with ST-Link/V2 in **python-v3**.

## Goal

At this time it only detect MCU and dump or download registers and memory.

The main goal is to bring flashing support and very basic debugging (something is right now) and maybe in future connection to GDB.

## Install

- Download and unpack or `git clone https://github.com/pavelrevak/pystlink.git`
- Connect ST-LINK/V2, with latest firmware
- Run `python3 pystlink.py help`

## Help

### Usage:
  `pystlink.py [commands ...]`

### Commands:
  `help` - show help<br />
  `version` - show version<br />
  `verbose:{level}` - set verbose level from 0 - minimal to 3 - maximal (can also use between commands)<br />
  `cpu[:{cputype}]` - connect and detect CPU, set expected cputype, eg: STM32F051R8 or STM32L4

  `dump:registers` - print all registers (halt program)<br />
  `dump:register:{reg_name}` - print register (halt program)<br />
  `dump:flash` - print content of FLASH memory<br />
  `dump:sram` - print content of SRAM memory<br />
  `dump:mem:{addr}:{size}` - print content of memory<br />
  `dump:reg:{addr}` - print content of 32 bit register<br />
  `dump:reg16:{addr}` - print content of 16 bit register<br />
  `dump:reg8:{addr}` - print content of 8 bit register

  `download:mem:{addr}:{size}:{file}` - download memory into file<br />
  `download:sram:{file}` - download SRAM into file<br />
  `download:flash:{file}` - download FLASH into file

  `write:reg:{addr}:{data}` - write 32 bit register

  `upload:mem:{addr}:{file}` - upload file into memory (not for writing FLASH, only SRAM or registers)

  `control:halt` - halt program<br />
  `control:run` - run program

### Examples:
```
pystlink.py cpu dump:mem:0x08000000:256
pystlink.py verbose:2 cpu:STM32F051R8
pystlink.py verbose:0 cpu:STM32F03 dump:flash dump:sram
pystlink.py cpu dump:registers download:sram:aaa.bin download:flash:bbb.bin
```

## Supported MCUs:

Actually all ST32F and ST32L [MCU](http://www.st.com/web/en/catalog/mmc/FM141/SC1169).

some basic info about STM32 naming is in our WiKi: [STM32 coding matrix](https://github.com/pavelrevak/pystlink/wiki/STM32-coding-matrix)

## Legal

Code is under MIT license.

In general, this program is allowed to use in commercial without any limitations, but if you make some changes or updates then will be nice to share it.

PYSTLINK is inspired by [OpenOCD](http://openocd.org/) and some info is from sniffed USB communication with [ST-LINK](http://www.st.com/web/en/catalog/tools/PF258168) program.

## TAGS
ST-Link/V2, stlink, SWD, Python, STM32, debug, flash, USB
