# Changelog

## 1.0.11 (2026-11-02)
### Added
- Optional **PhoneView** button: starts the separate PhoneView screen viewer on
  demand (one copy, port 6201) and opens it already signed in, with a per-run
  token derived from ISDi's own. PhoneView exits when ISDi stops, including
  when ISDi is killed (it watches its stdin pipe). Configure with
  `ISDI_PHONEVIEW_CMD`, `ISDI_PHONEVIEW_PORT`, `ISDI_PHONEVIEW_PUBLIC_URL`.
- `pip install "isdi-scanner[phoneview]"` installs PhoneView alongside ISDi
  (Python 3.11+); ISDi runs it with its own interpreter. `isdi phoneview status`
  shows what ISDi will run.
- remote.md: remote consultants through `tailscale serve`.

### Changed
- iOS uses pymobiledevice3 as a Python library on Linux, macOS and Windows
  (`isdi.scanner.ios_device`), instead of running its command-line tool three
  times per scan. `scripts/ios_scan.sh` is gone; dump files keep their format.
  An iPhone that is plugged in but not trusted now shows up with a hint.
- WSL2 and Termux keep the command-line tool, as **limited iOS support**: the
  afc2 jailbreak check is reported as not available there.
- pymobiledevice3 is pinned to `>=11.49,<11.50`, the same range as PhoneView, so
  `pip install "isdi-scanner[phoneview]"` installs both into one environment.
  Python 3.9+ is now required (pymobiledevice3 11.49 needs it).

- `make bump-version` makes the release: it bumps the version, dates the
  CHANGELOG, commits, tags `v<version>`, and pushes after asking. The tag push
  publishes to PyPI through GitHub Actions (trusted publishing) and creates the
  GitHub release. `PART=minor|major` now actually reaches the script.
- `isdi --version` and `config.VERSION` report the package version (they said
  1.0.2 and 1.0.0).

### Fixed
- The iOS afc2 jailbreak check never ran: it passed `udid=` to
  `create_using_usbmux`, which has no such parameter, and the error was swallowed.
- Native Windows was not recognised when choosing `adb.exe`.

### Tests
- One shared Flask app per test run (`tests/conftest.py`); a second
  `create_app()` in the same process has no routes.

## 1.0.10 (unreleased)

Security release. Please upgrade, and **rescan any device scanned with
1.0.2–1.0.9**: a bug since the pandas removal dropped app-flags.csv flags, so
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
- Root detection (upstream's checks from 1.0.9: build tags, SELinux, bootloader,
  verified boot, `su`, root-manager packages, Frida) runs without a local shell;
  the root-manager check also covers SuperUser and KingRoot. Root/jailbreak
  reasons shown on the page are escaped.
- iOS jailbreak detection reads the scanned device's own dump and now actually
  matches jailbreak package managers (Cydia, Sileo, Zebra, Filza).
- iOS scans under WSL failed with "Failed to dump or load iOS device" when an
  app's metadata had non-ASCII text (e.g. "©"): the Windows pymobiledevice3
  output was cp1252. It is now UTF-8, and older dumps still load.
- App details pages show the device's info (version, permissions, usage) for
  apps that are not in app-info.db, and say when no store description exists.
- Broken image paths on the instructions and privacy pages; the Google Photos
  hint showed the Google Maps image.

### Changed
- The home page lists connected phones (model, Android/iOS, last scan date)
  and updates as they are plugged in; each has its own Scan button. The
  "What type of device is this?" choice and the nickname field are gone, and
  only one scan runs at a time. Android phones that have not allowed USB
  debugging show what to do instead of a Scan button.
- Bootstrap 4.0.0 → 4.6.2 (bundle with Popper), jQuery 3.3.1 → 3.7.1; removed
  unused JavaScript.
