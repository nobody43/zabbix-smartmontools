from setuptools import setup, find_packages
setup(
    author="",
    name="smartctl-lld",
    description="Disk SMART monitoring for Linux, FreeBSD and Windows. LLD, trapper. ",
    version="1.5.5",
    packages=find_packages(),
    project_urls={
        "Source Code": "https://github.com/nobodysu/zabbix-smartmontools"
    },
    tests_require=['parameterized']
)
