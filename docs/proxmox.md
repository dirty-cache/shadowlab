# Setting up Proxmox

## Description

We will install the Proxmox hypervisor on a bare metal machine to run all of our services.

## Requirements

* See [Proxmox requirements](https://www.proxmox.com/en/products/proxmox-virtual-environment/requirements)
* An x86 host with 16GiB RAM and Intel VT or AMD-V
* An empty USB stick
* Internal disk with 512GiB capacity
* Ethernet connected to an isolated network
* Second Ethernet connected to a WAN (Internet uplink). This can also be a VLAN on the primary interface (if the server only has 1 NIC)
* A Desktop (VM or physical) on the same isolated network, configured with a static IP address - to bootstrap installation. This desktop can be removed later.

## Preparation

* Download the [Proxmox 9.2 Installer ISO](https://enterprise.proxmox.com/iso/proxmox-ve_9.2-1.iso)
* Create a bootable installer USB (On Linux Mint, use USB Image Writer)