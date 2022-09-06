import asyncio
import datetime
import logging

import tibber

from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.const import ENERGY_KILO_WATT_HOUR
from homeassistant.core import HomeAssistant, callback
from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="peak_consumption",
        name="Average of 3 highest hourly consumption",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
    ),
    SensorEntityDescription(
        key="monthly_avg_price",
        name="Monthly avg price",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="est_subsidy",
        name="Estimated subsidy",
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
    hass.data["tibber"].user_agent += " https://github.com/Danielhiversen/home_assistant_tibber_data"
    for home in hass.data["tibber"].get_homes(only_active=True):
        if not home.info:
            await home.update_info()
        coordinator = TibberDataCoordinator(hass, home)
        tasks.append(coordinator.async_request_refresh())
        for entity_description in SENSORS:
            dev.append(TibberDataSensor(coordinator, entity_description))
    async_add_entities(dev)
    await asyncio.gather(*tasks)


class TibberDataSensor(SensorEntity, CoordinatorEntity["TibberDataCoordinator"]):
    def __init__(self, coordinator, entity_description):
        """Initialize the sensor."""
        super().__init__(coordinator=coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = (
            f"{coordinator.tibber_home.home_id}_{entity_description.key}"
        )
        if entity_description.native_unit_of_measurement is None:
            self._attr_native_unit_of_measurement = coordinator.tibber_home.price_unit
        self._attr_name = f"{entity_description.name} {coordinator.tibber_home.address1}"

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
        if self.entity_description.key == "peak_consumption":
            self._attr_extra_state_attributes = self.coordinator.data.get(
                "peak_consumption_attrs"
            )

        self.async_write_ha_state()


class TibberDataCoordinator(DataUpdateCoordinator):
    """Handle Tibber data."""

    def __init__(self, hass, tibber_home: tibber.TibberHome):
        """Initialize the data handler."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"Tibber Data {tibber_home.name}",
            update_interval=datetime.timedelta(minutes=2),
        )
        self.tibber_home: tibber.TibberHome = tibber_home
        self._next_update_price = dt_util.now() - datetime.timedelta(minutes=1)
        self._next_update_consumption = dt_util.now() - datetime.timedelta(minutes=1)

    async def _async_update_data(self):
        """Update data via API."""
        now = dt_util.now()
        data = {} if self.data is None else self.data
        tasks = []
        if now >= self._next_update_consumption and self.data is not None:
            tasks.append(self._get_consumption_data(data, now))
        if now >= self._next_update_price and self.data is not None:
            tasks.append(self._get_price_data(data, now))
        await asyncio.gather(*tasks)
        return data

    async def _get_consumption_data(self, data, now):
        max_month = []
        cons_data = await self.tibber_home.get_historic_data(31 * 24)
        consumption_yesterday_available = False
        for _hour in cons_data:
            _cons = _hour.get("consumption")
            if _cons is None:
                continue
            date = dt_util.parse_datetime(_hour.get("from"))
            if not (date.month == now.month and date.year == now.year):
                continue
            if date.date() == now.date() - datetime.timedelta(days=1):
                consumption_yesterday_available = True

            cons = Consumption(_cons, date)
            if len(max_month) == 0 or cons > max_month[-1]:
                same_day = False
                for k, _cons in enumerate(max_month):
                    if cons.day == _cons.day:
                        if cons > _cons:
                            max_month[k] = cons
                        same_day = True
                        break
                if not same_day:
                    max_month.append(cons)
                max_month.sort(reverse=True)
                if len(max_month) > 3:
                    del max_month[-1]
            if max_month:
                data["peak_consumption"] = sum([x for x in max_month]) / len(max_month)
                data["peak_consumption_attrs"] = {
                    "peak_consumption_dates": [x.ts for x in max_month],
                    "peak_consumptions": [x.cons for x in max_month],
                }
            else:
                data["peak_consumption"] = None
                data["peak_consumption_attrs"] = None

            if consumption_yesterday_available:
                self._next_update_price = (now + datetime.timedelta(days=1)).replace(
                    hour=3, minute=0, second=0, microsecond=0
                )
            else:
                self._next_update_price = (now + datetime.timedelta(hours=1)).replace(
                    minute=5, second=0, microsecond=0
                )

    async def _get_price_data(self, data, now):
        await self.tibber_home.update_info_and_price_info()
        historic_data = await self.tibber_home.get_historic_price_data(
            tibber.const.RESOLUTION_MONTHLY
        )
        prices_tomorrow_available = False
        for key in self.tibber_home.price_total:
            price_time = dt_util.parse_datetime(key).astimezone(
                dt_util.DEFAULT_TIME_ZONE
            )
            if price_time.date() > now.date():
                prices_tomorrow_available = True
                break
        if prices_tomorrow_available:
            self._next_update_price = (now + datetime.timedelta(days=1)).replace(
                hour=13, minute=1, second=0, microsecond=0
            )
        elif now.hour >= 13:
            self._next_update_price = now + datetime.timedelta(minutes=2)
        else:
            self._next_update_price = now.replace(
                hour=13, minute=1, second=0, microsecond=0
            )
        for val in historic_data:
            date = dt_util.parse_datetime(val["time"])
            if now.month == date.month and now.year == date.year:
                data["monthly_avg_price"] = val["total"]
                data["est_subsidy"] = (val["total"] - 0.7 * 1.25) * 0.9


class Consumption:
    def __init__(self, cons, ts):
        self.cons = cons
        self.ts = ts

    @property
    def day(self):
        return dt_util.as_local(self.ts).date()

    def __lt__(self, other):
        return self.cons < other.cons

    def __radd__(self, other):
        return other + self.cons

    def __str__(self):
        return f"Cons({self.cons:.2f}, {self.ts})"

    def __repr__(self):
        return f"Cons({self.cons:.2f}, {self.ts})"
