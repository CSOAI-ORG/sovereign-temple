#!/bin/bash
# Legion WireGuard Mesh Setup
# Run on EACH GPU node: bash setup_mesh.sh <node_name>
# node_name: forge | archive | speed-demon
# WireGuard IPs: forge=10.200.200.1, archive=10.200.200.2, speed-demon=10.200.200.3

NODE=${1:-forge}
set -e

echo "🔒 Setting up WireGuard mesh — Node: $NODE"

# Install WireGuard
apt-get update -qq && apt-get install -y wireguard-tools >/dev/null 2>&1
echo "  WireGuard installed"

# Generate keys if not exist
mkdir -p /etc/wireguard
if [ ! -f /etc/wireguard/privatekey ]; then
    wg genkey | tee /etc/wireguard/privatekey | wg pubkey > /etc/wireguard/publickey
fi
PRIVKEY=$(cat /etc/wireguard/privatekey)
PUBKEY=$(cat /etc/wireguard/publickey)
echo "  Public key: $PUBKEY"
echo "  SAVE THIS — share with other nodes"

# Assign IP based on node name
case "$NODE" in
    forge)        WG_IP="10.200.200.1/24" ;;
    archive)      WG_IP="10.200.200.2/24" ;;
    speed-demon)  WG_IP="10.200.200.3/24" ;;
    *) echo "Unknown node: $NODE" && exit 1 ;;
esac

# Write base config (add peers manually after exchanging keys)
cat > /etc/wireguard/wg0.conf << EOF
[Interface]
Address = $WG_IP
ListenPort = 51820
PrivateKey = $PRIVKEY
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

# Add peers below after collecting their public keys:
# [Peer]
# PublicKey = <OTHER_NODE_PUBKEY>
# AllowedIPs = 10.200.200.X/32
# Endpoint = <OTHER_NODE_IP>:51820
# PersistentKeepalive = 25
EOF

echo "  Config written: /etc/wireguard/wg0.conf"
echo ""
echo "  NEXT STEPS:"
echo "  1. Run this script on other nodes and collect their public keys"
echo "  2. Edit /etc/wireguard/wg0.conf and add [Peer] entries"
echo "  3. Run: wg-quick up wg0"
echo "  4. Test: ping 10.200.200.1"
