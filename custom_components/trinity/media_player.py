"""Media player platform for Trinity."""

from __future__ import annotations

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    from .coordinator import TrinityCoordinator

    coordinator: TrinityCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([TrinityMediaPlayer(coordinator, entry)])


class TrinityMediaPlayer(MediaPlayerEntity):
    _attr_name = "Trinity"
    _attr_supported_features = MediaPlayerEntityFeature.PLAY_MEDIA | MediaPlayerEntityFeature.STOP
    _attr_media_content_type = MediaType.VIDEO

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_media_player"
        self._attr_state = MediaPlayerState.IDLE
        self._attr_media_content_id: str | None = None

    @property
    def state(self) -> MediaPlayerState:
        return self._attr_state  # type: ignore[return-value]

    async def async_play_media(self, media_type: str, media_id: str, **kwargs: object) -> None:
        self._attr_state = MediaPlayerState.PLAYING
        self._attr_media_content_id = media_id
        self.async_write_ha_state()
        await self._coordinator.do_display_url(media_id)
        self._coordinator.set_stream_end_callback(self._on_stream_ended)

    async def async_media_stop(self) -> None:
        self._coordinator.cancel_stream()
        self._attr_state = MediaPlayerState.IDLE
        self._attr_media_content_id = None
        self.async_write_ha_state()
        await self._coordinator._replay_default()

    @callback
    def _on_stream_ended(self) -> None:
        self._attr_state = MediaPlayerState.IDLE
        self._attr_media_content_id = None
        self.async_write_ha_state()
