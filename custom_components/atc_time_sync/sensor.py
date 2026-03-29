"""Sensor platform for ATC Time Sync."""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, VERSION

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities."""
    data = hass.data[DOMAIN][entry.entry_id]
    broadcaster = data["broadcaster"]

    async_add_entities([
        BroadcastTimestampSensor(entry, broadcaster),
    ])


class BroadcastTimestampSensor(SensorEntity):
    """Sensor showing the last broadcast timestamp."""

    _attr_has_entity_name = True
    _attr_name = "Last Broadcast"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:broadcast"

    def __init__(self, entry: ConfigEntry, broadcaster) -> None:
        """Initialize the sensor."""
        self._entry = entry
        self._broadcaster = broadcaster
        self._attr_unique_id = f"{entry.entry_id}_last_broadcast"

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "ATC Time Sync Beacon",
            "manufacturer": "ATC_MiThermometer",
            "model": "BTHome Time Broadcaster",
            "sw_version": VERSION,
        }

    @property
    def native_value(self) -> datetime | None:
        """Return the last broadcast time."""
        ts = self._broadcaster.last_broadcast
        if ts is None:
            return None
        return datetime.fromtimestamp(ts, tz=timezone.utc)

    @property
    def extra_state_attributes(self):
        """Return additional attributes."""
        return {
            "adapter": self._entry.data.get("adapter", "hci0"),
            "packet_count": self._broadcaster._packet_count,
        }

    async def async_update(self) -> None:
        """Update sensor state."""
        # State is derived from broadcaster properties, no action needed
        pass
