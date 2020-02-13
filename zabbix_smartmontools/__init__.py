# -*- coding: utf-8 -*-

import configparser
from fcntl import ioctl
import glob
from json import dumps
import ntpath
import os
import pprint
import re
from shlex import split
import subprocess
import sys
from time import sleep


def displayVersions(config, senderPath_):
    '''Display python and sender versions.'''
    print('  Python version:\n', sys.version)
    
    try:
        print('\n  Sender version:\n', subprocess.check_output([senderPath_, '-V']).decode())
    except:
        print('Could not run zabbix_sender.')

    print()


# zabbix-smartmontools works by sending discovery data by a normal pull request,
# but by pushing smart statistics with zabbix_sender.  Push statistics could
# theoretically be sent at any time, but we choose to do it immediately
# after discovery.
#
# fork_and_send creates a child process to send push statistics.  That way
# the parent process can swiftly reply with discovery info while the child
# gathers and sends detailed stats.
def fork_and_send(cmd, host, config, diskList, senderData):
    agentConf = config['agentConf']
    senderPath = config['senderPath']
    # Don't fork on Windows, because Windows doesn't have fork
    if cmd == "get" and not sys.platform == 'win32':
        # Must flush prior to fork, otherwise parent and child will both
        # flush the same data and zabbix_agentd will see it twice.
        sys.stdout.flush()
        sys.stderr.flush()
        parentpid = os.getpid()
        pid = os.fork()
        if pid == 0:
            # In child
            stdout = sys.stdout.fileno()
            sys.stdout.close()
            os.close(stdout)
            stderr = sys.stderr.fileno()
            sys.stderr.close()
            os.close(stderr)
            stdin = sys.stdin.fileno()
            sys.stdin.close()
            os.close(stdin)

            # Interrogate drives here so we don't block discovery
            senderData += getSmartData(config, host, cmd, diskList)
            senderDataNStr = '\n'.join(senderData)

            # Wait for the parent process to complete so the zabbix server
            # will have the latest discovery info.
            while True:
                try:
                    os.kill(parentpid, 0)
                except ProcessLookupError:
                    # parent has exited
                    break
                except Exception:
                    # Most likely, parent has exited, PID has been re-assigned,
                    # and we lack permission to signal that PID.
                    break
                # parent is still running; loop
                sleep(0.125)

            send(cmd, agentConf, senderPath, senderData)
        else:
            # In parent; simply return
            True
    elif cmd == "get" and sys.platform == "win32":
        senderData += getSmartData(config, host, cmd, diskList)
        send(cmd, agentConf, senderPath, senderData)
    elif cmd == "getverb":
        senderData += getSmartData(config, host, cmd, diskList)
        pprint.pprint(senderData)
        send(cmd, agentConf, senderPath, senderData)
    else:
        raise NotImplementedError

def getSmartData(config, host, command, diskList):
    driveHeaders = []
    senderData = []
    for (device, protocol) in diskList:   # cycle through disks
        getSmart_Out = getSmart(config, host, command, device, protocol)
        finalD = getSmart_Out[4]

        # Check for smartctl binary-related errors (if disk scan was bypassed)
        if getSmart_Out[0]:
            configError = getSmart_Out[0]   # D_OS_NOCMD, D_OS_ERROR; may rewrite previous (similar) error
            break   # fatal error

        # Begin duplicate check if desired
        if config['skipDuplicates']:
            serialCurrent = getSmart_Out[3][0]
            headerCurrent = getSmart_Out[3][1]

            if serialCurrent and headerCurrent:   # if serial and secondary identifying data is found
                duplicate = False
                for s,h in driveHeaders:
                    if s == serialCurrent and h == headerCurrent:
                        senderData.append('%s smartctl.info[%s,DriveStatus] "DUPLICATE"' % (host, device))
                        duplicate = True
                        break   # break from header check

                if duplicate == True:
                    continue   # continue to the next disk. other sender and json data is discarded

                driveHeaders.append((serialCurrent, headerCurrent))   # add header info for current disk, only if it's not duplicate

        senderData.extend(getSmart_Out[1])
    return senderData


