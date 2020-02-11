#! /usr/bin/env python3

import unittest
from unittest.mock import MagicMock, Mock, patch

from parameterized import parameterized

import zabbix_smartmontools

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

class TestGetAllDisks(unittest.TestCase):
    @patch('subprocess.check_output')
    def test_onedisk(self, patchCheckOutput):
        f = open("test/example/%s" % "ST4000NM0023.txt")
        da0_output = f.read()
        f.close()
        patchCheckOutput.side_effect = mock_smartctl({'-a /dev/da0 -d auto': da0_output})
        config = zabbix_smartmontools.parseConfig("test/example/empty")
        r = zabbix_smartmontools.getAllDisks(config, "myhost", "getverb", ["/dev/da0 -d scsi"])
        self.assertEqual(r,
            ([{'{#DDRIVESTATUS}': 'da0'}, {'{#DISKID}': 'da0'}, {'{#DISKIDSAS}': 'da0'}],
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
        r = zabbix_smartmontools.getAllDisks(config, "myhost", "getverb", [
            "/dev/da0 -d scsi",
            "/dev/da1 -d scsi",
        ])
        self.assertEqual(r,
            ([{'{#DDRIVESTATUS}': 'da0'},
              {'{#DISKID}': 'da0'},
              {'{#DISKIDSAS}': 'da0'},
              {'{#DDRIVESTATUS}': 'da1'}],
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
        r = zabbix_smartmontools.getAllDisks(config, "myhost", "getverb", ["/dev/da0 -d scsi"])
        self.assertEqual(r,
            ([{'{#DDRIVESTATUS}': 'Z1Z3SGMD00009437061J'},
              {'{#DISKID}': 'Z1Z3SGMD00009437061J'},
              {'{#DISKIDSAS}': 'Z1Z3SGMD00009437061J'}],
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
              'myhost smartctl.value[Z1Z3SGMD00009437061J,nonMediumErrors] "181"']))


class TestGetSmart(unittest.TestCase):
    def runtest(self, filename, expected, patchCheckOutput):
        f = open("test/example/%s" % filename)
        output = f.read()
        f.close()
        patchCheckOutput.side_effect = mock_smartctl({'-a /dev/da0 -d auto': output})
        config = zabbix_smartmontools.parseConfig("test/example/empty")
        r = zabbix_smartmontools.getSmart(config, "myhost", "getverb", "/dev/da0 -d scsi ")
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
             ('da0', 'da0'))
        )
    ])
    @patch('subprocess.check_output')
    def test_freebsd(self, filename, expected, patchCheckOutput):
        self.runtest(filename, expected, patchCheckOutput)

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
            "/dev/sda -d sat+megaraid,4",
            "/dev/da0 -d scsi"
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
        ("/dev/da0 -d scsi # /dev/da0, SCSI device\n", ["/dev/da0 -d scsi "]),
        # Two scsi disks
        ("/dev/da0 -d scsi # /dev/da0, SCSI device\n/dev/da1 -d scsi # /dev/da1, SCSI device\n",
            ["/dev/da0 -d scsi ", "/dev/da1 -d scsi "]),
        # TODO: ATA disks and NVME disks
    ])
    @patch('subprocess.check_output')
    def test_freebsd(self, smartctl_output, expected_disks, patchCheckOutput):
        self.runtest(smartctl_output, expected_disks, patchCheckOutput)

if __name__ == 'main':
    unittest.main()
