#!/usr/bin/env python3

## Installation instructions: https://github.com/nobodysu/zabbix-smartmontools ##

import sys

from smartctl_lld import parseConfig, scanDisks, getAllDisks
from smartctl_lld.sender_wrapper import fail_ifNot_Py3, processData

if __name__ == '__main__':
    fail_ifNot_Py3()

    cmd = sys.argv[1]
    host = '"%s"' % (sys.argv[2])
    config = parseConfig()

    configError = None
    if not 'Disks' in config:
        scanDisks_Out = scanDisks(config, cmd)   # scan the disks

        configError = scanDisks_Out[0]   # SCAN_OS_NOCMD, SCAN_OS_ERROR, SCAN_UNKNOWN_ERROR
        diskList = scanDisks_Out[1]
    else:
        diskList = config['Disks']

    jsonData, senderData = getAllDisks(config, host, cmd, diskList)

    if configError:
        senderData.append('%s smartctl.info[ConfigStatus] "%s"' % (host, configError))
    elif not diskList:
        senderData.append('%s smartctl.info[ConfigStatus] "NODISKS"' % (host))   # if no disks were found
    else:
        senderData.append('%s smartctl.info[ConfigStatus] "CONFIGURED"' % (host))   # signals that client host is configured (also fallback)

    link = r'https://github.com/nobodysu/zabbix-smartmontools/issues'
    processData(senderData, jsonData, config['agentConf'], config['senderPyPath'], config['senderPath'], host, link)
