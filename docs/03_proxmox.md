# Setting up Proxmox

## Description

We will install the Proxmox hypervisor on a bare metal machine to run all of our services.

## Requirements

* See [Proxmox requirements](https://www.proxmox.com/en/products/proxmox-virtual-environment/requirements)
* An x86 host with 16GiB RAM and Intel VT or AMD-V
* Screen/Keyboard attached to the host (only for initial install)
* An empty USB stick
* Internal disk with 512GiB capacity
* Ethernet connected to an isolated network
* Second Ethernet connected to a WAN (Internet uplink). This can also be a VLAN on the primary interface (if the server only has 1 NIC)
* A Desktop (VM or physical) on the same isolated network, configured with a static IP address - to bootstrap installation. This desktop can be removed later.

## Preparation

* Download the [Proxmox 9.2 Installer ISO](https://enterprise.proxmox.com/iso/proxmox-ve_9.2-1.iso)
* Create a bootable installer USB (On Linux Mint, use USB Image Writer)

## Installation
* Insert the USB stick in the server and boot from it
* The welcome screen should appear
* Select Install Proxmox VE (Graphical)
* Follow the install wizard
* Settings
    * Country: Select your preferred country/region
    * Password and email: Set password, change email to mail@example.local
    * Network: Select correct nic. Hostname=pve.shadowlab.lan, IP=192.168.70.1/24, gateway=192.168.70.254, dns=192.168.70.254
* Install and wait for the reboot
* The console login should show, with the login url (https://192.168.70.1:8006/)

## First login

* Open the browser and go to the [Proxmox URL](https://192.168.70.1:8006). Ignore certificate warnings.
* Login as root with your given password

## Setup

* Updates
    * In the Server view, select the server (pve) and go to Updates - Repositories
    * Disable the pve-enterprise repo (click on the line and click Disable)
    * Also disable the ceph-squid repo
    * Add an extra repository. Select from the list: No Subscription
    * You cannot update the system yet as the router is not configured. Skip for now.

* Uploading ISO and disk images
    * Expand Datacenter - pve and select local (pve)
    * Click ISO Images - Upload
    * Upload the Rocky 9.8 minimal ISO image
    * Click Import - Upload
    * Upload the OPNSense image (.raw extension)

Further steps: Install and configure OPNSense

After OPNSense setup is complete:

* Updates
    * Click Refresh. A list of updates should appear
    * Click Upgrade. A shell window opens. Hit enter in the window to continue updates.
    * When complete, reboot the server (Select pve, click Reboot button)