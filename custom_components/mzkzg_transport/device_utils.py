"""Helpers for keeping the device registry hierarchy consistent."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr


def async_link_device_to_parent(
    hass: HomeAssistant,
    identifiers: set[tuple[str, str]],
    parent_identifiers: set[tuple[str, str]],
    config_entry_id: str | None = None,
) -> None:
    """Link a stop device to its operator device without the deprecated ``via_device``.

    ``DeviceInfo`` no longer accepts ``via_device`` on current Home Assistant releases
    (it raises a RuntimeError), while older releases don't accept ``via_device_id`` in
    ``async_get_or_create``. Updating the registry entry directly works on both.
    """
    registry = dr.async_get(hass)

    def _find(device_identifiers: set[tuple[str, str]]):
        lookup = getattr(registry, "async_get_device_by_identifier", None)
        if config_entry_id and lookup:
            for identifier in device_identifiers:
                device = lookup(identifier, config_entry_id)
                if device is not None:
                    return device
            return None
        # Fallback for Home Assistant releases before the per-entry lookup API.
        return registry.async_get_device(identifiers=device_identifiers)

    parent = _find(parent_identifiers)
    child = _find(identifiers)
    if parent is None or child is None or child.via_device_id == parent.id:
        return
    registry.async_update_device(child.id, via_device_id=parent.id)
