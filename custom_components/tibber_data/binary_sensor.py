"""Tibber data"""
import logging

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .data_coordinator import TibberDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass: HomeAssistant, _, async_add_entities, config):
    """Set up the Tibber binary sensor."""
    if not config.get("password"):
        return
    coordinator = hass.data[DOMAIN]["coordinator"]
    dev = []
    for charger in coordinator.chargers:
        dev.append(
            TibberDataBinarySensor(
                coordinator,
                BinarySensorEntityDescription(
                    key=f"charger_{charger}_sc_enabled",
                    name=f"Smart charging enabled {coordinator.charger_name[charger]}",
                ),
            )
        )
        dev.append(
            TibberDataBinarySensor(
                coordinator,
                BinarySensorEntityDescription(
                    key=f"charger_{charger}_is_charging",
                    name=f"Is charging {coordinator.charger_name[charger]}",
                ),
            )
        )
    async_add_entities(dev)


class TibberDataBinarySensor(
    BinarySensorEntity, CoordinatorEntity[TibberDataCoordinator]
):
    """Representation of a Tibber binary sensor."""

    def __init__(self, coordinator, entity_description):
        """Initialize the sensor."""
        super().__init__(coordinator=coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = (
            f"{coordinator.tibber_home.home_id}_{entity_description.key}"
        )

    @property
    def _attr_name(self):
        """Return the name of the sensor."""
        return f"{self.entity_description.name} {self.coordinator.tibber_home.address1}"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_is_on = self.coordinator.data.get(self.entity_description.key)
        self.async_write_ha_state()
