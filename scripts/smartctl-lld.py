#!/usr/bin/env python3

## Installation instructions: https://github.com/nobodysu/zabbix-smartmontools

mode = 'device'   # 'device' or 'serial' as primary identifier in zabbix item's name

ctlPath = 'smartctl'
#ctlPath = r'"C:\Program Files\smartmontools\bin\smartctl.exe"'   # if smartctl isn't in PATH

# path to second send script
senderPyPath = r'/etc/zabbix/scripts/smartctl-send.py'               # Linux
#senderPyPath = r'C:\zabbix-agent\scripts\smartctl-send.py'          # Win
#senderPyPath = r'/usr/local/etc/zabbix/scripts/smartctl-send.py'    # BSD

# manually provide disk list or RAID configuration if needed
diskListManual = []
# like this:
#diskListManual = ['sda -d sat+megaraid,4', 'sda -d sat+megaraid,5']
# more info: https://www.smartmontools.org/wiki/Supported_RAID-Controllers

## End of configuration ##

import sys
import subprocess
import re
import json

hostname = '"' + sys.argv[2] + '"'

jsonData = []
senderData = []
allDisksStdout = ''
ctlOut = ''

stopChars = [(' -d', ''), (',', ''), ('[', ' '), (']', ' '), ('+', '_'), ('  ', ' '), ('/', '_'), ('~', '_'), ('`', '_'), ('@', '_'), ('#', '_'), ('$', '_'), ('%', '_'), ('^', '_'), ('&', '_'), ('*', '_'), ('(', '_'), (')', '_'), ('{', '_'), ('}', '_'), ('=', '_'), (':', '_'), (';', '_'), ('"', '_'), ('?', '_'), ('<', '_'), ('>', '_'), (' ', '_')]

def replace_all(string, stopChars):
    for i, j in stopChars:
        string = string.replace(i, j)
    return string

if not diskListManual:   # if manual list is not provided
    allDisksStdout = subprocess.getoutput(ctlPath + ' --scan')   # scan the disks
    diskListRe = re.findall(r'^/dev/(\w+)', allDisksStdout, re.M)   # and determine short device names
else:
    diskListRe = diskListManual   # or just use manually provided settings

