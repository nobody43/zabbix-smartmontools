#! /usr/bin/env python3

import unittest
from unittest.mock import MagicMock, Mock, patch

from parameterized import parameterized

import smartctl_lld

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
        r = smartctl_lld.getAllDisks("myhost", "getverb", ["/dev/da0 -d scsi"])
        # TODO: assertions

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
        r = smartctl_lld.getAllDisks("myhost", "getverb", [
            "/dev/da0 -d scsi",
            "/dev/da1 -d scsi",
        ])
        # TODO: assertions

class TestGetSmart(unittest.TestCase):
    def runtest(self, filename, expected, patchCheckOutput):
        f = open("test/example/%s" % filename)
        output = f.read()
        f.close()
        patchCheckOutput.side_effect = mock_smartctl({'-a /dev/da0 -d auto': output})
        r = smartctl_lld.getSmart("myhost", "getverb", "/dev/da0 -d scsi ")
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

class TestScan(unittest.TestCase):
    def runtest(self, output, expected_disks, patchCheckOutput):
        patchCheckOutput.side_effect = mock_smartctl({'--scan': output})
        (error, disks) = smartctl_lld.scanDisks("getverb")
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
