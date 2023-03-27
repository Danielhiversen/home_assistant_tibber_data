"""constants for Tibber integration."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import ENERGY_KILO_WATT_HOUR

DOMAIN = "tibber_data"

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
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
    ),
    SensorEntityDescription(
        key="customer_avg_price",
        name="Monthly avg customer price",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
    ),
    SensorEntityDescription(
        key="est_subsidy",
        name="Estimated subsidy",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
    ),
    SensorEntityDescription(
        key="est_current_price_with_subsidy",
        name="Estimated price with subsidy",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
    ),
    SensorEntityDescription(
        key="daily_cost_with_subsidy",
        name="Daily cost with subsidy",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
    ),
    SensorEntityDescription(
        key="yearly_cost",
        name="Yearly cost",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
    ),
    SensorEntityDescription(
        key="yearly_cons",
        name="Yearly consumption",
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
    ),
    SensorEntityDescription(
        key="compare_cons",
        name="Monthly consumption compared to last year",
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
    ),
    SensorEntityDescription(
        key="monthly_cost_with_subsidy",
        name="Monthly cost with subsidy",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
    ),
    SensorEntityDescription(
        key="production_profit_day",
        name="Daily production profit",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
    ),
    SensorEntityDescription(
        key="production_profit_month",
        name="Monthly production profit",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
    ),
)
TIBBER_APP_SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="total_price_with_subsidy",
        name="Estimated total price with subsidy and grid price",
        state_class=SensorStateClass.TOTAL,
    ),
    SensorEntityDescription(
        key="grid_price",
        name="Grid price",
        state_class=SensorStateClass.TOTAL,
    ),
    SensorEntityDescription(
        key="energy_price",
        name="Energy price",
        state_class=SensorStateClass.TOTAL,
    ),
    SensorEntityDescription(
        key="total_price",
        name="Total price",
        state_class=SensorStateClass.TOTAL,
    ),
)
