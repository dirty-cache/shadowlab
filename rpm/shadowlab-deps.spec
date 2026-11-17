Name:      shadowlab-deps
Summary:   Shadowlab dependencies
Version:   0.1
Release:   %{date}
License:   Private
Group:     System Environment/Base

%global debug_package %{nil}

%description
Meta package for Shadowlab dependencies

Requires: atop autofs bash-completion bind-utils bzip2 dnf-automatic dstat epel-release git htop
Requires: iftop iotop lsof net-tools nfs-utils nmap parted pciutils pv qemu-guest-agent rsync
Requires: screen sqlite sssd sssd-ldap sudo sysstat tar unzip vim wget xfsprogs

%files
