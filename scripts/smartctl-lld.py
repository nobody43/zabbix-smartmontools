#!/usr/bin/env python3

## Installation instructions: https://github.com/nobodysu/zabbix-smartmontools

mode = 'device'   # 'device' or 'serial' as primary identifier in zabbix item's name

ctlPath = r'smartctl'
#ctlPath = r'C:\Program Files\smartmontools\bin\smartctl.exe'   # if smartctl isn't in PATH
#ctlPath = r'/usr/local/sbin/smartctl'

# path to second send script
senderPyPath = r'/etc/zabbix/scripts/smartctl-send.py'              # Linux
#senderPyPath = r'C:\zabbix-agent\scripts\smartctl-send.py'         # Win
#senderPyPath = r'/usr/local/etc/zabbix/scripts/smartctl-send.py'   # BSD

# path to zabbix agent configuration file
agentConf = r'/etc/zabbix/zabbix_agentd.conf'                       # Linux
#agentConf = r'C:\zabbix_agentd.conf'                               # Win
#agentConf = r'/usr/local/etc/zabbix24/zabbix_agentd.conf'          # BSD

senderPath = r'zabbix_sender'                                       # Linux, BSD
#senderPath = r'C:\zabbix-agent\bin\win32\zabbix_sender.exe'        # Win

timeout = '60'   # how long the script must wait between LLD and sending, increase if data received late (does not affect windows)

# manually provide disk list or RAID configuration if needed
diskListManual = []
# like this:
#diskListManual = ['/dev/sda -d sat+megaraid,4', '/dev/sda -d sat+megaraid,5']
# more info: https://www.smartmontools.org/wiki/Supported_RAID-Controllers

## End of configuration ##

import sys
import subprocess
import re
from json import dumps
from shlex import split

hostname = '"' + sys.argv[2] + '"'

jsonData = []
senderData = []

stopChars = [('/dev/', ''), (' -d', ''), (',', ''), ('[', ' '), (']', ' '), ('+', '_'), ('  ', ' '), ('/', '_'), ('~', '_'), ('`', '_'), ('@', '_'), ('#', '_'), ('$', '_'), ('%', '_'), ('^', '_'), ('&', '_'), ('*', '_'), ('(', '_'), (')', '_'), ('{', '_'), ('}', '_'), ('=', '_'), (':', '_'), (';', '_'), ('"', '_'), ('?', '_'), ('<', '_'), ('>', '_'), (' ', '_')]

def replace_all(string, stopChars):
    for i, j in stopChars:
        string = string.replace(i, j)
    return string

allDisksStdout = ''
configStatusError = ''
if not diskListManual:   # if manual list is not provided
    try:
        allDisksStdout = subprocess.check_output([ctlPath, '--scan'], universal_newlines=True)   # scan the disks
    except OSError as e:
        if e.args[0] == 2:
            configStatusError = 'SCAN_OS_NOCMD'
        else:
            configStatusError = 'SCAN_OS_ERROR'
    except:
        configStatusError = 'SCAN_UNKNOWN_ERROR'

        if sys.argv[1] == 'getverb':
            raise

    diskListRe = re.findall(r'^(/dev/[^ ]+)', allDisksStdout, re.M)   # and determine short device names
else:
    diskListRe = diskListManual   # or just use manually provided settings
#print(diskListRe)


