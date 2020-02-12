import os
import sys

from setuptools import setup, find_packages

if 'bsd' in sys.platform:
    examplesdir = "/usr/local/share/examples/zabbix-smartmontools"
    sudoersfile = "Unix/sudoers.d/zabbix"
elif sys.platform.startswith("linux"):
    examplesdir = "/usr/local/share/doc/zabbix-smartmontools/examples"
    sudoersfile = "Unix/sudoers.d/zabbix"
else:
    raise NotImplementedError

setup(
    author="",
    name="zabbix-smartmontools",
    data_files=[
        (examplesdir, ['zabbix-smartmontools.conf']),
        (os.path.join(examplesdir, "sudoers.d"), [sudoersfile])
    ],
    description="Disk SMART monitoring for Linux, FreeBSD and Windows. LLD, trapper. ",
    entry_points = {
        'console_scripts':
            ['zabbix-smartctl = zabbix_smartmontools:main']
    },
    packages=find_packages(),
    project_urls={
        "Source Code": "https://github.com/nobodysu/zabbix-smartmontools"
    },
    tests_require=['parameterized'],
    version="1.5.5",
)
