#!/bin/bash
cd /Users/nicholas/clawd/sovereign-temple
python3 voice_server.py > /tmp/voice_server.log 2>&1 &
sleep 2
open voice_client.html
echo "Voice started! Check browser."
