"""Coordinator for the Trinity integration."""

from __future__ import annotations

import asyncio
import io
import logging
from typing import TYPE_CHECKING

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.storage import Store

from .const import (
    CONF_TOPIC,
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
        self._store = Store(hass, STORAGE_VERSION, f"trinity_{entry.entry_id}")

        # Persisted default — replayed on startup and after display_for reverts
        self._default_mode: str | None = None
        self._default_attrs: dict = {}

        # Cancel handle for display_for revert timer
        self._revert_unsub = None

        # Running stream task (if any)
        self._stream_task: asyncio.Task | None = None  # type: ignore[type-arg]

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
        elif mode == DISPLAY_MODE_IMAGE:
            path = attrs.get("path")
            entity_id = attrs.get("entity_id")
            if path or entity_id:
                await self.do_display_image(path=path, entity_id=entity_id, set_default=False)

    # ------------------------------------------------------------------
    # Stream

    def cancel_stream(self) -> None:
        """Cancel any in-progress stream."""
        if self._stream_task and not self._stream_task.done():
            self._stream_task.cancel()
        self._stream_task = None

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
            _LOGGER.debug("display_now_playing: skipping %s — no art or metadata", entity_id)
            return

        img: Image.Image | None = None
        if picture:
            img = await self._fetch_image_url(picture)

        if img is None:
            img = Image.new("RGB", (_SIZE, _SIZE), (0, 0, 0))

        img = await self.hass.async_add_executor_job(crop_and_resize, img)
        await self.hass.async_add_executor_job(apply_now_playing_overlay, img, title, artist)
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
        """Push an image from a file path or camera entity."""
        self.cancel_stream()
        from PIL import Image
        from tottie.image import crop_and_resize, to_rgb565

        img: Image.Image | None = None

        if path:
            img = await self.hass.async_add_executor_job(lambda: Image.open(path).convert("RGB"))
        elif entity_id:
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

    async def do_display_stream(self, entity_id: str, stream_for: float) -> None:
        """Stream camera snapshots to the display for the given duration."""
        self.cancel_stream()
        self.cancel_revert()
        self._stream_task = self.hass.async_create_task(self._stream_loop(entity_id, stream_for))

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

    async def _stream_loop(self, entity_id: str, stream_for: float) -> None:
        from tottie.image import crop_and_resize, to_rgb565

        deadline = asyncio.get_event_loop().time() + stream_for
        frames = 0
        completed = False

        try:
            while asyncio.get_event_loop().time() < deadline:
                frame_start = asyncio.get_event_loop().time()
                img = await self._snapshot_camera(entity_id)
                if img is not None:
                    img = await self.hass.async_add_executor_job(crop_and_resize, img)
                    await self._publish(to_rgb565(img))
                    frames += 1
                elapsed = asyncio.get_event_loop().time() - frame_start
                await asyncio.sleep(max(0, 0.15 - elapsed))
            completed = True
        except asyncio.CancelledError:
            pass
        finally:
            self._stream_task = None
            _LOGGER.info(
                "display_stream: %s — %d frames sent",
                "completed" if completed else "cancelled",
                frames,
            )

        if completed:
            await self._replay_default()
