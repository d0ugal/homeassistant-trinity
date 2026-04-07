# homeassistant-trinity

Home Assistant custom integration for [Trinity](https://esp32trinity.com/) Hub75 LED matrix displays.

Trinity is an ESP32-based controller for 64×64 HUB75 LED matrix panels. This integration
pushes images to the display over MQTT as raw RGB565 pixel data.

## Screenshots

| Moon phase | Now playing |
|---|---|
| ![Moon phase](docs/moon_phases.png) | ![Now playing](docs/now_playing.png) |

## Features

- **Moon phase** — renders the current moon phase using [tottie](https://github.com/d0ugal/tottie), accounting for location, altitude, and orientation
- **Now playing** — fetches album art from any media player entity and overlays scrolling track and artist text
- **Image push** — push any image file or camera snapshot to the display
- **Camera stream** — stream live camera snapshots at ~6 FPS
- **Clear** — send an empty payload so the display falls back to its built-in clock

## Installation

Install via [HACS](https://hacs.xyz/) by adding this repository as a custom repository,
or copy `custom_components/trinity/` into your HA config directory.

The HA **MQTT integration** must be set up first — Trinity uses it to publish pixel data.

## Configuration

Add the integration via **Settings → Devices & Services → Add Integration → Trinity**.

You will be asked for the MQTT topic the display subscribes to (default: `trinity-matrix/image`).

## ESPHome firmware

A ready-to-use ESPHome configuration is provided in [`esphome/trinity-matrix.yaml`](esphome/trinity-matrix.yaml).

It subscribes to the configured MQTT topic, receives raw RGB565 pixel data (8192 bytes for a
64×64 image), and renders it directly to the HUB75 panel via the
[`hub75` component](https://esphome.io/components/display/hub75.html).

Add the following to your ESPHome `secrets.yaml`:

```yaml
trinity_matrix_api_key: "<your-api-key>"
mqtt_broker: "10.10.10.x"
```

## Services

| Service | Description |
|---|---|
| `trinity.display_moon` | Render and push the current moon phase |
| `trinity.display_now_playing` | Push album art + overlay from a media player |
| `trinity.display_image` | Push a file path or camera snapshot |
| `trinity.display_stream` | Stream a camera entity for N seconds |
| `trinity.clear` | Clear the display (falls back to built-in clock) |
