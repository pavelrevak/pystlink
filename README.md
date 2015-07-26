This is very simple attempt to communicate with ST-LinkV2.
At this time it only detect MCU and read his registers.
This code is only for python v3


Connect ST-LinkV2 and run:
```
python3 stlink.py
```

supported MCUs are some:
- STM32F0xx
- STM32F4xx

code in this project is inspired from openocd and sniffed communication from STLINK program
