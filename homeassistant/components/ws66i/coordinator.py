"""Coordinator for WS66i."""
from __future__ import annotations

from datetime import timedelta
import logging

from pyws66i import WS66i, ZoneStatus

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)

POLL_INTERVAL = timedelta(seconds=30)


class Ws66iDataUpdateCoordinator(DataUpdateCoordinator):
    """DataUpdateCoordinator to gather data for WS66i Zones."""

    def __init__(
        self,
        hass: HomeAssistant,
        my_api: WS66i,
        zones: list[int],
    ) -> None:
        """Initialize DataUpdateCoordinator to gather data for specific zones."""
        super().__init__(
            hass,
            _LOGGER,
            name="WS66i",
            update_interval=POLL_INTERVAL,
        )
        self._ws66i = my_api
        self._zones = zones

    def _update_all_zones(self) -> list[ZoneStatus]:
        """Fetch data for each of the zones."""
        data = []
        for zone_id in self._zones:
            data_zone = self._ws66i.zone_status(zone_id)
            if data_zone is None:
                raise UpdateFailed(f"Failed to update zone {zone_id}")

            data.append(data_zone)

        # HA will call my entity's _handle_coordinator_update()
        return data

    async def _async_update_data(self) -> list[ZoneStatus]:
        """Fetch data for each of the zones."""
        # HA will call my entity's _handle_coordinator_update()
        # The data I pass back here can be accessed through coordinator.data.
        return await self.hass.async_add_executor_job(self._update_all_zones)
