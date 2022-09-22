from homeassistant.components.sensor import SensorEntityDescription, SensorStateClass, SensorDeviceClass
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
    SensorEntityDescription(
        key="daily_cost_with_subsidy",
        name="Daily cost with subsidy",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
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
    )
)
TIBBER_APP_SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="total_price_with_subsidy",
        name="Estimated total price with subsidy and grid price",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="grid_price",
        name="Grid price",
        state_class=SensorStateClass.MEASUREMENT,
    ),
)
