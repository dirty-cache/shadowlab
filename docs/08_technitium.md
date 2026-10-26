# Technitium DNS

## Description

Technitium is an easy to use, yet feature rich DNS and DHCP server. We will use it to assign nice hostnames to our servers and to hand out DHCP IP addresses to servers.

## Setup

Use Docker to create the Technitium container. Log in to [Technitium](http://192.168.70.2:5380).


On first login, change the password. The username is Admin.

* Settings
    * Proxy & Forwarders
        * Forwarders - Set to 1.1.1.1:853 1.0.0.1:853 (2 lines)
        * Forwarder protocol - DNS-over-TLS
        * These settings make Technitium use encrypted DNS requests  to Cloudflare.

* Zones
    * We create our primary zone fdelab.lan
        * Click Add Zone
        * Zone: fdelab.lan
        * Type: Primary Zone
        * Zone Serial: Enabled (just my preference)
    * We add records for our hosts:
        * Click Add Record
        * Name: pve
        * IPv4 Address: 192.168.70.1
        * Add reverse record: Enabled
        * Create reverse zone: Enabled (for the first host only)
    * Add A (Address) records for:
        * router.fdelab.lan 192.168.70.254
        * mgt.fdelab.lan 192.168.70.2
        * proxy.fdelab.lan 192.168.70.3
    * Add CNAME (Alias) record for homepage:
        * Name: homepage
        * Type: CNAME
        * Domain name: mgt.fdelab.lan
