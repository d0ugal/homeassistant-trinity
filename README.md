# homeassistant-trinity

A Home Assistant custom integration for [Trinity](https://esp32trinity.com/) Hub75 LED matrix
displays, built around automation-driven image display. Pushes images over MQTT as raw RGB565
pixel data with no cloud dependencies.

---

## Features

- **Moon phase display** — renders a real-time moon phase image using your HA home location
- **Now playing** — shows album art with track/artist overlay from any HA media player
- **Display any image** — send a PNG, JPG, or camera snapshot; automatically centre-cropped and resized to 64×64
- **Camera streaming** — stream live camera snapshots at ~6 FPS
- **Automation-friendly** — all display modes are triggered by service calls; schedule and combine them however you like
- **Temporary displays** — `display_for` reverts back to the previous default after a set number of seconds
- **Persistent default** — the last permanent display call is saved to disk and replayed on HA restart

---

## Previews

**Moon phase** — new moon through to waning crescent, rendered from London at 6× zoom. The top pixel row is a lunar cycle progress bar; the ring indicator shows the moon's current position in the sky.

![Moon phases across the full cycle](docs/moon_phases.png)

**Now playing** — album art centre-cropped to 64×64 with pixel-font track and artist overlay.

![Now playing — album art with track and artist overlay](docs/now_playing.png)

---

## Installation

Install via [HACS](https://hacs.xyz/) by adding this repository as a custom repository,
or copy `custom_components/trinity/` into your HA `config/custom_components/` directory
and restart Home Assistant.

The HA **MQTT integration** must be set up first — Trinity uses it to publish pixel data.

Add the integration via **Settings → Devices & Services → Add Integration → Trinity**.
You will be asked for the MQTT topic the display subscribes to (default: `trinity-matrix/image`).

---

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

---

## Services

### `trinity.display_moon`

Renders the current moon phase (using your HA home lat/lon/elevation) and pushes it to
the display. Becomes the new default.

```yaml
action: trinity.display_moon
```

### `trinity.display_now_playing`

Fetches album art from a media player entity and overlays scrolling track and artist text.
Becomes the new default.

```yaml
action: trinity.display_now_playing
data:
  entity_id: media_player.spotify_dougal_matthews
```

### `trinity.display_image`

Pushes any image or camera snapshot. Centre-cropped and resized to 64×64. Becomes the
new default unless `display_for` is set.

```yaml
action: trinity.display_image
data:
  path: /config/www/doorbell.jpg
  display_for: 30
```

### `trinity.display_stream`

Repeatedly snapshots a camera entity and pushes frames at ~6 FPS. Reverts to the default
display when the duration elapses or another display action is triggered.

```yaml
action: trinity.display_stream
data:
  entity_id: camera.front_door
  stream_for: 30
```

### `trinity.clear`

Publishes an empty payload, causing the display to fall back to its built-in clock.

```yaml
action: trinity.clear
```
