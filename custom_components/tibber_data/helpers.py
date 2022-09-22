"""Helpers for the Tibber integration."""
import base64
import datetime
import json
import logging

import tibber

_LOGGER = logging.getLogger(__name__)


async def get_historic_data(
    tibber_home: tibber.TibberHome, tibber_controller: tibber.Tibber
):
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
        base64.b64encode(datetime.datetime.now().isoformat().encode("ascii")).decode(),
    )

    if not (data := await tibber_controller.execute(query)):
        _LOGGER.error("Could not find the data.")
        return None
    data = data["viewer"]["home"]["consumption"]
    if data is None:
        return None
    return data["nodes"]


async def get_historic_production_data(
    tibber_home: tibber.TibberHome, tibber_controller: tibber.Tibber
):
    """Get historic data."""
    # pylint: disable=consider-using-f-string
    query = """
            {{
              viewer {{
                home(id: "{0}") {{
                  production(resolution: HOURLY, last: 744, before:"{1}") {{
                    nodes {{
                        from
                        profit
                    }}
                  }}
                }}
              }}
            }}
      """.format(
        tibber_home.home_id,
        base64.b64encode(datetime.datetime.now().isoformat().encode("ascii")).decode(),
    )

    if not (data := await tibber_controller.execute(query)):
        _LOGGER.error("Could not find the data.")
        return None
    data = data["viewer"]["home"]["production"]
    if data is None:
        return None
    return data["nodes"]


async def get_tibber_token(session, email: str, password: str):
    """Login to tibber."""
    post_args = {
        "headers": {
            "content-type": "application/json",
        },
        "data": json.dumps({"email": email, "password": password}),
    }
    resp = await session.post(
        "https://app.tibber.com/v1/login.credentials", **post_args
    )
    res = await resp.json()
    return res.get("token")


async def get_tibber_data(session, token: str):
    """Get tibber data."""
    post_args = {
        "headers": {"content-type": "application/json", "cookie": f"token={token}"},
        "data": json.dumps(
            {
                "variables": {},
                "query": "{\n  me {\n    homes {\n      id\n      address {\n"
                "        addressText\n      }\n      subscription {\n"
                "        priceRating {\n          hourly {\n"
                "            entries {\n              time\n"
                "              gridPrice\n            }\n"
                "          }\n        }\n      }\n    }\n  }\n}\n",
            }
        ),
    }
    resp = await session.post("https://app.tibber.com/v4/gql", **post_args)
    return await resp.json()
