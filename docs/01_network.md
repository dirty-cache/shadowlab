# Network Settings

## Description

Overview of the Shadow Lab Network settings

In our lab we assume the private LAN is 192.168.70.0/24. The domain is shadowlab.lan

See the [network diagram](diagram.md) for how these systems connect.

## IP Addresses

| System         | IP Address         | FQDN                   | Notes                   | Del |
|---             |---                 |---                     |---                      |---  |
| DNS & Homepage | 192.168.70.1       | dns.shadowlab.lan      | Future reserved         | |
| Proxy          | 192.168.70.2       | proxy.shadowlab.lan    | Alternate NIC on Docker | |
| Proxmox  	     | 192.168.70.11      | pve.shadowlab.lan      | Proxmox host            | |
| Docker         | 192.168.70.12      | docker01.shadowlab.lan | Management VM (Rocky Linux, Docker) | |
| Router         | 192.168.70.254     | router.shadowlab.lan   | OPNSense router         | |
| DHCP           | 192.168.70.101-200 | N/A                    | Dynamic IP              | |

## Docker Ports

| Port  	     | Application       | Notes | 
|---             |---                |--- |
| 80             | NPM HTTP          | Proxy |
| 81             | NPM Admin         | |
| 222            | Forgejo (ssh)     | |
| 389            | Authentik (ldap)  | |
| 443            | NPM HTTPS         | Proxy |
| 636            | Authentik (ldaps) | |
| 3001           | Dockhand          | |
| 3002           | Homepage          | |
| 3003           | Forgejo           | |
| 3004           | LiteLLM           | |
| 3005           | Authentik         | |
| 3006           | Headscale         | |
| 3007           | Headplane         | |
| 5432           | Postgres          | |
| 5380           | Technitium        | HTTP |
| 53443          | Technitium        | HTTPS |
