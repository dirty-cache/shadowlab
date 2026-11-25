# Profile for Shadowlab
# /etc/profile.d/shadowlab.sh

# homelab-bin: user tools
pathmunge /opt/shadowlab/bin after

# root-only admin tools
if [ "$(id -u)" -eq 0 ]; then
  pathmunge /opt/shadowlab/sbin after
fi
