# Home Assistant Apps

Personal apps (formerly called add-ons) for Home Assistant OS, maintained by Max Neuvians.

## Register this repository

Commit and push these files to GitHub before adding the repository to Home Assistant.
The repository must be accessible to your Home Assistant instance.

[![Add repository to Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fmaxneuvians%2Fhome-assistant-apps)

Alternatively:

1. In Home Assistant, open **Settings → Apps → App store** (called **Add-ons → Add-on store** in older versions).
2. Open the three-dot menu and select **Repositories**.
3. Add `https://github.com/maxneuvians/home-assistant-apps`.

## Available apps

| App | Hardware | Description |
| --- | --- | --- |
| [ADS-B Radar](adsb_radar/README.md) | Intel/AMD 64-bit with USB RTL-SDR | dump1090 and Virtual Radar Server, with a Home Assistant sidebar map. |

See the [ADS-B Radar installation guide](adsb_radar/DOCS.md) for setup.

## Add an app

Create a separate directory for each app, with its own `config.yaml` and the files
needed to build or run it. For example, an app built from source could use:

```text
repository.yaml
my_app/
  config.yaml
  Dockerfile
  README.md
  DOCS.md
  CHANGELOG.md
```

The root `repository.yaml` describes this repository. Each app's `config.yaml`
describes the individual app, including its name, slug, version, and supported
architectures. Follow the official tutorial to create a working app, then commit
and push its files and refresh the Home Assistant app store. Increment the app's
version when publishing updates.

- [Create an app repository](https://developers.home-assistant.io/docs/apps/repository/)
- [Tutorial: Making your first app](https://developers.home-assistant.io/docs/apps/tutorial/)
- [App configuration reference](https://developers.home-assistant.io/docs/apps/configuration/)

## License

[MIT](LICENSE)
