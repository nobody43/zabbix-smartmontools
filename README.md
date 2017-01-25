# zabbix-smartmontools
## Features
Cross-platform SMART monitoring scripts with two display modes: [device](https://github.com/nobodysu/zabbix-smartmontools/blob/master/screenshots/smartctl_mode-device-example.png?raw=true) and [serial](https://github.com/nobodysu/zabbix-smartmontools/blob/master/screenshots/smartctl_mode-serial-example.png?raw=true). LLD discovers and sends data in one pass, using minimal number of utilities. Supports any SMART name and displays it as is.

#### Advantages
- Full Low-Level Discovery: there is no need to add any SMART items
- Efficient: no unnecessary processes are spawned
- Bulk items upload with zabbix-sender
- Error-proof configuration: you'll know when host is not configured

#### Disadvantages
- Requires configuration
- Manual RAID passthrough
- Semi-hardcoded triggers (still for all disks though)

![Triggers-Discovery](https://raw.githubusercontent.com/nobodysu/zabbix-smartmontools/master/screenshots/smartctl_discovery_triggers_cut.png)

![Triggers](https://raw.githubusercontent.com/nobodysu/zabbix-smartmontools/master/screenshots/smartctl_triggers_cut.png)

## Installation
As prerequisites you need `python3`, `smartmontools`, `sudo` and `zabbix-sender` packages. For testing, `zabbix-get` is also required.
<br />
Take a look at scripts first lines and provide paths if needed. If you have a RAID configuration, also provide that by hand. Choose `device` or `serial` mode. Import `Template_App_smartmontools.xml` in zabbix web interface.

### First step
#### Linux
```bash
mv smartctl-lld.py smartctl-send.py /etc/zabbix/scripts/
mv sudoers.d/zabbix /etc/sudoers.d/   # place sudoers include here for smartctl-lld.py sudo access
mv userparameter_smartctl.conf /etc/zabbix/zabbix_agentd.d/   # move zabbix items include here
```

#### FreeBSD
```bash
mv smartctl-lld.py smartctl-send.py /usr/local/etc/zabbix/scripts/
mv sudoers.d/zabbix /usr/local/etc/sudoers.d/
mv userparameter_smartctl.conf /usr/local/etc/zabbix/zabbix_agentd.d/
```

#### Windows
```cmd
move smartctl-lld.py C:\zabbix-agent\scripts\
move smartctl-send.py C:\zabbix-agent\scripts\
move userparameter_smartctl.conf C:\zabbix-agent\zabbix_agentd.conf.d\
```
Install `python3` for all users, adding it to `PATH` during installation. Install `smartmontools` and add its bin folder to `PATH` in environment variables.
<br />
Note: currently windows version does not detaches and data can only be gathered on second run.

### Second step
Then you need to include your zabbix conf folder in `zabbix_agentd.conf`, like this:
```conf
Include=/usr/local/etc/zabbix/zabbix_agentd.conf.d/
```
Also its recomended to add at least `Timeout=5` to config file to allow drives spun up in rare cases.

Thats all for Windows. For others run the following to finish configuration:
```bash
chmod 750 scripts/smartctl-*.py   # apply necessary permissions
chown root:zabbix scripts/smartctl-*.py
chmod 640 userparameter_smartctl.conf
chown root:zabbix userparameter_smartctl.conf
chmod 400 sudoers.d/zabbix
chown root sudoers.d/zabbix
visudo   # test sudoers configuration
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

Note: before scripts would work, zabbix server must first discover available items. It is done in 12 hour cycles by default. You can temporary decrease this parameter for testing in `template -> Discovery -> SMART disk discovery -> Update interval`.

These scripts were tested to work with following configurations:
- Centos 7 / Zabbix 2.4 / Python 3.4
- Debian 8 / Zabbix 2.4 / Python 3.4
- FreeBSD 10.1 / Zabbix 2.4 / Python 3.4
- Windows XP / Zabbix 2.4 / Python 3.4
- Windows 7 / Zabbix 2.4 / Python 3.4
- Windows Server 2012 / Zabbix 2.4 / Python 3.4

## Updating
### 1.3:<br />
Replace all old files with new ones and reupload the template.

## Issues
- Zabbix web panel displays an error on json discovery, but apparently everything works fine
- Windows version does not detaches currently, and data will only be gathered on second pass

## Planned features
- Disk SMART capability auto-enabling

## Links
- https://www.smartmontools.org
- https://unlicense.org
- [The 5 SMART stats that actually predict hard drive failure](http://www.computerworld.com/article/2846009/the-5-smart-stats-that-actually-predict-hard-drive-failure.html)
- [Disk and CPU temperature monitoring solution](https://github.com/nobodysu/zabbix-mini-IPMI)
