# bootstrap desktop

## Description

We need a desktop for initial setup of the Proxmox host and virtual machines via a web browser. We have no functional network yet, so we configure the network manually. The Proxmox host cannot be reached from outside the network, so our desktop needs to be connected on the isolated LAN.

## Configuration

* Windows or Linux desktop/laptop (VM, or physical)
* Network connection to the private LAN

## Network

* Setup a static IP address outside of the reserved range:
    * IP 192.168.70.99/24
    * Gateway 192.168.70.254
    * DNS 192.168.70.254 (This IP does not exist yet but we set it in advance)
