import urllib.request
import json
import lib.stm32devices


def fix_cpu_type(cpu_type):
    cpu_type = cpu_type.upper()
    # now support only STM32
    if cpu_type.startswith('STM32'):
        # change character on 10 position to 'x' where is package size code
        if len(cpu_type) > 9:
            cpu_type = list(cpu_type)
            cpu_type[9] = 'x'
            cpu_type = ''.join(cpu_type)
        return cpu_type
    raise Exception('"%s" is not STM32 family' % cpu_type)

print("Downloading list of all STM32 MCUs from ST.com...")
res = urllib.request.urlopen('http://www.st.com/stonline/stappl/productcatalog/jsp/jsonDataForL3.jsp?subclassId=1169')
raw_json = json.loads(res.read().decode('utf-8'))
mcus = [record for record in raw_json['records']]

supported_mcus = []
for devs in lib.stm32devices.DEVICES:
    for dev in devs['devices']:
        for d in dev['devices']:
            supported_mcus.append(d['type'])

unsupported_mcus = {}

for mcu in mcus:
    m = fix_cpu_type(mcu.get('XJE010^VT-007!0'))
    if m not in supported_mcus:
        unsupported_mcus[m] = {
            'core': mcu.get('STP00920^VT-007!0'),
            'freq': mcu.get('XJG535^VT-007!45'),
            'flash_size': mcu.get('STP279^VT-007!24'),
            'sram_size': mcu.get('XJG510^VT-007!0'),
            'eeprom_size': mcu.get('STP681^VT-003!0'),
        }

print("On ST.com is %d new STM32 MCUs which is not supported by pystlink" % len(unsupported_mcus))
print("%-15s %-15s %6s %6s %6s %6s" % ('type', 'core', 'flash', 'sram', 'eeprom', 'freq'))
for k in sorted(unsupported_mcus.keys()):
    v = unsupported_mcus[k]
    print("%-15s %-15s %6s %6s %6s %6s" % (k, v['core'], v['flash_size'], v['sram_size'], v['eeprom_size'], v['freq']))
