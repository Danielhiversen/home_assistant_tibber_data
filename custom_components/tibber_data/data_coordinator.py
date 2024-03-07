"""Data coordinator for Tibber."""
import asyncio
import datetime
import logging
from random import randrange

import aiohttp
import tibber
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfElectricCurrent, UnitOfEnergy
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .consumption_data import Consumption
from .tibber_api import (
    get_historic_data,
    get_historic_production_data,
    get_tibber_chargers,
    get_tibber_chargers_data,
    get_tibber_data,
    get_tibber_offline_evs_data,
    get_tibber_token,
)

_LOGGER = logging.getLogger(__name__)


class TibberDataCoordinator(DataUpdateCoordinator):
    """Handle Tibber data."""

    def __init__(self, hass, tibber_home: tibber.TibberHome, email: str, password: str):
        """Initialize the data handler."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"Tibber Data {tibber_home.name}",
            update_interval=datetime.timedelta(seconds=15),
        )
        self.tibber_home: tibber.TibberHome = tibber_home
        tibber_home._timeout = 30  # noqa: SLF001
        self.email = email
        self._password = password
        self._token = None
        self._chargers: list[str] = []
        self._offline_evs: list[dict] = []
        self._month_consumption: set[Consumption] = set()

        self._session = aiohttp.ClientSession()
        self.charger_name = {}

        _next_update = dt_util.now() - datetime.timedelta(minutes=1)
        self._update_functions = {
            self._get_data: _next_update,
        }
        if self._password:
            self._update_functions[self._get_data_tibber] = _next_update
            self._update_functions[self._get_charger_data_tibber] = _next_update
            self._update_functions[self._get_offline_evs_data_tibber] = _next_update
        if self.tibber_home.has_production:
            self._update_functions[self._get_production_data] = _next_update

    def reset_updater(self):
        """Reset updater."""
        _next_update = dt_util.now() - datetime.timedelta(minutes=1)
        for key in self._update_functions:
            self._update_functions[key] = _next_update

    def get_price_at(self, timestamp: datetime.datetime):
        """Get price at a specific time."""
        timestamp = timestamp.replace(minute=0, second=0, microsecond=0)
        for consumption in self._month_consumption:
            if dt_util.as_local(consumption.timestamp) == dt_util.as_local(timestamp):
                return consumption.price
        return None

    async def _async_update_data(self):
        """Update data via API."""
        now = dt_util.now(dt_util.DEFAULT_TIME_ZONE)

        async def _update(_data, _func):
            try:
                self._update_functions[_func] = await _func(_data, now)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Error fetching Tibber data")
                self._update_functions[_func] = now + datetime.timedelta(minutes=2)

        data = {} if self.data is None else self.data
        tasks = []
        for func, next_update in self._update_functions.copy().items():
            _LOGGER.info("Updating Tibber data %s %s", func, next_update)
            if now >= next_update:
                tasks.append(_update(data, func))
        await asyncio.gather(*tasks)
        data["token"] = self._token
        self.hass.data[DOMAIN][self.tibber_home.home_id] = data
        return data

    async def _get_data_tibber(self, data, now):
        """Update data via Tibber API."""
        if self._token is None:
            self._token = await get_tibber_token(
                self._session, self.email, self._password
            )
            if self._token is None:
                return now + datetime.timedelta(minutes=2)

        try:
            _data = await get_tibber_data(self._session, self._token)
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Error fetching Tibber data")
            self._token = None
            return now + datetime.timedelta(minutes=2)

        for home in _data["data"]["me"]["homes"]:
            if home["id"] != self.tibber_home.home_id:
                continue
            data["grid_price"] = {}
            prices_tomorrow_available = False
            for price_info in home["subscription"]["priceRating"]["hourly"]["entries"]:
                dt_time = dt_util.parse_datetime(price_info["time"])
                if dt_time.date() == now.date() + datetime.timedelta(days=1):
                    prices_tomorrow_available = True
                data["grid_price"][dt_time] = price_info["gridPrice"]

            # Add all hourly entries to data
            data["hourly_prices"] = home["subscription"]["priceRating"]["hourly"][
                "entries"
            ]
        if now.hour < 13:
            return now.replace(
                hour=13, minute=0, second=0, microsecond=0
            ) + datetime.timedelta(seconds=randrange(60 * 3))
        if not prices_tomorrow_available:
            return now + datetime.timedelta(seconds=randrange(60 * 3))

        return (
            now.replace(hour=13, minute=0, second=0, microsecond=0)
            + datetime.timedelta(days=1)
            + datetime.timedelta(seconds=randrange(60 * 3))
        )

    async def _get_offline_evs_data_tibber(self, data, now):
        """Update offline ev data via Tibber API."""
        if self._token is None:
            self._token = await get_tibber_token(
                self._session, self.email, self._password
            )
            if self._token is None:
                return now + datetime.timedelta(minutes=2)

        try:
            self._offline_evs = await get_tibber_offline_evs_data(
                self._session, self._token
            )
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Error fetching Tibber offline ev data")
            self._token = None
            return now + datetime.timedelta(minutes=2)

        if not self._offline_evs:
            return now + datetime.timedelta(hours=2)

        for ev_device in self._offline_evs:
            if "batteryLevel" in ev_device:
                data[f"offline_ev_{ev_device['brandAndModel']}_soc"] = ev_device[
                    "batteryLevel"
                ]
        return now + datetime.timedelta(minutes=30)

    async def _get_charger_data_tibber(self, data, now):
        """Update charger data via Tibber API."""
        # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        if self._token is None:
            self._token = await get_tibber_token(
                self._session, self.email, self._password
            )
            if self._token is None:
                return now + datetime.timedelta(minutes=2)

        try:
            self._chargers = await get_tibber_chargers(
                self._session, self._token, self.tibber_home.home_id
            )
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Error fetching Tibber charger data")
            self._token = None
            return now + datetime.timedelta(minutes=2)

        if not self._chargers:
            return now + datetime.timedelta(hours=2)

        for charger in self._chargers:
            charger_data = await get_tibber_chargers_data(
                self._session,
                self._token,
                self.tibber_home.home_id,
                charger,
            )
            charging_cost_day = 0
            charging_consumption_day = 0
            charging_cost_month = 0
            charging_consumption_month = 0
            for _hour in charger_data["charger_consumption"]:
                _cost = _hour.get("energyCost")
                _cons = _hour.get("consumption")
                date = dt_util.parse_datetime(_hour.get("from"))
                if not (date.month == now.month and date.year == now.year):
                    continue
                if _cost is not None:
                    charging_cost_month += _cost
                    if date.date() == now.date():
                        charging_cost_day += _cost
                if _cons is not None:
                    charging_consumption_month += _cons
                    if date.date() == now.date():
                        charging_consumption_day += _cons
            data[f"charger_{charger}_cost_day"] = charging_cost_day
            data[f"charger_{charger}_cost_month"] = charging_cost_month
            data[f"charger_{charger}_consumption_day"] = charging_consumption_day
            data[f"charger_{charger}_consumption_month"] = charging_consumption_month
            data[f"charger_{charger}_is_charging"] = charger_data["meta_data"]["state"][
                "isCharging"
            ]
            for setting in charger_data["meta_data"]["settingsScreen"]["settings"]:
                key = setting["key"]
                val = setting["value"]
                if key == "schedule.isEnabled":
                    data[f"charger_{charger}_sc_enabled"] = val.lower() == "on"
                elif key == "departureTimes.sunday":
                    data[f"charger_{charger}_sunday_departure_time"] = val
                elif key == "departureTimes.monday":
                    data[f"charger_{charger}_monday_departure_time"] = val
                elif key == "departureTimes.tuesday":
                    data[f"charger_{charger}_tuesday_departure_time"] = val
                elif key == "departureTimes.wednesday":
                    data[f"charger_{charger}_wednesday_departure_time"] = val
                elif key == "departureTimes.thursday":
                    data[f"charger_{charger}_thursday_departure_time"] = val
                elif key == "departureTimes.friday":
                    data[f"charger_{charger}_friday_departure_time"] = val
                elif key == "departureTimes.saturday":
                    data[f"charger_{charger}_saturday_departure_time"] = val
                elif key == "maxCircuitPower":
                    data[f"charger_{charger}_max_circuit_power"] = val
                elif key == "maxCurrentCharger":
                    data[f"charger_{charger}_max_current_charger"] = val

            self.charger_name[charger] = _name = charger_data["meta_data"]["name"]
            data[f"charger_{charger}_consumption_month"] = charging_consumption_month
            data[f"charger_{charger}_cost_day_name"] = f"{_name} cost day"
            data[f"charger_{charger}_cost_month_name"] = f"{_name} cost month"
            data[f"charger_{charger}_consumption_day_name"] = f"{_name} consumption day"
            data[
                f"charger_{charger}_consumption_month_name"
            ] = f"{_name} consumption month"
            data[
                f"charger_{charger}_max_current_charger_name"
            ] = f"{_name} max current charger"
            data[
                f"charger_{charger}_max_circuit_power_name"
            ] = f"{_name} max circuit power"
        return now + datetime.timedelta(minutes=15)

    async def _get_production_data(self, data, now):
        """Get production data from Tibber."""
        # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        prod_data = await get_historic_production_data(
            self.tibber_home, self.hass.data["tibber"]
        )

        production_yesterday_available = False
        production_prev_hour_available = False
        production_profit_month = 0
        production_profit_day = 0

        for _hour in prod_data:
            _profit = _hour.get("profit")
            date = dt_util.parse_datetime(_hour.get("from"))
            if not (date.month == now.month and date.year == now.year):
                continue
            if _profit is None:
                continue
            if date.date() == now.date() - datetime.timedelta(days=1):
                production_yesterday_available = True
            if date == now - datetime.timedelta(hours=1):
                production_prev_hour_available = True
            production_profit_month += _profit
            if date.date() == now.date():
                production_profit_day += _profit

        if self.tibber_home.has_real_time_consumption:
            if production_prev_hour_available:
                next_update = (now + datetime.timedelta(hours=1)).replace(
                    minute=2, second=0, microsecond=0
                )
            else:
                next_update = now + datetime.timedelta(minutes=2)
        elif production_yesterday_available:
            next_update = (now + datetime.timedelta(days=1)).replace(
                hour=3, minute=0, second=0, microsecond=0
            )
        else:
            next_update = now + datetime.timedelta(minutes=15)
        data["production_profit_month"] = production_profit_month
        data["production_profit_day"] = production_profit_day
        return next_update

    async def _get_data(self, data, now):
        """Get data from Tibber."""
        # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        cons_data = await get_historic_data(self.tibber_home, self.hass.data["tibber"])

        consumption_yesterday_available = False
        consumption_prev_hour_available = False
        month_consumption = set()
        max_month = []

        for _hour in cons_data:
            _cons = _hour.get("consumption")
            date = dt_util.parse_datetime(_hour.get("from"))
            if not (date.month == now.month and date.year == now.year):
                continue
            if _cons is not None:
                if date.date() == now.date() - datetime.timedelta(days=1):
                    consumption_yesterday_available = True
                if date == now - datetime.timedelta(hours=1):
                    consumption_prev_hour_available = True
            cons = Consumption(date, _cons, _hour.get("unitPrice"), _hour.get("cost"))
            month_consumption.add(cons)

            if cons.cons is None:
                continue
            if len(max_month) < 3 or cons > max_month[-1]:
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

        if max_month and sum(max_month) is not None:
            data["peak_consumption"] = sum(max_month) / len(max_month)
            data["peak_consumption_attrs"] = {
                "peak_consumption_dates": [x.timestamp for x in max_month],
                "peak_consumptions": [x.cons for x in max_month],
            }
        else:
            data["peak_consumption"] = None
            data["peak_consumption_attrs"] = None

        if self.tibber_home.has_real_time_consumption:
            if consumption_prev_hour_available:
                next_update = (now + datetime.timedelta(hours=1)).replace(
                    minute=2, second=0, microsecond=0
                )
            else:
                next_update = now + datetime.timedelta(minutes=2)
        elif consumption_yesterday_available:
            next_update = (now + datetime.timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        else:
            next_update = now + datetime.timedelta(minutes=15)

        await self.tibber_home.update_price_info()
        prices_tomorrow_available = False
        for key, price in self.tibber_home.price_total.items():
            date = dt_util.parse_datetime(key)
            if date.date() == now.date() + datetime.timedelta(days=1):
                prices_tomorrow_available = True
            if not (date.month == now.month and date.year == now.year):
                continue
            month_consumption.add(Consumption(date, None, price, None))

        cons_data_sorted = sorted(list(month_consumption), key=lambda x: x.timestamp)
        for _cons in cons_data_sorted:
            _LOGGER.debug("Cons: %s", _cons)

        self.hass.data[DOMAIN][
            f"month_consumption_{self.tibber_home.home_id}"
        ] = month_consumption
        self._month_consumption = month_consumption

        if prices_tomorrow_available:
            next_update = min(
                next_update,
                (now + datetime.timedelta(days=1)).replace(
                    hour=13, minute=0, second=0, microsecond=0
                ),
            )
        elif now.hour >= 13:
            next_update = min(next_update, now + datetime.timedelta(minutes=2))
        else:
            next_update = min(
                next_update,
                now.replace(hour=13, minute=0, second=0, microsecond=0),
            )

        _total_price = 0
        _n_price = 0
        total_price = 0
        n_price = 0
        total_cost = 0
        total_cost_day = 0
        total_cons = 0
        total_cons_day = 0
        total_cost_day_subsidy = 0
        total_cost_month_subsidy = 0
        for cons in month_consumption:
            _total_price += cons.price if cons.price else 0
            _n_price += 1 if cons.price else 0
            if cons.cost is None or cons.cons is None:
                continue
            total_price += cons.price if cons.price else 0
            n_price += 1 if cons.price else 0
            total_cost += cons.cost
            total_cons += cons.cons
            total_cost_month_subsidy += (
                cons.cost - calculate_subsidy(cons.price) * cons.cons
            )
            if cons.day == now.date():
                total_cost_day += cons.cost
                total_cons_day += cons.cons
                total_cost_day_subsidy += (
                    cons.cost - calculate_subsidy(cons.price) * cons.cons
                )
        data["monthly_avg_price"] = total_price / n_price if n_price > 0 else None
        data["customer_avg_price"] = total_cost / total_cons if total_cons > 0 else None

        data["daily_cost_with_subsidy"] = total_cost_day_subsidy
        data["monthly_cost_with_subsidy"] = total_cost_month_subsidy

        yearly_cost = 0
        yearly_cons = 0
        for _hour in cons_data:
            date = dt_util.parse_datetime(_hour.get("from"))
            if not date.year == now.year:
                continue
            if _hour.get("consumption") is not None:
                yearly_cons += _hour["consumption"]
            if _hour.get("cost") is not None:
                yearly_cost += _hour["cost"]
        data["yearly_cost"] = yearly_cost
        data["yearly_cons"] = yearly_cons

        month_cons = 0
        month_cons_ts = []
        for _hour in cons_data:
            date = dt_util.parse_datetime(_hour.get("from"))
            if not (date.year == now.year and date.month == now.month):
                continue
            if _hour.get("consumption") is not None:
                month_cons += _hour["consumption"]
                month_cons_ts.append(date)
        data["month_cons"] = month_cons
        prev_year_month_cons = 0
        for _hour in cons_data:
            if _hour.get("consumption") is None:
                continue
            date = dt_util.parse_datetime(_hour.get("from"))
            _date = date + datetime.timedelta(days=365)
            if _date in month_cons_ts:
                prev_year_month_cons += _hour["consumption"]

        data["prev_year_month_cons"] = prev_year_month_cons
        data["compare_cons"] = month_cons - prev_year_month_cons

        return next_update

    @property
    def offline_ev_entity_descriptions(self):
        """Return the entity descriptions for the offline ev."""
        return [
            SensorEntityDescription(
                key=f"offline_ev_{ev_dev['brandAndModel']}_soc",
                name=f"{ev_dev['brandAndModel']} soc",
                native_unit_of_measurement=PERCENTAGE,
                state_class=SensorStateClass.MEASUREMENT,
            )
            for ev_dev in self._offline_evs
        ]

    @property
    def subsidy(self):
        """Get subsidy."""
        price = self.get_price_at(dt_util.now())
        return calculate_subsidy(price)

    @property
    def chargers(self):
        """Return the chargers."""
        return self._chargers

    @property
    def chargers_entity_descriptions(self):
        """Return the entity descriptions for the chargers."""
        entity_descriptions = []
        for charger in self._chargers:
            entity_descriptions.append(
                SensorEntityDescription(
                    key=f"charger_{charger}_cost_day",
                    name="Charger cost day",
                    device_class=SensorDeviceClass.MONETARY,
                    state_class=SensorStateClass.MEASUREMENT,
                )
            )
            entity_descriptions.append(
                SensorEntityDescription(
                    key=f"charger_{charger}_cost_month",
                    name="Charger cost month",
                    device_class=SensorDeviceClass.MONETARY,
                    state_class=SensorStateClass.MEASUREMENT,
                )
            )
            entity_descriptions.append(
                SensorEntityDescription(
                    key=f"charger_{charger}_consumption_day",
                    name="Charger consumption day",
                    device_class=SensorDeviceClass.ENERGY,
                    native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                )
            )
            entity_descriptions.append(
                SensorEntityDescription(
                    key=f"charger_{charger}_consumption_month",
                    name="Charger consumption month",
                    device_class=SensorDeviceClass.ENERGY,
                    native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                )
            )
            entity_descriptions.append(
                SensorEntityDescription(
                    key=f"charger_{charger}_max_circuit_power",
                    name="Max circuit power",
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                )
            )
            entity_descriptions.append(
                SensorEntityDescription(
                    key=f"charger_{charger}_max_current_charger",
                    name="Max current power",
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                )
            )
        return entity_descriptions


def calculate_subsidy(price):
    """Calculate subsidy. Norway."""
    vat_factor = 1.25
    return max(0, 0.9 * (price - 0.73 * vat_factor))
