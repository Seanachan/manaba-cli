#!/bin/zsh
# Installs the manaba → Google Calendar sync as a launchd job (macOS). Run it again to change settings.
set -euo pipefail

SRC="${0:A:h}"
LABEL="io.github.seanachan.manaba-calendar-sync"
DEST="$HOME/.local/share/manaba-calendar-sync"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
DOMAIN="gui/$(id -u)"

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

calendar_id="" lang="ja" run_time="22:00" model="sonnet" budget="1" dry_run=0
while (( $# )); do
  case "$1" in
    --calendar-id|--lang|--time|--model|--budget)
      (( $# >= 2 )) || die "$1 needs a value"
      case "$1" in
        --calendar-id) calendar_id="$2" ;;
        --lang) lang="$2" ;;
        --time) run_time="$2" ;;
        --model) model="$2" ;;
        --budget) budget="$2" ;;
      esac
      shift 2 ;;
    --dry-run) dry_run=1; shift ;;
    -h|--help) usage ;;
    *) print -u2 "unknown option: $1"; usage 1 ;;
  esac
done

[[ "$(uname -s)" == Darwin ]] || die "macOS only: the job is scheduled with launchd"
[[ -n "$calendar_id" ]] || usage 1
# Values end up in a prompt, a plist and a sourced file, so allow only plain characters.
[[ "$calendar_id" =~ '^[A-Za-z0-9._@+-]+$' ]] || die "--calendar-id has unexpected characters"
[[ "$run_time" =~ '^([01]?[0-9]|2[0-3]):[0-5][0-9]$' ]] || die "--time must be HH:MM, 24-hour"
[[ "$model" =~ '^[A-Za-z0-9._-]+$' ]] || die "--model has unexpected characters"
[[ "$budget" =~ '^[0-9]+(\.[0-9]+)?$' ]] || die "--budget must be a number"
hour=$(( 10#${run_time%%:*} ))
minute=$(( 10#${run_time##*:} ))

case "$lang" in
  ja) language="Japanese" due="締切" resubmit="再提出可" check="確認：" date_format="M/D（曜）HH:MM"
      example="サンプル講義 第2週レポート(manaba)" ;;
  en) language="English" due="Due" resubmit="resubmission allowed" check="Check: " date_format="ddd M/D HH:MM"
      example="Sample Course Week 2 report (manaba)" ;;
  *) die "--lang must be ja or en" ;;
esac

manaba_bin=$(command -v manaba) \
  || die "manaba not found. Install it: uv tool install git+https://github.com/Seanachan/manaba-cli"
claude_bin=$(command -v claude) \
  || die "claude not found. Install Claude Code and log in with your claude.ai account first"

status_json=$(manaba status --json 2>/dev/null || true)
if [[ "$status_json" != *'"credentials_stored": true'* ]]; then
  print -u2 "warning: no stored manaba password. Run 'manaba login --set-credentials' so the job can log in again by itself."
fi

typeset -A vars=(
  CALENDAR_ID "$calendar_id"  LANGUAGE "$language"  EXAMPLE_SUMMARY "$example"
  DUE "$due"  RESUBMIT "$resubmit"  CHECK "$check"  DATE_FORMAT "$date_format"
  LABEL "$LABEL"  RUN_SH "$DEST/run.sh"  HOUR "$hour"  MINUTE "$minute"
  LAUNCHD_LOG "$HOME/Library/Logs/manaba-calendar-sync.launchd.log"
)
render() {  # replace every {{KEY}} in template $1 with vars[KEY]
  local text key
  text=$(<"$1")
  for key in ${(k)vars}; do text=${text//"{{$key}}"/${vars[$key]}}; done
  print -r -- "$text"
}

if (( dry_run )); then
  out=$(mktemp -d)
  plist_out="$out/$LABEL.plist"
else
  out="$DEST"
  plist_out="$PLIST"
fi
mkdir -p "$out" "${plist_out:h}" "$HOME/Library/Logs"

render "$SRC/prompt.template.md" > "$out/prompt.md"
install -m 755 "$SRC/run.sh" "$out/run.sh"
{
  print -r -- "export PATH=${(q)${manaba_bin:h}}:${(q)${claude_bin:h}}:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
  print -r -- "MANABA_SYNC_MODEL=${(q)model}"
  print -r -- "MANABA_SYNC_BUDGET_USD=${(q)budget}"
} > "$out/config.env"
render "$SRC/launchd.plist.template" > "$plist_out"
plutil -lint -s "$plist_out"

if (( dry_run )); then
  print "Dry run: nothing installed. Rendered files:"
  print -l "  $out/prompt.md" "  $out/run.sh" "  $out/config.env" "  $plist_out"
  exit 0
fi

launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
for attempt in 1 2 3; do
  launchctl bootstrap "$DOMAIN" "$PLIST" 2>/dev/null && break
  sleep 1  # bootout of a previous install can take a moment
done
launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1 || die "launchctl could not load $PLIST"

cat <<EOF
Installed. Runs every day at $(printf '%02d:%02d' $hour $minute), or at the next wake if the Mac was asleep.

  Run once now:  launchctl kickstart $DOMAIN/$LABEL
  Log:           ~/Library/Logs/manaba-calendar-sync.log
  Settings:      run install.sh again with new options
  Uninstall:     $SRC/uninstall.sh
EOF
