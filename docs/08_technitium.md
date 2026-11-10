# Technitium DNS

## Description

Technitium is an easy to use, yet feature rich DNS and DHCP server. We will use it to assign nice hostnames to our servers and to hand out DHCP IP addresses to servers.

## Setup

Use Docker to create the Technitium container.

Install the Technitium Ansible collection. Copy `ansible/group_vars/technitium.yml.example` to `technitium.yml` and set `technitium_new_password`. On a fresh install the admin password is still `admin`.

```
ansible-galaxy collection install -r ansible/technitium/requirements.yml
ansible-playbook ansible/technitium/init.yml
```

The playbook changes the admin password to `technitium_new_password`, writes `technitium_api_token` into `ansible/group_vars/technitium.yml`, then sets the DNS-over-TLS forwarders. Later runs read the token from that file.

Zones and records from `ansible/technitium/defaults.yml` are a separate playbook:

```
ansible-playbook ansible/technitium/zones.yml
```

DHCP is another playbook. It removes the factory `192.168.1.0/24` scope and enables `192.168.70.101`–`192.168.70.200`, with gateway `192.168.70.254` and this DNS server:

```
ansible-playbook ansible/technitium/dhcp.yml
```

The same result, done by hand: log in to [Technitium](http://192.168.70.2:5380). On first login, change the password. The username is admin.

* Settings
    * Proxy & Forwarders
        * Forwarders - Set to 1.1.1.1:853 1.0.0.1:853 (2 lines)
        * Forwarder protocol - DNS-over-TLS
        * These settings make Technitium use encrypted DNS requests  to Cloudflare.

* Zones
    * We create our primary zone shadowlab.lan
        * Click Add Zone
        * Zone: shadowlab.lan
        * Type: Primary Zone
        * Zone Serial: Enabled (just my preference)
    * We add records for our hosts:
        * Click Add Record
        * Name: pve
        * IPv4 Address: 192.168.70.1
        * Add reverse record: Enabled
        * Create reverse zone: Enabled (for the first host only)
    * Add A (Address) records for:
        * router.shadowlab.lan 192.168.70.254
        * mgt.shadowlab.lan 192.168.70.2
        * proxy.shadowlab.lan 192.168.70.3
    * Add CNAME (Alias) record for homepage:
        * Name: homepage
        * Type: CNAME
        * Domain name: mgt.shadowlab.lan
