#!/bin/zsh
# Installs the manaba → Google Calendar sync as a launchd job (macOS). Run it again to change settings.
set -euo pipefail

SRC="${0:A:h}"
LABEL="io.github.seanachan.manaba-calendar-sync"
DEST="$HOME/.local/share/manaba-calendar-sync"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
DOMAIN="gui/$(id -u)"
LOCK="$HOME/Library/Caches/manaba-calendar-sync.lock"  # same file as run.sh

usage() {
  cat <<'EOF'
Usage: ./install.sh --calendar-id ID [options]

  --calendar-id ID   Google Calendar to write to ("primary" is your main calendar)
  --lang ja|en       language of event titles and descriptions (default: ja)
  --time HH:MM       daily run time, 24-hour clock (default: 22:00)
  --model NAME       Claude model for the job (default: sonnet)
  --budget USD       stop a run that would cost more than this (default: 1)
  --dry-run          write the files to a temporary folder and print where; install nothing
EOF
  exit "${1:-0}"
}
die() { print -u2 "error: $*"; exit 1; }
need_value() { (( $# >= 2 )) && [[ "$2" != -* ]] || die "$1 needs a value"; }

calendar_id="" lang="ja" run_time="22:00" model="sonnet" budget="1" dry_run=0
while (( $# )); do
  case "$1" in
    --calendar-id) need_value "$@"; calendar_id="$2"; shift 2 ;;
    --lang)        need_value "$@"; lang="$2"; shift 2 ;;
    --time)        need_value "$@"; run_time="$2"; shift 2 ;;
    --model)       need_value "$@"; model="$2"; shift 2 ;;
    --budget)      need_value "$@"; budget="$2"; shift 2 ;;
    --dry-run)     dry_run=1; shift ;;
    -h|--help)     usage ;;
    *)             print -u2 "unknown option: $1"; usage 1 ;;
  esac
done

