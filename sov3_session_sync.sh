#!/bin/bash
# SOV3 Session Auto-Sync
# Feeds session context into SOV3 memory after each Claude Code / OpenCode session
# Can be called manually or as a hook
#
# Usage:
#   ./sov3_session_sync.sh                    # Sync latest session
#   ./sov3_session_sync.sh "summary text"     # Sync custom summary
#   ./sov3_session_sync.sh --watch            # Watch for new sessions

SOV3_URL="${SOV3_URL:-http://localhost:3101}"
SESSIONS_DIR="$HOME/.claude/projects/-Users-nicholas"

sync_to_sov3() {
    local content="$1"
    local tags="${2:-session,auto-sync}"
    local source="${3:-claude-code-auto}"

    # Record to SOV3 via MCP endpoint
    curl -s -X POST "$SOV3_URL/mcp" \
        -H "Content-Type: application/json" \
        -d "{
            \"jsonrpc\": \"2.0\",
            \"method\": \"tools/call\",
            \"id\": \"sync-$(date +%s)\",
            \"params\": {
                \"name\": \"record_memory\",
                \"arguments\": {
                    \"content\": $(echo "$content" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'),
                    \"source_agent\": \"$source\",
                    \"memory_type\": \"insight\",
                    \"care_weight\": 0.85,
                    \"tags\": [$(echo "$tags" | sed 's/,/","/g' | sed 's/^/"/;s/$/"/')]
                }
            }
        }" 2>/dev/null | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    r = d.get('result', {})
    if isinstance(r, dict):
        content = r.get('content', [{}])
        if isinstance(content, list) and content:
            text = content[0].get('text', '{}')
            result = json.loads(text)
            if result.get('success'):
                print(f'✅ Synced to SOV3: {result.get(\"episode_id\", \"?\")[:8]}...')
            else:
                print(f'⚠️  SOV3 error: {result}')
        else:
            print(f'⚠️  Unexpected: {r}')
    else:
        print(f'⚠️  Response: {d}')
except Exception as e:
    print(f'❌ Parse error: {e}')
"
}

# Sync CLAUDE.md changes
sync_claude_md() {
    local claude_md="$HOME/clawd/CLAUDE.md"
    if [[ -f "$claude_md" ]]; then
        local content="CLAUDE.MD STATE ($(date +%Y-%m-%d)): $(head -20 "$claude_md" | tr '\n' ' ')"
        sync_to_sov3 "$content" "claude-md,config,workspace"
    fi
}

# Sync memory/*.md files
sync_memory_files() {
    local memory_dir="$HOME/.claude/projects/-Users-nicholas/memory"
    if [[ -d "$memory_dir" ]]; then
        for f in "$memory_dir"/*.md; do
            if [[ -f "$f" ]]; then
                local fname=$(basename "$f")
                local content="MEMORY FILE [$fname] ($(date +%Y-%m-%d)): $(head -30 "$f" | tr '\n' ' ')"
                sync_to_sov3 "$content" "memory,claude-memory,$fname" "memory-sync"
            fi
        done
    fi
}

case "${1:-}" in
    --watch)
        echo "👁️  Watching for session changes..."
        while true; do
            # Check for new .jsonl files in last 5 minutes
            find "$SESSIONS_DIR" -name "*.jsonl" -mmin -5 -type f 2>/dev/null | while read f; do
                echo "📝 New session activity: $(basename "$f")"
                # Extract last assistant message as summary
                local summary=$(tail -1 "$f" 2>/dev/null | python3 -c "
import json, sys
try:
    d = json.loads(sys.stdin.read())
    if d.get('role') == 'assistant':
        content = d.get('content', '')
        if isinstance(content, list):
            texts = [c.get('text','') for c in content if c.get('type') == 'text']
            content = ' '.join(texts)
        print(content[:500])
except: pass
" 2>/dev/null)
                if [[ -n "$summary" ]]; then
                    sync_to_sov3 "SESSION UPDATE ($(date)): $summary" "session,auto-sync"
                fi
            done
            sleep 300  # Check every 5 minutes
        done
        ;;
    "")
        echo "🔄 SOV3 Session Sync"
        echo "  SOV3: $SOV3_URL"

        # Check SOV3 is up
        health=$(curl -s "$SOV3_URL/health" 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin).get('status','?'))" 2>/dev/null)
        if [[ "$health" != "healthy" ]]; then
            echo "❌ SOV3 not responding at $SOV3_URL"
            exit 1
        fi
        echo "  Status: $health"

        sync_claude_md
        sync_memory_files
        echo "✅ Sync complete"
        ;;
    *)
        # Custom summary provided as argument
        sync_to_sov3 "$1" "${2:-session,manual-sync}" "${3:-manual}"
        ;;
esac
