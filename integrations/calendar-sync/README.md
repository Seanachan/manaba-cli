# Google Calendar sync

English | [日本語](README.ja.md)

A daily job that copies new manaba deadlines into your Google Calendar. macOS only.

Every day at a time you choose, launchd starts [Claude Code](https://docs.claude.com/en/docs/claude-code)
in headless mode. Claude lists the tasks due within 90 days with `manaba todo --days 90`, checks
which are already in your calendar, reads each new task page with `manaba show`, and creates one
event per new deadline. A task due later than that is added once it comes within 90 days.

- The event ends at the deadline and starts 15 minutes before it.
- Reminders fire 1 day and 3 hours before the event starts.
- The location is the task URL, and the description summarizes what to submit.

```text
$ tail ~/Library/Logs/manaba-calendar-sync.log
=== 2026-10-22 22:00:01
CREATED 2
- 10/25 23:55 Sample Course Week 2 report (manaba)
- 10/29 10:10 Sample Seminar reading quiz (manaba)
SKIPPED (already in calendar) 5
exit=0
```

A macOS notification shows the `CREATED` line after each run.

## Before you install: what leaves your Mac

manaba-cli itself talks only to manaba and your university's login page. This integration is
different: it sends your task list and the text of each new task page to **Anthropic** (Claude) and
writes events to **Google Calendar**. Install it only if you are fine with that.

## What the job can and cannot do

Three limits apply to every run:

1. **Tools.** The job has two Claude Code tools (`--tools Bash,ToolSearch`): Bash, and ToolSearch,
   which only loads tool definitions. With `--permission-mode dontAsk`, Claude Code refuses every
   command and connector tool that is not in the table below, without asking anyone.
2. **Commands and calendar calls.** A hook (`guard.sh`) checks every command and calendar call
   before it runs. Commands: only `manaba todo`, and `manaba show` on a task page. Calendar calls: only
   the calendar you chose and only the fields an event needs, so no guests, attachments or Meet links.
   Text in a manaba page therefore cannot make Claude read your grades or messages, invite someone,
   or touch another calendar. Event descriptions do quote task pages, so use a calendar only you can see.
3. **Your own setup stays out.** The job loads only its own `settings.json` (`--setting-sources ""`)
   and runs in a new private temporary folder. Your CLAUDE.md, hooks and plugins do not run inside it.
   MCP servers you added to Claude Code yourself still start with each run (turning them off would
   also turn off the claude.ai calendar connector), but the job cannot use their tools.

| Allowed | Not allowed |
|---|---|
| `manaba todo`, `manaba show` (both read-only) | any other shell command, file edits, web access |
| list and create events in the calendar you chose | other calendars, guests, attachments, editing or deleting events |

Each run also stops if it would cost more than `--budget` (default 1 USD). It runs on your Claude
plan's usage.

## Requirements

| | |
|---|---|
| macOS | the schedule uses launchd |
| manaba-cli | installed, and logged in once with `manaba login --set-credentials`. The stored password lets the job log in again when the session expires. If your SSO needs MFA, the job cannot log in by itself. |
| Claude Code | installed, and logged in with a claude.ai account (Pro, Max, Team or Enterprise). An API key login has no claude.ai connectors. |
| Google Calendar connector | connected in claude.ai under **Connectors** |

Check that Claude Code can see your calendars:

```sh
claude -p "List my Google calendars with their ids" \
  --allowedTools mcp__claude_ai_Google_Calendar__list_calendars
```

## Install

1. **Pick a calendar.** Use `primary` for your main calendar, or a calendar id from the command
   above. In Google Calendar you also find it under **Settings → (your calendar) → Integrate
   calendar → Calendar ID**.
2. **Get the files.**
   ```sh
   git clone https://github.com/Seanachan/manaba-cli.git
   cd manaba-cli/integrations/calendar-sync
   ```
3. **Install.**
   ```sh
   ./install.sh --calendar-id primary --lang en --time 22:00
   ```
4. **Test once now.** Expect a notification within about 2 minutes.
   ```sh
   launchctl kickstart gui/$(id -u)/io.github.seanachan.manaba-calendar-sync
   tail ~/Library/Logs/manaba-calendar-sync.log
   ```

| Option | Default | Meaning |
|---|---|---|
| `--calendar-id ID` | required | calendar to write to (`primary` = your main calendar) |
| `--lang ja\|en` | `ja` | language of event titles and descriptions |
| `--time HH:MM` | `22:00` | daily run time, 24-hour clock |
| `--model NAME` | `sonnet` | Claude model for the job |
| `--budget USD` | `1` | stop a run that would cost more than this |
| `--dry-run` | | write the files to a temporary folder and print where; install nothing |

To change a setting, run `install.sh` again with the new options.

## How it decides what is new

The job searches your calendar for events that contain `manaba todo` and looks in their location
and description for the task id (`_report_2001`, `_query_3002`, and so on, not followed by another
digit). A task is skipped if its id appears in any event, so one event may cover several tasks. Claude does
this comparison itself, so on rare occasions it may add an event twice; delete the extra copy.

Two things follow:

- **Keep the last line** of a generated description (`Check: manaba todo --course …`). Without it
  the search does not find the event, and the job creates it again.
- **Your own events count** if they contain `manaba todo` and the task URL. Paste the task URLs into
  one event's description to cover several tasks with it, and date that event at the earliest deadline
  it covers: the job only checks events from 14 days ago to 91 days ahead.

The job only adds events. It never moves an event when a teacher changes a deadline, and it never
removes events for submitted tasks.

## When it runs

launchd starts the job at the set time. If the Mac is asleep then, the job runs when it wakes, after
waiting up to about 7 minutes for the network. If the
Mac is shut down, that day's run is skipped. The next run adds every pending task, except a task
whose deadline passed in between.

## Files

| Path | What |
|---|---|
| `~/.local/share/manaba-calendar-sync/` | `prompt.md` (the job's instructions), `run.sh`, `guard.sh` (checks commands and calendar calls), `settings.json` (loads the check), `config.env`, `uninstall.sh` |
| `~/Library/LaunchAgents/io.github.seanachan.manaba-calendar-sync.plist` | the schedule |
| `~/Library/Logs/manaba-calendar-sync.log` | one entry per run |
| `~/Library/Caches/manaba-calendar-sync.lock`, `manaba-calendar-sync-log.lock` | keep two runs, and two writes to the log, from overlapping |

## Troubleshooting

| Symptom | What to do |
|---|---|
| `FAILED: … Not logged in` | Run `manaba login --headed` once, then `manaba login --set-credentials` if the password changed. |
| `FAILED` with a connector error, or `FAILED: no report` | Reconnect Google Calendar in claude.ai and rerun the check command above. |
| No notification | Allow notifications for **Script Editor** in System Settings → Notifications. |
| `guard: blocked …` lines in the log | Claude tried a command or calendar call outside the limits, sometimes because a page told it to. The call did not run. If it happens on an ordinary task, open an issue with that log line. |
| `FAILED: stopped after 15 minutes` | A run hung, usually on the network or a connector login, and was stopped. The next run tries again. If it repeats, run `~/.local/share/manaba-calendar-sync/run.sh` by hand and watch the log. |
| `skipped: another sync or install.sh is running` | Two runs overlapped, or `install.sh` was running at the scheduled time. The skipped run did nothing; the next run catches up. |
| `error: a sync is running right now` from `install.sh` | Wait about 2 minutes for the run to finish, then run `install.sh` again. |
| An event was created twice | Its description lost the `manaba todo` line or the task URL. Delete one copy and restore the line. |
| Nothing happens at the set time | `launchctl print gui/$(id -u)/io.github.seanachan.manaba-calendar-sync` shows the state and the last exit code. |

## Uninstall

```sh
~/.local/share/manaba-calendar-sync/uninstall.sh
```

It stops the job and removes the installed files, itself included. `./uninstall.sh` in this folder does
the same. The log stays in `~/Library/Logs/`.
