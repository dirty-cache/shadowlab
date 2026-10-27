# Setting up OPNSense

## Description

We are going to run a virtual [OPNSense](https://opnsense.org/) router within Proxmox. The router will handle traffic from the local network to the internet, as well as Tailscale (VPN) traffic from outside.

We can also block or limit outgoing traffic, and use it as a web proxy.

## Requirements

* Proxmox server up and running
* Proxmox connected to both local LAN and WAN (i.e. via VLAN or separate Ethernet interface)
* Tailscale or Headscale network pre-configured

We assume the local LAN is 192.168.70.0/24 and the WAN is 192.168.60.0/24

The local router IP will be 192.168.70.254

## Proxmox
* Download [OPNSense disk image 26.7](https://pkg.opnsense.org/releases/26.7/OPNsense-26.7-dvd-amd64.iso.bz2)
* Extract the image (Name should be ending with .iso)
    * The script download-images will do this for you and put the ISO image in ./iso
* Upload the image to Proxmox
    * In Proxmox select storage local, then select ISO Images
    * Click Upload and upload the file

* Create a new VM, settings:
    * General: Name=router, Start at boot=Enabled (Enable Advanced to see this option)
    * OS: Select the OPNSense ISO image
    * System: machine=q35, Qemu agent: enabled
    * Disks: Create an 8GiB disk
    * CPU: 1 socket, 2 cores, Type=host
    * Memory: 4 GiB (4096 MiB) (after install we may set it back to 1GiB)
    * Network: defaults

* After creation:
    * Add an extra network interface for the WAN. Set VLAN Tag if needed

* First boot
    * Open the console for the VM and start it, wait for the login
    * Login as installer, password opnsense
    * Keymap: default (unless you have a non-USA keyboard)
    * **Important!!** Use Install (UFS) (The default ZFS is not needed and requires more memory)
    * Select disk: Choose the 8GiB disk (our target). This may be the first or second option
    * Wait for the installer to copy files (may take a few minutes, and sometimes it seems to hang. Just be patient)
    * When done, select Complete Install
    * Select Halt Now

* Initial setup
    * Hardware - CD/DVD Drive: Set to Don't use any media
    * In Proxmox, detach the installer disk from the VM (smallest, 2.5GiB disk)
    * Optional - Set memory to 1GiB (4GiB is only needed for the installer)
    * Boot the system
    * On the console, login as root, password opnsense
    * Select 2: Set interface IP address
    * Select 1: LAN
    * Configure via DHCP: N
    * Enter the LAN IP address: 192.168.70.254
    * Enter the subnet mask: 24
    * Upstream gateway: None (just press Enter)
    * Configure IPv6 via WAN tracking: N
    * Configure IPv6 via DHCP6: N
    * IPv6 LAN address: None (press Enter)
    * Enable DHCP server: N (default)
    * Change GUI protocol: N (default)
    * Generate new certificate: N (default)
    * Restore GUI access defaults: N (default)

* First login
    * OPNsense should now be reachable on the browser (from within the LAN). The URL is given on the console, and shows http://192.168.70.254. Ignore certificate warnings.
    * Login as root, password opnsense. A wizard will start.
    * General Information
        * Hostname: router
        * Domain: shadowlab.lan
        * Timezone: Select your preferred timezone
        * DNS Servers: Select 1.1.1.1
        * Override DNS: Disable
    * Network [WAN]
        * Type: Leave it at DHCP or if the WAN network does not provide DHCP, set Type to Static and enter IP address/netmask (i.e. 192.168.60.254/24) and gateway IP (to whatever it is on the WAN)
        * Block RFC1918: Enable
        * Block Bogon: Enable
    * Network [LAN]
        * Disable LAN: Disabled
        * IP Address: 192.168.70.254/24 (prefilled)
        * Configure DHCP Server: Disable
    * Deployment type
        * Optimize for multi-WAN: Disable
        * Automatic DHCP/DNS registration: Enable
    * Initial password
        * Set a new password
    * Click Apply, then Continue to the dashboard

* Further setup
    * System - Firmware
        * Select Status, click Check for updates
        * If WAN connectivity works, you get a long list of updates. Scroll to the bottom and click Update
    * After reboot, login again
    * Go back to Firmware, and select Plugins
    * Click to view the community Plugins
    * Install os-qemu-guest-agent, os-tailscale and os-haproxy

* Setting up Tailscale
    * Generate a pre-authentication key on Tailscale or Headscale
    * Go to VPN - Tailscale and select Settings
    * Set Enabled, click Apply
    * Go to Tailscale - Authentication
    * Enable Advanced Mode (to view the pre-auth field)
    * For Headscale, enter the Headscale URL
    * Enter the pre-auth key and click Apply
    * Tailscale - Status: Should show a Tailscale IP and no errors
    * Go to Tailscale - Settings
    * Accept DNS: Disable, Advertise Exit Node: Enable, click Apply
    * Go to Advertised Routes
    * Add a subnet for the local network: 192.168.70.0/24
    * In the Tailscale or Headscale admin page, the router shows up as Exit Node and has subnets.
    * Click on the 3 dots for the node and choose Edit Route Settings
    * Enable the subnet and set Use as exit node

## Blocking

If our upstream WAN is part of a network that we shoud not have access to (i.e., corporate network), we can block access such that only outgoing connections to the internet are allowed. This is optional but some customers may require it.

For this, we are going to set up a rule that blocks all outgoing non-internet traffic. This means all private IP addresses as defined in RFC1918 [Wiki](https://en.wikipedia.org/wiki/Private_network).

However, we need to allow traffic on our local network. So we add an extra rule to only allow our local LAN.

The order of firewall rules is important, and OPNSense processes them top to bottom. So the Allow LAN rule should be the first, followed by the Block private rule. We are going to create the rules first, then place them in the right order.

* Firewall - Aliases
    * Create a new alias
    * Name: RFC1918_Nets
    * Type: Network(s)
    * Content: 192.168.0.0/16, 10.0.0.0/8, 172.16.0.0/12 (one per line)

* Firewall - Rules
    * Create a new rule
    * Description: Block private networks
    * Interface (rule): LAN
    * Action: Reject
    * Destination: RFC1918_Nets

    * Create a new rule
    * Description: Allow LAN
    * Interface (rule): LAN
    * Action: Pass
    * Destination: LAN Network

* Firewall - Rules
    * Checkmark the Allow LAN rule
    * On the first rule, click the left arrow. The Allow LAN should now be on top.
    * Checkmark the Block Private rule
    * On the rule (2nd line), click the left arrow
    * Click Apply

The order now should be:
1. Allow LAN
2. Block Private
3. & 4: Default allow LAN to any (regular and IPv6).