for d in diskListRe:   # loop through all found drives
    deviceNameOrig = d
    d = replace_all(d, stopChars)   # sanitize the item key
    deviceName = d   # save device name before mode selection and after manual substitution
    #print('disk:                         ', d)

    try:
        diskProc = subprocess.check_output([ctlPath, '-a'] + split(deviceNameOrig), universal_newlines=True)   # take string from 'diskListRe', make arguments from it and append to existing command, then run it
    except OSError as e:
        if e.args[0] == 2:
            configStatusError = 'D_OS_NOCMD'
            break
        else:
            configStatusError = 'D_OS_ERROR'
            break
    except subprocess.CalledProcessError as e:   # handle process-specific errors
        ''' see 'man smartctl' for more information
        Bit 0 = Code 1
        Bit 1 = Code 2
        Bit 2 = Code 4
        Bit 3 = Code 8
        Bit 4 = Code 16
        Bit 5 = Code 32
        Bit 6 = Code 64
        Bit 7 = Code 128
        '''
        diskProc = e.output   # substitude output even on error, so it can be processed further
        senderData.append(hostname + ' smartctl.info[' + d + ',DriveStatus] "ERR_CODE_' + str(e.args[0]) + '"')

        if e.args[0] == 1 or e.args[0] == 2:
            continue   # continue to the next disk on fatal error
    except:
        diskProc = e.output
        senderData.append(hostname + ' smartctl.info[' + d + ',DriveStatus] "UNKNOWN_ERROR_ON_PROCESSING"')

        if sys.argv[1] == 'getverb':
            raise
    else:
        senderData.append(hostname + ' smartctl.info[' + d + ',DriveStatus] "PROCESSED"')   # no trigger assigned, but its needed as a fallback value
    finally:
        jsonData.append({'{#DDRIVESTATUS}':d})   # it will fire even on OSError (no senderData)

    serialRe = re.search(r'^Serial Number:\s+(.+)$', diskProc, re.M | re.I)
    #print(d + ': serialRe.group(1):      ' + serialRe.group(1))
    if serialRe:
        if mode == 'serial':
            d = replace_all(serialRe.group(1), stopChars)   # in 'serial' mode, if serial number is found it will be used as main identifier, also sanitize it
            # ! 'd' becomes serial !

        jsonData.append({'{#DSERIAL}':d})
        senderData.append(hostname + ' smartctl.info[' + d + ',serial] "' + serialRe.group(1) + '"')

    jsonData.append({'{#DNAME}':d})
    senderData.append(hostname + ' smartctl.info[' + d + ',device] "' + deviceName + '"')

    modelRe = re.search(r'^Device Model:\s+(.+)$', diskProc, re.M | re.I)
    #print(d + ': modelRe.group(1):       ' + modelRe.group(1))
    if modelRe:
        jsonData.append({'{#DMODEL}':d})
        senderData.append(hostname + ' smartctl.info[' + d + ',model] "' + modelRe.group(1) + '"')

    firmwareRe = re.search(r'^Firmware Version:\s+(.+)$', diskProc, re.M | re.I)
    #print(d + ': firmwareRe.group(1):    ' + firmwareRe.group(1))
    if firmwareRe:
        jsonData.append({'{#DFIRMWARE}':d})
        senderData.append(hostname + ' smartctl.info[' + d + ',firmware] "' + firmwareRe.group(1) + '"')

    capacityRe = re.search(r'User Capacity:\s+(.+)bytes', diskProc, re.I)
    if capacityRe:
        capacityValue = re.sub('\D', '', capacityRe.group(1))   # substitute all but numbers
        #print(d + ': capacityValue:          ' + capacityValue)
        jsonData.append({'{#DCAPACITY}':d})
        senderData.append(hostname + ' smartctl.info[' + d + ',capacity] "' + capacityValue + '"')

    rpmRe = re.search(r'^Rotation Rate:\s+(\d+)\s+rpm$', diskProc, re.M | re.I)
    #print(d + ': rpmRe.group(1):         ' + rpmRe.group(1))
    if rpmRe:
        jsonData.append({'{#DRPM}':d})
        senderData.append(hostname + ' smartctl.info[' + d + ',rpm] "' + rpmRe.group(1) + '"')

    selftestRe = re.search(r'^SMART overall-health self-assessment test result:\s+(.+)$', diskProc, re.M | re.I)
    #print(d + ': selftestRe.group(1):    ' + selftestRe.group(1))
    if selftestRe:
        jsonData.append({'{#DSELFTEST}':d})
        senderData.append(hostname + ' smartctl.info[' + d + ',selftest] "' + selftestRe.group(1) + '"')

    valuesRe = re.findall(r'^(?:\s+)?(\d+)\s+([\w-]+)\s+[\w-]+\s+\d{3}\s+\d{3}\s+\d{3}\s+[\w-]+\s+[\w-]+\s+[\w-]+\s+(\d+)', diskProc, re.M | re.I)   # catch id, name and value
    #print(d + ': valuesRe:\n', valuesRe)

    jsonData.append({'{#DSMARTSTATUS}':d})
    if valuesRe:
        senderData.append(hostname + ' smartctl.info[' + d + ',SmartStatus] "PRESENT"')   # item does not correctly represents action, will be changed in future

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

    else:
        senderData.append(hostname + ' smartctl.info[' + d + ',SmartStatus] "NO_SMART_VALUES"')

if configStatusError != '':
    senderData.append(hostname + ' smartctl.info[ConfigStatus] "' + configStatusError + '"')
elif not diskListRe:
    senderData.append(hostname + ' smartctl.info[ConfigStatus] "NODISKS"')   # if no disks were found
else:
    senderData.append(hostname + ' smartctl.info[ConfigStatus] "CONFIGURED"')   # signals that client host is configured

senderDataNStr = '\n'.join(senderData)   # items for zabbix sender separated by newlines

if sys.platform != 'win32':   # if not windows
    pythonCmd = 'python3'
else:
    pythonCmd = 'python.exe'

# pass senderDataNStr to smartctl-send.py:
if sys.argv[1] == 'get':
    print(dumps({"data": jsonData}, indent=4))   # print data gathered for LLD

    subprocess.Popen([pythonCmd, senderPyPath, 'get', agentConf, senderPath, timeout, senderDataNStr], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)   # spawn new process and regain shell control immediately (only *nix, windows waits)

elif sys.argv[1] == 'getverb':
    subprocess.Popen([pythonCmd, senderPyPath, 'getverb', agentConf, senderPath, timeout, senderDataNStr], stdin=subprocess.PIPE)   # do not detach if in verbose mode, also skips timeout in smartctl-send.py

else:
    print(sys.argv[0] + " : Not supported. Use 'get' or 'getverb'.")
sys.exit(1)

