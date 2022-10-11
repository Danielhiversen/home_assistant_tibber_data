"""Data coordinator for Tibber."""
import datetime
import logging
from typing import List, Set
from random import randrange

import tibber
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import ENERGY_KILO_WATT_HOUR
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .consumption_data import Consumption
from .helpers import (
    get_historic_data,
    get_historic_production_data,
    get_tibber_chargers,
    get_tibber_chargers_data,
    get_tibber_data,
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
        self.email = email
        self._password = password
        self._token = None
        self._chargers: List[str] = []
        self._month_consumption: Set[Consumption] = set()

        _next_update = dt_util.now() - datetime.timedelta(minutes=1)
        self._update_functions = {
            self._get_data: _next_update,
        }
        if self._password:
            self._update_functions[self._get_data_tibber] = _next_update
            self._update_functions[self._get_charger_data_tibber] = _next_update
        if self.tibber_home.has_production:
            self._update_functions[self._get_production_data] = _next_update

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
        data = {} if self.data is None else self.data
        for func, next_update in self._update_functions.copy().items():
            _LOGGER.debug("Updating Tibber data %s %s", func, next_update)
            if now >= next_update:
                try:
                    self._update_functions[func] = await func(data, now)
                except Exception:  # pylint: disable=broad-except
                    _LOGGER.exception("Error fetching Tibber data")
                    self._update_functions[func] = now + datetime.timedelta(minutes=2)
        return data

    async def _get_data_tibber(self, data, now):
        """Update data via Tibber API."""
        session = async_get_clientsession(self.hass)
        if self._token is None:
            self._token = await get_tibber_token(session, self.email, self._password)
            if self._token is None:
                return now + datetime.timedelta(minutes=2)

        try:
            _data = await get_tibber_data(session, self._token)
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Error fetching Tibber data")
            self._token = None
            return now + datetime.timedelta(minutes=2)

        for home in _data["data"]["me"]["homes"]:
            if home["id"] != self.tibber_home.home_id:
                continue
            data["grid_price"] = {}
            for price_info in home["subscription"]["priceRating"]["hourly"]["entries"]:
                data["grid_price"][
                    dt_util.parse_datetime(price_info["time"])
                ] = price_info["gridPrice"]
            # Add all hourly entries to data
            data["hourly_prices"] = home["subscription"]["priceRating"]["hourly"][
                "entries"
            ]

        # make update happen between 13.15 and 13.30
        if now.hour < 13 and now.minute < 15:
            return now.replace(
                hour=13, minute=15, second=0, microsecond=0
            ) + datetime.timedelta(seconds=randrange(60 * 15))
        return (
            now.replace(hour=13, minute=15, second=0, microsecond=0)
            + datetime.timedelta(days=1)
            + datetime.timedelta(seconds=randrange(60 * 15))
        )

    async def _get_charger_data_tibber(self, data, now):
        """Update charger data via Tibber API."""
        session = async_get_clientsession(self.hass)
        if self._token is None:
            self._token = await get_tibber_token(session, self.email, self._password)
            if self._token is None:
                return now + datetime.timedelta(minutes=2)

        try:
            self._chargers = await get_tibber_chargers(
                session, self._token, self.tibber_home.home_id
            )
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Error fetching Tibber charger data")
            self._token = None
            return now + datetime.timedelta(minutes=2)

        if not self._chargers:
            return now + datetime.timedelta(hours=2)

        for charger in self._chargers:
            charger_data = await get_tibber_chargers_data(
                session,
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
            data[
                f"charger_{charger}_cost_day_name"
            ] = f"{charger_data['meta_data']['name']} cost day"
            data[
                f"charger_{charger}_cost_month_name"
            ] = f"{charger_data['meta_data']['name']} cost month"
            data[
                f"charger_{charger}_consumption_day_name"
            ] = f"{charger_data['meta_data']['name']} consumption day"
            data[
                f"charger_{charger}_consumption_month_name"
            ] = f"{charger_data['meta_data']['name']} consumption month"

        return now.replace(minute=1, second=1, microsecond=0) + datetime.timedelta(
            hours=1
        )

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
                hour=3, minute=0, second=0, microsecond=0
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
                now.replace(hour=13, minute=1, second=0, microsecond=0),
            )

        _total_price = 0
        _n_price = 0
        total_price = 0
        n_price = 0
        total_cost = 0
        total_cost_day = 0
        total_cons = 0
        total_cons_day = 0
        for cons in month_consumption:
            _total_price += cons.price if cons.price else 0
            _n_price += 1 if cons.price else 0
            if cons.cost is None or cons.cons is None:
                continue
            total_price += cons.price if cons.price else 0
            n_price += 1 if cons.price else 0
            total_cost += cons.cost
            total_cons += cons.cons
            if cons.day == now.date():
                total_cost_day += cons.cost
                total_cons_day += cons.cons
        data["monthly_avg_price"] = total_price / n_price if n_price > 0 else None
        data["est_subsidy"] = (
            (_total_price / _n_price - 0.7 * 1.25) * 0.9 if _n_price > 0 else None
        )
        data["customer_avg_price"] = total_cost / total_cons if total_cons > 0 else None

        data["daily_cost_with_subsidy"] = (
            (total_cost_day - data["est_subsidy"] * total_cons_day)
            if (data["est_subsidy"] is not None and total_cost_day is not None)
            else None
        )
        data["monthly_cost_with_subsidy"] = (
            (total_cost - data["est_subsidy"] * total_cons)
            if (data["est_subsidy"] is not None and total_cost is not None)
            else None
        )
        return next_update

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
                    native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
                )
            )
            entity_descriptions.append(
                SensorEntityDescription(
                    key=f"charger_{charger}_consumption_month",
                    name="Charger consumption month",
                    device_class=SensorDeviceClass.ENERGY,
                    native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
                )
            )
        return entity_descriptions
