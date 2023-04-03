#!/usr/bin/env python3

MODE = 'device'        # 'device' or 'serial' as primary identifier in zabbix item's name
                       # 'serial' is preferred for multi-disk system

BIN_PATH             = r'smartctl'
#BIN_PATH            = r'C:\Program Files\smartmontools\bin\smartctl.exe'         # if smartctl isn't in PATH
#BIN_PATH            = r'/usr/local/sbin/smartctl'

# path to second send script
SENDER_WRAPPER_PATH  = r'/etc/zabbix/scripts/sender_wrapper.py'                   # Linux
#SENDER_WRAPPER_PATH = r'C:\Program Files\Zabbix Agent\scripts\sender_wrapper.py' # Win
#SENDER_WRAPPER_PATH = r'/usr/local/etc/zabbix/scripts/sender_wrapper.py'         # BSD

# path to zabbix agent configuration file
AGENT_CONF_PATH      = r'/etc/zabbix/zabbix_agentd.conf'                          # Linux
#AGENT_CONF_PATH     = r'C:\Program Files\Zabbix Agent\zabbix_agentd.conf'        # Win
#AGENT_CONF_PATH     = r'/usr/local/etc/zabbix3/zabbix_agentd.conf'               # BSD

SENDER_PATH          = r'zabbix_sender'                                           # Linux, BSD
#SENDER_PATH         = r'C:\Program Files\Zabbix Agent\zabbix_sender.exe'         # Win

DELAY = '50'   # how long the script must wait between LLD and sending, increase if data received late (does not affect windows)
               # this setting MUST be lower than 'Update interval' in discovery rule

PER_DISK_TIMEOUT = 8   # Single disk query can not exceed this value. Python33 or above required.

IS_SKIP_DUPLICATES = True  # skip duplicate disk outputs. 'DriveStatus' json will not be skipped
                           # determined by disk serial, model, capacity and firmware (serial + at least one of others)

IS_CHECK_NVME = False      # Additional overhead. Should be disabled if smartmontools is >= 7 or NVMe is absent.

# manually provide disk list or RAID configuration if needed
DISK_DEVS_MANUAL = []
# like this:
#DISK_DEVS_MANUAL = ['/dev/sda -d sat+megaraid,4', '/dev/sda -d sat+megaraid,5']
# more info: https://www.smartmontools.org/wiki/Supported_RAID-Controllers

## End of configuration ##

import sys
import subprocess
import re
import shlex
from sender_wrapper import (readConfig, processData, clearDiskTypeStr, sanitizeStr, fail_ifNot_Py3)

HOST = sys.argv[2]


def scanDisks(mode_):
    '''Determines available disks. Can be skipped.'''
    if   mode_ == 'NOTYPE':
        cmd = addSudoIfNix([BIN_PATH, '--scan'])
    elif mode_ == 'NVME':
        cmd = addSudoIfNix([BIN_PATH, '--scan', '-d', 'nvme'])
    else:
        print('Invalid type %s. Terminating.' % mode_)
        sys.exit(1)

    try:
        p = subprocess.check_output(cmd, universal_newlines=True)
        error = ''
    except OSError as e:
        p = ''

        if e.args[0] == 2:
            error = 'FATAL_SCAN_OS_NOCMD_%s' % mode_
        else:
            error = 'FATAL_SCAN_OS_ERROR_%s' % mode_

    except Exception as e:
        try:
            p = e.output
        except:
            p = ''

        error = 'FATAL_SCAN_UNKNOWN_ERROR_%s' % mode_
        if sys.argv[1] == 'getverb': raise

    # Determine full device names and types
    disksRe = re.findall(r'^(/dev/[^#]+)', p, re.M)
    disks = [ x.strip() for x in disksRe ]

    return error, disks


def moveCsmiToBegining(disks):

    csmis = []
    others = []

    for i in disks:
        if re.search(r'\/csmi\d+\,\d+', i, re.I):
            csmis.append(i)
        else:
            others.append(i)

    result = csmis + others

    return result


