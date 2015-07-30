# PYSTLINK
This is successful  attempt to communicate with ST-LinkV2.

## Goal
 At this time it only detect MCU and dump or download registers and memory.

The main goal is to bring flashing support and then very basic debugging (something is now) or maybe connection to GDB

## Help

### Usage:
-  `stlink.py [commands ...]`

### Commands:
- `verbose:{level}` - set verbose level from 0 - minimal to 3 - maximal
- `cpu[:{cputype}]` - connect and detect CPU, set expected cputype, eg: STM32F051R8 or STM32L4

- `dump:registers` - print all registers
- `dump:flash` - print content of FLASH memory
- `dump:sram` - print content of SRAM memory
- `dump:mem:{addr}:{size}` - print content of memory
- `dump:reg:{addr}` - print content of 32 bit register
- `dump:reg16:{addr}` - print content of 16 bit register
- `dump:reg8:{addr}` - print content of 8 bit register

- `download:mem:{addr}:{size}:{file}` - download memory into file
- `download:sram:{file}` - download SRAM into file
- `download:flash:{file}` - download FLASH into file

### Examples:
```
stlink.py help
stlink.py cpu dump:registers download:sram:aaa.bin download:flash:bbb.bin
stlink.py verbose:0 cpu dump:mem:0x08000000:256
stlink.py verbose:2 cpu:STM32F03
```

## Supported MCUs:
Actually all ST32F and ST32L MCUs

some basic info in wiki about STM32 naming: [STM32 coding matrix](https://github.com/pavelrevak/pystlink/wiki/STM32-coding-matrix)

## About
This code is only for python v3

License is GPLv2

code in this project is inspired from openocd and sniffed communication from ST STLINK program
