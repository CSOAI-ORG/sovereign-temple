#!/bin/bash
# 0.1_infisical.sh - Secrets Management
# MIT License - Self-hosted secrets management

set -e

echo "🔐 Deploying Infisical..."

# Option 1: Docker (recommended for single node)
docker run -d \
  --name infisical \
  -p 443:443 \
  -e ENCRYPTION_KEY=your-32-char-encryption-key-here \
  -e AUTH_SECRET=your-64-char-auth-secret-here \
  -e DATABASE_URL=postgresql://sovereign:dragon@localhost:5432/infisical \
  -e NODE_ENV=production \
  infisical/infisical:latest

# Option 2: Helm (for k3s)
# helm repo add infisical https://charts.infisical.io
# helm install infisical infisical/infisical \
#   --set infisical.secret.encryptionKey=your-32-char-encryption-key-here \
#   --set infisical.secret.authSecret=your-64-char-auth-secret-here

echo "✅ Infisical deployed at https://localhost (or configure domain)"
echo "📝 Next: Add API keys via UI or CLI"
echo "   infisical secrets set OPENAI_API_KEY=sk-..."
echo "   infisical secrets set ANTHROPIC_API_KEY=sk-ant-..."