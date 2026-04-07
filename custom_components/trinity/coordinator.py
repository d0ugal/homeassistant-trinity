"""Coordinator for the Trinity integration."""

from __future__ import annotations

import asyncio
import io
import logging
from typing import TYPE_CHECKING

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_TOPIC

if TYPE_CHECKING:
    from PIL import Image

_LOGGER = logging.getLogger(__name__)

_SIZE = 64


class TrinityCoordinator:
    """Manages rendering and MQTT publishing for a Trinity display."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self._topic: str = entry.data[CONF_TOPIC]
        self._stream_task: asyncio.Task | None = None  # type: ignore[type-arg]

    # ------------------------------------------------------------------
    # Public service handlers
    # ------------------------------------------------------------------

    async def do_display_moon(self) -> None:
        """Render the current moon phase and publish it."""
        from tottie.image import to_rgb565
        from tottie.moon import render_image

        lat = str(self.hass.config.latitude)
        lon = str(self.hass.config.longitude)
        elev = int(self.hass.config.elevation)

        img = await self.hass.async_add_executor_job(render_image, lat, lon, elev)
        await self._publish(to_rgb565(img))

    async def do_display_now_playing(self, entity_id: str) -> None:
        """Fetch album art from a media player and publish with overlay."""
        from PIL import Image
        from tottie.image import crop_and_resize, to_rgb565
        from tottie.overlay import apply_now_playing_overlay

        state = self.hass.states.get(entity_id)
        if not state:
            _LOGGER.warning("Entity %s not found", entity_id)
            return

        title = str(state.attributes.get("media_title") or "")
        artist = str(state.attributes.get("media_artist") or "")
        picture: str = str(state.attributes.get("entity_picture") or "")

        img: Image.Image | None = None
        if picture:
            img = await self._fetch_image_url(picture)

        if img is None:
            img = Image.new("RGB", (_SIZE, _SIZE), (0, 0, 0))

        img = await self.hass.async_add_executor_job(crop_and_resize, img)
        await self.hass.async_add_executor_job(apply_now_playing_overlay, img, title, artist)
        await self._publish(to_rgb565(img))

    async def do_display_image(
        self,
        path: str | None = None,
        entity_id: str | None = None,
    ) -> None:
        """Push an image from a file path or camera entity."""
        from PIL import Image
        from tottie.image import crop_and_resize, to_rgb565

        img: Image.Image | None = None

        if path:
            img = await self.hass.async_add_executor_job(
                lambda: Image.open(path).convert("RGB")
            )
        elif entity_id:
            img = await self._snapshot_camera(entity_id)

        if img is None:
            _LOGGER.warning("do_display_image: no image source provided or fetch failed")
            return

        img = await self.hass.async_add_executor_job(crop_and_resize, img)
        await self._publish(to_rgb565(img))

    async def do_display_stream(self, entity_id: str, stream_for: float) -> None:
        """Stream camera snapshots to the display for the given duration."""
        self.cancel_stream()
        self._stream_task = self.hass.async_create_task(
            self._stream_loop(entity_id, stream_for)
        )

    async def do_clear(self) -> None:
        """Publish an empty payload, causing the display to fall back to clock."""
        await self._publish(b"")

    def cancel_stream(self) -> None:
        """Cancel any in-progress stream."""
        if self._stream_task and not self._stream_task.done():
            self._stream_task.cancel()
        self._stream_task = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

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
        from PIL import Image
        from homeassistant.components.camera import async_get_image as camera_get_image

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

        while asyncio.get_event_loop().time() < deadline:
            frame_start = asyncio.get_event_loop().time()
            img = await self._snapshot_camera(entity_id)
            if img is not None:
                img = await self.hass.async_add_executor_job(crop_and_resize, img)
                await self._publish(to_rgb565(img))
                frames += 1
            elapsed = asyncio.get_event_loop().time() - frame_start
            await asyncio.sleep(max(0, 0.15 - elapsed))

        _LOGGER.debug("Stream ended: %d frames sent to %s", frames, self._topic)
