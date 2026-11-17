Name:      shadowlab
Summary:   Shadowlab Addons
Version:   0.1
Release:   %{date}
License:   Private
Group:     System Environment/Base
Source0:   %{name}-%{version}.tbz2

%global debug_package %{nil}


%description
Some helper scripts and settings for Shadowlab

# cd ~/git/shadowlab
# tar -jcvf ~/rpmbuild/SOURCES/shadowlab-0.1.tbz2 shadowlab

%prep
%setup -q -n %{name}

%pre
die() { echo "[die] $@" >&2 ; exit 1 ; }
ROOTPW=$(getent shadow | awk -F: '$1=="root" {print $2}')

getent group ansible >/dev/null || groupadd -r -g 900 ansible || die "adding group ansible"
getent passwd ansible >/dev/null \
  || useradd -r -m -u 900 -g ansible -G wheel -c "Ansible" -p $ROOTPW || die "creating user ansible"

%install
rm -rf %{buildroot}
mkdir %{buildroot}
install -m 0755 -d %{buildroot}/usr/local/sbin
install -m 0755 -d %{buildroot}/usr/share/%{name}

cp -p  sbin/*    %{buildroot}/usr/local/sbin
cp -p  etc/*     %{buildroot}/usr/share/%{name}/

%files
%defattr(0644,root,root,755)
/usr/share/%{name}
%defattr(0755,root,root,755)
/usr/local/sbin/ip_auto
/usr/local/sbin/ip_fixed
/usr/local/sbin/install-docker
