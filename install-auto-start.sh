#!/bin/bash
# Install JARVIS auto-start on macOS boot

PLIST_SOURCE="/Users/nicholas/clawd/sovereign-temple/com.meok.jarvis.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.meok.jarvis.plist"

echo "Installing JARVIS auto-start..."

# Copy plist
cp "$PLIST_SOURCE" "$PLIST_DEST"

# Load the agent
launchctl load "$PLIST_DEST"

echo "✅ JARVIS will now start on boot!"
echo ""
echo "To manage:"
echo "  launchctl unload $PLIST_DEST  # Disable"
echo "  launchctl load $PLIST_DEST     # Enable"
echo "  launchctl start com.meok.jarvis  # Start now"
echo "  launchctl stop com.meok.jarvis    # Stop"
