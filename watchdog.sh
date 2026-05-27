#!/bin/bash
# Quick health check — run via cron every 5 min
SOV3=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3101/health 2>/dev/null)
OLLAMA=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:11434/api/tags 2>/dev/null)
DISK=$(df -h / | tail -1 | awk '{print $5}' | tr -d '%')

if [ "$SOV3" != "200" ]; then echo "$(date): SOV3 DOWN" >> /tmp/watchdog.log; fi
if [ "$OLLAMA" != "200" ]; then echo "$(date): OLLAMA DOWN" >> /tmp/watchdog.log; fi
if [ "$DISK" -gt 85 ]; then echo "$(date): DISK at ${DISK}%" >> /tmp/watchdog.log; fi
