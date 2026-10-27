# Network Settings

## Description

Overview of the Shadow Lab Network settings

In our lab we assume the private LAN is 192.168.70.0/24. The domain is shadowlab.lan

## IP Addresses

| System  	 | IP Address      | FQDN              | Notes | Del |
|---         |---              |---                |---    |---  |
| Proxmox  	 | 192.168.70.1    | pve.shadowlab.lan    | Proxmox host | |
| Router     | 192.168.70.254  | router.shadowlab.lan | OPNSense router | |
| Management | 192.168.70.2    | mgt.shadowlab.lan    | Management VM (Rocky Linux, Docker) | |
| Proxy      | 192.168.70.3    | proxy.shadowlab.lan  | Alternate NIC on OPNSense | |

