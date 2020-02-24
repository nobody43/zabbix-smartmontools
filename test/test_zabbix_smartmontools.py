#! /usr/bin/env python3

import os
import re
import subprocess
import sys
import unittest
from unittest.mock import MagicMock, Mock, patch

from parameterized import parameterized

import zabbix_smartmontools

# We can't mock the ioctl directly, because of the preceding call to open.
# open is used in so many different places that it's basically unmockable.
# Instead, we'll mock getSerial.
def mock_getserial(mocks):
    def f(config, devname, **kwargs):
        try:
            return mocks[devname]
        except KeyError:
            raise "Unexpected arguments to getSerial"
    return f

def mock_smartctl(diskData):
    def f(args, **kwargs):
        if kwargs['universal_newlines'] != True:
            raise NotImplementedError
        try:
            smartctlargs = " ".join(args[1:])
            return diskData[smartctlargs]
        except KeyError:
            raise "Unexpected arguments to smartctl"
        else:
            return output
    return f

class TestGetSmartData(unittest.TestCase):
    @patch('subprocess.check_output')
    def test_onedisk(self, patchCheckOutput):
        f = open("test/example/%s" % "ST4000NM0023.txt")
        da0_output = f.read()
        f.close()
        patchCheckOutput.side_effect = mock_smartctl({'-a /dev/da0 -d auto': da0_output})
        config = zabbix_smartmontools.parseConfig("test/example/empty")
        diskList = [("da0",  "scsi")]
        r = zabbix_smartmontools.getSmartData(config, "myhost", "getverb", diskList)
        self.assertEqual(r,
            (['myhost smartctl.info[da0,serial] "Z1Z3SGMD00009437061J"',
              'myhost smartctl.info[da0,DriveStatus] "PROCESSED"',
              'myhost smartctl.info[da0,device] "da0"',
              'myhost smartctl.info[da0,model] "ST4000NM0023"',
              'myhost smartctl.info[da0,capacity] "4000787030016"',
              'myhost smartctl.info[da0,selftest] "OK"',
              'myhost smartctl.info[da0,rpm] "7200"',
              'myhost smartctl.info[da0,formFactor] "3.5 inches"',
              'myhost smartctl.info[da0,vendor] "SEAGATE"',
              'myhost smartctl.info[da0,SmartStatus] "PRESENT_SAS"',
              'myhost smartctl.info[da0,revision] "0004"',
              'myhost smartctl.info[da0,compliance] "SPC-4"',
              'myhost smartctl.info[da0,manufacturedYear] "2014"',
              'myhost smartctl.value[da0,loadUnload] "2108"',
              'myhost smartctl.value[da0,loadUnloadMax] "300000"',
              'myhost smartctl.value[da0,startStop] "119"',
              'myhost smartctl.value[da0,startStopMax] "10000"',
              'myhost smartctl.value[da0,defects] "15"',
              'myhost smartctl.value[da0,nonMediumErrors] "181"']))

    @patch('subprocess.check_output')
    def test_duplicates(self, patchCheckOutput):
        f = open("test/example/%s" % "ST4000NM0023.txt")
        da0_output = f.read()
        da1_output = da0_output
        f.close()
        patchCheckOutput.side_effect = mock_smartctl({
            '-a /dev/da0 -d auto': da0_output,
            '-a /dev/da1 -d auto': da1_output,
        })
        config = zabbix_smartmontools.parseConfig("test/example/empty")
        config['skipDuplicates'] = True
        diskList = [("da0",  "scsi"), ("da1", "scsi")]
        r = zabbix_smartmontools.getSmartData(config, "myhost", "getverb", diskList)
        self.assertEqual(r,
            (['myhost smartctl.info[da0,serial] "Z1Z3SGMD00009437061J"',
              'myhost smartctl.info[da0,DriveStatus] "PROCESSED"',
              'myhost smartctl.info[da0,device] "da0"',
              'myhost smartctl.info[da0,model] "ST4000NM0023"',
              'myhost smartctl.info[da0,capacity] "4000787030016"',
              'myhost smartctl.info[da0,selftest] "OK"',
              'myhost smartctl.info[da0,rpm] "7200"',
              'myhost smartctl.info[da0,formFactor] "3.5 inches"',
              'myhost smartctl.info[da0,vendor] "SEAGATE"',
              'myhost smartctl.info[da0,SmartStatus] "PRESENT_SAS"',
              'myhost smartctl.info[da0,revision] "0004"',
              'myhost smartctl.info[da0,compliance] "SPC-4"',
              'myhost smartctl.info[da0,manufacturedYear] "2014"',
              'myhost smartctl.value[da0,loadUnload] "2108"',
              'myhost smartctl.value[da0,loadUnloadMax] "300000"',
              'myhost smartctl.value[da0,startStop] "119"',
              'myhost smartctl.value[da0,startStopMax] "10000"',
              'myhost smartctl.value[da0,defects] "15"',
              'myhost smartctl.value[da0,nonMediumErrors] "181"',
              'myhost smartctl.info[da1,DriveStatus] "DUPLICATE"']))

    @patch('subprocess.check_output')
    def test_serial(self, patchCheckOutput):
        f = open("test/example/%s" % "ST4000NM0023.txt")
        da0_output = f.read()
        f.close()
        patchCheckOutput.side_effect = mock_smartctl({'-a /dev/da0 -d auto': da0_output})
        config = zabbix_smartmontools.parseConfig("test/example/empty")
        config['mode'] = 'serial'
        diskList = [("da0",  "scsi")]
        r = zabbix_smartmontools.getSmartData(config, "myhost", "getverb", diskList)
        self.assertEqual(r,
            (['myhost smartctl.info[Z1Z3SGMD00009437061J,serial] "Z1Z3SGMD00009437061J"',
              'myhost smartctl.info[Z1Z3SGMD00009437061J,DriveStatus] "PROCESSED"',
              'myhost smartctl.info[Z1Z3SGMD00009437061J,device] "da0"',
              'myhost smartctl.info[Z1Z3SGMD00009437061J,model] "ST4000NM0023"',
              'myhost smartctl.info[Z1Z3SGMD00009437061J,capacity] "4000787030016"',
              'myhost smartctl.info[Z1Z3SGMD00009437061J,selftest] "OK"',
              'myhost smartctl.info[Z1Z3SGMD00009437061J,rpm] "7200"',
              'myhost smartctl.info[Z1Z3SGMD00009437061J,formFactor] "3.5 inches"',
              'myhost smartctl.info[Z1Z3SGMD00009437061J,vendor] "SEAGATE"',
              'myhost smartctl.info[Z1Z3SGMD00009437061J,SmartStatus] "PRESENT_SAS"',
              'myhost smartctl.info[Z1Z3SGMD00009437061J,revision] "0004"',
              'myhost smartctl.info[Z1Z3SGMD00009437061J,compliance] "SPC-4"',
              'myhost smartctl.info[Z1Z3SGMD00009437061J,manufacturedYear] "2014"',
              'myhost smartctl.value[Z1Z3SGMD00009437061J,loadUnload] "2108"',
              'myhost smartctl.value[Z1Z3SGMD00009437061J,loadUnloadMax] "300000"',
              'myhost smartctl.value[Z1Z3SGMD00009437061J,startStop] "119"',
              'myhost smartctl.value[Z1Z3SGMD00009437061J,startStopMax] "10000"',
              'myhost smartctl.value[Z1Z3SGMD00009437061J,defects] "15"',
              'myhost smartctl.value[Z1Z3SGMD00009437061J,nonMediumErrors] "181"']))

