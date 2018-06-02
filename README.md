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
![Triggers-Discovery](https://raw.githubusercontent.com/nobodysu/zabbix-smartmontools/master/screenshots/smartctl_discovery_triggers_cut.png)

![Triggers](https://raw.githubusercontent.com/nobodysu/zabbix-smartmontools/master/screenshots/smartctl_triggers_cut.png)

## Installation
As prerequisites you need `python3`, `smartmontools`, `sudo` and `zabbix-sender` packages. For testing, `zabbix-get` is also required.
<br />
Take a look at scripts first lines and provide paths if needed. If you have a RAID configuration, also provide that by hand. Choose `device` or `serial` mode. Import `Template_App_smartmontools.xml` in zabbix web interface.

### First step
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
Install `python3` for all users, adding it to `PATH` during installation. Install `smartmontools` and add its bin folder to `PATH` in environment variables (or specify absolute path to `smartctl` binary in `smartctl-lld.py`).
<br />
Note: currently windows version does not detaches and data can only be gathered on second run.

### Second step
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

Note: before scripts would work, zabbix server must first discover available items. It is done in 12 hour cycles by default. You can temporary decrease this parameter for testing in `template -> Discovery -> SMART disk discovery -> Update interval`. In this case update value must not be less than 80 seconds.

These scripts were tested to work with following configurations:
- Centos 7 / Zabbix 2.4 / Python 3.4
- Debian 8 / ZS (2.4, 3.4) / ZA (2.4, 3.0, 3.2, 3.4) / Python 3.4
- Ubuntu 17.10 / Zabbix 3.0 / Python 3.6
- FreeBSD 10.4 / Zabbix 2.4 / Python 3.6
- Windows XP / Zabbix 2.4 / Python 3.4
- Windows 7 / ZS (2.4, 3.4) / ZA (2.4, 3.0, 3.2, 3.4) / Python (3.2, 3.4)
- Windows Server 2012 / Zabbix 2.4 / Python 3.4

## Updating
Replace all old files with new ones and reupload the template. Old LLD items clearing may be required with 'Unlink and clear' on the hosts.

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
