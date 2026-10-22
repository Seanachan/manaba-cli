# Contributing to manaba-cli

Thanks for helping. This page covers setup, the rules every change must follow, and
how to report a page that no longer parses.

## The read-only rule (hard requirement)

manaba-cli must never be able to change anything on manaba. A PR that breaks this
rule will not be merged, whatever else it does.

- **No write requests.** Only `GET` through `ManabaSession.get`. Do not add `post`,
  `put`, `patch` or `delete` methods, or call `httpx` directly.
  `tests/test_session.py::test_session_exposes_no_write_methods` checks the method
  names.
- **No state-changing GET links.** manaba changes state with some plain links
  (`logout`, `home_lang_*`, `*_set_*` favourites, `?chglistformat=`). They are
  refused in `src/manaba_cli/urls.py`. If you find another such link, add it to
  `_STATE_CHANGING_LINK` with a test. Never request it.
- **No form submissions** except the SSO login in `auth.py`. Never click
  Start/Submit/Post/Retract buttons, even in the browser.
- **No new data leaves the machine.** No telemetry, and no requests to hosts other
  than the configured manaba site and its IdP.

## Development setup

```sh
git clone https://github.com/Seanachan/manaba-cli.git
cd manaba-cli
uv sync                     # creates .venv with runtime and dev dependencies
uv run pytest               # tests: no network, Chrome or keychain needed
uv run ruff check           # lint
uv run ruff format          # format (CI runs `ruff format --check`)
uv run manaba --help        # run the CLI from your checkout
```

CI runs the same checks on Ubuntu and macOS with Python 3.11, 3.12 and 3.13.

## Code layout

| Path | Role |
|---|---|
| `src/manaba_cli/cli.py` | Typer commands. Thin: call the client, then render. |
| `src/manaba_cli/client.py` | Read operations: fetch pages, run parsers, fill in course names. |
| `src/manaba_cli/session.py` | GET-only httpx session, expiry detection, one automatic re-login. |
| `src/manaba_cli/auth.py` | Playwright SSO login (the only form submission). |
| `src/manaba_cli/parsers/` | Pure functions from `Page` (URL + HTML) to dataclasses in `models.py`. |
| `src/manaba_cli/render.py` | Tables for people, JSON for machines. |
| `integrations/` | Optional add-ons outside the CLI, with their own README. Not installed by `uv tool install`; the read-only rule still applies to anything they run against manaba. |
| `tests/fixtures/` | Anonymized HTML used by the parser tests. |

## Adding or fixing a parser (fixture first)

1. **Capture the page.** Run `manaba show <url> --json` to see what you are dealing
   with, or save the page source from your browser.
2. **Make an anonymized fixture.** Trim it to the elements the parser needs and save
   it as `tests/fixtures/<page>.html`. Before you commit it:
   - Replace every real name (students, teachers), student id, username, email and
     user id (for example `userballoon('1234567')`).
   - Replace real course ids, item ids and course or task titles with made-up ones
     such as `course_1001`, `Sample Course` or `Week 2 report`.
   - Delete cookies, session ids, tokens, hidden form values, and SAML or IdP URLs
     with query strings.
   - Keep the markup (tags, classes, nesting) and the UI wording (`In progress`,
     `受付中`), since those are what the parser reads.
   - Start the file with a comment saying it is anonymized.
3. **Write the failing test** in `tests/test_parse_<page>.py`, asserting the exact
   dataclasses you expect.
4. **Implement the parser** in `src/manaba_cli/parsers/`. Keep it pure (no I/O).
   Raise `ParseError` when the page is not the expected one. Return an empty list
   when the page legitimately has no items. Prefer lenient parsing: keep raw text
   (like `status_raw`) instead of failing on unknown wording.
5. **Wire it up** in `client.py`, `render.py` and `cli.py`. Every command must
   support `--json`. Add new JSON keys freely, but do not rename or remove existing
   ones: agents depend on them.
6. **Check the result** against a real manaba page with `uv run manaba …`, then run
   `uv run pytest` and `uv run ruff check`.

**Never commit real pages.** Raw pages from your account (and
`~/.cache/manaba-cli/last-error.html`) contain personal data. Keep them outside the
repository.

## Branches, commits and pull requests

1. Fork, then branch from `main`: `feat/<topic>`, `fix/<topic>`, `docs/<topic>`.
2. Keep commits small and focused, one concern each. Tests go in the same commit
   as the code they cover.
3. Write commit messages in [Conventional Commits](https://www.conventionalcommits.org/)
   style:
   ```
   feat: parse grade list
   fix: accept Japanese publish window separator
   docs: explain KWallet setup
   ```
   Types: `feat`, `fix`, `refactor`, `test`, `docs`, `ci`, `chore`. Use the
   imperative mood, put the subject at 72 characters or less, and use the body to
   explain *why*.
4. Open a PR against `main` and fill in the template checklist. CI must be green.

## Reporting a selector break

Selectors are verified on the University of Tsukuba's manaba, in English and in
Japanese. Another university, or a manaba update, may render pages differently.
When a command exits with code 3, please open a **Bug report** issue that includes:

- **University / manaba URL host** (for example `manaba.example-u.ac.jp`)
- **manaba build:** in the page source, search for `manaba.js?`. The number after it
  identifies the deployed build (for example `manaba.js?1792038052`).
- **UI language:** English or Japanese
- **Command and output:** for example `manaba todo`, and the `error:` line
- **Anonymized HTML snippet:** from `~/.cache/manaba-cli/last-error.html`, only the
  part around the table or element that failed, anonymized as described above.
  Never attach the whole file.

## Code style

- Readable, small functions with clear names. Comment *why*, not *what*.
- Type hints everywhere. Code must run on Python 3.11, so do not use 3.12+ syntax.
- Ruff settings in `pyproject.toml` are the standard. Japanese fullwidth characters
  are allowed.
