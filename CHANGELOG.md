# Changelog

## 1.0.9 (unreleased)

Security release. Please upgrade, and **rescan any device scanned with
1.0.2–1.0.8**: a bug since the pandas removal dropped app-flags.csv flags, so
known spyware/stalkerware could be shown without its flag.

Thanks to the external reporter who sent us these issues.

### Security
- Device commands (adb, pymobiledevice3) are run as argument lists, never
  through a shell; serials from the web UI must belong to a connected device
  and app IDs must look like package names (command injection).
- The web UI listens on 127.0.0.1 only by default and needs a per-run access
  link (`/?token=...`, printed at startup); state-changing routes are POST-only
  with a CSRF token. `--host` other than localhost prints a warning.
- Privacy-checkup screenshots are saved in a private directory (0700) and
  served through an authenticated route instead of the package's static dir.
- Packages list their files explicitly; `scripts/check_dist.py` (run by
  `make build` and CI) fails on unlisted files, keys, databases or screenshots.
  ISDi no longer writes newly seen iOS permissions into the installed package.
- App details are read from that device's own dump; an unknown or missing
  serial is rejected.
- App descriptions from app-info.db are escaped (only `<br>` kept); app IDs
  are passed to JavaScript through data attributes; a Content-Security-Policy
  and other security headers are sent.
- app-info.db downloads are checked against a pinned SHA-256 and moved into
  place atomically.
- Keys are created 0600 and ISDi's config/data/cache dirs 0700.

### Fixed
- Blocklist flags (app-flags.csv) were dropped from scan results; spyware and
  stalkerware rows are now scored as top risk.
- Email addresses in Android dumps are redacted again, including `settings list`
  output, Google-account database names (`<db_email>`) and long TLDs.
- iOS scans always take a fresh dump (a dump less than 24 h old used to be
  reused, hiding newly installed apps); `--udid` is passed correctly.
- Root detection checks installed root-manager packages (Magisk, KernelSU,
  APatch, SuperSU, ...) and `su` by exit code instead of matching "not found".
- Broken image paths on the instructions and privacy pages; the Google Photos
  hint showed the Google Maps image.

### Changed
- Bootstrap 4.0.0 → 4.6.2 (bundle with Popper), jQuery 3.3.1 → 3.7.1; removed
  unused JavaScript.
