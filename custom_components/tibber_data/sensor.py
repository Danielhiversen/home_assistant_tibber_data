"""Tibber data"""
import asyncio
import datetime
import logging

import tibber
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import ENERGY_KILO_WATT_HOUR
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
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
        key="customer_avg_price",
        name="Monthly avg customer price",
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
    hass: HomeAssistant, _, async_add_entities, __=None
):
    """Set up the Tibber sensor."""
    dev = []
    tasks = []
    hass.data[
        "tibber"
    ].user_agent += " https://github.com/Danielhiversen/home_assistant_tibber_data"
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
    """Representation of a Tibber sensor."""
    def __init__(self, coordinator, entity_description):
        """Initialize the sensor."""
        super().__init__(coordinator=coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = (
            f"{coordinator.tibber_home.home_id}_{entity_description.key}"
        )
        if entity_description.native_unit_of_measurement is None:
            self._attr_native_unit_of_measurement = coordinator.tibber_home.price_unit
        self._attr_name = (
            f"{entity_description.name} {coordinator.tibber_home.address1}"
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.entity_description.key == "est_current_price_with_subsidy":
            price_data = self.coordinator.tibber_home.current_price_data()
            self._attr_native_value = price_data[0] - self.coordinator.data.get(
                "est_subsidy", 0
            )
        else:
            self._attr_native_value = round(
                self.coordinator.data.get(self.entity_description.key), 2
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
        self._next_update = dt_util.now() - datetime.timedelta(minutes=1)

    async def _async_update_data(self):
        """Update data via API."""
        now = dt_util.now(dt_util.DEFAULT_TIME_ZONE)
        data = {} if self.data is None else self.data
        if now >= self._next_update:
            await self._get_data(data, now)
        return data

    async def _get_data(self, data, now):
        """Get data from Tibber."""
        # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        max_month = []
        cons_data = await self.tibber_home.get_historic_data(31 * 24)
        consumption_yesterday_available = False
        month_consumption = set()

        for _hour in cons_data:
            _cons = _hour.get("consumption")
            if _cons is None:
                continue
            date = dt_util.parse_datetime(_hour.get("from"))
            if not (date.month == now.month and date.year == now.year):
                continue
            if date.date() == now.date() - datetime.timedelta(days=1):
                consumption_yesterday_available = True
            cons = Consumption(date, _cons, _hour.get("unitPrice"), _hour.get("cost"))
            month_consumption.add(cons)

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
            data["peak_consumption"] = sum(max_month) / len(max_month)
            data["peak_consumption_attrs"] = {
                "peak_consumption_dates": [x.timestamp for x in max_month],
                "peak_consumptions": [x.cons for x in max_month],
            }
        else:
            data["peak_consumption"] = None
            data["peak_consumption_attrs"] = None
        await self.tibber_home.update_price_info()

        if consumption_yesterday_available:
            self._next_update = (now + datetime.timedelta(days=1)).replace(
                hour=3, minute=0, second=0, microsecond=0
            )
        else:
            self._next_update = (now + datetime.timedelta(hours=1)).replace(
                minute=5, second=0, microsecond=0
            )

        prices_tomorrow_available = False
        for key, price in self.tibber_home.price_total.items():
            date = dt_util.parse_datetime(key)
            if date.date() == now.date() + datetime.timedelta(days=1):
                prices_tomorrow_available = True
            if not (date.month == now.month and date.year == now.year):
                continue
            month_consumption.add(Consumption(date, None, price, None))

        if prices_tomorrow_available:
            self._next_update = min(
                self._next_update,
                (now + datetime.timedelta(days=1)).replace(
                    hour=13, minute=1, second=0, microsecond=0
                ),
            )
        elif now.hour >= 13:
            self._next_update = min(
                self._next_update, now + datetime.timedelta(minutes=2)
            )
        else:
            self._next_update = min(
                self._next_update,
                now.replace(hour=13, minute=1, second=0, microsecond=0),
            )

        total_price = 0
        total_cost = 0
        total_cons = 0
        for cons in month_consumption:
            total_price += cons.price
            total_cost += cons.cost if cons.cost else 0
            total_cons += cons.cons if cons.cons else 0
        data["monthly_avg_price"] = total_price / len(month_consumption)
        data["est_subsidy"] = (data["monthly_avg_price"] - 0.7 * 1.25) * 0.9
        data["customer_avg_price"] = total_cost / total_cons


class Consumption:
    """Consumption data."""
    def __init__(self, timestamp, cons, price, cost):
        """Initialize the data."""
        self.timestamp = timestamp
        self.cons = cons
        self.price = price
        self.cost = cost

    @property
    def day(self):
        """Return day."""
        return dt_util.as_local(self.timestamp).date()

    def __lt__(self, other):
        if self.cons is None and other.cons is None:
            return self.timestamp < other.timestamp
        if self.cons is None:
            return True
        if other.cons is None:
            return False
        return self.cons < other.cons

    def __eq__(self, other):
        return self.timestamp == other.timestamp

    def __hash__(self):
        return hash(self.timestamp)

    def __radd__(self, other):
        return other + self.cons

    def __str__(self):
        return f"Cons({self.timestamp}, {self.cons:.2f})"

    def __repr__(self):
        return f"Cons({self.timestamp}, {self.cons:.2f})"
