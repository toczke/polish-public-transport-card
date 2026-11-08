"""Tests for the device hierarchy helper."""

from types import SimpleNamespace

from mzkzg_transport import device_utils


class FakeDeviceRegistry:
    def __init__(self, devices, per_entry=True):
        self.devices = devices
        self.calls = []
        if not per_entry:
            self.async_get_device_by_identifier = None

    def async_get_device_by_identifier(self, identifier, config_entry_id):
        self.calls.append((identifier, config_entry_id))
        return self.devices.get(identifier)

    def async_get_device(self, identifiers=None, connections=None):
        for identifier in identifiers or ():
            if identifier in self.devices:
                return self.devices[identifier]
        return None

    def async_update_device(self, device_id, **kwargs):
        for device in self.devices.values():
            if device.id == device_id:
                for key, value in kwargs.items():
                    setattr(device, key, value)
                return device
        return None


def _install(monkeypatch, registry):
    monkeypatch.setattr(device_utils.dr, "async_get", lambda hass: registry)


def test_links_stop_device_to_operator(monkeypatch):
    parent = SimpleNamespace(id="parent", via_device_id=None)
    child = SimpleNamespace(id="child", via_device_id=None)
    registry = FakeDeviceRegistry({("d", "plk"): parent, ("d", "plk_1"): child})
    _install(monkeypatch, registry)

    device_utils.async_link_device_to_parent(
        SimpleNamespace(),
        {("d", "plk_1")},
        {("d", "plk")},
        "entry",
    )

    assert child.via_device_id == "parent"
    assert registry.calls == [(("d", "plk"), "entry"), (("d", "plk_1"), "entry")]


def test_does_not_relink_already_linked_device(monkeypatch):
    parent = SimpleNamespace(id="parent", via_device_id=None)
    child = SimpleNamespace(id="child", via_device_id="parent")
    registry = FakeDeviceRegistry({("d", "plk"): parent, ("d", "plk_1"): child})
    _install(monkeypatch, registry)

    device_utils.async_link_device_to_parent(
        SimpleNamespace(), {("d", "plk_1")}, {("d", "plk")}, "entry"
    )

    assert child.via_device_id == "parent"


def test_falls_back_to_global_lookup_on_older_ha(monkeypatch):
    parent = SimpleNamespace(id="parent", via_device_id=None)
    child = SimpleNamespace(id="child", via_device_id=None)
    registry = FakeDeviceRegistry({("d", "plk"): parent, ("d", "plk_1"): child}, per_entry=False)
    _install(monkeypatch, registry)

    device_utils.async_link_device_to_parent(
        SimpleNamespace(), {("d", "plk_1")}, {("d", "plk")}, "entry"
    )

    assert child.via_device_id == "parent"


def test_missing_parent_or_child_is_a_noop(monkeypatch):
    child = SimpleNamespace(id="child", via_device_id=None)
    registry = FakeDeviceRegistry({("d", "plk_1"): child})
    _install(monkeypatch, registry)

    device_utils.async_link_device_to_parent(
        SimpleNamespace(), {("d", "plk_1")}, {("d", "missing")}, "entry"
    )

    assert child.via_device_id is None
