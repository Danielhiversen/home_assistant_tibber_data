import logging
import base64
import datetime

import tibber

_LOGGER = logging.getLogger(__name__)


async def get_historic_data(tibber_home: tibber.TibberHome, tibber_controller: tibber.Tibber):
    """Get historic data."""
    # pylint: disable=consider-using-f-string
    query = """
            {{
              viewer {{
                home(id: "{0}") {{
                  consumption(resolution: HOURLY, last: 744, before:"{1}") {{
                    nodes {{
                      consumption
                      cost
                      from
                      unitPrice
                    }}
                  }}
                }}
              }}
            }}
      """.format(
        tibber_home.home_id,
        base64.b64encode(datetime.datetime.now().isoformat().encode('ascii')).decode(),
    )

    if not (data := await tibber_controller.execute(query)):
        _LOGGER.error("Could not find the data.")
        return None
    data = data["viewer"]["home"]["consumption"]
    if data is None:
        return None
    return data["nodes"]


async def login(tibber_controller: tibber.Tibber, password: str):
    """Login to tibber."""
    return ""