class TestGetDiscoveryData(unittest.TestCase):
    @patch('zabbix_smartmontools.getSerial')
    def test_onedisk(self, patchGetSerial):
        mock_serials = {"da0": "ABCDEF"}
        patchGetSerial.side_effect = mock_getserial(mock_serials)
        config = zabbix_smartmontools.parseConfig("test/example/empty")
        diskList = [("da0",  "scsi")]
        r = zabbix_smartmontools.getDiscoveryData(config, "myhost", diskList)
        self.assertEqual(r,
            [
                {'{#DDRIVESTATUS}': 'da0'},
                {'{#DISKID}': 'da0'},
                {'{#DISKIDSAS}': 'da0'}
            ]
        )

    @patch('zabbix_smartmontools.getSerial')
    def test_onedisk_with_serial(self, patchGetSerial):
        mock_serials = {"da0": "ABCDEF"}
        patchGetSerial.side_effect = mock_getserial(mock_serials)
        config = zabbix_smartmontools.parseConfig("test/example/empty")
        config['mode'] = 'serial'
        diskList = [("da0",  "scsi")]
        r = zabbix_smartmontools.getDiscoveryData(config, "myhost", diskList)
        self.assertEqual(r,
            [
                {'{#DDRIVESTATUS}': 'ABCDEF'},
                {'{#DISKID}': 'ABCDEF'},
                {'{#DISKIDSAS}': 'ABCDEF'}
            ]
        )

    @patch('zabbix_smartmontools.getSerial')
    def test_skip_duplicates(self, patchGetSerial):
        mock_serials = {"da0": "ABCDEF", "da1": "ABCDEF"}
        patchGetSerial.side_effect = mock_getserial(mock_serials)
        config = zabbix_smartmontools.parseConfig("test/example/empty")
        diskList = [("da0",  "scsi"), ("da1", "scsi")]
        r = zabbix_smartmontools.getDiscoveryData(config, "myhost", diskList)
        self.assertEqual(r,
            [
                {'{#DDRIVESTATUS}': 'da0'},
                {'{#DISKID}': 'da0'},
                {'{#DISKIDSAS}': 'da0'},
                {'{#DDRIVESTATUS}': 'da1'},
            ]
        )

    def test_no_skip_duplicates(self):
        config = zabbix_smartmontools.parseConfig("test/example/empty")
        config['skipDuplicates'] = False
        diskList = [("da0",  "scsi"), ("da1", "scsi")]
        r = zabbix_smartmontools.getDiscoveryData(config, "myhost", diskList)
        self.assertEqual(r,
            [
                {'{#DDRIVESTATUS}': 'da0'},
                {'{#DISKID}': 'da0'},
                {'{#DISKIDSAS}': 'da0'},
                {'{#DDRIVESTATUS}': 'da1'},
                {'{#DISKID}': 'da1'},
                {'{#DISKIDSAS}': 'da1'},
            ]
        )


