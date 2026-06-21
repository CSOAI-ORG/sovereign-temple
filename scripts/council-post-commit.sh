#!/bin/bash
# council-post-commit.sh — git post-commit hook
# Submits each commit to the 34+ node BFT council for audit, non-blocking.
# Heavy work is delegated to _council_audit_worker.sh (avoids bash 3.2 quoting issues).

set -uo pipefail

LOG=/tmp/council_commits.log
COUNCIL_PY="/Users/nicholas/clawd/sovereign-temple/external_council_voice.py"
COUNCIL_VENV="/Users/nicholas/clawd/sovereign-temple/.venv/bin/python"
WORKER="/Users/nicholas/clawd/sovereign-temple/scripts/_council_audit_worker.sh"

# Skip if council not running
HEALTH=$(curl -s -m 2 -o /dev/null -w "%{http_code}" http://localhost:3101/health 2>/dev/null)
if [ "$HEALTH" != "200" ]; then
  echo "[$(date +%H:%M:%S)] council offline (http=$HEALTH) - skipping audit" >> $LOG
  exit 0
fi

# Skip if deps missing
if [ ! -x "$COUNCIL_VENV" ] || [ ! -f "$COUNCIL_PY" ] || [ ! -x "$WORKER" ]; then
  echo "[$(date +%H:%M:%S)] missing council deps - skipping audit" >> $LOG
  exit 0
fi

# Gather commit info
REPO=$(basename "$(pwd)")
SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
MSG_FIRST=$(git log -1 --format='%s' 2>/dev/null || echo "unknown")
MSG_FULL=$(git log -1 --format='%B' 2>/dev/null || echo "unknown")
AUTHOR=$(git log -1 --format='%an' 2>/dev/null || echo "unknown")
DIFFSTAT=$(git diff-tree --no-commit-id --shortstat -r HEAD 2>/dev/null || echo "")
FILES=$(git diff-tree --no-commit-id --name-only -r HEAD 2>/dev/null | head -20 | tr '\n' ' ' || echo "")

# Skip noise commits
case "$MSG_FIRST" in
  Merge*|"chore: format"*|"style: prettier"*|"build:"*|"test(council):"*|"docs: council"*)
    echo "[$(date +%H:%M:%S)] $REPO@$SHA skipped (noise filter)" >> $LOG
    exit 0
    ;;
esac

# Stage title + description into temp files (avoids quoting nightmare)
TITLE_FILE=$(mktemp -t council_title.XXXXXX)
DESC_FILE=$(mktemp -t council_desc.XXXXXX)

printf '%s' "${REPO}@${SHA}: ${MSG_FIRST}" > "$TITLE_FILE"

cat > "$DESC_FILE" <<EOF
Repo: ${REPO}
Commit: ${SHA}
Author: ${AUTHOR}
Full message:
${MSG_FULL}

Diff stat: ${DIFFSTAT}
Files changed (first 20): ${FILES}

This commit was just made. The council is asked to vote whether the work
described in the commit message accurately reflects the diff, and whether
the change is safe + advances the user's stated goals.
EOF

# Fire worker in background — instant return for the hook
nohup "$WORKER" "$REPO" "$SHA" "$TITLE_FILE" "$DESC_FILE" >/dev/null 2>&1 &

exit 0