def getDiscoveryData(config, host, diskList):
    """ Return the data that Zabbix expects for device discovery """
    reported_serials = set({})
    jsonData = []
    for (device, protocol) in diskList:
        if config['mode'] == 'serial' or config['skipDuplicates']:
            serial = getSerial(device)
        else:
            serial = None
        if config['mode'] == 'serial' and serial:
            identifier = serial
        else:
            identifier = device
        jsonData.append({'{#DDRIVESTATUS}': identifier})
        if not serial in reported_serials or not config['skipDuplicates']:
            jsonData.append({"{#DISKID}": identifier})
            jsonData.append({"{#DISKIDSAS}": identifier})
        if serial:
            reported_serials.add(serial)
    return jsonData


# Get the serial number of a hard drive, using the fastest method available on
# each platform.
def getSerial(device):
    """ Get the serial number of a hard drive """
    serial = None
    if 'freebsd' in sys.platform:
        DISK_IDENT_SIZE = 256       # from sys/disk.h
        DIOCGIDENT = 0x41006489     # from sys/disk.h
        ident = DISK_IDENT_SIZE * r" "
        f = open("/dev/%s" % device, 'r')
        serial = ioctl(f, DIOCGIDENT, ident).decode().strip("\x00")
    elif sys.platform.startswith('linux'):
        # TODO: is there a way to get this without using a subprocess?
        cp = subprocess.run(["/sbin/udevadm", "info", "--query=all",
            "--name=/dev/%s" % device], capture_output=True)
        for line in cp.stdout.decode().splitlines():
            match = re.match("ID_SERIAL_SHORT=(\S+)", line)
            if match:
                serial = match.groups()[1]
                break
    else:
        raise NotImplementedError
    return serial