for d in diskListRe:   # loop through all found drives
    ctlOut = subprocess.getoutput(ctlPath + ' -a /dev/' + d)

    if diskListManual:
        d = replace_all(d, stopChars)   # sanitize the item key
        # ! 'd' is statically assigned !
    #print('disk:                         ', d)

    deviceName = d   # save device name before mode selection and after manual substitution

    serialRe = re.search(r'^Serial Number:\s+(.+)$', ctlOut, re.M | re.I)
    #print(d + ': serialRe.group(1):      ' + serialRe.group(1))
    if serialRe:
        if mode == 'serial':
            d = replace_all(serialRe.group(1), stopChars)   # in 'serial' mode, if serial number is found it will be used as main identifier, also sanitize it
            # ! 'd' becomes serial !

        jsonData.append({'{#DSERIAL}':d})
        senderData.append(hostname + ' smartctl.info[' + d + ',serial] "' + serialRe.group(1) + '"')

    jsonData.append({'{#DNAME}':d})
    senderData.append(hostname + ' smartctl.info[' + d + ',device] "' + deviceName + '"')

    modelRe = re.search(r'^Device Model:\s+(.+)$', ctlOut, re.M | re.I)
    #print(d + ': modelRe.group(1):       ' + modelRe.group(1))
    if modelRe:
        jsonData.append({'{#DMODEL}':d})
        senderData.append(hostname + ' smartctl.info[' + d + ',model] "' + modelRe.group(1) + '"')

    firmwareRe = re.search(r'^Firmware Version:\s+(.+)$', ctlOut, re.M | re.I)
    #print(d + ': firmwareRe.group(1):    ' + firmwareRe.group(1))
    if firmwareRe:
        jsonData.append({'{#DFIRMWARE}':d})
        senderData.append(hostname + ' smartctl.info[' + d + ',firmware] "' + firmwareRe.group(1) + '"')

    capacityRe = re.search(r'User Capacity:\s+(.+)bytes', ctlOut, re.I)
    if capacityRe:
        capacityValue = re.sub('\D', '', capacityRe.group(1))   # substitute all but numbers
        #print(d + ': capacityValue:          ' + capacityValue)
        jsonData.append({'{#DCAPACITY}':d})
        senderData.append(hostname + ' smartctl.info[' + d + ',capacity] "' + capacityValue + '"')

    rpmRe = re.search(r'^Rotation Rate:\s+(\d+)\s+rpm$', ctlOut, re.M | re.I)
    #print(d + ': rpmRe.group(1):         ' + rpmRe.group(1))
    if rpmRe:
        jsonData.append({'{#DRPM}':d})
        senderData.append(hostname + ' smartctl.info[' + d + ',rpm] "' + rpmRe.group(1) + '"')

    selftestRe = re.search(r'^SMART overall-health self-assessment test result:\s+(.+)$', ctlOut, re.M | re.I)
    #print(d + ': selftestRe.group(1):    ' + selftestRe.group(1))
    if selftestRe:
        jsonData.append({'{#DSELFTEST}':d})
        senderData.append(hostname + ' smartctl.info[' + d + ',selftest] "' + selftestRe.group(1) + '"')

    valuesRe = re.findall(r'^(?:\s+)?(\d+)\s+([\w-]+)\s+[\w-]+\s+\d{3}\s+\d{3}\s+\d{3}\s+[\w-]+\s+[\w-]+\s+[\w-]+\s+(\d+)', ctlOut, re.M | re.I)   # catch id, name and value
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
            jsonData.append({'{#DVALUE}':d, '{#SMARTID}':v[0], '{#SMARTNAME}':v[1]})   # all other possible values

        senderData.append(hostname + ' smartctl.value[' + d + ',' + v[0] + '] ' + v[2])

if senderData:
    senderData.append(hostname + ' smartctl.info[ConfigStatus] "OK"')   # signals that client host is configured
else:
    if ctlOut.find('ermission denied') != -1 or ctlOut.find('missing admin rights') != -1:
        senderData.append(hostname + ' smartctl.info[ConfigStatus] "MISSINGRIGHTS"')
    elif allDisksStdout.find('smartctl: not found') != -1 or allDisksStdout.find('\"smartctl\" ') != -1:
        senderData.append(hostname + ' smartctl.info[ConfigStatus] "NOCMD"')
    elif not diskListRe:
        senderData.append(hostname + ' smartctl.info[ConfigStatus] "NODISKS"')   # if no disks were found
    else:
        senderData.append(hostname + ' smartctl.info[ConfigStatus] "ERROR"')   # something went wrong

senderDataNStr = '\n'.join(senderData)   # items for zabbix sender separated by system-specific newlines

if sys.platform != 'win32':   # if not windows
    cmd = 'python3'
else:
    cmd = 'python.exe'

# pass senderDataNStr to smartctl-send.py:
if sys.argv[1] == 'get':
    print(json.dumps({"data": jsonData}, indent=4))   # print data gathered for LLD

    senderPy = subprocess.Popen([cmd, senderPyPath, 'get'], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, universal_newlines=True)   # spawn new process and regain shell control immediately
    try:
        senderPy.communicate(input=senderDataNStr, timeout=1)
    except:
        pass
elif sys.argv[1] == 'getverb':
    senderPy = subprocess.Popen([cmd, senderPyPath, 'getverb'], stdin=subprocess.PIPE, universal_newlines=True)   # do not detach if in verbose mode, also skips timeout in smartctl-send.py
    try:
        senderPy.communicate(input=senderDataNStr)
    except:
        pass
else:
    print(sys.argv[0] + " : Not supported. Use 'get' or 'getverb'.")
    sys.exit(1)

