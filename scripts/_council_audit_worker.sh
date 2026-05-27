#!/bin/bash
# Background worker invoked by council-post-commit.sh
# Args: $1=REPO $2=SHA $3=TITLE_FILE $4=DESC_FILE
#
# Reads title + description from temp files (avoids bash arg-length limits)
# and submits the proposal to the council. Result goes to the log files.

set -uo pipefail

LOG=/tmp/council_commits.log
REJECT_LOG=/tmp/council_rejects.log
COUNCIL_PY="/Users/nicholas/clawd/sovereign-temple/external_council_voice.py"
COUNCIL_VENV="/Users/nicholas/clawd/sovereign-temple/.venv/bin/python"
PARSER="/Users/nicholas/clawd/sovereign-temple/scripts/_council_parse.py"

# Source API keys from ~/.zshrc (background subshells don't inherit interactive shell env)
# We grep only export lines to avoid running arbitrary zshrc code in bash
if [ -f "$HOME/.zshrc" ]; then
  eval "$(grep -E '^export (STEPFUN|ANTHROPIC|DEEPSEEK|GOOGLE|MISTRAL|XAI|MINIMAX|DASHSCOPE|HUNYUAN)_API_KEY=' "$HOME/.zshrc" 2>/dev/null || true)"
fi

REPO="${1:-unknown}"
SHA="${2:-unknown}"
TITLE_FILE="${3:-}"
DESC_FILE="${4:-}"

TITLE="(no title)"
DESC="(no description)"
[ -f "$TITLE_FILE" ] && TITLE=$(cat "$TITLE_FILE")
[ -f "$DESC_FILE" ] && DESC=$(cat "$DESC_FILE")

echo "[$(date +%H:%M:%S)] AUDITING $REPO@$SHA: $TITLE" >> $LOG

RESULT=$("$COUNCIL_VENV" "$COUNCIL_PY" --title "$TITLE" --description "$DESC" --action-type "git_commit" 2>>$LOG)

SUMMARY=$(printf '%s' "$RESULT" | python3 "$PARSER" 2>/dev/null)
[ -z "$SUMMARY" ] && SUMMARY=$(printf "?\n?\n?\n")
MAJORITY=$(printf '%s' "$SUMMARY" | sed -n '1p')
PROP=$(printf '%s' "$SUMMARY" | sed -n '2p')
COUNTS=$(printf '%s' "$SUMMARY" | sed -n '3p')

echo "[$(date +%H:%M:%S)] $REPO@$SHA -> $MAJORITY ($COUNTS) proposal=$PROP" >> $LOG

if [ "$MAJORITY" = "reject" ]; then
  {
    echo "---"
    echo "[$(date +%H:%M:%S)] COUNCIL REJECTED $REPO@$SHA"
    echo "Title: $TITLE"
    echo "Proposal: $PROP  counts: $COUNTS"
    echo "Full audit:"
    echo "$RESULT"
    echo ""
  } >> $REJECT_LOG
fi

# Clean up temp files
rm -f "$TITLE_FILE" "$DESC_FILE"
exit 0