def getSmart(config, host, command, device, protocol):
    if not 'Disks' in config and protocol == 'scsi':
        protocol = 'auto'           # prevent empty results

    identifier = device
    sender = []
    json = []
    driveStatus = None
    serial = None      # tracking duplicates
    driveHeader = []   # tracking duplicates

    try:
        p = subprocess.check_output([config['ctlPath'], '-a', "/dev/%s" % device, "-d", protocol], universal_newlines=True)
    except OSError as e:
        if e.args[0] == 2:
            fatalError = 'D_OS_NOCMD'
        else:
            fatalError = 'D_OS_ERROR'

        return fatalError, sender, json, (serial, driveHeader), identifier

    except subprocess.CalledProcessError as e:   # handle process-specific errors
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
        p = e.output   # substitude output even on error, so it can be processed further
        driveStatus = 'ERR_CODE_%s' % (str(e.args[0]))

        m1 = "SMART support is: Unavailable - Packet Interface Devices [this device: CD/DVD] don't support ATA SMART"
        if m1 in p:
            sender.append('%s smartctl.info[%s,DriveStatus] "CD_DVD_DRIVE"' % (host, identifier))
            return None, sender, json, (serial, driveHeader), identifier

        m2 = "Unknown USB bridge"
        if m2 in p:
            sender.append('%s smartctl.info[%s,DriveStatus] "UNK_USB_BRIDGE"' % (host, identifier))
            return None, sender, json, (serial, driveHeader), identifier

        if e.args[0] == 1 or e.args[0] == 2:
            sender.append('%s smartctl.info[%s,DriveStatus] "%s"' % (host, identifier, driveStatus))   # duplicate follows
            return None, sender, json, (serial, driveHeader), identifier

    except Exception as e:
        p = e.output
        driveStatus = 'UNKNOWN_ERROR_ON_PROCESSING'

        if command == 'getverb':
            raise
    else:
        driveStatus = 'PROCESSED'   # no trigger assigned, but its needed as a fallback value

    # Determine disk identifier
    serialRe = re.search(r'^Serial Number:\s+(.+)$', p, re.M | re.I)
    if serialRe:
        serial = sanitizeStr(serialRe.group(1))   # tracking duplicates
    if serial and config['mode'] == 'serial':
        identifier = serial
    if serial:
        sender.append('%s smartctl.info[%s,serial] "%s"' % (host, identifier, serialRe.group(1)))

    # Process disk errors when disk ID is determined
    if driveStatus:
        sender.append('%s smartctl.info[%s,DriveStatus] "%s"' % (host, identifier, driveStatus))

    # Adding main LLD
    json.append({'{#DISKID}':identifier})
    sender.append('%s smartctl.info[%s,device] "%s"' % (host, identifier, device))

    # SATA and SAS info
    familyRe = re.search(r'^Model Family:\s+(.+)$', p, re.M | re.I)
    if familyRe:
        sender.append('%s smartctl.info[%s,family] "%s"' % (host, identifier, str(familyRe.group(1)).replace('"', '\\"')))

    modelRe = re.search(r'^Device Model:\s+(.+)$|^Device:\s+(.+)$|^Product:\s+(.+)$', p, re.M | re.I)
    if modelRe:
        if modelRe.group(1):
            modelResult = modelRe.group(1)
        elif modelRe.group(2):
            modelResult = modelRe.group(2)
        elif modelRe.group(3):
            modelResult = modelRe.group(3)
        else:
            modelResult = 'UNKNOWN'

        sender.append('%s smartctl.info[%s,model] "%s"' % (host, identifier, modelResult))
        driveHeader.append(modelRe.group(1))   # tracking duplicates

    capacityRe = re.search(r'User Capacity:\s+(.+)bytes', p, re.I)
    if capacityRe:
        capacityValue = re.sub('\s|\,', '', capacityRe.group(1))
        sender.append('%s smartctl.info[%s,capacity] "%s"' % (host, identifier, capacityValue))
        driveHeader.append(capacityValue)   # tracking duplicates

    selftestRe = re.search(r'^SMART overall-health self-assessment test result:\s+(.+)$|^SMART Health Status:\s+(.+)$', p, re.M | re.I)
    if selftestRe:
        if selftestRe.group(1):
            selftestResult = selftestRe.group(1)
        elif selftestRe.group(2):
            selftestResult = selftestRe.group(2)
        else:
            selftestResult = 'UNKNOWN'

        sender.append('%s smartctl.info[%s,selftest] "%s"' % (host, identifier, selftestResult))

    rpmRe = re.search(r'^Rotation Rate:\s+(\d+)\s+rpm$', p, re.M | re.I)
    if rpmRe:
        sender.append('%s smartctl.info[%s,rpm] "%s"' % (host, identifier, rpmRe.group(1)))
        driveHeader.append(rpmRe.group(1))   # tracking duplicates

    formfactorRe = re.search(r'^Form Factor:\s+(.+)$', p, re.M | re.I)
    if formfactorRe:
        sender.append('%s smartctl.info[%s,formFactor] "%s"' % (host, identifier, formfactorRe.group(1)))

    # non-SAS info
    sataVerRe = re.search(r'^SATA Version is:\s+(.+)$', p, re.M | re.I)
    if sataVerRe:
        sender.append('%s smartctl.info[%s,sataVersion] "%s"' % (host, identifier, sataVerRe.group(1)))

    bandwidthMaxRe = re.search(r'^SATA Version is:\s+.+,\s+(\d+\.\d+)\s+Gb\/s', p, re.M | re.I)
    if bandwidthMaxRe:
        json.append({'{#DISKIDBANDWIDTH}':identifier})
        sender.append('%s smartctl.info[%s,bandwidthMax] "%s"' % (host, identifier, bandwidthMaxRe.group(1)))

        bandwidthCurrentRe = re.search(r'^SATA Version is:\s+.+current\:\s+(\d+\.\d+)\s+Gb\/s', p, re.M | re.I)
        if bandwidthCurrentRe:
            bandwidthCurrentResult = bandwidthCurrentRe.group(1)
        else:
            bandwidthCurrentResult = bandwidthMaxRe.group(1)

        sender.append('%s smartctl.info[%s,bandwidthCurrent] "%s"' % (host, identifier, bandwidthCurrentResult))

    firmwareRe = re.search(r'^Firmware Version:\s+(.+)$', p, re.M | re.I)
    if firmwareRe:
        sender.append('%s smartctl.info[%s,firmware] "%s"' % (host, identifier, firmwareRe.group(1)))
        driveHeader.append(firmwareRe.group(1))   # tracking duplicates

    vendorRe = re.search(r'^Vendor:\s+(.+)$', p, re.M | re.I)
    if vendorRe:
        sender.append('%s smartctl.info[%s,vendor] "%s"' % (host, identifier, vendorRe.group(1)))

    # SAS-only SSD value
    ssdwearRe = re.search(r'^Percentage used endurance indicator:\s+(\d+)', p, re.M | re.I)
    if ssdwearRe:
        json.append({'{#DISKIDSSD}':identifier})
        sender.append('%s smartctl.value[%s,SSDwear] "%s"' % (host, identifier, ssdwearRe.group(1)))

    # SATA values
    valuesRe = re.findall(r'^(?:\s+)?(\d+)\s+([\w-]+)\s+[\w-]+\s+\d{3}\s+[\w-]+\s+[\w-]+\s+[\w-]+\s+[\w-]+\s+[\w-]+\s+(\d+)', p, re.M | re.I)   # catch id, name and value
    if valuesRe:
        sender.append('%s smartctl.info[%s,SmartStatus] "PRESENT_SATA"' % (host, identifier))

        for v in valuesRe:
            json.append({'{#DVALUE%s}' % v[0]:identifier, '{#SMARTNAME}':v[1]})
            sender.append('%s smartctl.value[%s,%s] %s' % (host, identifier, v[0], v[2]))

    else:
        getSmartSAS_Out = getSmartSAS(host, p, identifier)
        if not getSmartSAS_Out[0]:
            sender.append('%s smartctl.info[%s,SmartStatus] "PRESENT_SAS"' % (host, identifier))
            sender.extend(getSmartSAS_Out[1])
            json.extend(getSmartSAS_Out[2])

        else:
            sender.extend(whyNoSmart(p, identifier))

    return None, sender, json, (serial, driveHeader), identifier


