#!/bin/zsh
# Runs one manaba → Google Calendar sync. launchd starts it on schedule; you can also run it by hand.
DIR="${0:A:h}"
LOG="$HOME/Library/Logs/manaba-calendar-sync.log"
CAL="mcp__claude_ai_Google_Calendar"

# Written by install.sh: PATH, MANABA_SYNC_MODEL, MANABA_SYNC_BUDGET_USD.
[[ -f "$DIR/config.env" ]] && source "$DIR/config.env"

cd "$DIR" || exit 1
{
  echo "=== $(date '+%Y-%m-%d %H:%M:%S')"
  # dontAsk refuses every tool that is not listed in --allowedTools.
  claude -p "$(<"$DIR/prompt.md")" \
    --model "${MANABA_SYNC_MODEL:-sonnet}" \
    --permission-mode dontAsk \
    --allowedTools "Bash(manaba todo:*)" "Bash(manaba show:*)" "Bash(manaba status:*)" \
                   "${CAL}__list_events" "${CAL}__create_event" \
    --max-budget-usd "${MANABA_SYNC_BUDGET_USD:-1}" \
    --no-session-persistence \
    --output-format text
  rc=$?
  echo "exit=$rc"
} >> "$LOG" 2>&1

summary=$(tail -n 30 "$LOG" | grep -E '^(CREATED|FAILED)' | tail -1)
(( rc != 0 )) && summary="FAILED: exit $rc, see $LOG"
osascript -e "display notification \"${summary//\"/}\" with title \"manaba calendar sync\"" 2>/dev/null
exit $rc
