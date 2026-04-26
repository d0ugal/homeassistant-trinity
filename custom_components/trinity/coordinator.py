"""Coordinator for the Trinity integration."""

from __future__ import annotations

import asyncio
import io
import logging
import os
from typing import TYPE_CHECKING

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.storage import Store

from .const import (
    CONF_TOPIC,
    DISPLAY_MODE_EMOJI,
    DISPLAY_MODE_IMAGE,
    DISPLAY_MODE_MOON,
    DISPLAY_MODE_NOW_PLAYING,
    STORAGE_VERSION,
)

if TYPE_CHECKING:
    from PIL import Image

_LOGGER = logging.getLogger(__name__)

_SIZE = 64


class TrinityCoordinator:
    """Manages rendering and MQTT publishing for a Trinity display."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self._topic: str = entry.data[CONF_TOPIC]
        # Brightness topic shares the same base path: "a/b/image" -> "a/b/brightness"
        self._brightness_topic: str = self._topic.rsplit("/", 1)[0] + "/brightness"
        self._store = Store(hass, STORAGE_VERSION, f"trinity_{entry.entry_id}")

        # Persisted default — replayed on startup and after display_for reverts
        self._default_mode: str | None = None
        self._default_attrs: dict = {}

        # Cancel handle for display_for revert timer
        self._revert_unsub = None

        # Running stream task (if any)
        self._stream_task: asyncio.Task | None = None  # type: ignore[type-arg]

        # Optional callback fired when a do_display_url stream ends naturally
        self._stream_end_cb: object = None

    # ------------------------------------------------------------------
    # Persistence

    async def async_load_and_replay(self) -> None:
        """Load persisted default on startup and push it to the display."""
        stored = await self._store.async_load() or {}
        self._default_mode = stored.get("mode")
        self._default_attrs = stored.get("attrs", {})
        if self._default_mode:
            _LOGGER.info("Replaying persisted default: %s", self._default_mode)
            await self._replay_default()

    async def _save(self) -> None:
        await self._store.async_save(
            {
                "mode": self._default_mode,
                "attrs": self._default_attrs,
            }
        )

    # ------------------------------------------------------------------
    # Revert timer

    def cancel_revert(self) -> None:
        if self._revert_unsub:
            self._revert_unsub()
            self._revert_unsub = None

    def schedule_revert(self, seconds: float) -> None:
        """Revert to the default display after `seconds`."""
        self.cancel_revert()

        @callback
        def _cb(_now) -> None:
            self.hass.async_create_task(self._replay_default())

        self._revert_unsub = async_call_later(self.hass, seconds, _cb)

    async def _replay_default(self) -> None:
        """Re-push the stored default display."""
        self._revert_unsub = None
        mode = self._default_mode
        attrs = self._default_attrs
        if mode == DISPLAY_MODE_MOON:
            await self.do_display_moon(set_default=False)
        elif mode == DISPLAY_MODE_NOW_PLAYING:
            entity_id = attrs.get("entity_id")
            if entity_id:
                await self.do_display_now_playing(entity_id, set_default=False)
        elif mode == DISPLAY_MODE_EMOJI:
            char = attrs.get("char")
            if char:
                await self.do_display_emoji(char, set_default=False)
        elif mode == DISPLAY_MODE_IMAGE:
            path = attrs.get("path")
            entity_id = attrs.get("entity_id")
            if path or entity_id:
                await self.do_display_image(
                    path=path, entity_id=entity_id, set_default=False
                )

    # ------------------------------------------------------------------
    # Stream

    # ------------------------------------------------------------------
    # Crop helpers

    _CROP_ENTITY = "input_select.trinity_crop"

    def _get_crop(self) -> str:
        state = self.hass.states.get(self._CROP_ENTITY)
        return state.state if state else "center"

    async def _set_crop(self, crop: str) -> None:
        await self.hass.services.async_call(
            "input_select",
            "select_option",
            {"entity_id": self._CROP_ENTITY, "option": crop},
        )

    async def _reset_crop(self) -> None:
        await self._set_crop("center")

    @staticmethod
    async def _crop_and_resize(hass, img, size: int, crop: str):
        """crop_and_resize wrapper that handles edge anchors tottie doesn't know."""
        from tottie.image import crop_and_resize

        if crop in ("top", "bottom", "left", "right"):

            def _edge_crop(img=img, crop=crop):
                w, h = img.size
                d = min(w, h)
                if crop == "top":
                    box = ((w - d) // 2, 0, (w + d) // 2, d)
                elif crop == "bottom":
                    box = ((w - d) // 2, h - d, (w + d) // 2, h)
                elif crop == "left":
                    box = (0, (h - d) // 2, d, (h + d) // 2)
                else:  # right
                    box = (w - d, (h - d) // 2, w, (h + d) // 2)
                return img.crop(box)

            img = await hass.async_add_executor_job(_edge_crop)
            crop = "center"

        return await hass.async_add_executor_job(crop_and_resize, img, size, crop)

    def cancel_stream(self, _fire_callback: bool = True) -> None:
        """Cancel any in-progress stream."""
        if self._stream_task and not self._stream_task.done():
            self._stream_task.cancel()
        self._stream_task = None
        cb = self._stream_end_cb
        self._stream_end_cb = None
        if _fire_callback and cb:
            cb()  # type: ignore[operator]

    def set_stream_end_callback(self, cb: object) -> None:
        self._stream_end_cb = cb

    async def do_display_url(self, url: str) -> None:
        """Stream any URL indefinitely via PyAV (used by the media player)."""
        # Keep any running stream (e.g. display_stream) alive as a bridge until
        # the first PyAV frame arrives, so the display isn't blank during startup.
        bridge = self._stream_task if (self._stream_task and not self._stream_task.done()) else None
        self._stream_task = None  # detach without cancelling
        self.cancel_revert()
        _LOGGER.info("display_url: received URL, starting stream task")
        self._stream_task = self.hass.async_create_task(self._stream_loop_url(url, bridge=bridge))

    async def _stream_loop_url(self, url: str, bridge: asyncio.Task | None = None) -> None:
        import queue as stdlib_queue
        import threading
        import time

        from tottie.image import to_rgb565

        t0 = time.monotonic()
        frame_q: stdlib_queue.Queue = stdlib_queue.Queue(maxsize=2)
        stop_event = threading.Event()

        def _reader() -> None:
            import av

            try:
                _LOGGER.info("display_url: opening stream (t=%.2fs)", time.monotonic() - t0)
                container = av.open(url, options={"stimeout": "5000000"})
                _LOGGER.info(
                    "display_url: stream opened, decoding first frame (t=%.2fs)",
                    time.monotonic() - t0,
                )
                for frame in container.decode(video=0):
                    if stop_event.is_set():
                        break
                    img = frame.to_image().convert("RGB")
                    if frame_q.full():
                        try:
                            frame_q.get_nowait()
                        except stdlib_queue.Empty:
                            pass
                    frame_q.put_nowait(img)
            except Exception as exc:
                _LOGGER.warning("Stream reader error (%s): %s", url, exc)
            finally:
                try:
                    frame_q.put_nowait(None)
                except stdlib_queue.Full:
                    pass

        thread = threading.Thread(target=_reader, daemon=True)
        thread.start()

        loop = asyncio.get_running_loop()
        this_task = asyncio.current_task()
        crop = self._get_crop()
        frames = 0
        completed = False
        last_publish = 0.0
        min_interval = 0.1  # cap at 10fps to avoid burst flooding from HLS segments

        try:
            while True:
                try:
                    img = frame_q.get_nowait()
                except stdlib_queue.Empty:
                    await asyncio.sleep(0.01)
                    continue
                if img is None:
                    completed = True
                    break
                if frames == 0:
                    _LOGGER.info(
                        "display_url: first frame received from queue (t=%.2fs)",
                        time.monotonic() - t0,
                    )
                    if bridge and not bridge.done():
                        bridge.cancel()
                now = loop.time()
                if now - last_publish < min_interval:
                    continue  # drop frame, too soon since last publish
                img = await self._crop_and_resize(self.hass, img, 64, crop)
                await self._publish(to_rgb565(img))
                if frames == 0:
                    _LOGGER.info(
                        "display_url: first frame published to display (t=%.2fs)",
                        time.monotonic() - t0,
                    )
                last_publish = loop.time()
                frames += 1
        except asyncio.CancelledError:
            pass
        finally:
            stop_event.set()
            if self._stream_task is this_task:
                self._stream_task = None
                await self._reset_crop()
            _LOGGER.info(
                "display_url: stopped after %d frames (t=%.2fs)", frames, time.monotonic() - t0
            )

        if completed:
            cb = self._stream_end_cb
            self._stream_end_cb = None
            if cb:
                cb()  # type: ignore[operator]

    # ------------------------------------------------------------------
    # Display services

    async def do_display_moon(
        self,
        display_for: float | None = None,
        set_default: bool = True,
    ) -> None:
        """Render the current moon phase and publish it."""
        self.cancel_stream()
        from tottie.image import to_rgb565
        from tottie.moon import render_image

        lat = str(self.hass.config.latitude)
        lon = str(self.hass.config.longitude)
        elev = int(self.hass.config.elevation or 0)

        img = await self.hass.async_add_executor_job(render_image, lat, lon, elev)
        img = img.convert("L").convert("RGB")
        await self._publish(to_rgb565(img))

        if set_default and not display_for:
            self._default_mode = DISPLAY_MODE_MOON
            self._default_attrs = {}
            await self._save()

        if display_for:
            self.schedule_revert(display_for)
        else:
            self.cancel_revert()

        _LOGGER.info("display_moon: published")

    async def do_display_now_playing(
        self,
        entity_id: str,
        display_for: float | None = None,
        set_default: bool = True,
    ) -> None:
        """Fetch album art from a media player and publish with overlay."""
        self.cancel_stream()
        from PIL import Image
        from tottie.image import crop_and_resize, to_rgb565
        from tottie.overlay import apply_now_playing_overlay

        state = self.hass.states.get(entity_id)
        if not state:
            _LOGGER.warning("display_now_playing: entity %s not found", entity_id)
            return

        title = str(state.attributes.get("media_title") or "")
        artist = str(state.attributes.get("media_artist") or "")
        picture: str = str(state.attributes.get("entity_picture") or "")

        if not picture and not title and not artist:
            _LOGGER.debug(
                "display_now_playing: skipping %s — no art or metadata", entity_id
            )
            return

        img: Image.Image | None = None
        if picture:
            img = await self._fetch_image_url(picture)

        if img is None:
            img = Image.new("RGB", (_SIZE, _SIZE), (0, 0, 0))

        img = await self.hass.async_add_executor_job(crop_and_resize, img)
        await self.hass.async_add_executor_job(
            apply_now_playing_overlay, img, title, artist
        )
        await self._publish(to_rgb565(img))

        if set_default and not display_for:
            self._default_mode = DISPLAY_MODE_NOW_PLAYING
            self._default_attrs = {"entity_id": entity_id}
            await self._save()

        if display_for:
            self.schedule_revert(display_for)
        else:
            self.cancel_revert()

        _LOGGER.info("display_now_playing: published — %s by %s", title, artist)

    async def do_display_image(
        self,
        path: str | None = None,
        entity_id: str | None = None,
        display_for: float | None = None,
        set_default: bool = True,
    ) -> None:
        """Push an image from a file path, camera entity, or image entity."""
        self.cancel_stream()
        from PIL import Image
        from tottie.image import crop_and_resize, to_rgb565

        img: Image.Image | None = None

        if path:
            img = await self.hass.async_add_executor_job(
                lambda: Image.open(path).convert("RGB")
            )
        elif entity_id:
            domain = entity_id.split(".")[0]
            if domain == "image":
                img = await self._snapshot_image_entity(entity_id)
            else:
                img = await self._snapshot_camera(entity_id)

        if img is None:
            _LOGGER.warning("display_image: no image source provided or fetch failed")
            return

        img = await self.hass.async_add_executor_job(crop_and_resize, img)
        await self._publish(to_rgb565(img))

        if set_default and not display_for:
            self._default_mode = DISPLAY_MODE_IMAGE
            self._default_attrs = {"path": path} if path else {"entity_id": entity_id}
            await self._save()

        if display_for:
            self.schedule_revert(display_for)
        else:
            self.cancel_revert()

        _LOGGER.info("display_image: published %s", entity_id or path)

    async def do_display_stream(
        self, entity_id: str, stream_for: float, crop: str = "center"
    ) -> None:
        """Stream camera snapshots to the display for the given duration."""
        self.cancel_stream()
        self.cancel_revert()
        await self._set_crop(crop)
        self._stream_task = self.hass.async_create_task(
            self._stream_loop(entity_id, stream_for, crop)
        )

    async def do_display_emoji(
        self,
        emoji_input: str,
        display_for: float | None = None,
        set_default: bool = True,
        line1: str | None = None,
        line2: str | None = None,
        corner: str | None = None,
    ) -> None:
        """Fetch a Twemoji PNG, resize to 64x64, and publish."""
        self.cancel_stream()
        import aiohttp
        import emoji as emoji_lib
        from homeassistant.helpers.aiohttp_client import async_get_clientsession

        raw = emoji_input.strip()
        if emoji_lib.is_emoji(raw):
            char = raw
        else:
            name = raw.strip(":")
            char = emoji_lib.emojize(f":{name}:", language="alias")
            if not emoji_lib.is_emoji(char):
                _LOGGER.error("display_emoji: unknown emoji %r", emoji_input)
                return

        # Build Twemoji filename: codepoints joined by "-", skipping U+FE0F
        codepoints = "-".join(f"{ord(c):x}" for c in char if c != "\ufe0f")
        cache_dir = self.hass.config.path(".storage", "trinity_emoji_cache")
        png_path = os.path.join(cache_dir, f"emoji_{codepoints}.png")

        if not os.path.exists(png_path):
            base_url = "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72"
            session = async_get_clientsession(self.hass)

            png_data: bytes | None = None
            for candidate in [codepoints, codepoints.replace("-fe0f", "")]:
                try:
                    async with session.get(
                        f"{base_url}/{candidate}.png",
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        if resp.status == 200:
                            png_data = await resp.read()
                            break
                except Exception as exc:
                    _LOGGER.debug("display_emoji: fetch attempt failed: %s", exc)

            if not png_data:
                _LOGGER.error(
                    "display_emoji: could not fetch Twemoji for %r (%s)",
                    char,
                    codepoints,
                )
                return

            def _render_png() -> None:
                from PIL import Image as PilImage

                img = PilImage.open(io.BytesIO(png_data)).convert("RGBA")
                bg = PilImage.new("RGB", img.size, (0, 0, 0))
                bg.paste(img, mask=img.split()[3])
                resized = bg.resize((_SIZE, _SIZE), PilImage.LANCZOS)
                os.makedirs(cache_dir, exist_ok=True)
                resized.save(png_path, format="PNG")

            await self.hass.async_add_executor_job(_render_png)
            _LOGGER.info("display_emoji: rendered and cached %r (%s)", char, codepoints)
        else:
            _LOGGER.info("display_emoji: cache hit %r (%s)", char, codepoints)

        def _to_payload() -> bytes:
            from PIL import Image as PilImage
            from tottie.image import to_rgb565
            from tottie.overlay import apply_corner_char, apply_now_playing_overlay

            img = PilImage.open(png_path).convert("RGB")
            if line1 or line2:
                apply_now_playing_overlay(img, line1 or "", line2 or "")
            if corner:
                apply_corner_char(img, corner)
            return to_rgb565(img)

        payload = await self.hass.async_add_executor_job(_to_payload)
        await self._publish(payload)

        if set_default and not display_for:
            self._default_mode = DISPLAY_MODE_EMOJI
            self._default_attrs = {"char": char}
            await self._save()

        if display_for:
            self.schedule_revert(display_for)
        else:
            self.cancel_revert()

        _LOGGER.info("display_emoji: published %r", char)

    async def do_set_brightness(self, brightness: int) -> None:
        """Publish brightness (0-255) to the brightness MQTT topic."""
        b = max(0, min(255, brightness))
        await mqtt.async_publish(self.hass, self._brightness_topic, str(b), retain=True)
        _LOGGER.info("set_brightness: %d", b)

    async def do_clear(self) -> None:
        """Publish an empty payload, causing the display to fall back to clock."""
        self.cancel_stream()
        self.cancel_revert()
        await self._publish(b"")

    # ------------------------------------------------------------------
    # Internal helpers

    async def _publish(self, payload: bytes) -> None:
        await mqtt.async_publish(self.hass, self._topic, payload, retain=True)

    async def _fetch_image_url(self, url: str) -> Image.Image | None:
        from PIL import Image

        if url.startswith("/"):
            url = f"http://localhost:8123{url}"

        session = async_get_clientsession(self.hass)
        try:
            async with session.get(url, timeout=10) as resp:
                resp.raise_for_status()
                data = await resp.read()
            return await self.hass.async_add_executor_job(
                lambda: Image.open(io.BytesIO(data)).convert("RGB")
            )
        except Exception as exc:
            _LOGGER.warning("Failed to fetch image from %s: %s", url, exc)
            return None

    async def _snapshot_image_entity(self, entity_id: str) -> Image.Image | None:
        """Fetch the latest image from an image.* entity via its entity_picture URL."""
        state = self.hass.states.get(entity_id)
        if not state:
            _LOGGER.warning("Image entity %s not found", entity_id)
            return None
        picture = str(state.attributes.get("entity_picture") or "")
        if not picture:
            _LOGGER.warning("Image entity %s has no entity_picture", entity_id)
            return None
        return await self._fetch_image_url(picture)

    async def _snapshot_camera(self, entity_id: str) -> Image.Image | None:
        from homeassistant.components.camera import async_get_image as camera_get_image
        from PIL import Image

        try:
            camera_image = await camera_get_image(self.hass, entity_id, timeout=5)
            return await self.hass.async_add_executor_job(
                lambda: Image.open(io.BytesIO(camera_image.content)).convert("RGB")
            )
        except Exception as exc:
            _LOGGER.warning("Failed to snapshot camera %s: %s", entity_id, exc)
            return None

    async def _stream_loop(
        self, entity_id: str, stream_for: float, crop: str = "center"
    ) -> None:
        from tottie.image import to_rgb565

        this_task = asyncio.current_task()
        deadline = asyncio.get_event_loop().time() + stream_for
        frames = 0
        completed = False

        try:
            while asyncio.get_event_loop().time() < deadline:
                frame_start = asyncio.get_event_loop().time()
                img = await self._snapshot_camera(entity_id)
                if img is not None:
                    img = await self._crop_and_resize(self.hass, img, 64, crop)
                    await self._publish(to_rgb565(img))
                    frames += 1
                elapsed = asyncio.get_event_loop().time() - frame_start
                await asyncio.sleep(max(0, 0.15 - elapsed))
            completed = True
        except asyncio.CancelledError:
            pass
        finally:
            if self._stream_task is this_task:
                self._stream_task = None
                await self._reset_crop()
            _LOGGER.info(
                "display_stream: %s — %d frames sent",
                "completed" if completed else "cancelled",
                frames,
            )

        if completed:
            await self._replay_default()