class TestGetSmart(unittest.TestCase):
    def runtest(self, filename, expected, patchCheckOutput, mode = 'device'):
        f = open("test/example/%s" % filename)
        output = f.read()
        f.close()
        patchCheckOutput.side_effect = mock_smartctl({'-a /dev/da0 -d auto': output})
        config = zabbix_smartmontools.parseConfig("test/example/empty")
        config['mode'] = mode
        r = zabbix_smartmontools.getSmart(config, "myhost", "getverb", "da0", "scsi")
        self.assertEqual(r, expected)

    @parameterized.expand([
        ("ST4000NM0023.txt",
            (None,
             ['myhost smartctl.info[da0,serial] "Z1Z3SGMD00009437061J"',
              'myhost smartctl.info[da0,DriveStatus] "PROCESSED"',
              'myhost smartctl.info[da0,device] "da0"',
              'myhost smartctl.info[da0,model] "ST4000NM0023"',
              'myhost smartctl.info[da0,capacity] "4000787030016"',
              'myhost smartctl.info[da0,selftest] "OK"',
              'myhost smartctl.info[da0,rpm] "7200"',
              'myhost smartctl.info[da0,formFactor] "3.5 inches"',
              'myhost smartctl.info[da0,vendor] "SEAGATE"',
              'myhost smartctl.info[da0,SmartStatus] "PRESENT_SAS"',
              'myhost smartctl.info[da0,revision] "0004"',
              'myhost smartctl.info[da0,compliance] "SPC-4"',
              'myhost smartctl.info[da0,manufacturedYear] "2014"',
              'myhost smartctl.value[da0,loadUnload] "2108"',
              'myhost smartctl.value[da0,loadUnloadMax] "300000"',
              'myhost smartctl.value[da0,startStop] "119"',
              'myhost smartctl.value[da0,startStopMax] "10000"',
              'myhost smartctl.value[da0,defects] "15"',
              'myhost smartctl.value[da0,nonMediumErrors] "181"'],
             [{'{#DISKID}': 'da0'}, {'{#DISKIDSAS}': 'da0'}],
             ('Z1Z3SGMD00009437061J', [None, '4000787030016', '7200']),
             'da0')
        )
    ])
    @patch('subprocess.check_output')
    def test_freebsd(self, filename, expected, patchCheckOutput):
        self.runtest(filename, expected, patchCheckOutput)

    # Test output when mode: serial in the config file
    @parameterized.expand([
        ("ST4000NM0023.txt",
            (None,
             ['myhost smartctl.info[Z1Z3SGMD00009437061J,serial] "Z1Z3SGMD00009437061J"',
              'myhost smartctl.info[Z1Z3SGMD00009437061J,DriveStatus] "PROCESSED"',
              'myhost smartctl.info[Z1Z3SGMD00009437061J,device] "da0"',
              'myhost smartctl.info[Z1Z3SGMD00009437061J,model] "ST4000NM0023"',
              'myhost smartctl.info[Z1Z3SGMD00009437061J,capacity] "4000787030016"',
              'myhost smartctl.info[Z1Z3SGMD00009437061J,selftest] "OK"',
              'myhost smartctl.info[Z1Z3SGMD00009437061J,rpm] "7200"',
              'myhost smartctl.info[Z1Z3SGMD00009437061J,formFactor] "3.5 inches"',
              'myhost smartctl.info[Z1Z3SGMD00009437061J,vendor] "SEAGATE"',
              'myhost smartctl.info[Z1Z3SGMD00009437061J,SmartStatus] "PRESENT_SAS"',
              'myhost smartctl.info[Z1Z3SGMD00009437061J,revision] "0004"',
              'myhost smartctl.info[Z1Z3SGMD00009437061J,compliance] "SPC-4"',
              'myhost smartctl.info[Z1Z3SGMD00009437061J,manufacturedYear] "2014"',
              'myhost smartctl.value[Z1Z3SGMD00009437061J,loadUnload] "2108"',
              'myhost smartctl.value[Z1Z3SGMD00009437061J,loadUnloadMax] "300000"',
              'myhost smartctl.value[Z1Z3SGMD00009437061J,startStop] "119"',
              'myhost smartctl.value[Z1Z3SGMD00009437061J,startStopMax] "10000"',
              'myhost smartctl.value[Z1Z3SGMD00009437061J,defects] "15"',
              'myhost smartctl.value[Z1Z3SGMD00009437061J,nonMediumErrors] "181"'],
             [{'{#DISKID}': 'Z1Z3SGMD00009437061J'}, {'{#DISKIDSAS}': 'Z1Z3SGMD00009437061J'}],
             ('Z1Z3SGMD00009437061J', [None, '4000787030016', '7200']),
             'Z1Z3SGMD00009437061J')
        )
    ])
    @patch('subprocess.check_output')
    def test_serial(self, filename, expected, patchCheckOutput):
        self.runtest(filename, expected, patchCheckOutput, 'serial')

