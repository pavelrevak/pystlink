# PYSTLINK

Small python application for communicating with **ST-Link/V2** and almost all **STM32** MCUs.

## Features

- support **Linux**, **Mac OS/X**, **Windows**
- simple command line interface
- detect MCU
- dump registers and memory
- write registers
- download memory to binary file
- upload binary file into memory
- basic runtime control: reset, halt, step, run
- supported MCUs for flashing: **STM32F0**, **STM32F1**, **STM32F2**, **STM32F3**, **STM32F4** and **STM32F7**

### Planed features

- flashing support for other MCU types (STM32Lxx)
- flashing information block (system memory, option bytes and OTP area)
- connecting under RESET
- other file formats (SREC, HEX)
- maybe in future connection to GDB
- and maybe GUI

### Known bugs

Instead of all unimplemented features there are these known bugs:

- ~~do not write second bank of FLASH in STM32F10x XL devices (with 768KB and 1024KB FLASH)~~ Implemented but not tested yet!!!
- do not stop WATCHDOGs in debug mode

## Install

### Requirements

- **Python v3.x** (tested with python-3.4)
- [**pyusbs**](https://github.com/walac/pyusb)
- [**libusb**](http://libusbx.org) or other libusb
  - for Windows copy libusb-1.0.dll into installed python: python/DLLs or into Windows/System32

### pystlink

- [Download](https://github.com/pavelrevak/pystlink/archive/master.zip) and unpack or `git clone https://github.com/pavelrevak/pystlink.git`
- Connect ST-LINK/V2, with [**latest firmware**](http://www.st.com/web/en/catalog/tools/PF258194)
- Run `./pystlink.py --help` (or `python3 pystlink.py ...` - depend on python installation)

## Help
```
usage:
  pystlink.py [options|verbose] [commands|verbose ...]

options:
  --help -h          show this help
  --version -V       show version
  --cpu -c {cputype} set expected cputype, eg: STM32F051R8 or STM32L4

verbose:
  all verbose modes can also use between any commands (to configure verbosity of any commands)
  -q                 set quiet
  -i                 set info (default)
  -v                 set verbose
  -d                 set debug

commands:
  dump:reg:all - print all registers (halt core)
  dump:reg:{reg_name} - print register (halt core)
  dump:reg:{addr} - print content of 32 bit memory register
  dump:reg16:{addr} - print content of 16 bit memory register
  dump:reg8:{addr} - print content of 8 bit memory register
  dump:mem:{addr}:{size} - print content of memory
  dump:flash[:{size}] - print content of FLASH memory
  dump:sram[:{size}] - print content of SRAM memory

  download:mem:{addr}:{size}:{file} - download memory into file
  download:sram:{file} - download SRAM into file
  download:flash:{file} - download FLASH into file

  write:reg:{reg_name}:{data} - write register (halt core)
  write:reg:{addr}:{data} - write 32 bit memory register

  upload:mem:{addr}:{file} - upload file into memory (not for writing FLASH, only SRAM or registers)

  flash:erase - complete erase FLASH memory aka mass erase - (in some cases it can be faster than flash:erase:write:...)
  flash:write[:verify][:{addr}]:{file} - write file into FLASH memory + optional verify
  flash:erase:write[:verify][:{addr}]:{file} - erase only pages or sectors where will be written program + write... (faster)

  core:reset - reset core
  core:reset:halt - reset and halt core
  core:halt - halt core
  core:step - step core
  core:run - run core

  norun - don't run core when disconnecting from ST-Link (when program end)

examples:
  pystlink.py --help
  pystlink.py -V --cpu STM32F051R8
  pystlink.py -q --cpu STM32F03 dump:flash dump:sram
  pystlink.py dump:mem:0x08000000:256
  pystlink.py write:reg:0x48000018:0x00000100 dump:reg:0x48000014
  pystlink.py download:sram:aaa.bin download:flash:bbb.bin
  pystlink.py norun core:reset:halt dump:reg:pc core:step dump:reg:all
  pystlink.py flash:erase:write:verify:app.bin
  pystlink.py flash:erase flash:write:verify:0x0800f000:boot.bin
```

## Supported MCUs:

Currently all **ST32F** and **ST32L** [MCU](http://www.st.com/web/en/catalog/mmc/FM141/SC1169).

FLASHing support is on all **STM32F0** to **STM32F4**.

Not all MCUs are tested. Please report all problems.

In WiKi is some basic info about STM32 naming: [STM32 coding matrix](https://github.com/pavelrevak/pystlink/wiki/STM32-coding-matrix)

## Legal

Code is under [MIT license](https://github.com/pavelrevak/pystlink/blob/master/LICENSE).

In general, this program is allowed to use in commercial and without any limitations, but if you make some changes or updates then will be nice to share it.

Support is only by [Issues tracker](https://github.com/pavelrevak/pystlink/issues)

PYSTLINK is inspired by [OpenOCD](http://openocd.org/), [STLINK](https://github.com/texane/stlink) and lot of info is from sniffed USB communication with [original ST-LINK](http://www.st.com/web/en/catalog/tools/PF258168) program.

## TAGS
ST-Link/V2, stlink, SWD, Python, ARM, CortexM, STM32, debug, FLASH, USB
