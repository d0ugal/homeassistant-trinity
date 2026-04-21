"""The Trinity integration."""

from __future__ import annotations

import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from tottie.overlay import MAX_CHARS

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_SCHEMA_DISPLAY_MOON = vol.Schema(
    {
        vol.Optional("display_for"): vol.Coerce(float),
    }
)

_SCHEMA_DISPLAY_NOW_PLAYING = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Optional("display_for"): vol.Coerce(float),
    }
)

_SCHEMA_DISPLAY_IMAGE = vol.Schema(
    {
        vol.Exclusive("path", "source"): cv.string,
        vol.Exclusive("entity_id", "source"): cv.entity_id,
        vol.Optional("display_for"): vol.Coerce(float),
    }
)

_CROP_ANCHORS = {"center", "top_left", "top_right", "bottom_left", "bottom_right"}

_SCHEMA_DISPLAY_STREAM = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("stream_for"): vol.All(vol.Coerce(float), vol.Range(min=1)),
        vol.Optional("crop", default="center"): vol.In(_CROP_ANCHORS),
    }
)

_SCHEMA_DISPLAY_EMOJI = vol.Schema(
    {
        vol.Required("emoji"): cv.string,
        vol.Optional("display_for"): vol.Coerce(float),
        vol.Optional("line1"): vol.All(cv.string, vol.Length(max=MAX_CHARS)),
        vol.Optional("line2"): vol.All(cv.string, vol.Length(max=MAX_CHARS)),
        vol.Optional("corner"): vol.All(cv.string, vol.Length(max=1)),
    }
)

_SCHEMA_SET_BRIGHTNESS = vol.Schema(
    {
        vol.Required("brightness"): vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
    }
)

_SCHEMA_CLEAR = vol.Schema({})


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    from .coordinator import TrinityCoordinator

    hass.data.setdefault(DOMAIN, {})

    coordinator = TrinityCoordinator(hass, entry)
    await coordinator.async_load_and_replay()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    def _coordinators() -> list[TrinityCoordinator]:
        return [
            c
            for c in hass.data.get(DOMAIN, {}).values()
            if isinstance(c, TrinityCoordinator)
        ]

    async def _display_moon(call) -> None:
        display_for = call.data.get("display_for")
        for coord in _coordinators():
            await coord.do_display_moon(display_for=display_for)

    async def _display_now_playing(call) -> None:
        display_for = call.data.get("display_for")
        for coord in _coordinators():
            await coord.do_display_now_playing(
                call.data["entity_id"], display_for=display_for
            )

    async def _display_image(call) -> None:
        display_for = call.data.get("display_for")
        for coord in _coordinators():
            await coord.do_display_image(
                path=call.data.get("path"),
                entity_id=call.data.get("entity_id"),
                display_for=display_for,
            )

    async def _display_stream(call) -> None:
        for coord in _coordinators():
            await coord.do_display_stream(
                entity_id=call.data["entity_id"],
                stream_for=call.data["stream_for"],
                crop=call.data.get("crop", "center"),
            )

    async def _display_emoji(call) -> None:
        display_for = call.data.get("display_for")
        for coord in _coordinators():
            await coord.do_display_emoji(
                call.data["emoji"],
                display_for=display_for,
                line1=call.data.get("line1"),
                line2=call.data.get("line2"),
                corner=call.data.get("corner"),
            )

    async def _set_brightness(call) -> None:
        for coord in _coordinators():
            await coord.do_set_brightness(call.data["brightness"])

    async def _clear(call) -> None:
        for coord in _coordinators():
            await coord.do_clear()

    if not hass.services.has_service(DOMAIN, "display_moon"):
        hass.services.async_register(
            DOMAIN, "display_moon", _display_moon, _SCHEMA_DISPLAY_MOON
        )
        hass.services.async_register(
            DOMAIN,
            "display_now_playing",
            _display_now_playing,
            _SCHEMA_DISPLAY_NOW_PLAYING,
        )
        hass.services.async_register(
            DOMAIN, "display_image", _display_image, _SCHEMA_DISPLAY_IMAGE
        )
        hass.services.async_register(
            DOMAIN, "display_stream", _display_stream, _SCHEMA_DISPLAY_STREAM
        )
        hass.services.async_register(
            DOMAIN, "display_emoji", _display_emoji, _SCHEMA_DISPLAY_EMOJI
        )
        hass.services.async_register(
            DOMAIN, "set_brightness", _set_brightness, _SCHEMA_SET_BRIGHTNESS
        )
        hass.services.async_register(DOMAIN, "clear", _clear, _SCHEMA_CLEAR)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    from .coordinator import TrinityCoordinator

    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if coordinator:
        coordinator.cancel_stream()
        coordinator.cancel_revert()

    hass.data[DOMAIN].pop(entry.entry_id, None)

    if not any(
        isinstance(c, TrinityCoordinator) for c in hass.data.get(DOMAIN, {}).values()
    ):
        for svc in (
            "display_moon",
            "display_now_playing",
            "display_image",
            "display_stream",
            "display_emoji",
            "set_brightness",
            "clear",
        ):
            hass.services.async_remove(DOMAIN, svc)

    return True
