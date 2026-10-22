#!/bin/zsh
# Stops the launchd job and removes the installed files. The log is kept.
LABEL="io.github.seanachan.manaba-calendar-sync"
DOMAIN="gui/$(id -u)"
DEST="$HOME/.local/share/manaba-calendar-sync"

# Deleting guard.sh under a running sync would leave its last calendar calls unchecked. Every run holds
# $DEST/.lock, including runs started by hand.
zmodload zsh/system
if [[ -d "$DEST" ]]; then
  : >> "$DEST/.lock"
  if ! zsystem flock -t 0 "$DEST/.lock" 2>/dev/null; then
    print -u2 "error: a sync is running right now. Run uninstall.sh again when it has finished (a few minutes)"
    exit 1
  fi
fi

if launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null; then
  echo "Stopped $LABEL"
else
  echo "$LABEL was not loaded"
fi
rm -f "$HOME/Library/LaunchAgents/$LABEL.plist"
rm -rf "$DEST"
echo "Removed. The log is still at ~/Library/Logs/manaba-calendar-sync.log"