class TestParseConfig(unittest.TestCase):
    def test_defaults(self):
        ''' Should have sane defaults if config file is not present '''
        config = zabbix_smartmontools.parseConfig("/does_not_exist!!!")
        self.assertEqual(config['mode'], 'device')
        self.assertTrue(config['skipDuplicates'])
        self.assertEqual(config['ctlPath'], 'smartctl')
        self.assertFalse('Disks' in config)

    def test_disk_list(self):
        config = zabbix_smartmontools.parseConfig('test/example/with_disk_list.conf')
        self.assertEqual(config['Disks'], [
            ("sda", "sat+megaraid,4"),
            ("da0", "scsi")
        ])

    def test_no_disk_list(self):
        config = zabbix_smartmontools.parseConfig('test/example/no_disk_list.conf')
        self.assertEqual(config['mode'], 'device')
        self.assertTrue(config['skipDuplicates'])
        self.assertEqual(config['ctlPath'], 'smartctl')
        self.assertEqual(config['senderPyPath'],
                '/etc/zabbix/scripts/sender_wrapper.py')
        self.assertEqual(config['agentConf'], '/etc/zabbix/zabbix_agentd.conf')
        self.assertEqual(config['senderPath'], 'zabbix_sender')
        self.assertFalse('Disks' in config)

