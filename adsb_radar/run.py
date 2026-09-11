"""Configure and supervise the receiver, VRS, and Home Assistant Ingress proxy."""
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET


def validate_options(options):
    for key in ("device_serial", "vrs_username", "vrs_password"):
        if not isinstance(options.get(key), str) or (key != "device_serial" and not options[key].strip()):
            raise ValueError(f"Set {key} in the app Configuration tab before starting.")
        if any(c in options[key] for c in ("\0", "\r", "\n")):
            raise ValueError(f"{key} must not contain control characters.")
    for key, low, high in (("gain", -10, 49.6), ("ppm", -200, 200),
                           ("latitude", -90, 90), ("longitude", -180, 180)):
        if key not in options and key in ("latitude", "longitude"):
            continue
        value = options.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{key} must be a number.")
        if not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f"{key} must be between {low} and {high}.")
    if int(options["ppm"]) != options["ppm"]:
        raise ValueError("ppm must be a whole number.")
    if ("latitude" in options) != ("longitude" in options):
        raise ValueError("Supply both latitude and longitude, or neither.")
    if options["gain"] < 0 and options["gain"] != -10:
        raise ValueError("Use -10 for automatic gain, or a gain between 0 and 49.6 dB.")


def resolve_location(options):
    """Use explicit coordinates, otherwise read HA's configured home location."""
    if "latitude" in options and "longitude" in options:
        return options
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        raise ValueError("Home Assistant location lookup needs SUPERVISOR_TOKEN. "
                         "For standalone use, set both latitude and longitude.")
    request = urllib.request.Request(
        "http://supervisor/core/api/config",
        headers={"Authorization": "Bearer " + token, "Accept": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                config = json.load(response)
            if not isinstance(config, dict):
                raise ValueError("Unexpected Home Assistant configuration response.")
            resolved = dict(options, latitude=config.get("latitude"), longitude=config.get("longitude"))
            validate_options(resolved)
            print("Using Home Assistant's configured receiver location.", flush=True)
            return resolved
        except (OSError, urllib.error.URLError, ValueError):
            # Core may still be becoming ready at boot. Do not print API bodies or tokens.
            if attempt < 2:
                print("Home Assistant location unavailable; retrying.", flush=True)
                time.sleep(2)
    raise ValueError("Could not read Home Assistant latitude/longitude. "
                     "Check that Home Assistant is running and its home location is set, "
                     "or configure both latitude and longitude in this app.")


def dump1090_command(options):
    command = ["/usr/local/bin/dump1090", "--device", options["device_serial"].strip() or "0",
               "--gain", str(options["gain"]), "--ppm", str(options["ppm"]),
               "--net", "--net-bind-address", "127.0.0.1",
               "--net-bo-port", "30005", "--net-bi-port", "0",
               "--net-ro-port", "0", "--net-ri-port", "0", "--net-sbs-port", "0",
               "--quiet"]
    if "latitude" in options:
        command += ["--lat", str(options["latitude"]), "--lon", str(options["longitude"])]
    return command


def set_text(parent, name, value):
    child = parent.find(name)
    if child is None:
        child = ET.SubElement(parent, name)
    child.text = str(value)


def configure_location(path, options):
    """Update only the HA-managed receiver location; retain VRS user settings."""
    if "latitude" not in options:
        return
    tree = ET.parse(path)
    root = tree.getroot()
    locations = root.find("ReceiverLocations")
    if locations is None:
        locations = ET.SubElement(root, "ReceiverLocations")
    location = next((loc for loc in locations if loc.findtext("Name") == "HAOS receiver"), None)
    if location is None:
        used_ids = [int(loc.findtext("UniqueId", "0")) for loc in locations]
        location = ET.SubElement(locations, "ReceiverLocation")
        set_text(location, "UniqueId", max(used_ids, default=0) + 1)
        set_text(location, "Name", "HAOS receiver")
    for name, key in (("Latitude", "latitude"), ("Longitude", "longitude")):
        set_text(location, name, options[key])
    for receiver in root.findall("./Receivers/Receiver"):
        if receiver.findtext("UniqueId") == "1":
            set_text(receiver, "ReceiverLocationId", location.findtext("UniqueId"))
    settings = root.find("GoogleMapSettings")
    set_text(settings, "InitialMapLatitude", options["latitude"])
    set_text(settings, "InitialMapLongitude", options["longitude"])
    temporary = path.with_suffix(".tmp")
    tree.write(temporary, encoding="utf-8", xml_declaration=True)
    temporary.replace(path)


def main():
    os.umask(0o077)
    options = json.loads(Path("/data/options.json").read_text())
    validate_options(options)
    options = resolve_location(options)
    folder = Path("/data/.local/share/VirtualRadar")
    folder.mkdir(parents=True, exist_ok=True)
    config = folder / "Configuration.xml"
    subprocess.run(["mono", "/opt/vrs/Configure.exe", str(config)], check=True)
    configure_location(config, options)
    (folder / "InstallerConfiguration.xml").write_text(
        '<InstallerSettings><WebServerPort>8080</WebServerPort></InstallerSettings>')
    subprocess.run(["nginx", "-t"], check=True)

    children = []
    stopping = False

    def stop(signum, frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        commands = [
            ("dump1090", dump1090_command(options)),
            ("Virtual Radar Server", ["mono", "/opt/vrs/VirtualRadar.exe", "-nogui",
              "-createAdmin:" + options["vrs_username"], "-password:" + options["vrs_password"]]),
            ("Ingress proxy", ["nginx", "-g", "daemon off;"]),
        ]
        for name, command in commands:
            if stopping:
                break
            print(f"Starting {name}.", flush=True)
            # Never log argv: VRS's documented account setup uses a password argument.
            children.append((name, subprocess.Popen(command, start_new_session=True)))
        while not stopping:
            for name, process in children:
                code = process.poll()
                if code is not None:
                    print(f"{name} exited (status {code}); stopping app. Check the logs above.",
                          file=sys.stderr, flush=True)
                    return 1
            time.sleep(0.5)
        return 0
    finally:
        for _, process in children:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
        deadline = time.monotonic() + 7
        for _, process in children:
            try:
                process.wait(timeout=max(0.1, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"Startup failed: {error}", file=sys.stderr)
        sys.exit(1)
