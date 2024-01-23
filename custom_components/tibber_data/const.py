"""constants for Tibber integration."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import Platform, UnitOfEnergy

DOMAIN = "tibber_data"
PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]

SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="peak_consumption",
        name="Average of 3 highest hourly consumption",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
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
        key="subsidy",
        name="Subsidy",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="current_price_with_subsidy",
        name="Price with subsidy",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="daily_cost_with_subsidy",
        name="Daily cost with subsidy",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="yearly_cost",
        name="Yearly cost",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="yearly_cons",
        name="Yearly consumption",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    ),
    SensorEntityDescription(
        key="compare_cons",
        name="Monthly consumption compared to last year",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    ),
    SensorEntityDescription(
        key="monthly_cost_with_subsidy",
        name="Monthly cost with subsidy",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="production_profit_day",
        name="Daily production profit",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="production_profit_month",
        name="Monthly production profit",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
)
TIBBER_APP_SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="total_price_with_subsidy",
        name="Total price with subsidy and grid price",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="grid_price",
        name="Grid price",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="energy_price",
        name="Energy price",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="total_price",
        name="Total price",
        state_class=SensorStateClass.MEASUREMENT,
    ),
)