def listDisks():

    errors = []

    if not DISK_DEVS_MANUAL:
        scanDisks_Out = scanDisks('NOTYPE')
        errors.append(scanDisks_Out[0])   # SCAN_OS_NOCMD_*, SCAN_OS_ERROR_*, SCAN_UNKNOWN_ERROR_*

        disks = scanDisks_Out[1]

        if IS_CHECK_NVME:
            scanDisksNVMe_Out = scanDisks('NVME')
            errors.append(scanDisksNVMe_Out[0])

            disks.extend(scanDisksNVMe_Out[1])
        else:
            errors.append('')

    else:
        disks = DISK_DEVS_MANUAL 

    # Remove duplicates preserving order
    diskResult = []
    for i in disks:
        if i not in diskResult:
            diskResult.append(i)

    diskResult = moveCsmiToBegining(diskResult)

    return errors, diskResult


def findAny(valuesRaw_):

    value = None
    for mixed in valuesRaw_:
        if   isinstance(mixed, str):
            value = mixed
            break
        elif isinstance(mixed, tuple):
            for string in mixed:
                if (isinstance(string, str) and string != ''):
                    value = string
                    break

    return value


def findProcOut(devicePath_):

    if not DISK_DEVS_MANUAL:
        devicePath_ = devicePath_.replace('-d scsi', '-d auto')   # bug handling; prevent empty results

    p = ''
    msg = None
    try:
        cmd = addSudoIfNix([BIN_PATH, '-a']) + shlex.split(devicePath_)

        if      (sys.version_info.major == 3 and
                 sys.version_info.minor <= 2):

            p = subprocess.check_output(cmd, universal_newlines=True)
 
            msg = 'ERR_PYTHON32_OR_LESS'
        else:
            p = subprocess.check_output(cmd, universal_newlines=True, timeout=PER_DISK_TIMEOUT)

    except OSError as e:
        if e.args[0] == 2:
            msg = 'FATAL_D_OS_NOCMD'
        else:
            msg = 'FATAL_D_OS_ERROR'

    except subprocess.CalledProcessError as e:
        ''' See 'man smartctl' for more information
        Bit 0 = Code 1
        Bit 1 = Code 2
        Bit 2 = Code 4
        Bit 3 = Code 8
        Bit 4 = Code 16
        Bit 5 = Code 32
        Bit 6 = Code 64
        Bit 7 = Code 128
        '''
        p = e.output

        if whyNoSmart(p):
            msg = str(whyNoSmart(p))
        elif e.args[0] == 1 or e.args[0] == 2:
            msg = 'DISKFATAL_ERR_CODE_%s' % (str(e.args[0]))
        else:
            msg = 'ERR_CODE_%s' % (str(e.args[0]))

    except subprocess.TimeoutExpired:
        msg = 'DISKFATAL_TIMEOUT'

    except:
        p = e.output
        msg = 'ERR_UNKNOWN'

        if sys.argv[1] == 'getverb':
            raise
    else:
        msg = 'PROCESSED'   # fallback

    return msg, p


