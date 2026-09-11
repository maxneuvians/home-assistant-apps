# ADS-B Radar

A Home Assistant OS app for Intel/AMD 64-bit hardware, combining
[FlightAware dump1090](https://github.com/flightaware/dump1090) and
[Virtual Radar Server](https://www.virtualradarserver.co.uk/).

The app decodes a USB RTL-SDR receiver and displays aircraft through Home
Assistant Ingress. Enable **Show in sidebar** to open **ADS-B Radar** directly
from Home Assistant.

By default, the app uses the first connected RTL-SDR and Home Assistant's configured
home location. An optional serial number selects a specific receiver when multiple
dongles are connected. Manual coordinates can override the home location.

See [DOCS.md](DOCS.md) for installation, configuration, and troubleshooting.
This first release is experimental pending testing with the physical receiver
and Home Assistant Ingress on HAOS.
