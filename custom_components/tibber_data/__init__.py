"""Tibber custom"""
import logging

from homeassistant.const import EVENT_HOMEASSISTANT_START
from homeassistant.helpers import discovery

from .const import DOMAIN

DEPENDENCIES = ["tibber"]

_LOGGER = logging.getLogger(__name__)


def setup(hass, config):
    """Setup component."""

    def ha_started(_):
        discovery.load_platform(hass, "sensor", DOMAIN, config[DOMAIN], config)

    hass.bus.listen_once(EVENT_HOMEASSISTANT_START, ha_started)

    return True
