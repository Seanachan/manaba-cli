# manaba-cli

English | [日本語](README.ja.md)

[![CI](https://github.com/Seanachan/manaba-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/Seanachan/manaba-cli/actions/workflows/ci.yml)

A read-only command-line tool for [manaba](https://manaba.jp/), the course system
used by many Japanese universities. It lists your courses, pending assignments and
their deadlines, course news and course contents. It can also print any manaba page
as text. Output is a table for people, or JSON (`--json`) for scripts and AI agents.

The default site is the University of Tsukuba. Other universities can be configured
(see [Other universities](#other-universities)).

```text
$ manaba todo --days 7
  Deadline          Course         Kind    Title               Status  Mine
 ─────────────────────────────────────────────────────────────────────────────
  2026-10-18 23:00  Sample Course  report  Week 2 report       open    unsubmitted
  2026-10-20 12:15  Sample Course  drill   Vocabulary drill    open    unsubmitted
```

## What it will never do

manaba-cli **reads only**. It never submits, answers, saves, retracts, deletes or
changes anything on manaba.

- Every manaba request is an HTTP `GET`. The HTTP session class has no `POST`,
  `PUT` or `DELETE` method, and a test fails if one is added.
- Some manaba links change state through a plain `GET`: log out, switch the UI
  language, toggle favourite courses, switch list layout. manaba-cli refuses those
  URLs before sending any request.
- The only form ever submitted is your university's SSO login form. Your Chrome
  submits it through Playwright, the same way you would by hand.
- The single side effect: opening an article or page marks it as read, exactly as
  it does in the browser.

## Requirements

| | |
|---|---|
| Python | 3.11 or newer |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | to install the tool |
| Google Chrome | used for the SSO login only. Playwright drives your installed Chrome, so `playwright install` is not needed |
| A system keyring | stores your password (see the table below) |

| OS | Status | Notes |
|---|---|---|
| macOS | primary, used daily | Password goes to the macOS Keychain. Click **Always Allow** if macOS asks. |
| Linux | unit tests run in CI; login not yet tried | Needs a Secret Service keyring (GNOME Keyring or KWallet), unlocked. Needs Google Chrome; distro Chromium is not used. |
| Windows | untested | Password goes to the Windows Credential Locker. File permission bits (0600) do not apply. |

## Install

```sh
uv tool install git+https://github.com/Seanachan/manaba-cli
manaba --version
```

To update, run `uv tool upgrade manaba-cli`. To remove, see [Uninstall](#uninstall).

## First run

```sh
manaba login --set-credentials --headed
manaba status
```

1. `--set-credentials` asks for your manaba (SSO) username and password. The
   password goes to the system keyring, never to a file.
2. `--headed` shows the Chrome window for this first login, so you can watch the
   SSO page fill in and close. If a consent page, MFA prompt or anything else
   unexpected shows up, finish it by hand within 5 minutes.
3. `manaba status` should now show `logged_in  yes`.

After that, every command runs headless. When the session expires, the next
command logs in again by itself, at most once per run.

## Commands

Every command accepts `--json`. JSON keys are stable, and times are ISO 8601 in
Japan time (`+09:00`). The samples below are trimmed and use made-up data.

### `manaba status`: is the session valid?

```sh
manaba status --json
```
```json
{"logged_in": true, "base_url": "https://manaba.tsukuba.ac.jp", "username": "s0000000",
 "credentials_stored": true, "cookies_expire_at": null,
 "config_file": "/home/you/.config/manaba-cli/config.toml",
 "cookies_file": "/home/you/.config/manaba-cli/cookies.json"}
```

### `manaba courses`: your courses

```sh
manaba courses --json
```
```json
[{"id": 1001, "name": "Sample Course", "year": 2026, "period": "Autumn AB Tue. 3",
  "teacher": "Teacher A", "url": "https://manaba.tsukuba.ac.jp/ct/course_1001",
  "flags": {"unread_news": true, "unsubmitted_tasks": true, "new_grades": false,
            "unread_threads": false, "individual_messages": false}}]
```

### `manaba todo`: assignments and deadlines (the main command)

```sh
manaba todo                    # pending tasks across all courses, soonest deadline first
manaba todo --days 7           # only those due within 7 days
manaba todo --all              # also submitted and closed tasks
manaba todo --course 1001      # one course
```
```json
[{"course_id": 1001, "course_name": "Sample Course", "kind": "report", "id": 2001,
  "title": "Week 2 report", "status": "open", "my_status": "unsubmitted",
  "status_raw": "In progress / Not submitted",
  "start": "2026-10-09T13:30:00+09:00", "deadline": "2026-10-18T23:00:00+09:00",
  "url": "https://manaba.tsukuba.ac.jp/ct/course_1001_report_2001"}]
```

| Field | Values |
|---|---|
| `kind` | `query` (quiz), `drill`, `report`, `survey` |
| `status` | `upcoming`, `open`, `closed`, or `null` when the wording is unknown (`status_raw` keeps the original text) |
| `my_status` | `unsubmitted`, `submitted`, `passed`, `unpassed`, or `null` |
| `deadline` | ISO 8601, or `null` when the task has no end date |

"Pending" means not closed, and not submitted or passed. A task with an unknown
status also counts as pending.

### `manaba news`: course announcements

```sh
manaba news --since 2026-10-01 --limit 10
```
```json
[{"course_id": 1001, "course_name": "Sample Course", "id": 3001, "title": "Homework and listening task",
  "author": "Teacher A", "posted_at": "2026-10-16T00:00:00+09:00", "unread": true,
  "url": "https://manaba.tsukuba.ac.jp/ct/course_1001_news_3001"}]
```

### `manaba news show`: one announcement

```sh
manaba news show https://manaba.tsukuba.ac.jp/ct/course_1001_news_3001
manaba news show 3001 --course 1001          # same thing
```
```json
{"course_id": 1001, "id": 3001, "title": "Homework and listening task", "author": "Teacher A",
 "posted_at": "2026-10-16T00:00:00+09:00", "body": "Please submit …",
 "links": [{"text": "Report page", "url": "https://…/ct/course_1001_report_2001"}],
 "attachments": [{"name": "handout.pdf", "uploaded_at": "2026-10-15T17:23:00+09:00", "url": "https://…"}]}
```

### `manaba contents <course id>`: course materials

```sh
manaba contents 1001
```
```json
[{"id": "5001c1001", "title": "Class records", "url": "https://…/ct/page_5001c1001",
  "pages": [{"title": "Orientation", "author": "Teacher A", "updated_at": "2026-10-02T11:30:00+09:00",
             "publish_start": null, "publish_end": null, "text": "How the class works …",
             "links": [], "attachments": [{"name": "slides.pdf", "url": "https://…"}]}]}]
```

Attachments are listed as links. Nothing is downloaded.

### `manaba show <url>`: any page as text

```sh
manaba show https://manaba.tsukuba.ac.jp/ct/course_1001_drill_2002
```
```json
{"url": "https://…/ct/course_1001_drill_2002_submitlog_9001", "title": "Vocabulary drill",
 "text": "1. Sample question\n( ) A\n(x) B\nFill in: [answer]",
 "links": [{"text": "Tests", "url": "https://…/ct/course_1001_query"}]}
```

Quiz result pages keep your answers in form fields. `show` renders a chosen option
as `(x)`, an unchosen one as `( )`, and a typed answer as `[answer]`. On a drill or
quiz page, follow the **Result** link to see your answers.

### `manaba login`

| Flag | Use |
|---|---|
| `--set-credentials` | Prompt for username and password and store them. |
| `--headed` | Show the Chrome window. Use it for debugging or to finish MFA by hand. |

Global flags go before the command. `manaba --debug todo` logs request URLs (query
strings removed) and status codes to stderr. `manaba --version` prints the version.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | success |
| 1 | other error: network, unknown course, a URL outside manaba, a refused state-changing link, an unusable keyring |
| 2 | not logged in, or SSO login failed |
| 3 | a page could not be parsed (see [Troubleshooting](#troubleshooting)) |

## Integrations

Optional add-ons built on the JSON output. They live in [`integrations/`](integrations/) and are not
installed with the CLI.

| Integration | What it does |
|---|---|
| [Google Calendar sync](integrations/calendar-sync/) | macOS. A daily launchd job runs Claude Code, which reads `manaba todo` and adds each new deadline to your Google Calendar. Needs a claude.ai plan and the Google Calendar connector. |

An integration may send manaba data to other services. The calendar sync sends task details to
Anthropic and Google. The CLI itself never does (see [Security notes](#security-notes)).

## Configuration

| What | Where |
|---|---|
| Config | `~/.config/manaba-cli/config.toml`, with keys `base_url` and `username` |
| Session cookies | `~/.config/manaba-cli/cookies.json`, mode 0600, directory 0700 |
| Password | system keyring, service name `manaba-cli` |
| Parse-error dump | `~/.cache/manaba-cli/last-error.html` |
| Environment overrides | `MANABA_BASE_URL`, `MANABA_USERNAME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME` |

```toml
# ~/.config/manaba-cli/config.toml
base_url = "https://manaba.tsukuba.ac.jp"
username = "s0000000"
```

## Other universities

manaba is the same product everywhere, so the page parsers are shared. Two things
can differ: the site URL and the SSO login page.

1. **Point at your site.** Set `base_url` in `config.toml` or export
   `MANABA_BASE_URL=https://manaba.example-u.ac.jp`. Use the part before `/ct/`.
2. **Check the login.** Run `manaba --debug login --set-credentials --headed` and
   watch the window.
   - If it logs in, you are done.
   - If it stops on the login form, your IdP uses different field names. The
     selectors are three constants at the top of
     [`src/manaba_cli/auth.py`](src/manaba_cli/auth.py):

     ```python
     USERNAME_FIELD = "input[name=j_username]"
     PASSWORD_FIELD = "input[name=j_password]"
     PROCEED_BUTTON = "button[name=_eventId_proceed], input[type=submit][name=_eventId_proceed]"
     ```

     These are the Shibboleth IdP v3+ defaults. Open your login page, inspect the
     username field, password field and login button, and adjust the selectors. A
     PR that adds support without breaking the defaults is welcome.
   - If your SSO needs MFA, `--headed` lets you finish it by hand (5-minute
     window). Automatic re-login cannot answer MFA, so after each session expiry
     you will need `manaba login --headed` again.
   - The error message names the page where the login stopped (query strings
     removed), which helps with debugging.
3. **Course list view.** manaba-cli reads the **List** view of My Courses. If yours
   shows thumbnails or a timetable, switch it to List once in the browser.

## Troubleshooting

| Symptom | What to do |
|---|---|
| `Not logged in to manaba` (exit 2) | Run `manaba login`. If it keeps failing, run `manaba login --headed` and watch. |
| `The IdP rejected the username or password` | Run `manaba login --set-credentials` to store the right ones. |
| `SSO did not return to manaba within 60s` | Something unexpected appeared during login (consent, MFA, password change). Run `manaba login --headed` and finish it by hand. |
| Login loops: works, then fails on the next command | Run `manaba status`. If `logged_in` flips back to `no` right away, your site may bind sessions to the browser. Open an issue with the `manaba --debug status` output. |
| `Could not find … (selector)` (exit 3) | manaba's HTML differs from what the parser expects. The page was saved to `~/.cache/manaba-cli/last-error.html`. Open an issue with an anonymized snippet (see [CONTRIBUTING](CONTRIBUTING.md#reporting-a-selector-break)). |
| `Course list table not found` | Switch My Courses to the **List** view in the browser. |
| `The system keyring is not usable` | Linux: install and unlock GNOME Keyring or KWallet. |
| macOS keeps asking for Keychain access | Click **Always Allow**. Reinstalling the tool can bring the prompt back once. |
| `Browser login failed: … Chromium distribution 'chrome' is not found` | Install Google Chrome. |

## Security notes

- **Password:** stored only in the system keyring. It is never written to disk,
  printed or logged.
- **Cookies:** `~/.config/manaba-cli/cookies.json` holds your manaba and IdP session
  cookies (mode 0600). Anyone who can read this file can act as you on manaba until
  the session expires. Do not share it or commit it.
- **Network:** the tool talks only to your manaba site and your university's login
  page. There is no telemetry, no analytics and no other server. URLs outside
  `base_url` are refused.
- **Logs:** `--debug` prints URLs without query strings, plus status codes. It never
  prints cookies, SAML data or form values.
- **Parse-error dumps:** `last-error.html` contains your own course page. Anonymize
  it before sharing.

See [SECURITY.md](SECURITY.md) for how to report a vulnerability.

## Uninstall

```sh
uv tool uninstall manaba-cli
rm -rf ~/.config/manaba-cli ~/.cache/manaba-cli
security delete-generic-password -s manaba-cli     # macOS: remove the stored password
```

## Contributing

Bug reports, fixes and support for more universities are welcome. Read
[CONTRIBUTING.md](CONTRIBUTING.md) first. The read-only rule is not negotiable.

Selector reference: [book000/get-manaba](https://github.com/book000/get-manaba) (MIT).
Every selector was re-checked against a live manaba, in both the English and the
Japanese UI.

## License

[MIT](LICENSE)