def getSmartSAS(host, p, identifier):
    sender = []
    json = []

    # SAS info
    revisionRe = re.search(r'^Revision:\s+(.+)$|^Version:\s+(.+)$', p, re.M | re.I)
    if revisionRe:
        if revisionRe.group(1):
            revisionResult = revisionRe.group(1)
        elif revisionRe.group(2):
            revisionResult = revisionRe.group(2)
        else:
            revisionResult = 'UNKNOWN'

        sender.append('%s smartctl.info[%s,revision] "%s"' % (host, identifier, revisionResult))

    complianceRe = re.search(r'^Compliance:\s+(.+)$', p, re.M | re.I)
    if complianceRe:
        sender.append('%s smartctl.info[%s,compliance] "%s"' % (host, identifier, complianceRe.group(1)))

    manufacturedRe = re.search(r'^Manufactured in week (\d+) of year (\d+)', p, re.M | re.I)
    if manufacturedRe:
        sender.append('%s smartctl.info[%s,manufacturedYear] "%s"' % (host, identifier, manufacturedRe.group(2)))

    # SAS values
    loadUnloadRe = re.search(r'^Accumulated load-unload cycles:\s+(\d+)', p, re.M | re.I)
    if loadUnloadRe:
        sender.append('%s smartctl.value[%s,loadUnload] "%s"' % (host, identifier, loadUnloadRe.group(1)))

        loadUnloadMaxRe = re.search(r'^Specified load-unload count over device lifetime:\s+(\d+)', p, re.M | re.I)
        if loadUnloadMaxRe:
            sender.append('%s smartctl.value[%s,loadUnloadMax] "%s"' % (host, identifier, loadUnloadMaxRe.group(1)))

    startStopRe = re.search(r'^Accumulated start-stop cycles:\s+(\d+)|^Current start stop count:\s+(\d+)', p, re.M | re.I)
    if startStopRe:
        if startStopRe.group(1):
            startStopResult = startStopRe.group(1)
        elif startStopRe.group(2):
            startStopResult = startStopRe.group(2)
        else:
            startStopResult = 'UNKNOWN'

        sender.append('%s smartctl.value[%s,startStop] "%s"' % (host, identifier, startStopResult))

        startStopMaxRe = re.search(r'^Recommended maximum start stop count:\s+(\d+)|^Specified cycle count over device lifetime:\s+(\d+)', p, re.M | re.I)
        if startStopMaxRe:
            if startStopMaxRe.group(1):
                startStopMaxResult = startStopMaxRe.group(1)
            elif startStopMaxRe.group(2):
                startStopMaxResult = startStopMaxRe.group(2)
            else:
                startStopMaxResult = 'UNKNOWN'

            sender.append('%s smartctl.value[%s,startStopMax] "%s"' % (host, identifier, startStopMaxResult))

    defectsRe = re.search(r'^Elements in grown defect list:\s+(\d+)', p, re.M | re.I)
    if defectsRe:
        sender.append('%s smartctl.value[%s,defects] "%s"' % (host, identifier, defectsRe.group(1)))

    poweredHoursRe = re.search(r'^number of hours powered up \=\s+(\d+)', p, re.M | re.I)
    if poweredHoursRe:
        sender.append('%s smartctl.value[%s,poweredHours] "%s"' % (host, identifier, poweredHoursRe.group(1)))

    nonMediumErrorsRe = re.search(r'^Non-medium error count:\s+(\d+)', p, re.M | re.I)
    if nonMediumErrorsRe:
        sender.append('%s smartctl.value[%s,nonMediumErrors] "%s"' % (host, identifier, nonMediumErrorsRe.group(1)))

    if sender:
        error = False
    else:
        error = True

    json.append({'{#DISKIDSAS}':identifier})

    return error, sender, json


