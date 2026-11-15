Name:   shadowlab
Summary:        Shadowlab Addons
Version:        0.1
Release:        %{date}
License:        Private
Group:          System Environment/Base
Source0:        %{name}-%{version}.tbz2

%description
Some helper scripts and settings for Shadowlab

# cd ~/git/shadowlab
# tar -jcvf ~/rpmbuild/SOURCES/shadowlab-0.1.tbz2 shadowlab

%prep
%setup -q -n %{name}

%install
rm -rf %{buildroot}
mkdir %{buildroot}
install -m 0755 -d %{buildroot}/usr/local/sbin

cp -p  sbin/*    %{buildroot}/usr/local/sbin


%files
%defattr(0755,root,root,755)
/usr/local/sbin/ip_auto
/usr/local/sbin/ip_fixed
