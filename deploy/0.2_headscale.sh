#!/bin/bash
# 0.2_headscale.sh - VPN for 9-node cluster
# BSD License - Headscale control server

set -e

echo "🌐 Deploying Headscale VPN..."

# Install headscale
brew install headscale  # macOS
# or: go install github.com/juanfont/headscale@latest

# Initialize headscale config
mkdir -p ~/headscale
cat > ~/headscale/config.yaml << 'EOF'
server:
  listen_addr: 0.0.0.0:8080
  metrics_listen_addr: 127.0.0.1:9090
  grpc_listen_addr: 0.0.0.0:50443
  grpc_allow_insecure: false
  private_key_path: /var/lib/headscale/private.key
  noise:
    private_key_path: /var/lib/headscale/noise_private.key
  derp:
    server:
      enabled: false
  auto_update_enabled: true
  update_frequency: 24h
  db_type: sqlite3
  db_path: /var/lib/headscale/db.sqlite
  acme_url: https://acme-v02.api.letsencrypt.org/directory
  acme_email: ""
  tls_letsencrypt_hostname: ""
  tls_cert_path: ""
  tls_key_path: ""
prefixes:
  v4: 100.64.0.0/10
  v6: fd7a:115c:a1e0::/53
  allocation: sequential
log:
  format: text
  level: info
EOF

# Create namespace for your nodes
headscale namespaces create meok-legion

# Generate keys for each node
headscale nodes create --user meok-legion --key gpu-0
headscale nodes create --user meok-legion --key gpu-1
headscale nodes create --user meok-legion --key gpu-2
headscale nodes create --user meok-legion --key gpu-3
headscale nodes create --user meok-legion --key gpu-4
headscale nodes create --user meok-legion --key gpu-5
headscale nodes create --user meok-legion --key gpu-6
headscale nodes create --user meok-legion --key mac-m4
headscale nodes create --user meok-legion --key mac-m2

# Start headscale server
headscale serve &
headscale_url="http://localhost:8080"

# Each node connects with (get key from headscale nodes list):
# tailscale up --login-server=$headscale_url --auth-key=<node-key>

echo "✅ Headscale deployed at $headscale_url"
echo "📝 Add nodes: headscale nodes list"
echo "🔑 Keys saved to ~/headscale/keys/"

# Install tailscale on each node
# Then: tailscale up --login-server=$headscale_url --auth-key=<key>