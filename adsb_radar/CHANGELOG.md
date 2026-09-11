# Changelog

## 0.1.2

- Reuse existing VRS accounts on restart and upgrade instead of invoking
  `-createAdmin` for a username that already exists.
- Check the persistent user database read-only, preserving passwords and permissions.
- Test restart and authentication with the same saved user database.

## 0.1.1

- Normalize duplicate slashes in Ingress request paths before forwarding to VRS,
  fixing Mono's "Bad Request (Invalid host)" error when opening the sidebar.
- Cover duplicate-slash URLs and Home Assistant proxy headers in the container
  smoke test.

## 0.1.0

- Initial experimental amd64 app with dump1090, Virtual Radar Server 2.4.4,
  and Web Admin 2.4.1.
- Use the first RTL-SDR by default, with optional serial selection.
- Read receiver coordinates from Home Assistant automatically, with manual overrides.
- Add Home Assistant Ingress and ADS-B Radar sidebar entry.
- Persist VRS settings and expose gain, frequency correction, location, and
  administration credentials in app configuration.
