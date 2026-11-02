# Remote consultations with ISDi and PhoneView

This guide lets a consultant work with a client's phone from somewhere else. The
phone stays plugged into a **clinic laptop** next to its owner. The consultant uses
ISDi to scan the phone and PhoneView to see and operate its screen.

Nothing is opened to the internet or the local network. Both programs listen only on
the laptop itself. [Tailscale](https://tailscale.com) carries the connection, and only
members of your Tailscale network ("tailnet") whom you allow can reach them.

```
consultant's browser ──HTTPS──▶ Tailscale (tailscale serve) on the clinic laptop
                                 ├─ :443  → ISDi       127.0.0.1:6200
                                 └─ :8443 → PhoneView  127.0.0.1:6201 ──USB──▶ phone
```

Who is who in this guide:

- **Clinic laptop:** the computer the phone is plugged into: Linux, macOS or
  Windows. Native Windows covers iPhones for now (Android there is still to be
  done). WSL2 cannot see USB devices, so it has only limited iOS support, and
  PhoneView does not work there.
- **Consultant:** the remote expert, on their own (untagged) Tailscale device.
- **Client:** the phone's owner, who is with the clinic laptop.

## 1. One-time setup

### Tailscale network

1. Create a tailnet, or use your organisation's. In the admin console, under
   **DNS**, turn on **MagicDNS** and **HTTPS Certificates**. `tailscale serve`
   needs both for its `https://<laptop>.<tailnet>.ts.net` address.
2. Add an access rule so that only consultants can reach the clinic laptop, and only
   on these two ports. In the access controls file:

   ```json
   {
     "groups": {
       "group:consultants": ["alice@example.org", "bob@example.org"]
     },
     "tagOwners": {
       "tag:clinic-laptop": ["autogroup:admin"]
     },
     "grants": [
       {
         "src": ["group:consultants"],
         "dst": ["tag:clinic-laptop"],
         "ip":  ["tcp:443", "tcp:8443"]
       }
     ]
   }
   ```

   Keep any other rules from reaching `tag:clinic-laptop`. Consultants should use
   personal, untagged devices: Tailscale only adds the viewer's identity (used in
   PhoneView's audit log) for traffic from user devices.

### Clinic laptop

1. Install Tailscale, sign in, and make sure it starts at boot. On Linux run
   `sudo systemctl enable --now tailscaled`; macOS and Windows do this already.
2. In the admin console, give the laptop the tag `tag:clinic-laptop` and choose
   **Disable key expiry** for it. Otherwise it drops off the tailnet every 180 days
   until someone signs in again.
3. Install ISDi and PhoneView, plus the USB tools (see [README](README.md)):

   ```bash
   pip install "isdi-scanner[phoneview]"      # Python 3.11+
   sudo apt install adb usbmuxd      # Debian/Ubuntu; macOS: brew install --cask android-platform-tools
   ```

4. Publish both programs inside the tailnet. This only needs doing once: `--bg` keeps
   the setting through reboots and Tailscale restarts.

   ```bash
   tailscale serve --bg --https=443  http://127.0.0.1:6200   # ISDi
   tailscale serve --bg --https=8443 http://127.0.0.1:6201   # PhoneView
   tailscale serve status
   ```

   Use `tailscale serve`, **never `tailscale funnel`**, which publishes to the
   whole internet. Do not use `isdi run --host` for remote access either; it has no
   TLS.

If you change ISDi's port (`--port`) or PhoneView's (`ISDI_PHONEVIEW_PORT`), change
the matching `serve` line. If the PhoneView address is not `https://<same host>:8443`,
set `ISDI_PHONEVIEW_PUBLIC_URL` to it.

## 2. Each session

**At the clinic laptop** (staff or client):

1. Plug in the phone. The client unlocks it and approves the connection *on the
   phone*:
   - Android: *Allow USB debugging?* Leave **"Always allow from this computer"
     unticked**.
   - iPhone: *Trust This Computer?* ISDi's instructions cover Developer Mode if
     PhoneView is needed.
2. Start ISDi: `isdi run --no-browser`. It prints a one-time link:
   `http://127.0.0.1:6200/?token=…`.
3. Send the consultant the same link with the tailnet name in place of
   `127.0.0.1:6200`, for example `https://clinic-laptop.tail1234.ts.net/?token=…`.
   Use a private channel. The token changes every time ISDi starts.

**Consultant:**

1. Open the link. ISDi signs you in and removes the token from the address bar.
2. Scan as usual. Press **PhoneView** to open a live view of the phone in a new tab
   (`https://clinic-laptop.tail1234.ts.net:8443`), already signed in.
3. Only one PhoneView window can control the phone at a time.

**Client consent:** the client sees everything happen on their own phone screen,
and can end the session at any moment by unplugging the phone.

**Ending the session:**

1. Click **Close App and End Session** in ISDi. This also stops PhoneView, and the
   links stop working.
2. Remove the trust left on the phone:
   - Android: **Settings → Developer options → Revoke USB debugging
     authorizations**, then turn USB debugging off.
   - iPhone: **Settings → General → Transfer or Reset iPhone → Reset → Reset
     Location & Privacy** (this forgets trusted computers), then turn Developer
     Mode off if it was turned on for this session.

## 3. Security model

| Layer | Protection |
|---|---|
| Network | ISDi and PhoneView listen on 127.0.0.1 only; nothing is reachable from the LAN or the internet. |
| Transport | `tailscale serve` provides HTTPS with a valid certificate, and WireGuard encryption between devices. |
| Who can connect | Tailnet membership plus your access rule (only `group:consultants`, only ports 443 and 8443). |
| Who can use the apps | A new random token every time ISDi starts. It is swapped for an HttpOnly, SameSite=Strict session cookie, and ISDi also requires CSRF tokens on every change. PhoneView's token is derived from ISDi's, so only a signed-in ISDi user is handed a PhoneView link. |
| Cross-site attacks | Host and Origin allow-lists in PhoneView, a strict Content-Security-Policy, and no framing. |
| Accountability | PhoneView logs each view's start and end with the consultant's Tailscale login to `~/.cache/isdi/logs/phoneview-audit.jsonl`. Tailscale removes forged identity headers. |
| Phone | Every session needs the owner to unlock the phone and approve USB debugging or Trust. |

What this does **not** protect against:

- **Someone with access to the clinic laptop itself.** A local user or malware can
  reach the phone through adb or usbmuxd directly. Use a dedicated, up-to-date laptop
  with its own login.
- **A leaked link while ISDi is running.** Anyone in the tailnet who is allowed by
  your access rule and has the link can sign in. Keep the access rule tight, and send
  the link privately.
- **Trust left on the phone after the session.** Use the checklist above.

## 4. Troubleshooting

| Symptom | Fix |
|---|---|
| Browser can't reach the `ts.net` address | Is the consultant's device signed in to the tailnet and allowed by the access rule? Is the laptop online (`tailscale status`)? |
| HTTPS or certificate error | Turn on MagicDNS and HTTPS Certificates in the admin console. |
| "502 Bad Gateway" | ISDi isn't running on the laptop. |
| "Access denied" | The link is from an earlier run. Use the link from the current `isdi run`. |
| PhoneView tab: "Same-origin browser required" | The PhoneView address doesn't match. Set `ISDI_PHONEVIEW_PUBLIC_URL` to the address in the tab, and restart ISDi. |
| PhoneView tab: "Another browser controls this phone" | Close the other PhoneView tab; only one can control the phone. |
| PhoneView shows no video | Open it over `https://` (the `ts.net` address); browsers only decode video on HTTPS or `localhost` pages. |
| PhoneView button is greyed out | Run `pip install "isdi-scanner[phoneview]"` with the same Python as ISDi (3.11+), then restart ISDi. |
| Laptop disappears from the tailnet after months | Key expiry: disable it for the laptop in the admin console. |

To stop remote access entirely: `tailscale serve reset`.
