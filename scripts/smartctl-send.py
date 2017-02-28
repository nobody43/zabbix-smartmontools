#!/usr/bin/env python3

## Installation instructions: https://github.com/nobodysu/zabbix-smartmontools

# path to zabbix agent configuration file
agentConf = r'/etc/zabbix/zabbix_agentd.conf'                   # Linux
#agentConf = r'C:\zabbix_agentd.conf'                           # Win
#agentConf = r'/usr/local/etc/zabbix24/zabbix_agentd.conf'      # BSD

senderPath = 'zabbix_sender'                                    # Linux, BSD
#senderPath = r'C:\zabbix-agent\bin\win32\zabbix_sender.exe'    # Win

timeout = 60   # how long the script must wait between LLD and sending, increase if data received late (does not affect windows)

## End of configuration ##

import sys
import subprocess
from time import sleep
import re

stdin4Sender = sys.stdin.read()

if sys.platform == 'win32':   # if windows
    timeout = 0   # probably permanent workaround

if sys.argv[1] == 'get':
    sleep(timeout)   # wait for LLD to be processed by server
    senderProc = subprocess.Popen([senderPath, '-c', agentConf, '-i', '-'],  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, universal_newlines=True)   # send data gathered from second argument to zabbix server
elif sys.argv[1] == 'getverb':
    print('\n  Note: the sender will fail if server did not gather LLD previously.')
    print('\n  Data sent to zabbix sender:\n')
    print(stdin4Sender)
    senderProc = subprocess.Popen([senderPath, '-vv', '-c', agentConf, '-i', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)   # verbose sender output
else:
    print(sys.argv[0] + " : Not supported. Use 'get' or 'getverb'.")
    sys.exit(1)

senderProc.communicate(input=stdin4Sender)