class TestScan(unittest.TestCase):
    def runtest(self, output, expected_disks, patchCheckOutput):
        patchCheckOutput.side_effect = mock_smartctl({'--scan': output})
        config = zabbix_smartmontools.parseConfig("test/example/empty")
        (error, disks) = zabbix_smartmontools.scanDisks(config, "getverb")
        self.assertEqual(error, "")
        self.assertEqual(disks, expected_disks)

    @parameterized.expand([
        # No disks at all
        ("", []),
        # One scsi disk
        (
            "/dev/da0 -d scsi # /dev/da0, SCSI device\n",
            [("da0", "scsi")],
        ),
        # Two scsi disks
        (
            "/dev/da0 -d scsi # /dev/da0, SCSI device\n/dev/da1 -d scsi # /dev/da1, SCSI device\n",
            [("da0", "scsi"), ("da1", "scsi")],
        ),
        # TODO: ATA disks and NVME disks
    ])
    @patch('subprocess.check_output')
    def test_freebsd(self, smartctl_output, expected_disks, patchCheckOutput):
        self.runtest(smartctl_output, expected_disks, patchCheckOutput)

class TestGetSerial(unittest.TestCase):
    """ Look for a real device and actually try to get its serial """

    def find_device(self, regex):
        device = None
        for fn in os.listdir("/dev"):
            if re.match(regex, fn):
                device = fn
                break
        if device is None:
            self.skipTest("No disk devices found")
        return device

    @unittest.skipIf(not "freebsd" in sys.platform,
            "This test only applies to FreeBSD")
    def test_freebsd(self):
        config = zabbix_smartmontools.parseConfig("test/example/empty")
        device = self.find_device("(da|ada|vtbd|nvme|nvd)[0-9]+$")
        try:
            serial = zabbix_smartmontools.getSerial(config, device)
            cp = subprocess.run(["/usr/sbin/diskinfo", "-s", device],
                    stdout=subprocess.PIPE)
        except PermissionError:
            self.skipTest("Insufficient permissions")
        self.assertEqual(0, cp.returncode)
        self.assertEqual(serial, cp.stdout.decode().strip())

    def test_freebsd_ses(self):
        """ Program shouldn't crash when scanning a ses device """
        config = zabbix_smartmontools.parseConfig("test/example/empty")
        device = self.find_device("(ses)[0-9]+$")
        try:
            serial = zabbix_smartmontools.getSerial(config, device)
        except PermissionError:
            self.skipTest("Insufficient permissions")
        self.assertEqual(serial, None)

    @unittest.skipIf(not sys.platform.startswith("linux"),
            "This test only applies to Linux")
    def test_linux(self):
        config = zabbix_smartmontools.parseConfig("test/example/empty")
        device = self.find_device("(nvme|sda)[0-9]+$")
        try:
            serial = zabbix_smartmontools.getSerial(config, device)
            cp = subprocess.run(["/sbin/udevadm", "info", "--query=all",
                "--name=/dev/%s" % device], stdout=subprocess.PIPE)
        except PermissionError:
            self.skipTest("Insufficient permissions")
        self.assertEqual(0, cp.returncode)
        for line in cp.stdout.decode().splitlines():
            match = re.match("ID_SERIAL_SHORT=(\S+)", line)
            if match:
                self.assertEqual(serial, match.groups()[1])
                break



if __name__ == 'main':
    unittest.main()
