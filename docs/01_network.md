# Network Settings

## Description

Overview of the Shadow Lab Network settings

In our lab we assume the private LAN is 192.168.70.0/24. The domain is shadowlab.lan

See the [network diagram](diagram.md) for how these systems connect.

## IP Addresses

| System  	     | IP Address      | FQDN                   | Notes        | Del |
|---             |---              |---                     |---           |---  |
| DNS & Homepage | 192.168.70.1    | dns.shadowlab.lan      | Future reserved | |
| Proxy          | 192.168.70.2    | proxy.shadowlab.lan    | Alternate NIC on Docker | |
| Proxmox  	     | 192.168.70.11   | pve.shadowlab.lan      | Proxmox host | |
| Docker         | 192.168.70.12   | docker01.shadowlab.lan | Management VM (Rocky Linux, Docker) | |
| Router         | 192.168.70.254  | router.shadowlab.lan   | OPNSense router | |


