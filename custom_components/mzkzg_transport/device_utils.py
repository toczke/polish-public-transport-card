"""Helpers for keeping the device registry hierarchy consistent."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr


def async_link_device_to_parent(
    hass: HomeAssistant,
    identifiers: set[tuple[str, str]],
    parent_identifiers: set[tuple[str, str]],
) -> None:
    """Link a stop device to its operator device without the deprecated ``via_device``.

    ``DeviceInfo`` no longer accepts ``via_device`` on current Home Assistant releases
    (it raises a RuntimeError), while older releases don't accept ``via_device_id`` in
    ``async_get_or_create``. Updating the registry entry directly works on both.
    """
    registry = dr.async_get(hass)
    parent = registry.async_get_device(identifiers=parent_identifiers)
    child = registry.async_get_device(identifiers=identifiers)
    if parent is None or child is None or child.via_device_id == parent.id:
        return
    registry.async_update_device(child.id, via_device_id=parent.id)
