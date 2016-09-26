#!/usr/bin/env python3

## Installation instructions: https://github.com/nobodysu/zabbix-smartmontools

# path to second send script
senderPyPath = r'/etc/zabbix/scripts/smartctl-send.py'               # Linux
#senderPyPath = r'C:\zabbix-agent\scripts\smartctl-send.py'          # Win
#senderPyPath = r'/usr/local/etc/zabbix/scripts/smartctl-send.py'    # BSD

# provide raid configuration if needed
raidOverride = []
# like this:
#raidOverride = ['sda -d sat+megaraid,4', 'sda -d sat+megaraid,5']
# more info: https://www.smartmontools.org/wiki/Supported_RAID-Controllers

import sys
import subprocess
import re
import json

jsonData = []
senderData = []

if not raidOverride:   # if RAID is not defined
    allDisksStdout = subprocess.getoutput('smartctl --scan')   # scan the disks
    diskListRe = re.findall(r'^/dev/(\w+)', allDisksStdout, re.M)   # and determine short device names
else:
    diskListRe = raidOverride   # or just use manually provided settings

for d in diskListRe:   # loop through all found drives
    ctlOut = subprocess.getoutput('smartctl -a /dev/' + d)

    if raidOverride:
        d = d.replace(',', '').replace(' -d', '').replace('[', '').replace(']', '').replace('+', '_').replace('  ', ' ').replace(' ', '_')  # slightly sanitize the item key. for RAID only
    #print('disk:                         ', d)

    modelRe = re.search(r'^Device Model:\s+(.+)$', ctlOut, re.M | re.I)
    #print(d + ': modelRe.group(1):       ' + modelRe.group(1))
    if modelRe:
        jsonData.append({'{#DMODEL}':d})
        senderData.append('- smartctl.info[' + d + ',model] "' + modelRe.group(1) + '"')

    serialRe = re.search(r'^Serial Number:\s+(.+)$', ctlOut, re.M | re.I)
    #print(d + ': serialRe.group(1):      ' + serialRe.group(1))
    if serialRe:
        jsonData.append({'{#DSERIAL}':d})
        senderData.append('- smartctl.info[' + d + ',serial] "' + serialRe.group(1) + '"')

    firmwareRe = re.search(r'^Firmware Version:\s+(.+)$', ctlOut, re.M | re.I)
    #print(d + ': firmwareRe.group(1):    ' + firmwareRe.group(1))
    if firmwareRe:
        jsonData.append({'{#DFIRMWARE}':d})
        senderData.append('- smartctl.info[' + d + ',firmware] "' + firmwareRe.group(1) + '"')

    capacityRe = re.search(r'User Capacity:\s+(.+)bytes', ctlOut, re.I)
    if capacityRe:
        capacityValue = re.sub('\D', '', capacityRe.group(1))   # substitute all but numbers
        #print(d + ': capacityValue:          ' + capacityValue)
        jsonData.append({'{#DCAPACITY}':d})
        senderData.append('- smartctl.info[' + d + ',capacity] "' + capacityValue + '"')

    rpmRe = re.search(r'^Rotation Rate:\s+(\d+)\s+rpm$', ctlOut, re.M | re.I)
    #print(d + ': rpmRe.group(1):         ' + rpmRe.group(1))
    if rpmRe:
        jsonData.append({'{#DRPM}':d})
        senderData.append('- smartctl.info[' + d + ',rpm] "' + rpmRe.group(1) + '"')

    selftestRe = re.search(r'^SMART overall-health self-assessment test result:\s+(.+)$', ctlOut, re.M | re.I)
    #print(d + ': selftestRe.group(1):    ' + selftestRe.group(1))
    if selftestRe:
        jsonData.append({'{#DSELFTEST}':d})
        senderData.append('- smartctl.info[' + d + ',selftest] "' + selftestRe.group(1) + '"')

    valuesRe = re.findall(r'^(?:\s+)?(\d+)\s+([a-z_-]+)\s+[\w-]+\s+\d+\s+\d+\s+\d+\s+[\w-]+\s+[\w-]+\s+[\w-]+\s+(\d+)', ctlOut, re.M | re.I)
    #print(d + ': valuesRe:\n', valuesRe)
    for v in valuesRe:
        if v[0] == '5':                         # semi-hardcoded values for triggers
            jsonData.append({'{#DVALUE5}':d})
        elif v[0] == '187':
            jsonData.append({'{#DVALUE187}':d})
        elif v[0] == '188':
            jsonData.append({'{#DVALUE188}':d})
        elif v[0] == '197':
            jsonData.append({'{#DVALUE197}':d})
        elif v[0] == '198':
            jsonData.append({'{#DVALUE198}':d})
        elif v[0] == '199':
            jsonData.append({'{#DVALUE199}':d})
        else:
            jsonData.append({'{#DVALUE}':d, '{#SMARTID}':v[0], '{#SMARTNAME}':v[1]})    # all other possible values

        senderData.append('- smartctl.value[' + d + ',' + v[0] + '] ' + v[2])

print(json.dumps({"data": jsonData}, indent=4))   # print data gathered for LLD

senderDataNStr = '\n'.join(senderData)   # items for zabbix sender separated by newlines

# pass senderDataNStr to smartctl-send.py:
if sys.platform != 'win32':   # if not windows
    if sys.argv[1] == 'get':
        subprocess.Popen([senderPyPath, 'get', senderDataNStr], stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)    # spawn new process and regain shell control immediately
    elif sys.argv[1] == '-v':
        subprocess.Popen([senderPyPath, '-v', senderDataNStr])   # do not detach if in verbose mode, also skips timeout in smartctl-send.py
else:   # windows have certain caveats
    if sys.argv[1] == 'get':
        subprocess.Popen(['python', senderPyPath, 'get', senderDataNStr], stdout=None, stderr=None, stdin=None)    
    elif sys.argv[1] == '-v':
        subprocess.Popen(['python', senderPyPath, '-v', senderDataNStr])

if sys.argv[1] != 'get' and sys.argv[1] != '-v':
    print("smartctl-lld: Not supported. Use 'get' or '-v'.")
    sys.exit(1)
