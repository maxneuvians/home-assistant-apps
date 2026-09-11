# Installation and use

1. Commit and push the repository to GitHub.
2. In Home Assistant, open **Settings → Apps → App store**, open the three-dot
   menu, and select **Check for updates**. Older versions call these Add-ons.
3. Find **ADS-B Radar** in this repository and select **Install**. The first
   installation builds the image on your Intel mini PC and can take several minutes.
4. Open **Configuration**, set `vrs_password` to your chosen admin password, and save.
   The username defaults to `admin`. The app will explain in its log if a required
   value is missing.
5. The receiver location is read from Home Assistant automatically. Add both
   `latitude` and `longitude` only if you want to override it.
6. Start the app. Enable **Start on boot**, **Watchdog**, and **Show in sidebar**.
7. Open **ADS-B Radar** in the sidebar or select **Open web UI** on the app page.

The RTL-SDR receiver must be plugged into the HAOS machine and available exclusively
for this app. Stop any other app that uses the same dongle. An antenna suitable for
1090 MHz is required for useful reception.

## Configuration

| Option | Default | Purpose |
| --- | --- | --- |
| `device_serial` | empty | Uses the first connected RTL-SDR. Optionally enter a serial number to select a specific dongle; keep it quoted in YAML. |
| `gain` | `-10` | RTL-SDR automatic gain. Set 0–49.6 for a fixed gain in dB; dump1090 selects a supported tuner step. |
| `ppm` | `0` | Frequency correction in parts per million. |
| `latitude` | Home Assistant | Optional receiver latitude override, from -90 to 90. Supply with longitude. |
| `longitude` | Home Assistant | Optional receiver longitude override, from -180 to 180. Supply with latitude. |
| `vrs_username` | `admin` | VRS Web Admin account, separate from your Home Assistant login. |
| `vrs_password` | empty | Required before startup. Choose your own password. |

Restart the app after changing these options. Coordinates update the VRS receiver
location and initial map center at startup; an existing browser's saved map view
may take precedence. When coordinates are omitted, the app reads Home Assistant's
configured home location through its internal API at each startup and applies it
to both dump1090 and VRS. No API token needs to be entered manually. Restart the
app after changing the home location in Home Assistant. If the API cannot supply
valid coordinates after three attempts, startup stops with an explanatory error;
manual coordinates bypass the lookup.

The app creates the VRS receiver connection on first startup:

- Format: **Beast**
- Address: **127.0.0.1**
- Port: **30005**

VRS connects automatically. There is no need to enable a separate dump1090 app.
The map uses VRS's Leaflet provider, so a Google Maps API key is not required.
Map tiles and optional aircraft metadata need internet access.

## VRS administration and persistence

The map is reached through your authenticated Home Assistant session. VRS's
Web Admin plugin additionally requires your VRS account credentials, initially
created from the username/password configured above.
Select **Administration** above the map to open it. Select **Live map** to return
to the aircraft display.

VRS configuration and its user database are stored under the app's persistent
`/data/.local/share/VirtualRadar` directory and survive restarts and upgrades.
Include this app in Home Assistant backups. Uninstalling the app can remove its data.

The configured VRS admin account is created only if that username does not already
exist. Restarts and upgrades preserve existing passwords and permissions. The
`vrs_password` option is used only when creating an account; change an existing
account's password in VRS Web Admin. Changing `vrs_username` creates another account
if it is missing; it does not delete an older account.
Use Web Admin to remove obsolete accounts. Other VRS settings remain intact.

## Networking and hardware

The frontend proxy accepts only Home Assistant's Ingress gateway. No host ports
are published. dump1090's Beast feed is bound to loopback inside the app.
VRS runs internally on port 8080; its administration interface has its own login.
The app requests USB access and Home Assistant Core API access for the location
lookup, without host networking or full hardware access.

It does not upload receiver data to FlightAware or other ADS-B feed services.
This version receives 1090 MHz ADS-B/Mode S, not 978 MHz UAT.

## Troubleshooting

- **No supported RTLSDR devices found / receiver missing:** verify the USB connection
  and serial number in **Settings → System → Hardware → All hardware**. Check
  the app logs for the devices detected by dump1090.
- **Device busy / cannot claim USB interface:** stop any other receiver app and
  restart this app. A host DVB driver can also claim an RTL2832U device; capture
  the exact log error before making host changes.
- **Map loads but has no aircraft:** allow a few minutes, check antenna placement,
  and confirm the receiver is connected in VRS Web Admin. A working decoder can
  have zero aircraft when no transmissions are in range.
- **Map is centered elsewhere:** check Home Assistant's home location (or set
  both override coordinates) and reset the map's saved
  browser view, or move the map manually.
- **Sidebar gives a 502:** check the app logs for a VRS or Mono startup error.
- **Sidebar says "Bad Request (Invalid host)":** update to 0.1.1 or later, which
  normalizes duplicate slashes in Ingress paths, then reload the sidebar page.
- **Startup says "User Already Exists":** update to 0.1.2 or later. Existing
  accounts are reused; you do not need to delete the user database or reinstall.
- **App stops:** all three services are supervised together. If one exits, the
  app stops so Home Assistant's enabled Watchdog can restart it.

## Development

Build on an Intel Docker host, or an ARM host with amd64 emulation:

```sh
docker build --platform linux/amd64 -t ha-adsb-radar:0.1.2 adsb_radar
python3 -m unittest discover -s adsb_radar/tests
```

For an ARM host where Mono's JIT fails under amd64 emulation, add
`--build-arg MONO_ENV_OPTIONS=--interp` to the build command. This is a local
testing workaround; it is not needed for normal installation on Intel HAOS.

Run the container smoke test without a real receiver or persistent data mount:

```sh
docker run --rm --platform linux/amd64 \
  -v "$PWD/adsb_radar/tests:/tests:ro" \
  ha-adsb-radar:0.1.2 python3 /tests/smoke.py
```

On an ARM test host, also pass `-e MONO_ENV_OPTIONS=--interp` to `docker run`.
The smoke test runs dump1090 in network-only mode, injects synthetic ADS-B
messages, and verifies they appear in VRS. It also checks proxy access control,
map scripts, duplicate-slash Ingress paths, Web Admin authentication, restart with
the existing user database, and clean shutdown. Its temporary proxy
access change applies only inside the disposable test container.

The amd64 image build, smoke test (under emulation), and configuration unit tests
passed during development. Physical USB reception and the actual HAOS sidebar
remain to be verified on the target machine.

The dump1090 source is pinned to a commit. VRS 2.4.4 and Web Admin 2.4.1 downloads
are checksum-verified. If upstream replaces those downloads, builds deliberately
fail until the replacements are reviewed and the checksums updated.

Upstream references:

- [VRS on Linux / Mono](https://www.virtualradarserver.co.uk/Mono.aspx)
- [VRS downloads](https://www.virtualradarserver.co.uk/Download.aspx)
- [Home Assistant Ingress](https://developers.home-assistant.io/docs/apps/presentation/#ingress)
- [Home Assistant internal API](https://developers.home-assistant.io/docs/apps/communication/#home-assistant-core)
- [Home Assistant app configuration](https://developers.home-assistant.io/docs/apps/configuration/)
