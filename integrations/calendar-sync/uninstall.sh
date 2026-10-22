#!/bin/zsh
# Stops the launchd job and removes the installed files. The log is kept. install.sh also copies this
# script into the install folder; it works from either place.
LABEL="io.github.seanachan.manaba-calendar-sync"
DOMAIN="gui/$(id -u)"
DEST="$HOME/.local/share/manaba-calendar-sync"
LOCK="$HOME/Library/Caches/manaba-calendar-sync.lock"  # same file as run.sh

# Deleting guard.sh under a running sync would leave its last calendar calls unchecked. Every run holds
# $LOCK, including runs started by hand. The lock file stays, so it keeps working while $DEST goes.
zmodload zsh/system
if [[ -f "$LOCK" ]]; then
  if ! zsystem flock -t 0 "$LOCK" 2>/dev/null; then
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
