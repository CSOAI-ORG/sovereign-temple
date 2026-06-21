#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# Syncthing Setup for M2 ↔ M4 Model Sync
# Run on BOTH machines
# ═══════════════════════════════════════════════════════════════════════════════
set -e

MACHINE=${1:-m4}  # Pass 'm2' or 'm4'

if ! command -v syncthing &>/dev/null; then
  echo "[SYNCTHING] Installing..."
  brew install syncthing || { echo "Install failed"; exit 1; }
fi

mkdir -p ~/.config/syncthing
mkdir -p ~/Sync/meokclaw-models

cat > ~/.config/syncthing/config.xml << XMLEOF
<configuration version="37">
  <folder id="meokclaw-models" label="MEOKCLAW Models" path="~/Sync/meokclaw-models" type="sendreceive">
    <device id="M4-DEVICE-ID"/>
    <device id="M2-DEVICE-ID"/>
  </folder>
</configuration>
XMLEOF

# Start syncthing in background
nohup syncthing > /tmp/syncthing.log 2>&1 &
echo "[SYNCTHING] Started on $MACHINE"
echo "[SYNCTHING] GUI: http://localhost:8384"
echo "[SYNCTHING] Add the other machine's Device ID in the GUI"