def isWindows():
    if sys.platform == 'win32':
        return True
    else:
        return False


def main():
    cmd = sys.argv[1]
    host = '"%s"' % (sys.argv[2])
    config = parseConfig()
    senderData = []

    configError = None
    if not 'Disks' in config:
        scanDisks_Out = scanDisks(config, cmd)   # scan the disks

        configError = scanDisks_Out[0]   # SCAN_OS_NOCMD, SCAN_OS_ERROR, SCAN_UNKNOWN_ERROR
        diskList = scanDisks_Out[1]
    else:
        diskList = config['Disks']

    jsonData = getDiscoveryData(config, host, diskList)

    if configError:
        senderData.append('%s smartctl.info[ConfigStatus] "%s"' % (host, configError))
    elif not diskList:
        senderData.append('%s smartctl.info[ConfigStatus] "NODISKS"' % (host))   # if no disks were found
    else:
        senderData.append('%s smartctl.info[ConfigStatus] "CONFIGURED"' % (host))   # signals that client host is configured (also fallback)

    # pass senderDataNStr to sender_wrapper.py:
    if cmd == 'get':
        print(dumps({"data": jsonData}, indent=4))   # print data gathered for LLD

        fork_and_send(cmd, host, config, diskList, senderData)

    elif cmd == 'getverb':
        displayVersions(config['agentConf'], config['senderPath'])
        readConfig(config['agentConf'])
        print('\n  Note: the sender will fail if server did not gather LLD previously.')
        print('\n  Data sent to zabbix sender:')
        print('\n')

        fork_and_send(cmd, host, config, diskList, senderData)

    else:
        print(sys.argv[0] + ": Not supported. Use 'get' or 'getverb'.")



def whyNoSmart(p, dR):
    sender = []

    smartUnavailableRe = re.search(r'^SMART support is:\s+Unavailable - device lacks SMART capability', p, re.M | re.I)
    smartDisabledRe = re.search(r'^SMART support is:\s+Disabled', p, re.M | re.I)

    if smartUnavailableRe:
        sender.append('%s smartctl.info[%s,SmartStatus] "UNAVAILABLE"' % (host, dR))
    elif smartDisabledRe:
        sender.append('%s smartctl.info[%s,SmartStatus] "DISABLED"' % (host, dR))
    else:
        sender.append('%s smartctl.info[%s,SmartStatus] "NO_SMART_VALUES"' % (host, dR))   # something else

    return sender


# Read the config file and return a dict of settings
def parseConfig(path=None):
    if sys.platform.startswith('linux'):
        agent_conf = '/etc/zabbix/zabbix_agentd.conf'
        sender_path = "zabbix_sender"
        sender_py_path = "/etc/zabbix/scripts/sender_wrapper.py"
        if not path:
            path = "/etc/zabbix-smartmontools.conf"
    elif 'freebsd' in sys.platform:
        # FreeBSD usually installs Zabbix in a dir containing the version
        # number, ala "zabbix42"
        try:
            zabbixdir = [
                    p
                    for p in glob.glob('/usr/local/etc/zabbix*')
                    if os.path.isdir(p)
            ][0]
        except IndexError:
            raise 'Error: can\'t find path to Zabbix config directory'
        agent_conf = '%s/zabbix_agentd.conf' % zabbixdir
        sender_path = "zabbix_sender"
        sender_py_path = "%s/scripts/sender_wrapper.py" % zabbixdir
        if not path:
            path = "/usr/local/etc/zabbix-smartmontools.conf"
    elif sys.platform == 'win32':
        agent_conf = r'C:\zabbix_agentd.conf'
        sender_path = r"C:\zabbix-agent\bin\win32\zabbix_sender.exe"
        sender_py_path = r"C:\zabbix-agent\scripts\sender_wrapper.py"
        if not path:
            path = r"C:\zabbix-agent\zabbix-smartmontools.conf"
    else:
        raise NotImplementedError
    config = configparser.ConfigParser()
    config.read(path)
    d = {
        'mode': config.get('settings', 'mode', fallback='device'),
        'skipDuplicates': config.getboolean('settings', 'skipDuplicates',
            fallback=True),
        'ctlPath': config.get('settings', 'ctlPath', fallback='smartctl'),
        'senderPath': config.get('settings', 'senderPath',
            fallback=sender_path),
        'senderPyPath': config.get('settings', 'senderPyPath',
            fallback=sender_py_path),
        'agentConf': config.get('settings', 'agentConf', fallback=agent_conf),
    }
    if config.has_section('Disks'):
        d['Disks'] = [(k, v) for (k, v) in config['Disks'].items()]

    return d


