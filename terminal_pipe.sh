#!/bin/bash
# terminal_pipe.sh — pipe terminal output to Sovereign's StreamAggregator
# Usage: command 2>&1 | ./terminal_pipe.sh
# Or: tail -f logfile | ./terminal_pipe.sh
# Or add to shell: exec > >(./terminal_pipe.sh) 2>&1

SOV_URL="${SOV_URL:-http://localhost:3200}"
BUFFER=()
BUFFER_SIZE=0
MAX_BUFFER=10

flush_buffer() {
    if [ ${#BUFFER[@]} -eq 0 ]; then return; fi
    # Build JSON array
    local json='{"lines":['
    local first=true
    for line in "${BUFFER[@]}"; do
        # Escape JSON
        line="${line//\\/\\\\}"
        line="${line//\"/\\\"}"
        line="${line//	/\\t}"
        if $first; then
            json+="\"$line\""
            first=false
        else
            json+=",\"$line\""
        fi
    done
    json+='],"source":"terminal_pipe"}'

    curl -s -X POST "$SOV_URL/context/terminal" \
        -H "Content-Type: application/json" \
        -d "$json" > /dev/null 2>&1 &

    BUFFER=()
    BUFFER_SIZE=0
}

# Read stdin line by line
while IFS= read -r line; do
    echo "$line"  # Pass through to stdout
    BUFFER+=("$line")
    ((BUFFER_SIZE++))
    if [ $BUFFER_SIZE -ge $MAX_BUFFER ]; then
        flush_buffer
    fi
done

flush_buffer  # Flush remaining