[[ "$(uname -s)" == Darwin ]] || die "macOS only: the job is scheduled with launchd"
[[ -n "$calendar_id" ]] || usage 1
# Values end up in a prompt, a plist, a JSON hook command and a sourced file, so allow only plain
# characters. Install paths start with $HOME, so it is checked too.
[[ "$HOME" =~ '^[A-Za-z0-9._/ -]+$' ]] || die "this installer cannot handle the home folder path $HOME"
[[ "$calendar_id" =~ '^[A-Za-z0-9._@+-]+$' ]] || die "--calendar-id has unexpected characters"
[[ "$run_time" =~ '^([01]?[0-9]|2[0-3]):[0-5][0-9]$' ]] || die "--time must be HH:MM, 24-hour"
[[ "$model" =~ '^[A-Za-z0-9._-]+$' ]] || die "--model has unexpected characters"
[[ "$budget" =~ '^[0-9]+(\.[0-9]+)?$' ]] && (( budget > 0 )) || die "--budget must be a number above 0"
hour=$(( 10#${run_time%%:*} ))
minute=$(( 10#${run_time##*:} ))

case "$lang" in
  ja) language="Japanese" due="締切" resubmit="再提出可" check="確認：" date_format="M/D（曜）HH:MM"
      example="サンプル講義 第2週レポート(manaba)" ;;
  en) language="English" due="Due" resubmit="resubmission allowed" check="Check: " date_format="ddd M/D HH:MM"
      example="Sample Course Week 2 report (manaba)" ;;
  *) die "--lang must be ja or en" ;;
esac

# Look up real files: install.sh does not read ~/.zshrc, so a shell alias for claude is not visible.
find_bin() {
  local c
  for c in "$(whence -p $1)" "${@:2}"; do [[ -x "$c" ]] && { print -r -- "$c"; return; }; done
  return 1
}
manaba_bin=$(find_bin manaba ~/.local/bin/manaba) \
  || die "manaba not found. Install it: uv tool install git+https://github.com/Seanachan/manaba-cli"
claude_bin=$(find_bin claude ~/.local/bin/claude ~/.claude/local/claude) \
  || die "claude not found. Install Claude Code and log in with your claude.ai account first"

# Replacing files or reloading the job mid-run would cut a sync off halfway. Every run holds $LOCK,
# including runs started by hand; holding it until install.sh exits also keeps a run from starting
# while the files change.
if (( ! dry_run )); then
  zmodload zsh/system
  mkdir -p "${LOCK:h}"
  : >> "$LOCK"
  zsystem flock -t 0 "$LOCK" 2>/dev/null \
    || die "a sync is running right now. Run install.sh again when it has finished (a few minutes)"
fi

status_json=$("$manaba_bin" status --json 2>/dev/null || true)
# The guard only lets Claude read task pages on this site.
base_url=""
[[ "$status_json" =~ '"base_url": "([^"]+)"' ]] && base_url=${match[1]%/}
[[ "$base_url" =~ '^https?://[A-Za-z0-9.-]+(:[0-9]+)?(/[A-Za-z0-9._~-]+)*$' ]] \
  || die "could not read the manaba site from 'manaba status --json'. Check that manaba-cli works, then try again"
if [[ "$status_json" != *'"credentials_stored": true'* ]]; then
  print -u2 "warning: no stored manaba password. Run 'manaba login --set-credentials' so the job can log in again by itself."
fi

if (( dry_run )); then
  out=$(mktemp -d)
  plist_out="$out/$LABEL.plist"
else
  out="$DEST"
  plist_out="$PLIST"
fi
mkdir -p "$out" "${plist_out:h}" "$HOME/Library/Logs"

typeset -A vars=(
  CALENDAR_ID "$calendar_id"  LANGUAGE "$language"  EXAMPLE_SUMMARY "$example"
  DUE "$due"  RESUBMIT "$resubmit"  CHECK "$check"  DATE_FORMAT "$date_format"
  LABEL "$LABEL"  RUN_SH "$out/run.sh"  GUARD_SH "$out/guard.sh"  HOUR "$hour"  MINUTE "$minute"
  LAUNCHD_LOG "$HOME/Library/Logs/manaba-calendar-sync.launchd.log"
)
render() {  # replace every {{KEY}} in template $1 with vars[KEY]; {{NOW}} is left for run.sh
  local text key
  text=$(<"$1")
  for key in ${(k)vars}; do text=${text//"{{$key}}"/${vars[$key]}}; done
  print -r -- "$text"
}

# Check the launchd file and settings.json before replacing anything, so a bad render leaves the old
# install intact.
render "$SRC/launchd.plist.template" > "$plist_out.new"
plutil -lint "$plist_out.new" >/dev/null || die "the rendered launchd file is invalid: $plist_out.new"
render "$SRC/settings.template.json" > "$out/settings.json.new"
hook=$(plutil -extract hooks.PreToolUse.0.hooks.0.command raw -o - "$out/settings.json.new" 2>/dev/null) || hook=""
[[ "$hook" == "\"$out/guard.sh\"" ]] || die "the rendered settings.json is invalid: $out/settings.json.new"

render "$SRC/prompt.template.md" > "$out/prompt.md"
mv "$out/settings.json.new" "$out/settings.json"
install -m 755 "$SRC/run.sh" "$out/run.sh"
install -m 755 "$SRC/guard.sh" "$out/guard.sh"
{
  print -r -- "export PATH=${(q)${manaba_bin:h}}:${(q)${claude_bin:h}}:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
  print -r -- "MANABA_SYNC_CALENDAR_ID=${(q)calendar_id}"
  print -r -- "MANABA_SYNC_BASE_URL=${(q)base_url}"
  print -r -- "MANABA_SYNC_MODEL=${(q)model}"
  print -r -- "MANABA_SYNC_BUDGET_USD=${(q)budget}"
  # manaba reads these from your shell setup, which launchd does not load: keep the values set now.
  for var in MANABA_BASE_URL MANABA_USERNAME XDG_CONFIG_HOME XDG_CACHE_HOME; do
    if [[ -n "${(P)var:-}" ]]; then print -r -- "export $var=${(q)${(P)var}}"; fi
  done
} > "$out/config.env"
mv "$plist_out.new" "$plist_out"

if (( dry_run )); then
  print "Dry run: nothing installed. Rendered files:"
  print -l "  $out/"{prompt.md,settings.json,run.sh,guard.sh,config.env} "  $plist_out"
  exit 0
fi

# Unload a previous install first. bootout can return before the job is gone, so wait for it; if the
# old job stayed loaded, a later check would mistake it for the new one.
launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
for attempt in {1..20}; do
  launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1 || break
  sleep 0.25
done
if launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1; then
  die "the previous job is still loaded. Run uninstall.sh, then install.sh again"
fi
# A label disabled earlier (launchctl disable) would make bootstrap fail.
launchctl enable "$DOMAIN/$LABEL" 2>/dev/null || true
launchctl bootstrap "$DOMAIN" "$PLIST" \
  || die "launchctl could not load $PLIST. Nothing is scheduled now; to retry: launchctl bootstrap $DOMAIN $PLIST"
launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1 || die "launchctl could not load $PLIST"

cat <<EOF
Installed. Runs every day at $(printf '%02d:%02d' $hour $minute), or at the next wake if the Mac was asleep.

  Run once now:  launchctl kickstart $DOMAIN/$LABEL
  Log:           ~/Library/Logs/manaba-calendar-sync.log
  Settings:      run install.sh again with new options
  Uninstall:     $SRC/uninstall.sh
EOF
