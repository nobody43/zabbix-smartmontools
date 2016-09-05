#!/usr/bin/python3

# path to zabbix agent configuration file
agentConf = '/etc/zabbix/zabbix_agentd.conf'

import re
import subprocess
import json

senderPath = 'zabbix_sender'
jsonData = []
senderData = []
isDebug = ''

allDisksStdout = subprocess.getoutput('smartctl --scan')

diskList = re.findall(r'^/dev/(\w+)', allDisksStdout, re.M)

for d in diskList:
    ctlOut = subprocess.getoutput('smartctl -a /dev/' + d)

    modelRe = re.search(r'^Device Model:\s+(.+)$', ctlOut, re.M | re.I)
    #print(modelRe.group(1))
    if modelRe:
        jsonData.append({'{#DMODEL}':d})
        senderData.append('- smartctl.info[' + d + ',model] "' + modelRe.group(1) + '"')

    serialRe = re.search(r'^Serial Number:\s+(.+)$', ctlOut, re.M | re.I)
    #print(serialRe.group(1))
    if serialRe:
        jsonData.append({'{#DSERIAL}':d})
        senderData.append('- smartctl.info[' + d + ',serial] "' + serialRe.group(1) + '"')

    firmwareRe = re.search(r'^Firmware Version:\s+(.+)$', ctlOut, re.M | re.I)
    #print(firmwareRe.group(1))
    if firmwareRe:
        jsonData.append({'{#DFIRMWARE}':d})
        senderData.append('- smartctl.info[' + d + ',firmware] "' + firmwareRe.group(1) + '"')

    selftestRe = re.search(r'^SMART overall-health self-assessment test result:\s+(.+)$', ctlOut, re.M | re.I)
    #print(selftestRe.group(1))
    if selftestRe:
        jsonData.append({'{#DSELFTEST}':d})
        senderData.append('- smartctl.info[' + d + ',selftest] "' + selftestRe.group(1) + '"')

    valuesRe = re.findall(r'^(?:\s+)?(\d+)\s+([a-z_-]+)\s+[\w-]+\s+\d+\s+\d+\s+\d+\s+[\w-]+\s+[\w-]+\s+[\w-]+\s+(\d+)', ctlOut, re.M | re.I)
    #print('valuesRe:    ', valuesRe)

    for i in valuesRe:
        jsonData.append({'{#DVALUE}':d, '{#SMARTID}':i[0], '{#SMARTNAME}':i[1]})
        senderData.append('- smartctl.value[' + d + ',' + i[0] + '] ' + i[2])

#        print('DEVICE:    ', d)
#        print('i[0]:      ', i[0])
#        print('i[1]:      ', i[1])

print(json.dumps({"data": jsonData}, indent=4), flush=True)

import time
time.sleep(2)

senderDataNStr = '\n'.join(senderData)

senderProc = subprocess.Popen([senderPath, isDebug, '-c', agentConf, '-i', '-'], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, universal_newlines=True)
senderProc.communicate(input=senderDataNStr)

#for i in senderData:
#    print(i)
