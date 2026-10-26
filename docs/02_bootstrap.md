# bootstrap desktop

## Description

We need a desktop for initial setup of the Proxmox host and virtual machines. We have no functional network yet, so we configure the network manually.

## Configuration

* Windows or Linux desktop
* Network connection to the private LAN

## Network

* Setup a static IP address outside of the reserved range:
    * IP 192.168.70.99/24
    * Gateway 192.168.70.254
    * DNS 192.168.70.254
    * This IP does not exist yet but we set it in advance.

