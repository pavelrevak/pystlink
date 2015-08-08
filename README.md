# PYSTLINK

This is small python application for communicating with **ST-Link/V2** and almost all STM32 MCUs. It has very simple command-line interface.

## Features

- detect MCU
- dump registers and memory
- write registers
- download memory to binary file
- upload binary file into memory
- basic runtime control: reset, halt, step, run

### Planed features

- flashing support
- maybe in future connection to GDB
- and maybe GUI

## Install

- Need Linux or OS/X (Windows is not tested, but probably can work if there will be not installed USB drivers from ST)
- Also need Python v3.x (tested with python-3.4) and [pyusbs](https://github.com/walac/pyusb)
- Download and unpack or `git clone https://github.com/pavelrevak/pystlink.git`
- Connect ST-LINK/V2, with latest firmware
- Run `python3 pystlink.py help`

## Help

### Usage:
  `pystlink.py [commands ...]`

### Commands:
  `help` - show help<br />
  `version` - show version<br />
  `v:{level}` - set verbose level from 0 - minimal to 3 - maximal (can also use between commands)<br />
  `cpu[:{cputype}]` - connect and detect CPU, set expected cputype, eg: STM32F051R8 or STM32L4

  `dump:reg:all` - print all registers (halt core)<br />
  `dump:reg:{reg_name}` - print register (halt core)<br />
  `dump:reg:{addr}` - print content of 32 bit memory register<br />
  `dump:reg16:{addr}` - print content of 16 bit memory register<br />
  `dump:reg8:{addr}` - print content of 8 bit memory register<br />
  `dump:mem:{addr}:{size}` - print content of memory<br />
  `dump:flash[:{size}]` - print content of FLASH memory<br />
  `dump:sram[:{size}]` - print content of SRAM memory

  `download:mem:{addr}:{size}:{file}` - download memory into binary file<br />
  `download:sram:{file}` - download SRAM into binary file<br />
  `download:flash:{file}` - download FLASH into binary file

  `write:reg:{reg_name}:{data}` - write register (halt core)<br />
  `write:reg:{addr}:{data}` - write 32 bit memory register

  `upload:mem:{addr}:{file}` - upload file into memory (not for writing FLASH, only SRAM or registers)

  `core:reset` - reset core<br />
  `core:reset:halt` - reset and halt core<br />
  `core:halt` - halt core<br />
  `core:step` - step core<br />
  `core:run` - run core<br />
  `core:norun` - don't run core when disconnecting from ST-Link (when program end)

### Examples:
```
pystlink.py cpu dump:mem:0x08000000:256
pystlink.py v:2 cpu:STM32F051R8
pystlink.py v:0 cpu:STM32F03 dump:flash dump:sram
pystlink.py cpu dump:registers download:sram:aaa.bin download:flash:bbb.bin
pystlink.py cpu control:norun control:reset:halt dump:register:pc control:step dump:registers
```

## Supported MCUs:

Actually all ST32F and ST32L [MCU](http://www.st.com/web/en/catalog/mmc/FM141/SC1169).

some basic info about STM32 naming is in our WiKi: [STM32 coding matrix](https://github.com/pavelrevak/pystlink/wiki/STM32-coding-matrix)

## Legal

Code is under MIT license.

In general, this program is allowed to use in commercial without any limitations, but if you make some changes or updates then will be nice to share it. Any damaged MCUs are on your risk.

PYSTLINK is inspired by [OpenOCD](http://openocd.org/), [STLINK](https://github.com/texane/stlink) and some info is from sniffed USB communication with [ST-LINK](http://www.st.com/web/en/catalog/tools/PF258168) program.

## TAGS
ST-Link/V2, stlink, SWD, Python, STM32, debug, flash, USB
