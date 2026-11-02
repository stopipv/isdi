# ISDi security fix & restructure plan (temporary working doc)

Source: external report (11 claims), verified 2026-10-07. Fork fix (beauregardhenry/isdi) not used.

## Phase 0: Containment (today)
- [ ] Check whether 1.0.8 wheel/sdist were uploaded to PyPI. Both contain:
      `isdi/web/static/images/tmp.png` (real phone screenshot, Feb 19), `data/pii.key`, `data/flask.secret`.
- [ ] If published: yank 1.0.8 (and any earlier release with tmp.png); treat the screenshot as a data exposure.
- [ ] Delete `src/isdi/web/static/images/tmp.png`, `src/isdi/data/{pii.key,flask.secret}`; rebuild `dist/`.

## Phase 1: Patch release 1.0.9 (small, targeted fixes)
- [x] #2 Blocklist flags dropped (`fix/blocklist-flags`, d621a74). Spyware == stalkerware.
- [x] #1 Command injection: validate `serial` against connected devices; no `shell=True` in paths reachable from HTTP.
- [x] Default bind host 127.0.0.1 (`config.py:306`), not 0.0.0.0.
- [x] Per-run random token required on all routes; POST + CSRF for state-changing ones (`/kill`, `/delete_device`, uninstall, privacy).
- [x] #7 Screenshots: write to private dir (0700) outside package; serve via token-checked route; fix broken preview path.
- [x] Packaging: explicit file list in `pyproject.toml`/`MANIFEST.in` (no `**/*`); CI step that lists wheel contents and fails on surprises.
- [x] #4 Details page: key loaded dump by serial; reject missing/unknown serial.
- [x] #8 Restore `_gmail.com` → `<db_email>` redaction; TLD `{2,}`; apply to `settings list` output.
- [x] #3 Remove 24 h `-mtime -1` early exit in `ios_scan.sh`.
- [x] Release notes: anyone scanned since ~1.0.2 should rescan (blocklist bug); credit reporter.

## Phase 2: Hardening (lower severity)
- [x] #6/#9 Remove `|safe` on app-info.db fields (sanitize `descriptionHTML`, allow `<br>` only); `appId` via `data-` attr; add CSP.
- [x] #9 Pin SHA-256 of app-info.db; atomic download (temp file + `os.replace`).
- [x] #5 Create keys with 0600, config/data dirs 0700.
- [x] #10 Root check: detect root packages via `pm list packages` (magisk, supersu...); drop `/data/adb` ls; use exit codes, not "not found" string.
- [x] #11 Upgrade Bootstrap 4.6.x, jQuery 3.7.x; delete dead JS (`create_tab`, `?id=&ser=` links).

## Phase 3: Restructure (capture → analyze)
Goal: the core is "app list vs blocklist"; isolate device I/O and keep dumps as evidence.

```
src/isdi/
  core/       models.py (App, Finding), blocklist.py (dict lookup), classify.py   # pure, no I/O
  capture/    android.py, ios.py   # argv-list subprocess only; serial must be in list_devices()
  analyze/    android.py, ios.py   # parse a scan folder -> list[App]; works offline
  cli.py      # `isdi scan`, `isdi analyze <scan-dir> --json`
  web/        # thin UI, no module-global scanner state
```
- Scan folder per scan: `scans/<scan-id>/` with one raw file per command and `manifest.json`
  (time, tool versions, commands, sha256 per file). 0700 dir, outside package, never served statically.
- Live scan = capture + analyze; offline investigation = analyze on stored folder.
- Raw capture kept unredacted & private; redaction only on export (decide policy).
- WSL: keep calling `adb.exe` / `pymobiledevice3.exe`, but as argv lists (no shell, drop `ios_scan.sh`/`android_scan.sh`).
- Delete after migration: `runcmd.py`, `lightweight_df.py`, most of `parse_dump.py`, shell scripts.
- Tests: recorded real outputs in `tests/fixtures/` → analyze → classify.

Migration order: core + tests → Android capture/analyze → iOS → slim web layer.

## Future: privacy/access reports (deferred 2026-10-29)
- iOS App Privacy Report (iOS 15.2+): Settings → Privacy & Security → App Privacy Report → share →
  "Save App Privacy Report" gives an `.ndjson` with per-app data access (location, camera, mic,
  contacts, photos + timestamps) and domains contacted. Only covers the last 7 days, and only if it
  was already turned on.
  - `pymobiledevice3` has no command for it, and `afc` (/var/mobile/Media) can't reach it.
  - Open question: can `pymobiledevice3 apps pull` read Files → "On My iPhone" over USB (house_arrest
    only serves apps with file sharing enabled)? Test with a saved report first; it decides the design.
  - If yes: "Pull from iPhone" button. If no: upload box on iOS results page (token + CSRF, size
    limit, parse in memory). Transfer by AirDrop is fine; avoid email/iCloud/Messages (abuser may
    have account access).
  - UI: per app, sensitive categories used + last time, and domains contacted; flagged apps first.
    Store parsed results with the scan; raw file only in the private 0700 dir if kept as evidence.
- Android equivalent: TBD (look for a comparable per-app access/permission-usage report).
