# Setting up HTTP Proxy

## Description

On our lab, we want nice URLs instead of ip addresses and port numbers. We will use HAProxy on the OPNSense router to achieve this.

## VM Setup

For the proxy to work best, it needs a separate network interface. In proxmox, add an extra interface: Add - Network device. Default settings should work fine.

## OPNSense setup

* Login to opnsense (router)

* Settings - Administration
    * Listen Interfaces: set to LAN (this prevents port conflicts)

* Interfaces
    * Assignments - Add the new interface (opt1)
    * Select the correct device (probably vtnet2)
    * IPv4 config type: Static IPv4
    * IPv4 address: 192.168.70.3/24
    * IPv6: None

* Firewall - Aliases - Add
    * Name: Proxy_Ports
    * Content: 80 and 443 (enter 80, enter, enter 443, enter)

* Firewall - Rules - Add
    * Description: Proxy Traffic
    * Interface (rule): PXY
    * Protocol: TCP/UDP
    * Destination Port: Proxy_ports

* Install haproxy
    * System - Firmware
    * On Plugins, install os-haproxy from community plugins

* Services - HAProxy
    * Virtual Services - Public Services - Add a service:
        * Name: Web
        * Listen addresses: 192.168.70.3:80

    * Real servers: Add an entry for Homepage
        * Name: homepage
        * FQDN: mgt.shadowlab.lan
        * Port: 3001

    * Virtual services - Backend pools: Add an entry for homepage
        * Name: homepage
        * Servers: homepage (select from options)

    * Rules & Checks - Conditions: Add a condition
        * Name: homepage
        * Condition type: hdr (HTTP Host Header matches)
        * Host string: homepage.shadowlab.lan
    
    * Rules & Checks - Rules: Add a rule
        * Name: homepage
        * Select conditions: Select homepage
        * Type: Use specified backend pool
        * Use backend pool: homepage
    
    * Virtual Services - Public Services - Edit Web
        * Select Rules: add homepage
    * Settings - Service
        * Enable haproxy
        * Apply

