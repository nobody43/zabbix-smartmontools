import os
import sys

from setuptools import setup, find_packages

if 'bsd' in sys.platform:
    examplesdir = "/usr/local/share/examples/smartctl-lld"
    sudoersdir = "/usr/local/etc/sudoers.d"
    sudoersfile = "Unix/sudoers.d/zabbix"
elif sys.platform.startswith("linux"):
    examplesdir = "/usr/local/share/doc/smartctl-lld/examples"
    sudoersdir = "/etc/sudoers.d"
    sudoersfile = "Unix/sudoers.d/zabbix"
else:
    raise NotImplementedError

setup(
    author="",
    name="smartctl-lld",
    data_files=[
        (examplesdir, ['zabbix-smartmontools.conf']),
        (os.path.join(examplesdir, "sudoers.d"), [sudoersfile])
    ],
    description="Disk SMART monitoring for Linux, FreeBSD and Windows. LLD, trapper. ",
    entry_points = {
        'console_scripts':
            ['zabbix-smartctl = smartctl_lld:main']
    },
    packages=find_packages(),
    project_urls={
        "Source Code": "https://github.com/nobodysu/zabbix-smartmontools"
    },
    tests_require=['parameterized'],
    version="1.5.5",
)
