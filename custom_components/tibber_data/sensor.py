import asyncio
import datetime
import logging

import tibber

from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

PRICE_SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="monthly_avg_price",
        name="Monthly avg price",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="est_subsidy",
        name="Estimated subsidy price",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="est_current_price_with_subsidy",
        name="Estimated price with subsidy",
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


async def async_setup_platform(
    hass: HomeAssistant, config, async_add_entities, discovery_info=None
):
    dev = []
    tasks = []
    for home in hass.data["tibber"].get_homes(only_active=True):
        if not home.info:
            await home.update_info()
        price_coordinator = TibberPriceDataCoordinator(hass, home)
        tasks.append(price_coordinator.async_request_refresh())
        for entity_description in PRICE_SENSORS:
            dev.append(TibberPriceSensor(price_coordinator, entity_description))
    async_add_entities(dev)
    await asyncio.gather(*tasks)


class TibberPriceSensor(SensorEntity, CoordinatorEntity["TibberDataCoordinator"]):
    def __init__(self, coordinator, entity_description):
        """Initialize the sensor."""
        super().__init__(coordinator=coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = (
            f"{coordinator.tibber_home.home_id}_{entity_description.key}"
        )
        self._attr_native_unit_of_measurement = coordinator.tibber_home.price_unit
        self._attr_name = f"{entity_description.name} {coordinator.tibber_home.name}"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.entity_description.key == "est_current_price_with_subsidy":
            price_data = self.coordinator.tibber_home.current_price_data()
            self._attr_native_value = price_data[0] - self.coordinator.data.get(
                "est_subsidy", 0
            )
        else:
            self._attr_native_value = self.coordinator.data.get(
                self.entity_description.key
            )
        self.async_write_ha_state()


class TibberPriceDataCoordinator(DataUpdateCoordinator):
    """Handle Tibber data and insert statistics."""

    def __init__(self, hass, tibber_home: tibber.TibberHome):
        """Initialize the data handler."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"Tibber Data {tibber_home.name}",
            update_interval=None,
        )
        self.tibber_home: tibber.TibberHome = tibber_home
        self._next_update = dt_util.now() + datetime.timedelta(minutes=1)

    @callback
    def _schedule_refresh(self) -> None:
        """Schedule a refresh."""
        if self._unsub_refresh:
            self._unsub_refresh()
            self._unsub_refresh = None

        self._unsub_refresh = async_track_point_in_utc_time(
            self.hass,
            self._job,
            self._next_update,
        )

    async def _async_update_data(self):
        """Update data via API."""
        await self.tibber_home.update_info_and_price_info()
        historic_data = await self.tibber_home.get_historic_price_data(
            tibber.const.RESOLUTION_MONTHLY
        )
        now = dt_util.now()
        prices_tomorrow_available = False
        for key in self.tibber_home.price_total:
            price_time = dt_util.parse_datetime(key).astimezone(
                dt_util.DEFAULT_TIME_ZONE
            )
            if price_time.date() > now.date():
                prices_tomorrow_available = True
                break
        if prices_tomorrow_available:
            self._next_update = (now + datetime.timedelta(days=1)).replace(
                hour=13, minute=1, second=0, microsecond=0
            )
        elif now.hour >= 13:
            self._next_update = now + datetime.timedelta(minutes=2)
        else:
            self._next_update = now.replace(hour=13, minute=1, second=0, microsecond=0)
        data = {}
        for val in historic_data:
            date = dt_util.parse_datetime(val["time"])
            if now.month == date.month and now.year == date.year:
                data["monthly_avg_price"] = val["total"]
                data["est_subsidy"] = (val["total"] - 0.7 * 1.25) * 0.9

        return data
