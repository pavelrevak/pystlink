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

supported_mcus = {}
for devs in lib.stm32devices.DEVICES:
    for dev in devs['devices']:
        for d in dev['devices']:
            supported_mcus[d['type']] = d

unsupported_mcus = {}
wrong_param_mcus = {}

for mcu in mcus:
    m = fix_cpu_type(mcu.get('XJE010^VT-007!0'))
    core = mcu.get('STP00920^VT-007!0')
    freq = int(mcu.get('XJG535^VT-007!45'))
    flash = mcu.get('STP279^VT-007!24')
    flash = 0 if flash == '-' else int(flash)
    sram = mcu.get('XJG510^VT-007!0')
    if sram.isnumeric():
        sram = int(sram)
    eeprom = mcu.get('STP681^VT-003!0')
    eeprom = 0 if eeprom == '-' else int(eeprom) // 1024
    url = 'http://www.st.com/' + mcu.get('URL')
    if m in supported_mcus:
        smcu = supported_mcus[m]
        ok = True
        if smcu['freq'] != freq:
            ok = False
        if smcu['flash_size'] != flash:
            ok = False
        if smcu['sram_size'] != sram:
            ok = False
        if smcu['eeprom_size'] != eeprom:
            ok = False
        if not ok:
            wrong_param_mcus[m] = {
                'core': core,
                'freq': freq,
                'flash_size': flash,
                'sram_size': sram,
                'eeprom_size': eeprom,
                'url': url,
                'supported_mcu': smcu,
            }
    else:
        unsupported_mcus[m] = {
            'core': core,
            'freq': freq,
            'flash_size': flash,
            'sram_size': sram,
            'eeprom_size': eeprom,
            'url': url,
        }

print("%-15s %-15s %6s %6s %6s %6s" % ('type', 'core', 'flash', 'sram', 'eeprom', 'freq'))
if unsupported_mcus:
    print('---- unsupported mcus ----')
    for k in sorted(unsupported_mcus.keys()):
        v = unsupported_mcus[k]
        print("%-15s %-15s %6s %6s %6s %6s %s" % (k, v['core'], v['flash_size'], v['sram_size'], v['eeprom_size'], v['freq'], v['url']))
if wrong_param_mcus:
    print('---- mcus with wrong params ----')
    for k in sorted(wrong_param_mcus.keys()):
        v = wrong_param_mcus[k]
        s = v['supported_mcu']
        print("%-15s %-15s %6s %6s %6s %6s %s" % (k, v['core'], v['flash_size'], v['sram_size'], v['eeprom_size'], v['freq'], v['url']))
        print("%-15s %-15s %6s %6s %6s %6s" % ('...', v['core'], s['flash_size'], s['sram_size'], s['eeprom_size'], s['freq']))