def readConfig(config):
    '''Read and display important config values for debug.'''
    try:
        f = open(config, 'r')
        text = f.read()
        f.close()

        print("  Config's main settings:")
        server = re.search(r'^(?:\s+)?(Server(?:\s+)?\=(?:\s+)?.+)$', text, re.M)
        if server:
            print(server.group(1))
        else:
            print("Could not find 'Server' setting in config!")

        serverActive = re.search(r'^(?:\s+)?(ServerActive(?:\s+)?\=(?:\s+)?.+)$', text, re.M)
        if serverActive:
            print(serverActive.group(1))
        else:
            print("Could not find 'ServerActive' setting in config!")

    except:
        print('  Could not process config file:\n' + config)
    finally:
        print()


def sanitizeStr(s):
    '''Sanitizes provided string in sequential order.'''
    stopChars = (
        ('/dev/', ''), (' -d', ''),
        ('!', '_'), (',', '_'), ('[', '_'), ('~', '_'), ('  ', '_'),
        (']', '_'), ('+', '_'), ('/', '_'), ('\\', '_'), ('\'', '_'),
        ('`', '_'), ('@', '_'), ('#', '_'), ('$', '_'), ('%', '_'),
        ('^', '_'), ('&', '_'), ('*', '_'), ('(', '_'), (')', '_'),
        ('{', '_'), ('}', '_'), ('=', '_'), (':', '_'), (';', '_'),
        ('"', '_'), ('?', '_'), ('<', '_'), ('>', '_'), (' ', '_'),
    )

    for i, j in stopChars:
        s = s.replace(i, j)

    s = s.strip()

    return s


def scanDisks(config, command):
    '''Determines available disks. Can be skipped.'''
    disks = []
    try:
        p = subprocess.check_output([config['ctlPath'], '--scan'], universal_newlines=True)   # scan the disks
        error = ''
    except OSError as e:
        p = ''

        if e.args[0] == 2:
            error = 'SCAN_OS_NOCMD'
        else:
            error = 'SCAN_OS_ERROR'
    except Exception as e:
        try:   # extra safe
            p = e.output
        except:
            p = ''

        error = 'SCAN_UNKNOWN_ERROR'
        if command == 'getverb':
            raise

    for l in p.splitlines():
        match = re.match(r'/dev/(\S+) [-]d (\S+)', l)
        if match:
            disks.append((match[1], match[2]))

    return error, disks


def send(cmd, agentConf, senderPath, senderData):
    senderDataNStr = '\n'.join(senderData)
    if cmd == 'get':
        devnull = open(os.devnull, 'w')
        senderProc = subprocess.Popen([senderPath, '-c', agentConf, '-i', '-'],
                                      stdin=subprocess.PIPE,
                                      stdout=devnull,
                                      universal_newlines=True,
                                      close_fds=(not isWindows()))

    elif cmd == 'getverb':
        senderProc = subprocess.Popen([senderPath, '-vv', '-c', agentConf, '-i', '-'],
                                      stdin=subprocess.PIPE, universal_newlines=True, close_fds=(not isWindows()))

    else:
        print(sys.argv[0] + " : Not supported. Use 'get' or 'getverb'.")
        sys.exit(1)

    senderProc.communicate(input=senderDataNStr)