def findSmart(p_, diskIdent_):

    keysAndRegexps = (
        ('smartctl.info[%s,family]',           r'^Model Family:\s+(.+)$'),
        ('smartctl.info[%s,model]',            r'^Device Model:\s+(.+)$|^Device:\s+(.+)$|^Product:\s+(.+)$|^Model Number:\s+(.+)$'),
        ('smartctl.info[%s,selftest]',         r'^SMART overall-health self-assessment test result:\s+(.+)$|^SMART Health Status:\s+(.+)$'),
        ('smartctl.info[%s,serial]',           r'^Serial Number:\s+(.+)$'),
        ('smartctl.info[%s,sataVersion]',      r'^SATA Version is:\s+(.+)$'),
        ('smartctl.info[%s,bandwidthMax]',     r'^SATA Version is:\s+.+,\s+(\d+\.\d+)\s+Gb\/s'),
        ('smartctl.info[%s,bandwidthCurrent]', r'^SATA Version is:\s+.+current\:\s+(\d+\.\d+)\s+Gb\/s|^SATA Version is:\s+.+,\s+(\d+\.\d+)\s+Gb\/s'),  # magic; second one is 'current' only when first one is absent
        ('smartctl.info[%s,rpm]',              r'^Rotation Rate:\s+(\d+)\s+rpm$'),
        ('smartctl.info[%s,formFactor]',       r'^Form Factor:\s+(.+)$'),
        ('smartctl.info[%s,firmware]',         r'^Firmware Version:\s+(.+)$'),
        ('smartctl.info[%s,vendor]',           r'^Vendor:\s+(.+)$'),
        ('smartctl.value[%s,SSDwear]',         r'^Percentage used endurance indicator:\s+(\d+)'),
    )
    sender = []
    json = []

    json.append({'{#DISKIDBANDWIDTH}':diskIdent_})
    json.append({'{#DISKIDSSD}':diskIdent_})
    json.append({'{#DISKID}':diskIdent_})

    # Parse main disk output
    for key, regexp in keysAndRegexps:
        valuesRaw = re.findall(regexp, p_, re.M | re.I)
        value = findAny(valuesRaw)
        if value:
            sender.append('"%s" %s "%s"' % (HOST, (key % diskIdent_), sanitizeQuotes(value.strip())))

    # Special cases <3
    capacityRe = re.search(r'^User Capacity:\s+(.+)bytes', p_, re.M | re.I)
    if capacityRe:
        capacitySub = re.sub('\s|\,', '', capacityRe.group(1))
        sender.append('"%s" smartctl.info[%s,capacity] "%s"' % (HOST, diskIdent_, capacitySub))

    # Catch number, name and value
    gotValues = False
    valuesRe = re.findall(r'^(?:\s+)?(\d+)\s+([\w-]+)\s+[\w-]+\s+\d{3}\s+[\w-]+\s+[\w-]+\s+[\w-]+\s+[\w-]+\s+[\w-]+\s+(\d+)', p_, re.M | re.I)
    if valuesRe:
        gotValues = True
        sender.append('"%s" smartctl.info[%s,SmartStatus] "SMART_SATA"' % (HOST, diskIdent_))
        for num, name, val in valuesRe:
            sender.append('"%s" smartctl.value[%s,%s] %s' % (HOST, diskIdent_, num, val))
            json.append({('{#DVALUE%s}' % num):diskIdent_, '{#SMARTNAME}':name})

    return sender, json, gotValues


def findSmartSAS(p_, diskIdent_):

    keysAndRegexpsSAS = (
        ('smartctl.info[%s,revision]',         r'^Revision:\s+(.+)$|^Version:\s+(.+)$'),
        ('smartctl.info[%s,compliance]',       r'^Compliance:\s+(.+)$'),
        ('smartctl.info[%s,manufacturedYear]', r'^Manufactured in week \d+ of year (\d+)'),
        ('smartctl.value[%s,loadUnload]',      r'^Accumulated load-unload cycles:\s+(\d+)'),
        ('smartctl.value[%s,loadUnloadMax]',   r'^Specified load-unload count over device lifetime:\s+(\d+)'),
        ('smartctl.value[%s,startStop]',       r'^Accumulated start-stop cycles:\s+(\d+)|^Current start stop count:\s+(\d+)'),
        ('smartctl.value[%s,startStopMax]',    r'^Recommended maximum start stop count:\s+(\d+)|^Specified cycle count over device lifetime:\s+(\d+)'),
        ('smartctl.value[%s,defects]',         r'^Elements in grown defect list:\s+(\d+)'),
        ('smartctl.value[%s,poweredHours]',    r'^number of hours powered up \=\s+(\d+)'),
        ('smartctl.value[%s,nonMediumErrors]', r'^Non-medium error count:\s+(\d+)'),
    )
    sender = []
    json = []

    for key, regexp in keysAndRegexpsSAS:
        valuesRaw = re.findall(regexp, p_, re.M | re.I)
        value = findAny(valuesRaw)
        if value:
            sender.append('"%s" %s "%s"' % (HOST, (key % diskIdent_), sanitizeQuotes(value.strip())))

    if sender:
        json = [{'{#DISKIDSAS}':diskIdent_}]

    return sender, json


