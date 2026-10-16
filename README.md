# manaba-cli

A CLI tool for agents (and humans) to read [manaba](https://manaba.jp/), the
course management system used by many Japanese universities: your courses,
pending tasks with deadlines, course news, course contents, and any other page
as plain text or JSON.

The default site is the University of Tsukuba (`https://manaba.tsukuba.ac.jp`).
Other manaba sites work by setting `MANABA_BASE_URL`, as long as they log in
through a standard Shibboleth IdP.

## Read-only by design

manaba-cli never submits, answers, saves, or deletes anything on manaba.

- All page reads are HTTP `GET`s. The HTTP session class has no method that can
  send `POST`, `PUT`, or `DELETE`, and a test enforces that.
- The only form ever submitted is the SSO login form. The browser submits it, as
  you would by hand.
- Some links in manaba's UI change state through a plain `GET` (log out, switch
  language, toggle favourites, switch list layout). manaba-cli refuses those URLs
  before sending any request.
- Opening a news article or content page marks it as read, the same as viewing it
  in the browser.

## Install

Requirements: Python 3.13+, [uv](https://docs.astral.sh/uv/), and Google Chrome.
The SSO login drives your installed Chrome through Playwright, so there is no
`playwright install` step.

```sh
git clone https://github.com/Seanachan/manaba-cli.git
cd manaba-cli
uv tool install .
manaba --help
```

## Log in

```sh
manaba login --set-credentials   # prompts for username + password, then logs in
manaba status                    # logged_in: yes
```

- The password goes to the OS keychain (macOS Keychain via `keyring`). It is never
  written to disk or printed.
- Session cookies are saved to `~/.config/manaba-cli/cookies.json` with mode 0600.
- When the session expires, any command logs in again by itself, headless, once
  per run.
- `manaba login --headed` opens a visible Chrome window. Use it if the IdP shows
  something unexpected, such as a consent page or MFA, and finish the step by hand.

## Commands

Every command accepts `--json` for stable, machine-readable output. Datetimes are
ISO 8601 in Japan time (`+09:00`).

| Command | What it prints |
|---|---|
| `manaba login [--headed] [--set-credentials]` | Logs in through SSO and saves cookies. |
| `manaba status` | Whether the session is valid, cookie expiry, file locations. |
| `manaba courses` | Your courses: id, name, year, period, teacher, alert icons. |
| `manaba todo [--all] [--course ID] [--days N]` | Tasks across all courses, soonest deadline first. |
| `manaba news [--course ID] [--since YYYY-MM-DD] [--limit N]` | Course news, newest first. |
| `manaba news show <url \| id --course ID>` | One news article: text, links, attachments. |
| `manaba contents <course ID>` | Content folders, each page's text, links and attachment links. |
| `manaba show <url>` | Any manaba page as title, text and links, e.g. a quiz result. |

`todo` covers quizzes (`query`), drills (`drill`), reports (`report`) and surveys
(`survey`). By default it shows only pending tasks, meaning not closed and not
submitted or passed. A task whose status text is unknown also counts as pending.
`--all` shows everything.

`show` renders form fields so quiz results stay readable: a chosen option is `(x)`,
an unchosen one is `( )`, and a typed answer is `[answer]`.

### JSON example

```sh
manaba todo --json
```

```json
[
  {
    "course_id": 1001,
    "course_name": "Sample Course",
    "kind": "report",
    "id": 2001,
    "title": "Week 2 report",
    "status": "open",
    "my_status": "unsubmitted",
    "status_raw": "In progress / Not submitted",
    "start": "2026-10-09T13:30:00+09:00",
    "deadline": "2026-10-18T23:00:00+09:00",
    "url": "https://manaba.tsukuba.ac.jp/ct/course_1001_report_2001"
  }
]
```

| Field | Values |
|---|---|
| `kind` | `query`, `drill`, `report`, `survey` |
| `status` | `upcoming`, `open`, `closed`, or `null` if unknown (`status_raw` keeps the text) |
| `my_status` | `unsubmitted`, `submitted`, `passed`, `unpassed`, or `null` |
| `deadline` | ISO 8601, or `null` when the task has no end date |

## Configuration

| Setting | Where |
|---|---|
| Config file | `~/.config/manaba-cli/config.toml` (`base_url`, `username`) |
| Cookies | `~/.config/manaba-cli/cookies.json` (0600) |
| Password | OS keychain, service `manaba-cli` |
| Env overrides | `MANABA_BASE_URL`, `MANABA_USERNAME` |
| Debug dump | `~/.cache/manaba-cli/last-error.html`, written when a page fails to parse |

`XDG_CONFIG_HOME` and `XDG_CACHE_HOME` are honoured. `--debug` logs request URLs
(query strings removed) and status codes. It never logs cookies or form data.

Exit codes: `0` success, `1` other error, `2` not logged in or login failed,
`3` a page could not be parsed.

The course list is read from manaba's **List** view of My Courses. If yours shows
thumbnails, switch it to List once in the browser.

## Development

```sh
uv sync
uv run pytest
uv run ruff check && uv run ruff format --check
```

Parsers are pure functions from a fetched page to dataclasses
(`src/manaba_cli/parsers/`). Their tests run on hand-trimmed HTML in
`tests/fixtures/`. The fixtures copy manaba's markup but contain only made-up
names, ids and dates. Keep it that way: never commit real course pages, cookies,
or student data.

Selector reference: [book000/get-manaba](https://github.com/book000/get-manaba) (MIT).
Every selector was re-checked against a live manaba (English and Japanese UI
wording are both handled).

## License

MIT
