# zabbix-smartmontools
## Features
Cross-platform SMART monitoring scripts with two display modes: [device](https://github.com/nobodysu/zabbix-smartmontools/blob/master/screenshots/smartctl_mode-device-example.png?raw=true) and [serial](https://github.com/nobodysu/zabbix-smartmontools/blob/master/screenshots/smartctl_mode-serial-example.png?raw=true). LLD discovers and sends data in one pass, using minimal number of utilities. Supports any SMART name and displays it as is.

- Utilises smartctl error return codes
- Low-Level Discovery
- SAS support
- SSD wear monitoring (SAS only)
- csmi support
- Efficient: no unnecessary processes are spawned
- Bulk items upload with zabbix-sender
- Error-proof configuration: various safeguard triggers
- Automatic RAID passthrough (when smartctl detects the drives)

## Triggers
![Triggers-Discovery2](https://raw.githubusercontent.com/nobodysu/zabbix-smartmontools/master/screenshots/smartctl_discovery_triggers2.png)

[More disk triggers](https://raw.githubusercontent.com/nobodysu/zabbix-smartmontools/master/screenshots/smartctl_discovery_triggers1.png)<br>

[Disk items](https://raw.githubusercontent.com/nobodysu/zabbix-smartmontools/master/screenshots/smartctl_discovery_items.png)<br>

[Template triggers](https://raw.githubusercontent.com/nobodysu/zabbix-smartmontools/master/screenshots/smartctl_triggers.png)

Triggers that contain `delta(5d)>0` and `last()>0` will fire on any change unless last value is zero. E.g. when disk is replaced with zero values the trigger will not fire, but if value is less or more - it will. Therefore, replacing a faulty drive with faulty one will still trigger a problem that stays for 5 days (default).

Note: disk temperature is monitored using [different approach](https://github.com/nobodysu/zabbix-mini-IPMI).

## Installation
As prerequisites you need `python3`, `smartmontools`, `sudo` and `zabbix-sender` packages. For testing, `zabbix-get` is also required.
<br />
Take a look at scripts first lines and provide paths if needed. If you have a RAID configuration, also provide that by hand. Choose `device` or `serial` mode. Import `Template_App_smartmontools.xml` in zabbix web interface.

### Prerequisites
[Repository installation](https://www.zabbix.com/documentation/3.0/manual/installation/install_from_packages/repository_installation)
#### Debian
```bash
apt-get install zabbix-agent zabbix-sender smartmontools sudo
apt-get install zabbix-get   # testing
```
#### Centos
```bash
yum install zabbix-agent zabbix-sender smartmontools sudo
yum install zabbix-get   # testing
```

### Placing the files
Note: `sender_wrapper.py` is shared among multiple projects and have the same contents - it can be overwritten.
#### Linux
```bash
mv smartctl-lld.py sender_wrapper.py /etc/zabbix/scripts/
mv sudoers.d/zabbix /etc/sudoers.d/   # place sudoers include here for smartctl-lld.py sudo access
mv userparameter_smartctl.conf /etc/zabbix/zabbix_agentd.d/   # move zabbix items include here
```

#### FreeBSD
```bash
mv smartctl-lld.py sender_wrapper.py /usr/local/etc/zabbix/scripts/
mv sudoers.d/zabbix /usr/local/etc/sudoers.d/
mv userparameter_smartctl.conf /usr/local/etc/zabbix/zabbix_agentd.d/
```

#### Windows
```cmd
move smartctl-lld.py C:\zabbix-agent\scripts\
move sender_wrapper.py C:\zabbix-agent\scripts\
move userparameter_smartctl.conf C:\zabbix-agent\zabbix_agentd.conf.d\
```
Install `python3` for [all users](https://github.com/nobodysu/zabbix-smartmontools/blob/master/screenshots/windows_python_installation1.png), [adding it](https://github.com/nobodysu/zabbix-smartmontools/blob/master/screenshots/windows_python_installation2.png) to `PATH` during installation. Install `smartmontools` and add its bin folder to `PATH` in [environment variables](https://raw.githubusercontent.com/nobodysu/zabbix-smartmontools/master/screenshots/windows_environment_variables.png) (or specify absolute path to `smartctl` binary in `smartctl-lld.py`).
<br />
Note: currently windows version does not detaches and data can only be gathered on second run.

### Finalizing
Then you need to include your zabbix conf folder in `zabbix_agentd.conf`, like this:
```conf
Include=/usr/local/etc/zabbix/zabbix_agentd.conf.d/
```
Also its recomended to add at least `Timeout=10` to config file to allow drives spun up in rare cases.

Thats all for Windows. For others run the following to finish configuration:
```bash
chmod 755 smartctl-lld.py sender_wrapper.py   # apply necessary permissions
chown root:zabbix smartctl-lld.py sender_wrapper.py
chmod 644 userparameter_smartctl.conf
chown root:zabbix userparameter_smartctl.conf
chmod 400 sudoers.d/zabbix
chown root sudoers.d/zabbix
visudo   # test sudoers configuration, type :q! to exit
```

## Testing
```bash
zabbix_get -s 192.0.2.1 -k smartctl.discovery[get,"Example host"]
```
Default operation mode. Displays json that server should get, detaches, then waits and sends data with zabbix-sender. `Example host` is your `Host name` field in zabbix.
<br /><br />

```bash
zabbix_get -s 192.0.2.1 -k smartctl.discovery[getverb,"Example host"]
```
Verbose mode. Does not detaches or prints LLD. Lists all items sent to zabbix-sender, also it is possible to see sender output in this mode.
<br /><br />

Note: before scripts would work, zabbix server must first discover available items. It is done in 12 hour cycles by default. You can temporary decrease this parameter for testing in `template -> Discovery -> SMART disk discovery -> Update interval`. In this monitoring solution update interval must not be less than 80 seconds.

These scripts were tested to work with following configurations:
- Centos 7 / Zabbix 2.4 / Python 3.4
- Debian 8 / ZS (2.4, 3.4) / ZA (2.4, 3.0, 3.2, 3.4) / Python 3.4
- Ubuntu 17.10 / Zabbix 3.0 / Python 3.6
- FreeBSD 10.4 / Zabbix 2.4 / Python 3.6
- Windows XP / Zabbix 2.4 / Python 3.4
- Windows 7 / ZS (2.4, 3.4) / ZA (2.4, 3.0, 3.2, 3.4) / Python (3.1, 3.2, 3.4)
- Windows Server 2012 / Zabbix 2.4 / Python 3.4

## Updating
If template had changed from previous version - update it first in zabbix web interface. Otherwise just overwrite old scripts and UserParameters with new ones.

## FAQ
Q: Trigger fires when it clearly shouldn't.<br>
Q: Trigger's macro does not expand.<br>
A: Reassign the template with `Unlink and clear` on the host.

Q: Is it possible to monitor specific drives or exclude some of them?<br>
Q: SCSI drive returns empty results while `-A` option working correctly.<br>
A: Specify `diskListManual` in `smartctl-lld.py`:
```python
diskListManual = ['/dev/sda -d sat+megaraid,4', '/dev/sda -d sat+megaraid,5']
diskListManual = ['/dev/csmi0,0 -d scsi', '/dev/csmi0,1 -d scsi']
```

Q: Old triggers are misleading after disk replacement.<br>
A: Wait for 24 hours (default) or perform `Unlink and clear` on the host. You can also adjust the interval at `template -> Discovery -> SMART disk discovery -> Keep lost resources period`.

Q: Script exits with exception/error.<br>
A: [Report](https://github.com/nobodysu/zabbix-smartmontools/issues) it.

## Issues
- Zabbix web panel displays an error on json discovery, but everything works fine
- Windows version does not detaches, and data will only be gathered on second pass (probably permanent workaround)

## Planned features
- SSD life monitoring (SATA)
- ERC / TLER / CCTL is-enabled check

## Links
- https://www.smartmontools.org
- https://unlicense.org
- [The 5 SMART stats that actually predict hard drive failure](https://www.computerworld.com/article/2846009/the-5-smart-stats-that-actually-predict-hard-drive-failure.html)
- [What SMART Stats Tell Us About Hard Drives](https://www.backblaze.com/blog/what-smart-stats-indicate-hard-drive-failures/)
- [SMART attributes detailed explanation](https://en.wikipedia.org/wiki/S.M.A.R.T.#Known_ATA_S.M.A.R.T._attributes)
- [Оцениваем состояние жёстких дисков при помощи S.M.A.R.T. (Russian)](https://www.ixbt.com/storage/hdd-smart-testing.shtml)
- [Disk and CPU temperature monitoring solution](https://github.com/nobodysu/zabbix-mini-IPMI)
