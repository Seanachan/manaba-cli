# Security policy

**Reporting:** please report vulnerabilities privately through
[GitHub private vulnerability reporting](https://github.com/Seanachan/manaba-cli/security/advisories/new),
not in public issues. Include steps to reproduce, but no real credentials,
cookies or student data.

**What the tool stores:** manaba-cli keeps your manaba username in
`~/.config/manaba-cli/config.toml` and your password in the OS keyring (service
`manaba-cli`). It never writes the password to disk. Session cookies for manaba and
your university's IdP are in `~/.config/manaba-cli/cookies.json` (mode 0600) and
grant access to your account until they expire. When a page fails to parse, its
HTML is saved to `~/.cache/manaba-cli/last-error.html`. The tool sends data only to
your configured manaba site and its login page, and it never submits or changes
anything on manaba.
