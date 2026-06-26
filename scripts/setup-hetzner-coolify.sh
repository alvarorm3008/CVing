#!/usr/bin/env bash
# Run on a fresh Ubuntu 24.04 Hetzner VPS (as root or with sudo).
# Usage: curl -fsSL <raw-url> | bash   OR   bash scripts/setup-hetzner-coolify.sh

set -euo pipefail

echo "==> Updating system..."
apt-get update -qq
apt-get upgrade -y -qq

echo "==> Installing Coolify..."
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash

echo ""
echo "============================================"
echo " Coolify installed."
echo " Open in browser: http://$(curl -s ifconfig.me):8000"
echo " (Coolify may use port 8000 or 80 — check install output above)"
echo "============================================"
