"""ATC Thermometer Time Sync integration for Home Assistant.

Broadcasts a BTHome v2 beacon containing the current UTC timestamp
so ATC_MiThermometer devices (with SERVICE_SCANTIM enabled) can
automatically sync their clocks without a BLE connection.
"""
from __future__ import annotations

import asyncio
import logging
import struct
import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

from datetime import timedelta

from .const import (
    DOMAIN,
    BTHOME_UUID16,
    BTHOME_INFO_UNENCRYPTED,
    BTHOME_ID_TIMESTAMP,
    BTHOME_ID_PACKET_ID,
    ADV_TYPE_SERVICE_DATA_16BIT,
    DEFAULT_BROADCAST_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ATC Time Sync from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    adapter = entry.data.get("adapter", "hci0")
    broadcast_interval = entry.options.get(
        "broadcast_interval", DEFAULT_BROADCAST_INTERVAL
    )

    broadcaster = BTHomeTimeBroadcaster(hass, adapter)
    hass.data[DOMAIN][entry.entry_id] = {
        "broadcaster": broadcaster,
        "adapter": adapter,
    }

    # Start broadcasting
    await broadcaster.async_start()

    # Schedule periodic timestamp updates
    async def _update_beacon(_now=None):
        await broadcaster.async_update_timestamp()

    unsub = async_track_time_interval(
        hass, _update_beacon, timedelta(seconds=broadcast_interval)
    )
    hass.data[DOMAIN][entry.entry_id]["unsub_interval"] = unsub

    # Set up sensor/binary_sensor platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    data = hass.data[DOMAIN].pop(entry.entry_id, {})

    # Stop broadcasting
    broadcaster = data.get("broadcaster")
    if broadcaster:
        await broadcaster.async_stop()

    # Cancel interval
    unsub = data.get("unsub_interval")
    if unsub:
        unsub()

    # Unload platforms
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


# D-Bus interface for LEAdvertisement1
ADVERTISEMENT_IFACE = "org.bluez.LEAdvertisement1"
DBUS_OM_IFACE = "org.freedesktop.DBus.ObjectManager"
DBUS_PROP_IFACE = "org.freedesktop.DBus.Properties"
LE_ADVERTISING_MANAGER_IFACE = "org.bluez.LEAdvertisingManager1"
ADV_PATH = "/org/homeassistant/atc_time_sync/advertisement0"


class BTHomeTimeBroadcaster:
    """Broadcasts BTHome v2 time beacon via bluez D-Bus LEAdvertisingManager1."""

    def __init__(self, hass: HomeAssistant, adapter: str = "hci0") -> None:
        """Initialize the broadcaster."""
        self.hass = hass
        self.adapter = adapter
        self._adapter_path = f"/org/bluez/{adapter}"
        self._running = False
        self._packet_count = 0
        self._last_broadcast: float | None = None
        self._bus = None
        self._adv_registered = False

    @property
    def is_running(self) -> bool:
        """Return whether broadcasting is active."""
        return self._running

    @property
    def last_broadcast(self) -> float | None:
        """Return the last broadcast timestamp."""
        return self._last_broadcast

    def _build_service_data(self) -> bytes:
        """Build BTHome v2 service data with current local timestamp."""
        from datetime import datetime, timezone
        import zoneinfo

        # Use HA's configured timezone to send local time
        try:
            tz = zoneinfo.ZoneInfo(self.hass.config.time_zone)
            local_now = datetime.now(tz)
            utc_offset = int(local_now.utcoffset().total_seconds())
        except Exception:
            utc_offset = 0

        now = int(time.time()) + utc_offset
        self._packet_count = (self._packet_count + 1) & 0xFF

        return struct.pack(
            "<BBBB I",
            BTHOME_INFO_UNENCRYPTED,      # 0x40
            BTHOME_ID_PACKET_ID,          # 0x00
            self._packet_count,           # packet counter
            BTHOME_ID_TIMESTAMP,          # 0x50
            now,                          # 4-byte local timestamp
        )

    async def async_start(self) -> None:
        """Start BLE advertising via bluez D-Bus."""
        try:
            from dbus_fast.aio import MessageBus
            from dbus_fast import BusType, Variant
            from dbus_fast.service import ServiceInterface, method, dbus_property
            from dbus_fast.service import PropertyAccess

            self._bus = await MessageBus(bus_type=BusType.SYSTEM).connect()

            service_data = self._build_service_data()
            uuid_str = f"0000fcd2-0000-1000-8000-00805f9b34fb"

            # Create the advertisement object on D-Bus
            class Advertisement(ServiceInterface):
                def __init__(self, svc_data: bytes):
                    super().__init__(ADVERTISEMENT_IFACE)
                    self._svc_data = svc_data

                @dbus_property(access=PropertyAccess.READ)
                def Type(self) -> "s":
                    return "broadcast"

                @dbus_property(access=PropertyAccess.READ)
                def ServiceUUIDs(self) -> "as":
                    return [uuid_str]

                @dbus_property(access=PropertyAccess.READ)
                def ServiceData(self) -> "a{sv}":
                    return {uuid_str: Variant("ay", bytes(self._svc_data))}

                @dbus_property(access=PropertyAccess.READ)
                def Includes(self) -> "as":
                    return []

                @dbus_property(access=PropertyAccess.READ)
                def LocalName(self) -> "s":
                    return "ATC_TS"

                @method()
                def Release(self):
                    pass

            self._adv_obj = Advertisement(service_data)
            self._bus.export(ADV_PATH, self._adv_obj)

            # Register with LEAdvertisingManager1
            introspect = await self._bus.introspect("org.bluez", self._adapter_path)
            proxy = self._bus.get_proxy_object(
                "org.bluez", self._adapter_path, introspect
            )
            le_adv_mgr = proxy.get_interface(LE_ADVERTISING_MANAGER_IFACE)

            await le_adv_mgr.call_register_advertisement(ADV_PATH, {})

            self._running = True
            self._adv_registered = True
            self._last_broadcast = time.time()
            _LOGGER.info(
                "ATC Time Sync beacon broadcasting started on %s via bluez D-Bus",
                self.adapter,
            )

        except Exception as e:
            _LOGGER.error("Failed to start BLE advertising: %s", e)
            self._running = False

    async def async_update_timestamp(self) -> None:
        """Update the beacon with current timestamp by re-registering."""
        if not self._running or not self._bus:
            return

        try:
            from dbus_fast import Variant

            service_data = self._build_service_data()
            uuid_str = "0000fcd2-0000-1000-8000-00805f9b34fb"

            # Unregister old advertisement
            introspect = await self._bus.introspect("org.bluez", self._adapter_path)
            proxy = self._bus.get_proxy_object(
                "org.bluez", self._adapter_path, introspect
            )
            le_adv_mgr = proxy.get_interface(LE_ADVERTISING_MANAGER_IFACE)

            try:
                await le_adv_mgr.call_unregister_advertisement(ADV_PATH)
            except Exception:
                pass

            self._bus.unexport(ADV_PATH)

            # Create new advertisement with updated timestamp
            from dbus_fast.service import ServiceInterface, method, dbus_property
            from dbus_fast.service import PropertyAccess

            class Advertisement(ServiceInterface):
                def __init__(self, svc_data: bytes):
                    super().__init__(ADVERTISEMENT_IFACE)
                    self._svc_data = svc_data

                @dbus_property(access=PropertyAccess.READ)
                def Type(self) -> "s":
                    return "broadcast"

                @dbus_property(access=PropertyAccess.READ)
                def ServiceUUIDs(self) -> "as":
                    return [uuid_str]

                @dbus_property(access=PropertyAccess.READ)
                def ServiceData(self) -> "a{sv}":
                    return {uuid_str: Variant("ay", bytes(self._svc_data))}

                @dbus_property(access=PropertyAccess.READ)
                def Includes(self) -> "as":
                    return []

                @dbus_property(access=PropertyAccess.READ)
                def LocalName(self) -> "s":
                    return "ATC_TS"

                @method()
                def Release(self):
                    pass

            self._adv_obj = Advertisement(service_data)
            self._bus.export(ADV_PATH, self._adv_obj)
            await le_adv_mgr.call_register_advertisement(ADV_PATH, {})

            self._last_broadcast = time.time()

        except Exception as e:
            _LOGGER.error("Failed to update beacon: %s", e)

    async def async_stop(self) -> None:
        """Stop BLE advertising."""
        if self._bus and self._adv_registered:
            try:
                introspect = await self._bus.introspect(
                    "org.bluez", self._adapter_path
                )
                proxy = self._bus.get_proxy_object(
                    "org.bluez", self._adapter_path, introspect
                )
                le_adv_mgr = proxy.get_interface(LE_ADVERTISING_MANAGER_IFACE)
                await le_adv_mgr.call_unregister_advertisement(ADV_PATH)
                self._bus.unexport(ADV_PATH)
            except Exception as e:
                _LOGGER.warning("Error stopping advertisement: %s", e)

            self._adv_registered = False

        if self._bus:
            self._bus.disconnect()
            self._bus = None

        self._running = False
        _LOGGER.info("ATC Time Sync beacon broadcasting stopped")
