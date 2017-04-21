#!/usr/bin/env python3

## Configuration was moved to 'smartctl-lld.py'

import sys
from subprocess import Popen, PIPE
from time import sleep

agentConf = sys.argv[2]
senderPath = sys.argv[3]
timeout = int(sys.argv[4])
senderDataNStr = sys.argv[5]

if sys.platform == 'win32':   # if windows
    timeout = 0   # probably permanent workaround

if sys.argv[1] == 'get':
    sleep(timeout)   # wait for LLD to be processed by server
    senderProc = Popen([senderPath, '-c', agentConf, '-i', '-'], stdin=PIPE, universal_newlines=True)   # send data gathered from second argument to zabbix server
elif sys.argv[1] == 'getverb':
    print('\n  Note: the sender will fail if server did not gather LLD previously.')
    print('\n  Data sent to zabbix sender:\n')
    print(senderDataNStr)
    senderProc = Popen([senderPath, '-vv', '-c', agentConf, '-i', '-'], stdin=PIPE, universal_newlines=True)   # verbose sender output
else:
    print(sys.argv[0] + " : Not supported. Use 'get' or 'getverb'.")
    sys.exit(1)

senderProc.communicate(input=senderDataNStr)

