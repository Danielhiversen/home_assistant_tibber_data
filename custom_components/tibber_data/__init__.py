"""Tibber data"""
import asyncio
import logging
from typing import cast

import tibber
from homeassistant.helpers import discovery

from .const import DOMAIN, PLATFORMS
from .data_coordinator import TibberDataCoordinator

DEPENDENCIES = ["tibber"]

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass, config):
    """Setup component."""

    hass.data[DOMAIN] = {}
    for home in hass.data["tibber"].get_homes(only_active=True):
        home = cast(tibber.TibberHome, home)
        if not home.info:
            for k in range(20):
                try:
                    await home.update_info()
                except Exception:  # pylint: disable=broad-exception-caught
                    _LOGGER.error("Error", exc_info=True)
                    if k == 19:
                        raise
                    await asyncio.sleep(min(60, 2**k))
                else:
                    break

        coordinator = TibberDataCoordinator(
            hass, home, config[DOMAIN].get("email"), config[DOMAIN].get("password")
        )
        await coordinator.async_request_refresh()

    hass.data[DOMAIN]["coordinator"] = coordinator

    for component in PLATFORMS:
        hass.async_create_task(
            discovery.async_load_platform(
                hass, component, DOMAIN, config[DOMAIN], config
            )
        )

    return True