def whyNoSmart(p_):

    messagesAndRegexps = (
        ('SMART_UNAVAILABLE',     r'^SMART support is:\s+Unavailable - device lacks SMART capability'),
        ('SMART_UNAVAILABLE_PID', r'^SMART support is:\s+Unavailable - Packet Interface Devices'),
        ('SMART_DISABLED',        r'^SMART support is:\s+Disabled'),
        ('SMART_UNK_USB_BRIDGE',  r'Unknown USB bridge'),
    )

    msg = None
    for m, regexp in messagesAndRegexps:
        val = re.search(regexp, p_, re.M | re.I)
        if val:
            msg = m
            break

    return msg


def addSudoIfNix(cmd):

    result = cmd
    if not sys.platform == 'win32':
        result = ['sudo'] + cmd

    return result


def sanitizeQuotes(string):

    if string:
        string = string.replace('"', r'\"')
        string = string.replace("'", r"\'")

    return string


def findIdent(p_, devName_):

    identPatterns = (
        '^Serial Number:\s+(.+)$',
        '^LU WWN Device Id:\s+(.+)$',
        '^Logical Unit id:\s+(.+)$',
    )

    ident = None
    for i in identPatterns:
        identRe = re.search(i, p_, re.I | re.M)
        if identRe:
            ident = sanitizeStr(identRe.group(1))
            break

    if not ident:
        ident = devName_

    return ident


if __name__ == '__main__':

    fail_ifNot_Py3()

    senderData = []
    jsonData = []

    listDisks_Out = listDisks()
    scanErrors = listDisks_Out[0]
    diskDevs   = listDisks_Out[1]

    fatalError = None
    allDiskIdents = []
    for devPath in diskDevs:
        devName = sanitizeStr(clearDiskTypeStr(devPath))
        findProc_Out = findProcOut(devPath)
        disk_msg  = findProc_Out[0]
        disk_pOut = findProc_Out[1]

        diskIdent = findIdent(disk_pOut, devName)
        diskIdentDup = diskIdent

        if MODE == 'device':
            diskIdent = devName

        jsonData.append({'{#DDRIVESTATUS}':diskIdent})
        if   disk_msg.startswith('FATAL_'):  # if scan was bypassed
            fatalError = disk_msg
            break
        elif disk_msg.startswith('DISKFATAL_'):
            senderData.append('"%s" smartctl.info[%s,DriveStatus] "%s"' % (HOST, diskIdent, disk_msg))
            continue

        if IS_SKIP_DUPLICATES:
            if diskIdentDup in allDiskIdents:
                senderData.append('"%s" smartctl.info[%s,DriveStatus] "DUPLICATE"' % (HOST, diskIdent))
                continue
            allDiskIdents.append(diskIdentDup)

        senderData.append('"%s" smartctl.info[%s,DriveStatus] "%s"' % (HOST, diskIdent, disk_msg))
        senderData.append('"%s" smartctl.info[%s,device] "%s"'      % (HOST, diskIdent, devName))
        findSmart_Out = findSmart(disk_pOut, diskIdent)
        diskSender = findSmart_Out[0]
        diskJson   = findSmart_Out[1]
        gotSmart   = findSmart_Out[2]
        if diskSender:
            senderData.extend(diskSender)
            jsonData.extend(diskJson)

        if not gotSmart:
            findSmartSAS_Out = findSmartSAS(disk_pOut, diskIdent)
            diskSenderSAS = findSmartSAS_Out[0]
            diskJsonSAS   = findSmartSAS_Out[1]
            if diskSenderSAS:
                senderData.append('"%s" smartctl.info[%s,SmartStatus] "SMART_SAS"' % (HOST, diskIdent))
                senderData.extend(diskSenderSAS)
                jsonData.extend(diskJsonSAS)
            else:
                senderData.append('"%s" smartctl.info[%s,SmartStatus] "%s"' % (HOST, diskIdent, str(whyNoSmart(disk_pOut))))

    if fatalError:
        configStatus = fatalError
    elif not diskDevs:
        configStatus = "NODISKS"
    else:
        configStatus = "CONFIGURED"

    senderData.append('"%s" smartctl.info[ConfigStatus] "%s"' % (HOST, configStatus))

    link = r'https://github.com/nobody43/zabbix-smartmontools/issues'
    processData(senderData, jsonData, AGENT_CONF_PATH, SENDER_WRAPPER_PATH, SENDER_PATH, DELAY, HOST, link)

