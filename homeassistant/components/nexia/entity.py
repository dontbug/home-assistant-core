"""The nexia integration base entity."""
from nexia.thermostat import NexiaThermostat
from nexia.zone import NexiaThermostatZone

from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTRIBUTION,
    DOMAIN,
    MANUFACTURER,
    SIGNAL_THERMOSTAT_UPDATE,
    SIGNAL_ZONE_UPDATE,
)
from .coordinator import NexiaDataUpdateCoordinator


class NexiaEntity(CoordinatorEntity):
    """Base class for nexia entities."""

    def __init__(
        self, coordinator: NexiaDataUpdateCoordinator, name: str, unique_id: str
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._unique_id = unique_id
        self._name = name

    @property
    def unique_id(self):
        """Return the unique id."""
        return self._unique_id

    @property
    def name(self):
        """Return the name."""
        return self._name

    @property
    def extra_state_attributes(self):
        """Return the device specific state attributes."""
        return {
            ATTR_ATTRIBUTION: ATTRIBUTION,
        }


class NexiaThermostatEntity(NexiaEntity):
    """Base class for nexia devices attached to a thermostat."""

    def __init__(self, coordinator, thermostat, name, unique_id):
        """Initialize the entity."""
        super().__init__(coordinator, name, unique_id)
        self._thermostat: NexiaThermostat = thermostat

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device_info of the device."""
        assert isinstance(self.coordinator, NexiaDataUpdateCoordinator)
        return DeviceInfo(
            configuration_url=self.coordinator.nexia_home.root_url,
            identifiers={(DOMAIN, self._thermostat.thermostat_id)},
            manufacturer=MANUFACTURER,
            model=self._thermostat.get_model(),
            name=self._thermostat.get_name(),
            sw_version=self._thermostat.get_firmware(),
        )

    async def async_added_to_hass(self):
        """Listen for signals for services."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_THERMOSTAT_UPDATE}-{self._thermostat.thermostat_id}",
                self.async_write_ha_state,
            )
        )

    def _signal_thermostat_update(self):
        """Signal a thermostat update.

        Whenever the underlying library does an action against
        a thermostat, the data for the thermostat and all
        connected zone is updated.

        Update all the zones on the thermostat.
        """
        async_dispatcher_send(
            self.hass, f"{SIGNAL_THERMOSTAT_UPDATE}-{self._thermostat.thermostat_id}"
        )


class NexiaThermostatZoneEntity(NexiaThermostatEntity):
    """Base class for nexia devices attached to a thermostat."""

    def __init__(self, coordinator, zone, name, unique_id):
        """Initialize the entity."""
        super().__init__(coordinator, zone.thermostat, name, unique_id)
        self._zone: NexiaThermostatZone = zone

    @property
    def device_info(self):
        """Return the device_info of the device."""
        data = super().device_info
        zone_name = self._zone.get_name()
        data.update(
            {
                "identifiers": {(DOMAIN, self._zone.zone_id)},
                "name": zone_name,
                "suggested_area": zone_name,
                "via_device": (DOMAIN, self._zone.thermostat.thermostat_id),
            }
        )
        return data

    async def async_added_to_hass(self):
        """Listen for signals for services."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_ZONE_UPDATE}-{self._zone.zone_id}",
                self.async_write_ha_state,
            )
        )

    def _signal_zone_update(self):
        """Signal a zone update.

        Whenever the underlying library does an action against
        a zone, the data for the zone is updated.

        Update a single zone.
        """
        async_dispatcher_send(self.hass, f"{SIGNAL_ZONE_UPDATE}-{self._zone.zone_id}")
